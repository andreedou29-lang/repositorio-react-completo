import os
try:
    import pikepdf
    print("Comprimiendo VII y VIII SIMMAC.pdf...")
    input_path = r"C:\Users\USUARIO\Desktop\Andre\Libros\VII y VIII SIMMAC.pdf"
    output_path = r"C:\Users\USUARIO\Desktop\Andre\Libros\VII y VIII SIMMAC_compressed.pdf"
    
    if os.path.exists(input_path):
        pdf = pikepdf.Pdf.open(input_path)
        pdf.save(output_path, linearize=True)
        pdf.close()
        
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"[ÉXITO] Archivo comprimido generado: {size_mb:.2f} MB")
    else:
        print("No se encontró el archivo original.")
except Exception as e:
    print(f"Instala pikepdf o usa una herramienta web/Ghostscript para reducir el PDF a < 50MB. Error: {e}")
