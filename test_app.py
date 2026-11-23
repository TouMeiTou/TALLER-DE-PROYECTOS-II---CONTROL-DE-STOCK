"""
Pruebas automaticas del Sistema de Control de Stock.

Cada prueba trabaja sobre una base temporal nueva: nunca toca stock.db.

Para ejecutarlas:  python -m unittest -v
"""

import os
import shutil
import tempfile
import unittest

import db

# La base temporal se define antes de importar la aplicacion,
# para que al iniciarse no use la base real.
_CARPETA_INICIAL = tempfile.mkdtemp()
db.RUTA_DB = os.path.join(_CARPETA_INICIAL, "prueba.db")

import app as aplicacion  # noqa: E402  (se importa despues de cambiar la ruta de la base)


class BasePrueba(unittest.TestCase):
    """Crea una base temporal con los datos iniciales antes de cada prueba."""

    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        db.RUTA_DB = os.path.join(self.carpeta, "prueba.db")
        db.crear_base()
        self.conexion = db.conectar()
        self.cliente = aplicacion.app.test_client()

    def tearDown(self):
        self.conexion.close()
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def cargar_stock(self, cantidad):
        """Ingresa la misma cantidad de todos los materiales."""
        for material in db.listar_materiales(self.conexion):
            db.registrar_ingreso(self.conexion, material["codigo"], cantidad)

    def cantidad_de_salidas(self):
        return self.conexion.execute(
            "SELECT COUNT(*) FROM movimientos WHERE tipo = 'SALIDA'").fetchone()[0]


# ====================================================== Pruebas de unidad (db.py)

