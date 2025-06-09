# Flask CLIMAS-SIGO

Este proyecto es una aplicación web para el control y mantenimiento de sistemas de climatización de unidades de transporte, con roles diferenciados por funcionalidad y responsabilidad.

## Roles y Funcionalidades

### Logística/Administrador

**Responsabilidad principal**: Gestión general del sistema y administración de datos.

**Funcionalidades**:
- Carga y actualización de bases de datos desde archivos Excel (vehículos y servicios).
- Monitoreo del estado de revisión de todas las unidades activas.
- Exportación de datos consolidados a Excel para informes y trazabilidad.
- Visualización rápida de unidades pendientes y revisadas.
- Acceso a la bitácora de cambios y notificaciones del sistema.
- Envío automático de notificaciones a coordinadores y taller.

### Coordinador/Cliente

**Responsabilidad principal**: Gestión de sus flotas vehiculares y verificación del estado de los sistemas de climatización.

**Funcionalidades**:
- Selección y filtrado de unidades por cliente asignado.
- Verificación y documentación del estado de los sistemas de climatización:
  - Aire (funcionamiento del sistema de aire acondicionado)
  - Funciona (eficiencia del sistema)
  - Mochila (estado del componente mochila)
  - Conversión/Reparación (estado del mantenimiento)
  - Reinsidente (si es un problema recurrente)
- Solicitud de mantenimiento para unidades con problemas de climatización.
- Seguimiento del estado de sus solicitudes de mantenimiento.
- Historial de revisiones y mantenimientos de sus unidades.

### Taller

**Responsabilidad principal**: Ejecución y seguimiento de mantenimientos de los sistemas de climatización.

**Funcionalidades**:
- Visualización de unidades asignadas para mantenimiento.
- Filtrado de unidades por estatus (Pendiente, En proceso, Terminado).
- Registro de diagnósticos, acciones realizadas y observaciones.
- Actualización del estado de las órdenes de mantenimiento.
- Documentación de fechas, responsables y tipos de servicio realizados.
- Historial de mantenimientos realizados por unidad y técnico.
- Notificación automática a coordinadores cuando se completa un mantenimiento.

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



## guia para los templates 
1. base.html
Layout general, navbar, footer, mensajes flash, bloques para contenido y scripts.
Incluye lógica para mostrar el nombre del usuario y su rol si está autenticado.
Espacio para notificaciones globales.

2. login.html
Formulario de acceso general.
Selección de rol (o redirección a login específico).
Mensajes de error y ayuda.
Diseño responsivo y profesional.



4. admin.html
Panel principal para logística/admin.
Estadísticas generales (unidades revisadas, pendientes, mantenimientos abiertos/cerrados).
Acceso rápido a carga/exportación de Excel.
Tabla resumen de unidades y su estatus.
Acceso a bitácora y notificaciones.


5. coordinador.html
Panel para coordinador.
Filtro por cliente.
Tabla de unidades asignadas.
Acceso a revisión/edición de cada unidad.
Estado visual de revisión de climas.


6. taller.html
Panel para taller.
Lista de unidades asignadas para mantenimiento.
Filtros por estatus (pendiente, en proceso, terminado).
Acceso a formulario de registro de diagnóstico, acciones y cierre.
Historial de mantenimientos por unidad.


7. unidad_detalle.html
Vista detallada de una unidad (para cualquier rol).
Muestra todos los datos, historial de mantenimientos, bitácora de cambios.
Acciones según permisos: editar, marcar como revisado, asignar a taller, etc.


8. mantenimiento_form.html
Formulario para que taller registre diagnóstico, acciones, estatus y observaciones.
Validación robusta y feedback visual.


9. bitacora.html
Tabla con el historial de cambios y acciones sobre las unidades.
Filtros por usuario, fecha, tipo de acción.


10. notificaciones.html
Lista de notificaciones recibidas (si decides mostrar también en web, además de correo).
Acciones para marcar como leídas o ver detalles.


11. error.html
Página de error personalizada (404, 500, permisos, etc).

#####################################################################################################################################################################################################################################################################################################==============================================================================>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<>>>>>>>>>>>>>>>>>>

###  ROADMAP GENERAL (ENFOQUE FRONTEND FIRST)

1. **Diseño y Prototipado de Frontend**
   - Crea todos los templates base en `/templates/`:
     - `base.html`, `login.html`, `login_logistica.html`, `login_taller.html`, `dashboard_admin.html`, `dashboard_coordinador.html`, `dashboard_taller.html`, `unidad_detalle.html`, `mantenimiento_form.html`, `bitacora.html`, `notificaciones.html`, `error.html`.
   - Usa datos simulados (mock data) en los templates para mostrar tablas, formularios y flujos completos.
   - Define la navegación, los formularios y la experiencia de usuario para cada rol.
   - Valida el diseño y la usabilidad en desktop y móvil.

2. **Definición de Contratos de Datos**
   - Documenta qué datos espera y muestra cada template (campos, tipos, validaciones).
   - Especifica las acciones de usuario y los endpoints que necesitarás del backend.

3. **Estructura y Modularización del Proyecto (Backend)**
   - Crea carpetas para blueprints:
     `/app/auth/`, `/app/admin/`, `/app/coordinador/`, `/app/taller/`, `/app/api/`
   - Centraliza modelos y utilidades en `/app/models.py` y `/app/utils.py`.
   - Mantén `templates` y `static` como carpetas globales de vistas y recursos.

4. **Modelos y Base de Datos**
   - Agrega modelos SQLAlchemy para:
     - usuarios (con roles y email)
     - mantenimientos
     - bitácora
   - Asegúrate de que los modelos reflejen fielmente tus tablas MySQL reales.
   - Agrega migraciones con Flask-Migrate para facilitar cambios futuros.

5. **Gestión de Usuarios y Autenticación**
   - Implementa registro y login usando Flask-Login.
   - Asigna roles a cada usuario (admin, coordinador, taller).
   - Protege rutas con decoradores según el rol.
   - Agrega campo email para notificaciones.

6. **Bitácora y Trazabilidad**
   - Crea lógica para registrar en la bitácora cada vez que se edite, revise o mantenga una unidad.
   - Agrega vistas para consultar la bitácora filtrando por usuario, unidad, acción, etc.

7. **Carga y Exportación de Excel**
   - Mantén y mejora la lógica actual de carga/exportación de Excel.
   - Agrega validaciones robustas y feedback visual en el frontend.
   - Permite que solo admin/logística pueda cargar/exportar datos.

8. **Notificaciones por Correo**
   - Configura Flask-Mail.
   - Envía correos automáticos cuando se asigne una unidad a taller, se cierre un mantenimiento, etc.
   - Guía a los usuarios para que mantengan su email actualizado.

9. **Integración Backend-Frontend**
   - Sustituye los datos simulados por datos reales del backend.
   - Conecta formularios y vistas a las rutas y lógica de Flask.
   - Prueba los flujos completos por rol.

10. **Documentación y Escalabilidad**
    - Actualiza el README con la nueva estructura, roles y flujos.
    - Documenta endpoints y lógica clave.
    - Prepara la base para exponer una API REST en el futuro.