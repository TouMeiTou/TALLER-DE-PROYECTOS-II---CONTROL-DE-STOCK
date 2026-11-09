"""
Acceso a la base de datos SQLite.

Toda la informacion se guarda en un unico archivo (stock.db), que se puede
copiar como copia de seguridad (RNF-04 y RNF-06).
"""

import os
import sqlite3
from datetime import datetime

import datos_iniciales

RUTA_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock.db")


def conectar(ruta=None):
    """Abre una conexion a la base y activa las claves foraneas."""
    conexion = sqlite3.connect(ruta or RUTA_DB)
    conexion.row_factory = sqlite3.Row  # permite leer columnas por nombre
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def crear_base(ruta=None):
    """Crea las 4 tablas y carga los datos iniciales, si la base todavia no existe."""
    conexion = conectar(ruta)
    conexion.executescript(
        """
        CREATE TABLE IF NOT EXISTS materiales (
            codigo        TEXT PRIMARY KEY,           -- RN-03: codigo unico
            nombre        TEXT NOT NULL,
            categoria     TEXT NOT NULL,
            unidad        TEXT NOT NULL,              -- unidad, metro o par
            stock_minimo  INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS muebles (
            codigo       TEXT PRIMARY KEY,            -- formato color.modelo (1.1 a 4.4)
            modelo       INTEGER NOT NULL,
            color        TEXT NOT NULL,
            descripcion  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS recetas (
            codigo_mueble    TEXT NOT NULL REFERENCES muebles(codigo),
            codigo_material  TEXT NOT NULL REFERENCES materiales(codigo),
            cantidad         INTEGER NOT NULL CHECK (cantidad > 0),
            PRIMARY KEY (codigo_mueble, codigo_material)
        );

        CREATE TABLE IF NOT EXISTS movimientos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora       TEXT NOT NULL,                              -- RF-08
            tipo             TEXT NOT NULL CHECK (tipo IN ('INGRESO', 'SALIDA')),
            codigo_material  TEXT NOT NULL REFERENCES materiales(codigo),
            cantidad         INTEGER NOT NULL CHECK (cantidad > 0),      -- RN-02 y RN-06
            codigo_mueble    TEXT REFERENCES muebles(codigo)             -- vacio en ingresos
        );
        """
    )

    # Los datos iniciales se cargan una sola vez (si la tabla materiales esta vacia).
    vacia = conexion.execute("SELECT COUNT(*) FROM materiales").fetchone()[0] == 0
    if vacia:
        conexion.executemany(
            "INSERT INTO materiales (codigo, nombre, categoria, unidad, stock_minimo) VALUES (?, ?, ?, ?, ?)",
            [m + (datos_iniciales.STOCK_MINIMO,) for m in datos_iniciales.MATERIALES],
        )
        conexion.executemany(
            "INSERT INTO muebles (codigo, modelo, color, descripcion) VALUES (?, ?, ?, ?)",
            datos_iniciales.generar_muebles(),
        )
        conexion.executemany(
            "INSERT INTO recetas (codigo_mueble, codigo_material, cantidad) VALUES (?, ?, ?)",
            datos_iniciales.generar_recetas(),
        )
        conexion.commit()
    conexion.close()


def _ahora():
    """Fecha y hora actual, asignada por el sistema (RF-08)."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- Consultas

def listar_materiales(conexion):
    """Devuelve los materiales ordenados por codigo (para la lista desplegable de Ingresos)."""
    return conexion.execute("SELECT * FROM materiales ORDER BY codigo").fetchall()


def obtener_material(conexion, codigo):
    return conexion.execute("SELECT * FROM materiales WHERE codigo = ?", (codigo,)).fetchone()


def obtener_mueble(conexion, codigo):
    return conexion.execute("SELECT * FROM muebles WHERE codigo = ?", (codigo,)).fetchone()


def stock_de(conexion, codigo_material):
    """Stock de un material = suma de ingresos - suma de salidas (no se guarda, se calcula)."""
    fila = conexion.execute(
        """
        SELECT COALESCE(SUM(CASE WHEN tipo = 'INGRESO' THEN cantidad ELSE -cantidad END), 0)
        FROM movimientos WHERE codigo_material = ?
        """,
        (codigo_material,),
    ).fetchone()
    return fila[0]


def stock_actual(conexion):
    """Stock de todos los materiales, con su unidad, minimo y si esta en alerta (RF-06, RF-07, RN-04)."""
    filas = conexion.execute(
        """
        SELECT m.codigo, m.nombre, m.unidad, m.stock_minimo,
               COALESCE(SUM(CASE WHEN mov.tipo = 'INGRESO' THEN mov.cantidad
                                 WHEN mov.tipo = 'SALIDA'  THEN -mov.cantidad END), 0) AS stock
        FROM materiales m
        LEFT JOIN movimientos mov ON mov.codigo_material = m.codigo
        GROUP BY m.codigo
        ORDER BY m.codigo
        """
    ).fetchall()
    resultado = []
    for fila in filas:
        resultado.append({
            "codigo": fila["codigo"],
            "nombre": fila["nombre"],
            "unidad": fila["unidad"],
            "minimo": fila["stock_minimo"],
            "stock": fila["stock"],
            "alerta": fila["stock"] <= fila["stock_minimo"],  # RN-04: en o por debajo del minimo
        })
    return resultado


def receta_por_cantidad(conexion, codigo_mueble, cantidad):
    """Materiales a descontar: receta del mueble x cantidad (RN-07), con el stock disponible de cada uno."""
    filas = conexion.execute(
        """
        SELECT r.codigo_material, m.nombre, m.unidad, r.cantidad
        FROM recetas r JOIN materiales m ON m.codigo = r.codigo_material
        WHERE r.codigo_mueble = ?
        ORDER BY r.codigo_material
        """,
        (codigo_mueble,),
    ).fetchall()
    detalle = []
    for fila in filas:
        necesario = fila["cantidad"] * cantidad
        disponible = stock_de(conexion, fila["codigo_material"])
        detalle.append({
            "codigo": fila["codigo_material"],
            "nombre": fila["nombre"],
            "unidad": fila["unidad"],
            "necesario": necesario,
            "disponible": disponible,
            "faltante": max(necesario - disponible, 0),
        })
    return detalle


# ---------------------------------------------------------------- Registros

def registrar_ingreso(conexion, codigo_material, cantidad):
    """Registra la compra de un material (RF-01). Devuelve el stock actualizado."""
    conexion.execute(
        "INSERT INTO movimientos (fecha_hora, tipo, codigo_material, cantidad) VALUES (?, 'INGRESO', ?, ?)",
        (_ahora(), codigo_material, cantidad),
    )
    conexion.commit()
    return stock_de(conexion, codigo_material)
