import os
import pikepdf

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
else:
    print(f"Archivo localizado en: {found_path}")
    output_path = os.path.join(os.path.dirname(found_path), "VII y VIII SIMMAC_compressed.pdf")
    
    print("Comprimiendo flujos de datos y estructura PDF...")
    pdf = pikepdf.Pdf.open(found_path)
    pdf.save(output_path, compress_streams=True, linearize=True)
    pdf.close()
    
    orig_mb = os.path.getsize(found_path) / (1024 * 1024)
    comp_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[ÉXITO] Tamaño original: {orig_mb:.2f} MB | Tamaño comprimido: {comp_mb:.2f} MB")
    
    if comp_mb < 50:
        print("[LISTO] El archivo ya pesa menos de 50 MB y se podrá subir a Supabase.")
    else:
        print("[ADVERTENCIA] El archivo sigue superando los 50 MB.")