class PruebasDeUnidad(BasePrueba):

    def test_datos_iniciales(self):
        """La base se crea con 12 materiales, 16 muebles y 136 renglones de recetas."""
        contar = lambda tabla: self.conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        self.assertEqual(contar("materiales"), 12)
        self.assertEqual(contar("muebles"), 16)
        self.assertEqual(contar("recetas"), 136)

    def test_stock_minimo_35(self):
        """Todos los materiales tienen stock minimo 35."""
        for material in db.listar_materiales(self.conexion):
            self.assertEqual(material["stock_minimo"], 35)

    def test_datos_iniciales_no_se_duplican(self):
        """Si la base ya existe, al iniciar de nuevo no se vuelven a cargar los datos."""
        db.crear_base()
        total = self.conexion.execute("SELECT COUNT(*) FROM materiales").fetchone()[0]
        self.assertEqual(total, 12)

    def test_stock_inicial_en_cero(self):
        self.assertEqual(db.stock_de(self.conexion, "TOR-001"), 0)

    def test_ingreso_suma_stock(self):
        """RF-01: un ingreso suma al stock del material."""
        db.registrar_ingreso(self.conexion, "TOR-001", 150)
        db.registrar_ingreso(self.conexion, "TOR-001", 50)
        self.assertEqual(db.stock_de(self.conexion, "TOR-001"), 200)

    def test_cantidad_cero_rechazada_por_la_base(self):
        """RN-02 / RN-06: la base no acepta movimientos con cantidad 0."""
        with self.assertRaises(Exception):
            db.registrar_ingreso(self.conexion, "TOR-001", 0)

    def test_receta_por_cantidad(self):
        """RN-07: receta del mueble x cantidad (modelo 2 negro x 2)."""
        detalle = {m["codigo"]: m["necesario"] for m in db.receta_por_cantidad(self.conexion, "2.2", 2)}
        self.assertEqual(detalle["PLA-002"], 4)    # 2 placas negras x 2
        self.assertEqual(detalle["FIL-001"], 50)   # 25 metros x 2
        self.assertEqual(detalle["TOR-001"], 70)   # 35 tornillos x 2
        self.assertEqual(len(detalle), 9)

    def test_color_solo_cambia_la_placa(self):
        """El 1.1 usa placa blanca y el 4.1 placa gris; el resto de la receta es igual."""
        blanco = {m["codigo"]: m["necesario"] for m in db.receta_por_cantidad(self.conexion, "1.1", 1)}
        gris = {m["codigo"]: m["necesario"] for m in db.receta_por_cantidad(self.conexion, "4.1", 1)}
        self.assertIn("PLA-001", blanco)
        self.assertIn("PLA-004", gris)
        del blanco["PLA-001"], gris["PLA-004"]
        self.assertEqual(blanco, gris)

    def test_salida_descuenta_toda_la_receta(self):
        """RF-04: al confirmar se descuenta cada material de la receta x cantidad."""
        self.cargar_stock(100)
        self.assertTrue(db.registrar_salida(self.conexion, "1.1", 2))
        self.assertEqual(db.stock_de(self.conexion, "PLA-001"), 98)   # 100 - 1 x 2
        self.assertEqual(db.stock_de(self.conexion, "FIL-001"), 70)   # 100 - 15 x 2
        self.assertEqual(db.stock_de(self.conexion, "TOR-001"), 40)   # 100 - 30 x 2
        self.assertEqual(db.stock_de(self.conexion, "PLA-002"), 100)  # otra placa: no cambia

    def test_salida_sin_stock_no_descuenta_nada(self):
        """RN-01 / RF-05: si falta un material, no se descuenta ninguno."""
        self.cargar_stock(100)
        # Tornillos: 100 disponibles, se necesitan 30 x 4 = 120.
        self.assertFalse(db.registrar_salida(self.conexion, "1.1", 4))
        self.assertEqual(self.cantidad_de_salidas(), 0)
        self.assertEqual(db.stock_de(self.conexion, "PLA-001"), 100)

    def test_faltante_informa_cuanto_falta(self):
        """RF-05: se informa que material falta y cuanto."""
        self.cargar_stock(100)
        faltantes = {m["codigo"]: m["faltante"] for m in db.receta_por_cantidad(self.conexion, "1.1", 4)
                     if m["faltante"] > 0}
        self.assertEqual(faltantes, {"TOR-001": 20})

    def test_alerta_en_el_minimo(self):
        """RN-04: el material en el minimo (35) entra en alerta; con 36 no."""
        db.registrar_ingreso(self.conexion, "TOR-001", 35)
        db.registrar_ingreso(self.conexion, "CLA-001", 36)
        alertas = {m["codigo"]: m["alerta"] for m in db.stock_actual(self.conexion)}
        self.assertTrue(alertas["TOR-001"])
        self.assertFalse(alertas["CLA-001"])

    def test_alerta_despues_de_una_salida(self):
        """RF-07: el filo queda en 35 (50 - 15) y aparece en las alertas del mueble."""
        self.cargar_stock(50)
        db.registrar_salida(self.conexion, "1.1", 1)
        codigos = [m["codigo"] for m in db.materiales_en_alerta(self.conexion, "1.1")]
        self.assertIn("FIL-001", codigos)
        self.assertNotIn("PLA-001", codigos)   # quedan 49


# ====================================================== Pruebas de sistema (pantallas)

