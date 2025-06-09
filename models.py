from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Vehiculo(db.Model):
    __tablename__ = 'vehiculos'
    idvehiculo = db.Column(db.Integer, primary_key=True)
    serial = db.Column(db.String(50))
    marca = db.Column(db.String(50))
    modelo = db.Column(db.String(50))
    asientos = db.Column(db.Integer)
    motor = db.Column(db.String(50))
    anio = db.Column(db.Integer)
    tipo_vehiculo = db.Column(db.String(50))
    gpo_estatus = db.Column(db.String(50))
    uso = db.Column(db.String(50))
    estatus = db.Column(db.String(50))
    combustible = db.Column(db.String(30))
    eco = db.Column(db.String(30))
    placas = db.Column(db.String(30))
    placas_federales = db.Column(db.String(30))
    descripcion = db.Column(db.String(255))
    odometro = db.Column(db.Integer)

class Servicios(db.Model):
    __tablename__ = 'servicios'
    id = db.Column(db.Integer, primary_key=True)
    marca_ac = db.Column(db.String(50))

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(255))
    rol = db.Column(db.String(30))
    email = db.Column(db.String(100), unique=True)

class SolicitudTaller(db.Model):
    __tablename__ = 'solicitudes_taller'
    id = db.Column(db.Integer, primary_key=True)
    unidad_id = db.Column(db.Integer, db.ForeignKey('vehiculos.idvehiculo'), nullable=False)
    tipo_servicio = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    fecha_estimada = db.Column(db.Date, nullable=False)
    prioridad = db.Column(db.String(20), nullable=False)
    observaciones = db.Column(db.Text)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, aprobada, rechazada, en_proceso, completada
    fecha_solicitud = db.Column(db.DateTime, default=db.func.current_timestamp())
    fecha_aprobacion = db.Column(db.DateTime)
    aprobado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    comentarios_aprobacion = db.Column(db.Text)
    
    # Relaciones
    unidad = db.relationship('Vehiculo', backref='solicitudes_taller')
    aprobador = db.relationship('Usuario', backref='solicitudes_aprobadas')