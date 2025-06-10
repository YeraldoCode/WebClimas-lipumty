from sqlalchemy import create_engine, inspect, text
from app import app, db
from models import Usuario, Vehiculo, ReporteClima
from werkzeug.security import generate_password_hash
from datetime import datetime

# Configurar la conexión a la base de datos
DATABASE_URL = "postgresql://lipu_admin:XTHV02bIaM8kXSVuMsZ2Sg7FzZQ5HoQr@dpg-d0qvdpripnbc73ept3m0-a.oregon-postgres.render.com/lipuclimas"
engine = create_engine(DATABASE_URL)

def ver_usuarios():
    print("\n=== USUARIOS ===")
    with app.app_context():
        usuarios = Usuario.query.all()
        if not usuarios:
            print("No hay usuarios registrados")
            return
        
        print("\nID | Usuario | Rol | Email")
        print("-" * 50)
        for u in usuarios:
            print(f"{u.id} | {u.username} | {u.rol} | {u.email}")

def ver_vehiculos():
    print("\n=== VEHÍCULOS ===")
    with app.app_context():
        vehiculos = Vehiculo.query.all()
        if not vehiculos:
            print("No hay vehículos registrados")
            return
        
        print("\nID | Serial | Marca | Modelo | Estatus")
        print("-" * 70)
        for v in vehiculos:
            print(f"{v.idvehiculo} | {v.serial} | {v.marca} | {v.modelo} | {v.estatus} | {v.descripcion}")

def ver_reportes():
    print("\n=== REPORTES DE CLIMA ===")
    with app.app_context():
        reportes = ReporteClima.query.all()
        if not reportes:
            print("No hay reportes registrados")
            return
        
        print("\nID | Vehículo | Fecha | Descripción | Estado | Técnico")
        print("-" * 100)
        for r in reportes:
            fecha = r.fecha_reporte.strftime('%Y-%m-%d %H:%M') if r.fecha_reporte else 'N/A'
            tecnico = r.tecnico.username if r.tecnico else 'N/A'
            print(f"{r.id} | {r.vehiculo_id} | {fecha} | {r.descripcion[:30]}... | {r.estado} | {tecnico}")

def menu():
    while True:
        print("\n=== MENÚ DE CONSULTA ===")
        print("1. Ver Usuarios")
        print("2. Ver Vehículos")
        print("3. Ver Reportes")
        print("4. Ver Todo")
        print("5. Salir")
        
        opcion = input("\nSeleccione una opción (1-5): ")
        
        if opcion == '1':
            ver_usuarios()
        elif opcion == '2':
            ver_vehiculos()
        elif opcion == '3':
            ver_reportes()
        elif opcion == '4':
            ver_usuarios()
            ver_vehiculos()
            ver_reportes()
        elif opcion == '5':
            print("\n¡Hasta luego!")
            break
        else:
            print("\nOpción no válida. Por favor, seleccione una opción del 1 al 5.")
        
        input("\nPresione Enter para continuar...")

if __name__ == '__main__':
    menu() 