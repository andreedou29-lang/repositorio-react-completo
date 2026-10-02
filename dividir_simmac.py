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
    print(f"[ERROR] No se encontró '{target_filename}'")
    exit(1)

print("Dividiendo el documento en dos partes para conservar calidad al 100%...")

doc = pymupdf.open(found_path)
total_pages = len(doc)
mitad = total_pages // 2

# Generar Parte 1
doc1 = pymupdf.open()
doc1.insert_pdf(doc, from_page=0, to_page=mitad-1)
path1 = found_path.replace(".pdf", " - Parte 1.pdf")
doc1.save(path1, garbage=3, deflate=True)
doc1.close()

# Generar Parte 2
doc2 = pymupdf.open()
doc2.insert_pdf(doc, from_page=mitad, to_page=total_pages-1)
path2 = found_path.replace(".pdf", " - Parte 2.pdf")
doc2.save(path2, garbage=3, deflate=True)
doc2.close()

doc.close()

mb1 = os.path.getsize(path1) / (1024 * 1024)
mb2 = os.path.getsize(path2) / (1024 * 1024)

print(f"\n[ÉXITO] Parte 1 generada: {mb1:.2f} MB")
print(f"[ÉXITO] Parte 2 generada: {mb2:.2f} MB")

if mb1 < 50 and mb2 < 50:
    os.remove(found_path)
    print("\n[LISTO] Archivo original eliminado. Las dos partes están listas para la sincronización con Supabase.")
else:
    print("\n[ADVERTENCIA] Alguna parte sigue superando el límite de 50 MB.")
