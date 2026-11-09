# Sistema de Control de Stock

Control de stock de materias primas para una pyme fabricante de muebles prefabricados en melamina.
Al registrar la venta de un mueble se descuentan los materiales de su receta, y el sistema avisa
cuando un material llega a su stock mínimo.

**Tecnología:** Python 3.13, Flask y SQLite.

## Instalación y ejecución (Windows)

1. Instalar Python 3.13.
2. En una terminal, dentro de esta carpeta, crear el entorno e instalar las dependencias:

   ```
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```

3. Ejecutar la aplicación:

   ```
   .venv\Scripts\python app.py
   ```

4. Abrir <http://127.0.0.1:5000> en el navegador.

La base de datos (`stock.db`) se crea sola la primera vez, con los materiales, los 16 muebles y sus recetas.
Para hacer una copia de seguridad, alcanza con copiar ese archivo.

## Estructura

| Archivo | Contenido |
| --- | --- |
| `app.py` | Pantallas y validaciones |
| `db.py` | Base de datos: tablas, consultas y registros |
| `datos_iniciales.py` | Materiales, muebles y recetas |
| `templates/` | Pantallas en HTML |
| `static/estilos.css` | Estilos |

## Estado del desarrollo

| Función | Estado |
| --- | --- |
| Base de datos y datos iniciales | Terminado |
| Pantalla Stock con alertas de mínimo (RF-06, RF-07) | Terminado |
| Pantalla Ingresos (RF-01, RF-08) | Terminado |
| Pantalla Salidas: validación, detalle a descontar y control de stock (RF-02, RF-03, RF-05) | Terminado |
| Pantalla Salidas: confirmación y descuento (RF-04) y alerta al registrar (RF-07) | En desarrollo |
| Pruebas | Pendiente |
