"""
Datos iniciales del sistema (materiales, muebles y recetas).

Estos datos son fijos: segun el alcance de la version 1.0, no hay pantallas
para modificarlos. Si cambian, se edita este archivo y se genera una nueva
version del sistema.
"""

# Stock minimo igual para todos los materiales (definido en el analisis y diseno).
# 35 es la mayor cantidad de un material en una receta (35 tornillos del modelo 2).
STOCK_MINIMO = 35

# Colores de los muebles: el numero es la primera parte del codigo color.modelo.
COLORES = {
    1: "blanco",
    2: "negro",
    3: "grafito",
    4: "gris",
}

# Placa de melamina que corresponde a cada color.
PLACA_POR_COLOR = {
    1: "PLA-001",
    2: "PLA-002",
    3: "PLA-003",
    4: "PLA-004",
}

# Materiales: (codigo, nombre, categoria, unidad)
MATERIALES = [
    ("PLA-001", "Placa melamina blanca 2,70 x 1,80 m", "Placas", "unidad"),
    ("PLA-002", "Placa melamina negra 2,70 x 1,80 m", "Placas", "unidad"),
    ("PLA-003", "Placa melamina grafito 2,70 x 1,80 m", "Placas", "unidad"),
    ("PLA-004", "Placa melamina gris 2,70 x 1,80 m", "Placas", "unidad"),
    ("FIL-001", "Filo de aluminio", "Filo", "metro"),
    ("FON-001", "Fondo 3 mm", "Fondos", "unidad"),
    ("COR-001", "Corredera telescopica 50 cm", "Correderas", "par"),
    ("BIS-001", "Bisagra simil aluminio", "Bisagras", "unidad"),
    ("PAT-001", "Pata simil aluminio", "Patas", "unidad"),
    ("MAN-001", "Manija simil aluminio", "Manijas", "unidad"),
    ("CLA-001", "Clavo 0,9 x 25", "Clavos", "unidad"),
    ("TOR-001", "Tornillo 3,5 x 50", "Tornillos", "unidad"),
]

# Modelos: numero -> descripcion del mueble.
MODELOS = {
    1: "1,20 m, 2 puertas, 3 cajones",
    2: "1,80 m, 3 puertas, 3 cajones",
    3: "Cajonera 0,80 m, 3 cajones",
    4: "1,60 m, 4 puertas",
}

# Recetas por modelo. "PLACA" se reemplaza por la placa del color del mueble.
# Los materiales que el modelo no usa no se incluyen.
RECETAS_POR_MODELO = {
    1: {"PLACA": 1, "FIL-001": 15, "FON-001": 1, "COR-001": 3, "BIS-001": 4,
        "PAT-001": 5, "MAN-001": 5, "CLA-001": 25, "TOR-001": 30},
    2: {"PLACA": 2, "FIL-001": 25, "FON-001": 1, "COR-001": 3, "BIS-001": 6,
        "PAT-001": 6, "MAN-001": 6, "CLA-001": 30, "TOR-001": 35},
    3: {"PLACA": 1, "FIL-001": 10, "FON-001": 1, "COR-001": 3,
        "PAT-001": 4, "MAN-001": 3, "CLA-001": 10, "TOR-001": 20},
    4: {"PLACA": 2, "FIL-001": 20, "FON-001": 1, "BIS-001": 4,
        "PAT-001": 5, "MAN-001": 4, "CLA-001": 25, "TOR-001": 20},
}


def generar_muebles():
    """Devuelve los 16 muebles (4 colores x 4 modelos) con su codigo color.modelo."""
    muebles = []
    for color, nombre_color in COLORES.items():
        for modelo, descripcion in MODELOS.items():
            codigo = f"{color}.{modelo}"
            muebles.append((codigo, modelo, nombre_color, f"Modelo {modelo} {nombre_color}: {descripcion}"))
    return muebles


def generar_recetas():
    """Devuelve las filas de la tabla recetas: una receta exacta por cada uno de los 16 codigos.

    El color solo define que placa se descuenta; el resto de la receta es igual.
    """
    recetas = []
    for color in COLORES:
        for modelo, receta in RECETAS_POR_MODELO.items():
            codigo_mueble = f"{color}.{modelo}"
            for material, cantidad in receta.items():
                if material == "PLACA":
                    material = PLACA_POR_COLOR[color]
                recetas.append((codigo_mueble, material, cantidad))
    return recetas
