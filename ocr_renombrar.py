import os
import fitz  # PyMuPDF
import json
import time
import shutil
import easyocr
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import simpledialog, messagebox

# ---------------- CONFIGURACIÓN ----------------
carpeta_entrada = r"C:\OCR\entrada"
carpeta_salida = r"C:\OCR\salida"
archivo_plantilla_principal = r"C:\OCR\plantilla_campos.json"
carpeta_plantillas_adicionales = r"C:\OCR\plantillas_adicionales"

os.makedirs(carpeta_salida, exist_ok=True)
os.makedirs(carpeta_plantillas_adicionales, exist_ok=True)

reader = easyocr.Reader(['es'], gpu=False)  # GPU True si tienes disponible

# ---------------- FUNCIONES ----------------
def mostrar_imagen_y_seleccionar_campos(cv_img):
    coordenadas = {}
    root = tk.Tk()
    root.title("Selecciona los campos")

    img_pil = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
    img_w, img_h = img_pil.size

    canvas_frame = tk.Frame(root)
    canvas_frame.pack(fill="both", expand=True)
    h_scroll = tk.Scrollbar(canvas_frame, orient="horizontal")
    h_scroll.pack(side="bottom", fill="x")
    v_scroll = tk.Scrollbar(canvas_frame, orient="vertical")
    v_scroll.pack(side="right", fill="y")

    canvas = tk.Canvas(canvas_frame, width=800, height=600,
                       xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
    canvas.pack(side="left", fill="both", expand=True)
    h_scroll.config(command=canvas.xview)
    v_scroll.config(command=canvas.yview)

    tk_img = ImageTk.PhotoImage(img_pil)
    canvas.img_ref = tk_img
    canvas.create_image(0, 0, anchor="nw", image=tk_img)
    canvas.config(scrollregion=(0, 0, img_w, img_h))

    rect = {}

    def on_button_press(event):
        rect['x1'] = int(canvas.canvasx(event.x))
        rect['y1'] = int(canvas.canvasy(event.y))
        rect['rect_id'] = canvas.create_rectangle(rect['x1'], rect['y1'],
                                                  rect['x1'], rect['y1'],
                                                  outline='red', width=2)

    def on_move_press(event):
        if 'rect_id' in rect:
            x2, y2 = int(canvas.canvasx(event.x)), int(canvas.canvasy(event.y))
            canvas.coords(rect['rect_id'], rect['x1'], rect['y1'], x2, y2)

    def agregar_campo():
        if 'rect_id' not in rect:
            messagebox.showerror("Error", "No se ha dibujado ningún recuadro.")
            return
        x1, y1, x2, y2 = canvas.coords(rect['rect_id'])
        nombre_campo = simpledialog.askstring("Campo", "Nombre del campo para este recorte:")
        if nombre_campo:
            coordenadas[nombre_campo] = [int(x1), int(y1), int(x2), int(y2)]
            rect.clear()

    def terminar_pagina():
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_button_press)
    canvas.bind("<B1-Motion>", on_move_press)

    btn_frame = tk.Frame(root)
    btn_frame.pack()
    tk.Button(btn_frame, text="Agregar campo", command=agregar_campo).pack(side="left", padx=5, pady=5)
    tk.Button(btn_frame, text="Terminar selección", command=terminar_pagina).pack(side="left", padx=5, pady=5)

    root.mainloop()
    return coordenadas, (img_w, img_h)

def extraer_texto_por_plantilla(img, plantilla):
    campos = {}
    for nombre, (x1, y1, x2, y2) in plantilla['campos'].items():
        recorte = img[int(y1):int(y2), int(x1):int(x2)]
        if recorte.size > 0:
            texto = " ".join(reader.readtext(recorte, detail=0)).strip()
        else:
            texto = ""
        campos[nombre] = texto
    return campos

def formato_coincide(img, plantilla):
    ancho, alto = img.shape[1], img.shape[0]
    if 'size' not in plantilla or 'campos' not in plantilla:
        return False
    return (ancho, alto) == tuple(plantilla['size'])

def cargar_plantillas_adicionales():
    plantillas = []
    for f in os.listdir(carpeta_plantillas_adicionales):
        if f.lower().endswith(".json"):
            path = os.path.join(carpeta_plantillas_adicionales, f)
            with open(path, "r") as archivo:
                plantillas.append(json.load(archivo))
    return plantillas

def procesar_pdf(ruta_pdf):
    global plantilla_principal, usar_plantilla_principal

    try:
        doc = fitz.open(ruta_pdf)
        pagina = doc.load_page(0)  # SOLO primera página
        pix = pagina.get_pixmap()
        img = np.array(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        doc.close()  # 🔹 cerrar documento para liberar archivo
    except Exception as e:
        print(f"Error al abrir PDF {ruta_pdf}: {e}")
        return

    plantilla_usar = None
    if usar_plantilla_principal and formato_coincide(img, plantilla_principal):
        plantilla_usar = plantilla_principal
    else:
        plantillas_adicionales = cargar_plantillas_adicionales()
        for pl in plantillas_adicionales:
            if formato_coincide(img, pl):
                plantilla_usar = pl
                break

    if plantilla_usar is None:
        print("\nFormato desconocido. Selecciona los campos para nueva plantilla.")
        campos, size = mostrar_imagen_y_seleccionar_campos(img)
        plantilla_usar = {'size': size, 'campos': campos}
        num = len(os.listdir(carpeta_plantillas_adicionales)) + 1
        ruta_nueva_plantilla = os.path.join(carpeta_plantillas_adicionales, f"plantilla_{num}.json")
        with open(ruta_nueva_plantilla, "w") as f:
            json.dump(plantilla_usar, f, indent=4)
        print(f"✅ Plantilla adicional guardada: {ruta_nueva_plantilla}")

    campos_pdf = extraer_texto_por_plantilla(img, plantilla_usar)
    nombre_campos = "_".join([v.replace(" ", "_") for v in campos_pdf.values()])
    if not nombre_campos:
        nombre_campos = "SIN-CAMPOS"

    nuevo_nombre = f"{nombre_campos}.pdf"
    ruta_nueva = os.path.join(carpeta_salida, nuevo_nombre)

    # Esperar un poco antes de mover
    time.sleep(0.5)
    try:
        shutil.move(ruta_pdf, ruta_nueva)
        print(f"✅ Procesado: {nuevo_nombre}")
    except Exception as e:
        print(f"No se pudo mover el archivo {ruta_pdf}: {e}")

# ---------------- VIGILANCIA DE CARPETA ----------------
class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".pdf"):
            time.sleep(1)
            procesar_pdf(event.src_path)

if __name__ == "__main__":
    if os.path.exists(archivo_plantilla_principal):
        with open(archivo_plantilla_principal, "r") as f:
            plantilla_principal = json.load(f)
        usar_plantilla_principal = True
    else:
        plantilla_principal = None
        usar_plantilla_principal = False

    event_handler = Handler()
    observer = Observer()
    observer.schedule(event_handler, carpeta_entrada, recursive=False)
    observer.start()

    print(f"👀 Monitoreando {carpeta_entrada}... (Ctrl+C para detener)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
