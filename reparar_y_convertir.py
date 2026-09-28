import re
import subprocess
import sys

nota_path = r"C:\Users\USUARIO\OneDrive\Andre\THIRTH\ALGEBRA 2\Diagonalizacion\Enginevalue and enginevector\POLINOMIOS.md"

# 1. Leer el archivo
with open(nota_path, "r", encoding="utf-8") as f:
    contenido = f.read()

# 2. Limpiar rutas de Windows residuales
contenido = re.sub(r'C:\\Users\\[^\s\$\n\r]*', '', contenido)

# 3. Reemplazar caracteres Unicode por sintaxis LaTeX válida
contenido = contenido.replace('ℜ', r'\Re ').replace('ℑ', r'\Im ')

# 4. Corregir ecuaciones fragmentadas (ej. $p$ |z| = \sqrt{...})
# Unifica fragmentos donde el signo $ se cerró antes de comandos matemáticos
contenido = re.sub(r'\$p\$\s*(\\textbar|\||\\sqrt|\\overline|\\Re|\\Im|=)', r'$\1', contenido)

# 5. Reparar líneas que contienen comandos de LaTeX fuera de $...$
lineas = contenido.splitlines()
lineas_corregidas = []

para_math = [r'\sqrt', r'\overline', r'\Re', r'\Im', r'\mathbb', r'\qquad', r'\cdots', r'\begin{aligned}']

for linea in lineas:
    linea_str = linea.strip()
    # Si la línea contiene comandos matemáticos pero no tiene $, envolver la línea en modo matemático
    if any(cmd in linea_str for cmd in para_math):
        if not (linea_str.startswith('$') or linea_str.startswith('$$')):
            # Si hay texto antes del comando, meter solo la parte matemática entre $
            if r'\sqrt' in linea_str and '$' not in linea_str:
                linea = f"${linea_str}$"
            elif not linea_str.startswith('$'):
                linea = f"${linea_str}$"
    
    lineas_corregidas.append(linea)

contenido_final = "\n".join(lineas_corregidas)

# 6. Guardar cambios en UTF-8
with open(nota_path, "w", encoding="utf-8") as f:
    f.write(contenido_final)

print("--- Nota POLINOMIOS.md reparada correctamente ---")

# 7. Ejecutar la conversión a PDF
comando_conversion = [
    "py", "-3", ".\\convertir_nota.py",
    "--nota", nota_path
]

print("Compilando PDF...")
resultado = subprocess.run(comando_conversion, capture_output=True, text=True)

print(resultado.stdout)
if resultado.stderr:
    print(resultado.stderr)