class PruebasDeSistema(BasePrueba):

    def test_inicio_lleva_a_stock(self):
        respuesta = self.cliente.get("/")
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/stock", respuesta.location)

    def test_pantallas_responden(self):
        for ruta in ("/stock", "/ingresos", "/salidas"):
            self.assertEqual(self.cliente.get(ruta).status_code, 200, ruta)

    def test_stock_muestra_reponer_con_stock_en_cero(self):
        texto = self.cliente.get("/stock").get_data(as_text=True)
        self.assertEqual(texto.count("Reponer"), 12)

    def test_ingreso_valido(self):
        """RF-01: el ingreso se guarda y se informa el stock actual."""
        respuesta = self.cliente.post("/ingresos", data={"material": "TOR-001", "cantidad": "150"},
                                      follow_redirects=True)
        texto = respuesta.get_data(as_text=True)
        self.assertIn("Ingreso registrado", texto)
        self.assertIn("150 unidades", texto)
        self.assertEqual(db.stock_de(self.conexion, "TOR-001"), 150)

    def test_ingreso_sin_material(self):
        texto = self.cliente.post("/ingresos", data={"material": "", "cantidad": "10"}).get_data(as_text=True)
        self.assertIn("Seleccione un material.", texto)

    def test_cantidades_invalidas_rechazadas(self):
        """RN-02 / RN-06: vacio, cero, negativo, decimal y letras no se aceptan."""
        for valor in ("", "0", "-5", "2,5", "2.5", "abc"):
            texto = self.cliente.post("/ingresos", data={"material": "TOR-001", "cantidad": valor}
                                      ).get_data(as_text=True)
            self.assertIn("La cantidad debe ser un número entero mayor a cero.", texto, valor)
        self.assertEqual(db.stock_de(self.conexion, "TOR-001"), 0)

    def test_codigo_de_mueble_inexistente(self):
        """RF-02: codigos fuera del 1.1 al 4.4 se rechazan."""
        for codigo in ("5.1", "1.5", "0.0", "abc", ""):
            texto = self.cliente.post("/salidas", data={"codigo": codigo, "cantidad": "1"}).get_data(as_text=True)
            self.assertIn("El código ingresado no existe.", texto, codigo)

    def test_vista_previa_no_descuenta(self):
        """RF-03: Continuar muestra lo que se va a descontar, sin descontar."""
        self.cargar_stock(100)
        texto = self.cliente.post("/salidas", data={"codigo": "3.2", "cantidad": "1"}).get_data(as_text=True)
        self.assertIn("se van a descontar", texto)
        self.assertIn("Confirmar", texto)
        self.assertEqual(self.cantidad_de_salidas(), 0)

    def test_vista_previa_con_faltantes(self):
        """RF-05: sin stock se informa que falta y no se ofrece Confirmar."""
        texto = self.cliente.post("/salidas", data={"codigo": "1.1", "cantidad": "1"}).get_data(as_text=True)
        self.assertIn("Stock insuficiente", texto)
        self.assertNotIn("Confirmar", texto)

    def test_confirmar_salida(self):
        """RF-04 / RF-07: confirmar descuenta, informa y muestra la alerta de minimo."""
        self.cargar_stock(50)
        respuesta = self.cliente.post("/salidas", data={"codigo": "1.1", "cantidad": "1", "accion": "confirmar"},
                                      follow_redirects=True)
        texto = respuesta.get_data(as_text=True)
        self.assertIn("Salida registrada", texto)
        self.assertIn("Atención: reponer stock.", texto)
        self.assertIn("Filo de aluminio: quedan 35 metros", texto)
        self.assertEqual(db.stock_de(self.conexion, "FIL-001"), 35)

    def test_recargar_no_duplica_la_salida(self):
        """Despues de confirmar se redirige: recargar la pagina no registra otra salida."""
        self.cargar_stock(100)
        respuesta = self.cliente.post("/salidas", data={"codigo": "1.1", "cantidad": "1", "accion": "confirmar"})
        self.assertEqual(respuesta.status_code, 302)
        movimientos = self.cantidad_de_salidas()
        self.cliente.get(respuesta.location)   # equivale a recargar (F5)
        self.cliente.get(respuesta.location)
        self.assertEqual(self.cantidad_de_salidas(), movimientos)

    def test_confirmar_sin_stock_no_descuenta(self):
        """RN-01: aunque se envie Confirmar, si falta stock no se registra nada."""
        texto = self.cliente.post("/salidas", data={"codigo": "1.1", "cantidad": "1", "accion": "confirmar"}
                                  ).get_data(as_text=True)
        self.assertIn("Stock insuficiente", texto)
        self.assertEqual(self.cantidad_de_salidas(), 0)


if __name__ == "__main__":
    unittest.main()
