-- Actualizar tabla reportes_clima
ALTER TABLE reportes_clima 
ADD COLUMN IF NOT EXISTS coordinador_id INTEGER REFERENCES usuarios(id),
ADD COLUMN IF NOT EXISTS fecha_solicitud_taller TIMESTAMP,
ADD COLUMN IF NOT EXISTS fecha_asignacion_taller TIMESTAMP,
ADD COLUMN IF NOT EXISTS fecha_llamada_taller TIMESTAMP;

-- Actualizar tabla servicios
ALTER TABLE servicios 
ADD COLUMN IF NOT EXISTS vehiculo_id INTEGER REFERENCES vehiculos(idvehiculo); 