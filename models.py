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
    aire = db.Column(db.String(10))
    jala = db.Column(db.String(10))
    mochila = db.Column(db.String(10))
    conversion_reparacion = db.Column(db.String(50))
    reinsidente = db.Column(db.String(10))

class Servicios(db.Model):
    __tablename__ = 'servicios'
    id = db.Column(db.Integer, primary_key=True)
    marca_ac = db.Column(db.String(50))