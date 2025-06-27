from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(100), nullable=False)

    def set_password(self, password):
        print(f"\n=== Set Password ===")
        print(f"Password a hashear: {password}")
        self.password_hash = generate_password_hash(password)
        print(f"Hash generado: {self.password_hash}")

    def check_password(self, password):
        print(f"\n=== Check Password ===")
        print(f"Password a verificar: {password}")
        print(f"Hash almacenado: {self.password_hash}")
        result = check_password_hash(self.password_hash, password)
        print(f"Resultado verificación: {result}")
        return result

class Vehiculo(db.Model):
    __tablename__ = 'vehiculos'
    idvehiculo = db.Column(db.Integer, primary_key=True, autoincrement=True)
    serial = db.Column(db.String(100))
    marca = db.Column(db.String(50))
    motor = db.Column(db.String(50))
    anio = db.Column(db.Integer)
    tipo_vehiculo = db.Column(db.String(50))
    gpo_estatus = db.Column(db.String(50))
    uso = db.Column(db.String(50))
    estatus = db.Column(db.String(50))
    mecanix = db.Column(db.String(100))  # Nuevo campo
    costo_reparacion = db.Column(db.Float)  # Nuevo campo
    placas = db.Column(db.String(20))
    placas_federales = db.Column(db.String(20))
    descripcion = db.Column(db.Text)
    odometro = db.Column(db.Integer)

class Servicio(db.Model):
    __tablename__ = 'servicios'
    id = db.Column(db.Integer, primary_key=True)
    marca_ac = db.Column(db.String(50))
    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculos.idvehiculo'))
    vehiculo = db.relationship('Vehiculo', backref='servicios')

class ReporteClima(db.Model):
    __tablename__ = 'reportes_clima'
    id = db.Column(db.Integer, primary_key=True)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculos.idvehiculo'))
    fecha_reporte = db.Column(db.DateTime, default=datetime.utcnow)
    descripcion = db.Column(db.Text)
    tipo_problema = db.Column(db.String(50))  # Asegurar que el tipo_problema esté definido
    estado = db.Column(db.String(20))
    tecnico_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    fecha_revision = db.Column(db.DateTime)
    coordinador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    fecha_solicitud_taller = db.Column(db.DateTime)
    fecha_asignacion_taller = db.Column(db.DateTime)
    fecha_llamada_taller = db.Column(db.DateTime)
    fecha_inicio = db.Column(db.DateTime)  # Fecha de inicio del servicio 
    fecha_completado = db.Column(db.DateTime)  # Fecha de finalización del servicio
    vehiculo = db.relationship('Vehiculo', backref='reportes_clima')
    coordinador = db.relationship('Usuario', foreign_keys=[coordinador_id], backref='reportes_creados')
    tecnico = db.relationship('Usuario', foreign_keys=[tecnico_id], backref='reportes_revisados')
    motivo = db.Column(db.Text, nullable=True)  # Agregar este campo
    fecha_aprobacion = db.Column(db.DateTime)


class HistorialReporte(db.Model):
    __tablename__ = 'historial_reportes'
    id = db.Column(db.Integer, primary_key=True)
    reporte_id = db.Column(db.Integer, db.ForeignKey('reportes_clima.id'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    accion = db.Column(db.String(50))  # Ejemplo: "en_proceso", "completado"
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    reporte = db.relationship('ReporteClima', backref='historial')
    usuario = db.relationship('Usuario', backref='acciones')