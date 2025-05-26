from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Vehiculo(db.Model):
    __tablename__ = 'Vehiculos'
    IdVehiculo = db.Column(db.Integer, primary_key=True)
    Serial = db.Column(db.String(100))
    Marca = db.Column(db.String(100))
    Modelo = db.Column(db.String(100))
    Asientos = db.Column(db.String(10))
    Motor = db.Column(db.String(100))
    Año = db.Column(db.String(10))
    Tipo_vehiculo = db.Column(db.String(100))
    Gpo_estatus = db.Column(db.String(100))
    Uso = db.Column(db.String(100))
    Estatus = db.Column(db.String(100))
    Combustible = db.Column(db.String(100))
    Eco = db.Column(db.String(100))
    Placas = db.Column(db.String(100))
    Placas_federales = db.Column(db.String(100))
    Descripcion = db.Column(db.String(255))
    aire = db.Column(db.String(10))
    jala = db.Column(db.String(10))
    mochila = db.Column(db.String(10))
    conversion_reparacion = db.Column(db.String(100))
    reinsidente = db.Column(db.String(10))

class Servicios(db.Model):
    __tablename__ = 'Servicios'
    ID = db.Column(db.Integer, primary_key=True)
    Marca_AC = db.Column(db.String(50))