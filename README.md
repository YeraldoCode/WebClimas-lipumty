# Flask Transport Review System

Este proyecto es una aplicación web para revisión y edición de datos logísticos de vehículos, con roles de coordinador y administrador, usando Flask y Tailwind CSS.

## Estructura inicial

- `app.py`: App principal Flask, rutas y lógica básica.
- `models.py`: Modelos de datos y utilidades para SQLite.
- `forms.py`: Formularios WTForms para login, edición, carga.
- `utils.py`: Funciones para manejo de Excel y utilidades.
- `config.py`: Configuración de Flask y rutas de archivos.
- `/templates/`: Plantillas base (Jinja2):
  - `base.html`, `login.html`, `admin.html`, `coordinador.html`
- `/static/css/`: Tailwind CSS compilado.
- `/uploads/`: Archivos Excel originales subidos.
- `/data/`: Archivos editados/exportados.

## Instalación

1. Instala dependencias:
   ```bash
   pip install flask flask-login flask-wtf openpyxl pandas
   ```
2. Compila Tailwind CSS en `/static/css/` (ver documentación Tailwind).
3. Ejecuta la app:
   ```bash
   python app.py
   ```

## Funcionalidades
- Coordinador: ingresa IDVehículo, revisa y edita datos, envía cambios.
- Admin: login, carga Excel, ve estado de revisión, exporta consolidado.
- Cambios y revisiones quedan trazados en SQLite o archivo aparte.

## Seguridad
- Panel admin protegido por contraseña.
- Coordinador solo accede a su unidad por ID.

## Notas
- El sistema está preparado para carga dinámica de archivos semana a semana.
- El diseño es responsivo y claro gracias a Tailwind CSS.
