# Flujo de estados en el frontend

## Panel Coordinador (`coordinador.html`)
- **Formulario de reporte:** El coordinador reporta un problema de una unidad. Al enviar, el frontend muestra confirmación y limpia el formulario.
- **Visualización:** Puede ver el historial de reportes de su(s) unidad(es), normalmente en una tabla o lista, con el estado actual de cada reporte (pendiente, aprobado, rechazado, etc.).
- **Restricciones:** No puede editar ni cambiar estados después de enviar el reporte.

---

## Panel Administrador / Logística (`admin.html`)
- **Vista de reportes:** Lista todos los reportes pendientes, aprobados, rechazados, planificados, en proceso y completados.
- **Acciones:** Puede aprobar o rechazar reportes desde la interfaz (botones de acción). Al aprobar/rechazar, el estado se actualiza dinámicamente en la tabla/lista.
- **Carga/Exportación Excel:** Puede cargar archivos Excel para importar datos y exportar el estado actual de los reportes/unidades. El frontend muestra mensajes de éxito/error y actualiza la vista tras la acción.
- **Filtros:** Puede filtrar por fecha, semana, estado, unidad, etc., usando selectores y campos de búsqueda.

---

## Panel Taller (`taller/index.html`)
- **Calendario interactivo:** Muestra los reportes planificados, en proceso y completados en un calendario FullCalendar.
- **Modal de acción:** Al hacer clic en un evento, se abre un modal con detalles del reporte y botones para cambiar el estado:
  - Si el reporte está "completado", solo se muestra la hora de finalización.
  - Si está en otro estado, aparecen botones para marcar como "Listo", "En atención" o "Pendiente" (con motivo).
- **Planificación:** Puede seleccionar uno o varios reportes y agendar fecha/hora. El frontend valida los campos y muestra alertas de éxito/error.
- **Actualización dinámica:** Al cambiar el estado de un reporte, el calendario se actualiza automáticamente sin recargar la página.
- **Restricciones:** Los botones de acción se ocultan o deshabilitan según el estado del reporte.

---

## Estado visual de las unidades y reportes
- **Colores y etiquetas:** El frontend usa colores y badges para indicar el estado de cada reporte (ejemplo: naranja para planificado, azul para en atención, verde para completado).
- **Unidades:** El estado de la unidad se refleja en la vista de logística/admin, mostrando si está "Operando", "Espera" o "Mantenimiento" según los reportes activos.

---

## Resumen
- El frontend guía al usuario mostrando solo las acciones válidas según el estado.
- Los cambios de estado se reflejan en tiempo real usando AJAX/fetch y actualizaciones dinámicas de la UI.
- El usuario siempre recibe feedback visual (alertas, badges, cambios de color, actualización de tablas/calendario) tras cada acción.



# Flujo de estados en el backend

## Panel Coordinador
- **Crea reporte:**  
  - El coordinador reporta un problema de una unidad.
  - **Unidad:** Cambia de `Operando` a `Espera`.
  - **Reporte:** Se crea con estado `pendiente`.

## Panel Administrador / Logística
- **Aprueba o rechaza reportes:**  
  - **Reporte:** 
    - Si es aprobado, pasa a estado `aprobado`.
    - Si es rechazado, pasa a estado `rechazado`.
  - **Unidad:**  
    - Si el reporte es aprobado, la unidad permanece en `Espera`.
    - Si el reporte es rechazado y no hay otros reportes pendientes, la unidad puede volver a `Operando`.

## Panel Taller
- **Planifica y atiende reportes:**  
  - **Reporte:**  
    1. `aprobado` → `planificado` (al agendar fecha/hora)
    2. `planificado` → `en_proceso` (cuando el taller lo atiende)
    3. `en_proceso` → `completado` (al finalizar el trabajo)
    4. Si no se puede atender, puede volver a `pendiente` con motivo, y luego regresar a `planificado` o `en_proceso` cuando se retome.
  - **Unidad:**  
    - Cuando el reporte pasa a `en_proceso`, la unidad pasa a `Mantenimiento`.
    - Cuando el reporte se marca como `completado`, la unidad vuelve a `Operando`.

## Resumen de estados

### Unidad
- `Operando` → (se reporta un problema) → `Espera` → (taller lo atiende) → `Mantenimiento` → (reporte completado) → `Operando`

### Reporte
- `pendiente` (creado por coordinador)
- `aprobado` (aprobado por logística/admin)
- `planificado` (taller agenda fecha/hora)
- `en_proceso` (taller lo está atendiendo)
- `pendiente` (si no se puede atender, con motivo)
- `completado` (trabajo terminado)
- `rechazado` (si logística no lo aprueba)

---

**Notas:**
- `"en atención"` y `en_proceso` son equivalentes: significa que el taller ya está trabajando en el reporte.
- El estado de la unidad depende de los reportes activos asociados.