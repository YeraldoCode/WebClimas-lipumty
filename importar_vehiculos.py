import pandas as pd
from app import app, db
from models import Vehiculo

# Cambia la ruta a tu archivo Excel
archivo = 'data/Vehiculos.xlsx'

# Lee el archivo Excel (ajusta sheet_name si es necesario)
df = pd.read_excel(archivo, engine='openpyxl')

with app.app_context():
    for _, row in df.iterrows():
        vehiculo = Vehiculo(
            idvehiculo=row['IdVehiculo'],
            serial=row['Serial'],
            marca=row['Marca'],
            motor=row['Motor'],
            anio=row['Anio'],
            tipo_vehiculo=row['Tipo vehiculo'],
            gpo_estatus=row['Gpo. estatus'],
            uso=row['Uso'],
            estatus=row['Estatus'],
            mecanix=row.get('Mecanix'),
            costo_reparacion=row.get('Costo de reparacion', 0),
            placas=row['Placas'],
            placas_federales=row['Placas federales'],
            descripcion=row['Descripcion'],
            odometro=row['Odometro']
        )
        db.session.add(vehiculo)
    db.session.commit()
    print("Vehículos importados correctamente.")