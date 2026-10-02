import os
import pymupdf

base_dir = r"C:\Users\USUARIO\Desktop\Andre\Libros"
target_filename = "VII y VIII SIMMAC.pdf"

found_path = None
for root, dirs, files in os.walk(base_dir):
    for f in files:
        if f.lower() == target_filename.lower():
            found_path = os.path.join(root, f)
            break
    if found_path:
        break

if not found_path:
    print(f"[ERROR] No se encontró '{target_filename}' dentro de {base_dir}")
    exit(1)

print(f"Archivo localizado en: {found_path}")
temp_output = found_path + ".tmp.pdf"

print("Rasterizando y comprimiendo páginas a 120 DPI (formato JPEG)... esto puede tardar un minuto.")

doc = pymupdf.open(found_path)
new_doc = pymupdf.open()

for page_idx in range(len(doc)):
    page = doc[page_idx]
    # Extraer página como imagen (DPI 120 para balancear calidad y peso)
    pix = page.get_pixmap(dpi=120)
    # Convertir a JPEG para máxima compresión
    img_bytes = pix.tobytes("jpeg")
    
    # Crear nueva página con las mismas dimensiones e insertar la imagen JPEG
    new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
    new_page.insert_image(page.rect, stream=img_bytes)

new_doc.save(temp_output, garbage=4, deflate=True)
new_doc.close()
doc.close()

orig_mb = os.path.getsize(found_path) / (1024 * 1024)
comp_mb = os.path.getsize(temp_output) / (1024 * 1024)

print(f"\nTamaño original: {orig_mb:.2f} MB")
print(f"Tamaño comprimido: {comp_mb:.2f} MB")

if comp_mb < 50:
    os.remove(found_path)
    os.rename(temp_output, found_path)
    print(f"\n[ÉXITO] Archivo comprimido con éxito.")
    print(f"[REEMPLAZADO] Se eliminó el archivo original y se guardó la versión ligera ({comp_mb:.2f} MB).")
else:
    if os.path.exists(temp_output):
        os.remove(temp_output)
    print(f"\n[ADVERTENCIA] Sigue superando los 50 MB ({comp_mb:.2f} MB).")
