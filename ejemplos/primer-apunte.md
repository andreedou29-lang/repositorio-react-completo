# Continuidad de una transformación lineal

Este es un apunte original para comprobar el lector de Markdown y las fórmulas.

## Definición

Una aplicación $T:\mathbb{R}^2\to\mathbb{R}^2$ es continua en $p$ si

$$
\forall \varepsilon>0\;\exists\delta>0\;\forall x\in\mathbb{R}^2,
\quad \|x-p\|_2<\delta \implies \|T(x)-T(p)\|_2<\varepsilon.
$$

## Ejemplo

Sea $T(x,y)=(2x,3y)$. Para todo $(x,y)$,

$$
\|T(x,y)\|_2^2=4x^2+9y^2\leq 9(x^2+y^2).
$$

Por linealidad, $\|T(u)-T(v)\|_2\leq 3\|u-v\|_2$.
Dado $\varepsilon>0$, basta tomar $\delta=\varepsilon/3$.

> La misma estimación prueba la continuidad en todos los puntos.

| Archivo | Uso |
|---|---|
| Markdown | Lectura con fórmulas |
| LaTeX | Código fuente |
| PDF | Documento compilado |
