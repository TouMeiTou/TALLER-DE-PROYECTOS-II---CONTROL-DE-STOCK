"""
Sistema de Control de Stock - aplicacion Flask.

Pantallas (alcance version 1.0):
  - Stock:    consulta de cantidades y alertas de minimo (RF-06, RF-07).
  - Ingresos: registro de materiales comprados (RF-01).
  - Salidas:  registro de muebles vendidos (RF-02 a RF-05).

Para ejecutarla:  python app.py   y abrir http://127.0.0.1:5000 en el navegador.
"""

from flask import Flask, redirect, render_template, request, url_for

import db

app = Flask(__name__)


def leer_cantidad(texto):
    """Convierte el texto ingresado en un entero mayor a cero (RN-02, RN-06).

    Devuelve None si el valor no es valido.
    """
    texto = (texto or "").strip()
    if not texto.isdigit():  # rechaza vacios, negativos, decimales y letras
        return None
    cantidad = int(texto)
    return cantidad if cantidad > 0 else None


# Plural de cada unidad de medida, para los mensajes.
PLURALES = {"unidad": "unidades", "metro": "metros", "par": "pares"}


@app.template_filter("con_unidad")
def con_unidad(cantidad, unidad):
    """Escribe la cantidad con su unidad en singular o plural: 1 unidad, 6 unidades, 25 metros."""
    if cantidad != 1:
        unidad = PLURALES.get(unidad, unidad)
    return f"{cantidad} {unidad}"


@app.route("/")
def inicio():
    return redirect(url_for("stock"))


# ---------------------------------------------------------------- Stock

@app.route("/stock")
def stock():
    """Pantalla Stock: solo consulta, no recibe datos."""
    conexion = db.conectar()
    materiales = db.stock_actual(conexion)
    conexion.close()
    return render_template("stock.html", materiales=materiales, pantalla="stock")


# ---------------------------------------------------------------- Ingresos

@app.route("/ingresos", methods=["GET", "POST"])
def ingresos():
    """Pantalla Ingresos: suma al stock los materiales comprados (RF-01, RF-08)."""
    conexion = db.conectar()
    materiales = db.listar_materiales(conexion)
    error = None
    mensaje = None
    valores = {"material": "", "cantidad": ""}

    if request.method == "POST":
        valores = {"material": request.form.get("material", ""),
                   "cantidad": request.form.get("cantidad", "")}
        material = db.obtener_material(conexion, valores["material"])
        cantidad = leer_cantidad(valores["cantidad"])

        if material is None:
            error = "Seleccione un material."
        elif cantidad is None:
            error = "La cantidad debe ser un número entero mayor a cero."
        else:
            db.registrar_ingreso(conexion, material["codigo"], cantidad)
            conexion.close()
            # Despues de guardar se redirige a la pantalla (GET). Asi, si el usuario
            # recarga la pagina, el navegador no vuelve a enviar el ingreso y no se duplica.
            return redirect(url_for("ingresos", registrado=material["codigo"]))

    else:
        # Mensaje de confirmacion despues de registrar un ingreso.
        registrado = db.obtener_material(conexion, request.args.get("registrado", ""))
        if registrado is not None:
            mensaje = (f"Ingreso registrado. Stock actual de {registrado['nombre']}: "
                       f"{con_unidad(db.stock_de(conexion, registrado['codigo']), registrado['unidad'])}.")

    conexion.close()
    return render_template("ingresos.html", materiales=materiales, error=error,
                           mensaje=mensaje, valores=valores, pantalla="ingresos")


# ---------------------------------------------------------------- Salidas

@app.route("/salidas", methods=["GET", "POST"])
def salidas():
    """Pantalla Salidas.

    Paso 1 (Continuar): valida el codigo y la cantidad, calcula la receta x cantidad
    y verifica que alcance el stock de todos los materiales (RF-02, RF-03, RF-05, RN-01).
    Paso 2 (Confirmar): pendiente para la proxima etapa del desarrollo (RF-04, RF-07).
    """
    conexion = db.conectar()
    error = None
    detalle = None
    mueble = None
    faltantes = []
    valores = {"codigo": "", "cantidad": ""}

    if request.method == "POST":
        valores = {"codigo": request.form.get("codigo", "").strip(),
                   "cantidad": request.form.get("cantidad", "")}
        mueble = db.obtener_mueble(conexion, valores["codigo"])
        cantidad = leer_cantidad(valores["cantidad"])

        if mueble is None:
            error = "El código ingresado no existe."
        elif cantidad is None:
            error = "La cantidad debe ser un número entero mayor a cero."
        else:
            detalle = db.receta_por_cantidad(conexion, mueble["codigo"], cantidad)
            faltantes = [m for m in detalle if m["faltante"] > 0]  # RN-01

    conexion.close()
    return render_template("salidas.html", error=error, detalle=detalle, mueble=mueble,
                           faltantes=faltantes, valores=valores, pantalla="salidas")


# La base se crea (con sus datos iniciales) al iniciar la aplicacion, si no existe.
db.crear_base()

if __name__ == "__main__":
    app.run(debug=False)
