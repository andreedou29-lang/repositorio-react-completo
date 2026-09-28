import shutil
p = r"C:\Users\USUARIO\OneDrive - Universidad Central del Ecuador\Andre\THIRTH\ECUACIONES DIFERENCIALES ORDINARIAS\Clases\Ejercicios - VARIABLES SEPARABLES.md"
t = open(p, encoding="utf-8-sig", newline="").read().replace("\r\n", "\n").replace("\r", "\n")
L = t.split("\n")
ok = all(not x.strip() for x in L[1::2])
print("lineas:", len(L), "| lineas impares vacias:", ok)
if not ok:
    raise SystemExit("NO se modifico nada")
shutil.copy(p, p + ".bak")
n = "\n".join(L[0::2]).replace("\u00a0", " ")
open(p, "w", encoding="utf-8", newline="\n").write(n)
print("reparado, lineas ahora:", n.count("\n") + 1)
