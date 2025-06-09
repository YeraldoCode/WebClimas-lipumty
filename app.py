# App principal para el control y mantenimiento de climas de unidades de transporte.
# Roles: coordinador, logística (admin), próximamente taller.
# Funcionalidades: revisión, edición, trazabilidad, carga/exportación Excel.

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FileField, SubmitField
from wtforms.validators import DataRequired
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import os
from models import db, Vehiculo, Servicios, Usuario, SolicitudTaller
import pandas as pd
from io import BytesIO
from datetime import datetime

# =============================
# Configuración e inicialización
# =============================
app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# =============================
# Rutas principales
# =============================

@app.route('/')
def index():
    # Página de inicio/login general
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Login unificado para logística y taller
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Usuario.query.filter_by(username=username, password_hash=password).first()
        if user:
            session['admin_autenticado'] = True
            session['rol'] = user.rol
            if user.rol == 'logistica':
                return redirect(url_for('admin_panel'))
            elif user.rol == 'taller':
                return redirect(url_for('taller_panel'))
            else:
                error = 'Rol no soportado.'
        else:
            error = 'Usuario o contraseña incorrectos.'
    return render_template('login.html', error=error)

@app.route('/taller')
def taller_panel():
    # Panel principal de taller
    if not session.get('admin_autenticado') or session.get('rol') != 'taller':
        return redirect(url_for('login'))
    vehiculos = Vehiculo.query.filter(
        Vehiculo.gpo_estatus == 'Activo',
        Vehiculo.uso == 'Operaciones',
        Vehiculo.estatus == 'Operando',
        Vehiculo.descripcion != None,
        Vehiculo.descripcion != ''
    ).all()
    filtrados = sorted(vehiculos, key=lambda v: (v.descripcion or '').lower())
    return render_template('taller.html', vehiculos=filtrados)

@app.route('/coordinador/select', methods=['GET', 'POST'])
def coordinador_select():
    # Selección de unidades por cliente para coordinador
    clientes = Vehiculo.query.all()
    selected_cliente = request.args.get('cliente')
    unidades = []
    if selected_cliente:
        unidades = Vehiculo.query.filter_by(descripcion=selected_cliente).all()
        for v in unidades:
            v.revisado = all(getattr(v, campo) not in [None, '', ' '] for campo in ['aire', 'jala', 'mochila', 'conversion_reparacion'])
    if request.method == 'POST' and request.form.get('idvehiculo'):
        return redirect(url_for('coordinador', idvehiculo=request.form.get('idvehiculo')))
    return render_template('coordinador_select.html', clientes=clientes, unidades=unidades, selected_cliente=selected_cliente)

@app.route('/coordinador')
def coordinador():
    return render_template('coordinador.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    # Panel principal de administración (logística)
    if not session.get('admin_autenticado'):
        return redirect(url_for('login'))
    vehiculos = Vehiculo.query.filter(
        Vehiculo.gpo_estatus == 'Activo',
        Vehiculo.uso == 'Operaciones',
        Vehiculo.estatus == 'Operando',
        Vehiculo.descripcion != None,
        Vehiculo.descripcion != ''
    ).all()
    filtrados = sorted(vehiculos, key=lambda v: (v.descripcion or '').lower())
    return render_template('admin.html', vehiculos=filtrados)

@app.route('/admin/upload', methods=['POST'])
def upload_excel():
    # Carga de archivos Excel para actualizar la base de datos
    file = request.files.get('file')
    if not file:
        flash('No se ha seleccionado ningún archivo.', 'danger')
        return redirect(url_for('admin_panel'))
    filename = file.filename.lower()
    try:
        import pandas as pd
        import math
        def clean_nan(val):
            return None if (isinstance(val, float) and math.isnan(val)) else val
        df = pd.read_excel(file)
        if 'vehiculos' in filename:
            for _, row in df.iterrows():
                vehiculo = Vehiculo.query.filter_by(idvehiculo=row['idvehiculo']).first()
                if vehiculo:
                    for col in ['serial', 'marca', 'modelo', 'asientos', 'motor', 'anio', 'tipo_vehiculo', 'gpo_estatus', 'uso', 'estatus', 'combustible', 'eco', 'placas', 'placas_federales', 'descripcion', 'aire', 'jala', 'mochila', 'conversion_reparacion', 'reinsidente']:
                        if col in row:
                            setattr(vehiculo, col, clean_nan(row[col]))
                else:
                    vehiculo = Vehiculo(**{col: clean_nan(row.get(col)) for col in ['idvehiculo', 'serial', 'marca', 'modelo', 'asientos', 'motor', 'anio', 'tipo_vehiculo', 'gpo_estatus', 'uso', 'estatus', 'combustible', 'eco', 'placas', 'placas_federales', 'descripcion', 'aire', 'jala', 'mochila', 'conversion_reparacion', 'reinsidente']})
                    db.session.add(vehiculo)
            db.session.commit()
            flash('Vehículos actualizados correctamente.', 'success')
        elif 'servicios' in filename:
            for _, row in df.iterrows():
                servicio = Servicios.query.filter_by(id=row['id']).first()
                if servicio:
                    for col in ['marca_ac']:
                        if col in row:
                            setattr(servicio, col, row[col])
                else:
                    servicio = Servicios(**{col: row.get(col) for col in ['id', 'marca_ac']})
                    db.session.add(servicio)
            db.session.commit()
            flash('Servicios actualizados correctamente.', 'success')
        else:
            flash('El archivo debe llamarse vehiculos.xlsx o servicios.xlsx.', 'danger')
    except Exception as e:
        flash(f'Error procesando el archivo: {e}', 'danger')
    return redirect(url_for('admin_panel'))

@app.route('/admin/export')
def export():
    # Exporta la información consolidada de vehículos y servicios a Excel
    results = db.session.query(
        Vehiculo,
        Servicios.marca_ac
    ).join(Servicios, Vehiculo.idvehiculo == Servicios.id).all()
    data = []
    for v, marca_ac in results:
        row = {col: getattr(v, col) for col in [
            'idvehiculo', 'serial', 'marca', 'modelo', 'asientos', 'motor', 'anio', 'tipo_vehiculo', 'gpo_estatus', 'uso', 'estatus', 'combustible', 'eco', 'placas', 'placas_federales', 'descripcion', 'aire', 'jala', 'mochila', 'conversion_reparacion', 'reinsidente']}
        row['marca_ac'] = marca_ac
        data.append(row)
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return send_file(output, download_name='sigo_climas.xlsx', as_attachment=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/solicitud-taller', methods=['GET', 'POST'])
def solicitud_taller():
    if request.method == 'POST':
        # Simular éxito en el envío
        return jsonify({'success': True, 'message': 'Solicitud enviada correctamente'})
    return render_template('solicitud_taller.html', unidades=UNIDADES)

@app.route('/taller/solicitudes')
def taller_solicitudes():
    # Datos falsos para las solicitudes pendientes
    solicitudes = [
        {
            'id': 1,
            'unidad': 'Mercedes Benz O500',
            'tipo_servicio': 'Preventivo',
            'descripcion': 'Cambio de aceite y filtros',
            'fecha_estimada': '2024-02-25',
            'prioridad': 'Media',
            'estado': 'pendiente'
        },
        {
            'id': 2,
            'unidad': 'Volvo B7R',
            'tipo_servicio': 'Correctivo',
            'descripcion': 'Reparación de frenos',
            'fecha_estimada': '2024-02-26',
            'prioridad': 'Alta',
            'estado': 'pendiente'
        }
    ]
    return render_template('taller_solicitudes.html', solicitudes=solicitudes)

@app.route('/admin/solicitudes')
@login_required
def admin_solicitudes():
    return render_template('admin_solicitudes.html', solicitudes=SOLICITUDES)

@app.route('/admin/modificar-unidad')
@login_required
def admin_modificar_unidad():
    return render_template('admin_modificar_unidad.html', unidades=UNIDADES, operadores=OPERADORES, rutas=RUTAS)

@app.route('/admin/actualizar-unidad', methods=['POST'])
@login_required
def actualizar_unidad():
    data = request.get_json()
    # Simular actualización exitosa
    return jsonify({
        'success': True,
        'message': 'Unidad actualizada correctamente'
    })

@app.route('/admin/aprobar-solicitud/<int:id>', methods=['POST'])
@login_required
def aprobar_solicitud(id):
    # Simular aprobación exitosa
    return jsonify({
        'success': True,
        'message': 'Solicitud aprobada correctamente'
    })

@app.route('/admin/rechazar-solicitud/<int:id>', methods=['POST'])
@login_required
def rechazar_solicitud(id):
    # Simular rechazo exitoso
    return jsonify({
        'success': True,
        'message': 'Solicitud rechazada correctamente'
    })

# Rutas para el coordinador
@app.route('/coordinador/rutas')
def coordinador_rutas():
    rutas = [
        {
            'id': 1,
            'nombre': 'Ruta 1',
            'origen': 'Ciudad A',
            'destino': 'Ciudad B',
            'operador': 'Juan Pérez',
            'unidad': 'Mercedes Benz O500'
        },
        {
            'id': 2,
            'nombre': 'Ruta 2',
            'origen': 'Ciudad C',
            'destino': 'Ciudad D',
            'operador': 'María García',
            'unidad': 'Volvo B7R'
        }
    ]
    return render_template('coordinador_rutas.html', rutas=rutas)

@app.route('/coordinador/operadores')
def coordinador_operadores():
    operadores = [
        {
            'id': 1,
            'nombre': 'Juan Pérez',
            'estado': 'Activo',
            'unidad': 'ABC-123',
            'rutas_activas': 2
        },
        {
            'id': 2,
            'nombre': 'María García',
            'estado': 'Activo',
            'unidad': 'XYZ-789',
            'rutas_activas': 1
        }
    ]
    return render_template('coordinador_operadores.html', operadores=operadores)

@app.route('/coordinador/flota')
def coordinador_flota():
    flota = [
        {
            'id': 1,
            'placa': 'ABC-123',
            'modelo': 'Mercedes-Benz O500',
            'operador': 'Juan Pérez',
            'estado': 'En Servicio'
        },
        {
            'id': 2,
            'placa': 'XYZ-789',
            'modelo': 'Volvo B340',
            'operador': 'María García',
            'estado': 'En Taller'
        }
    ]
    return render_template('coordinador_flota.html', flota=flota)

# Rutas para el taller
@app.route('/taller/servicios')
@login_required
def taller_servicios():
    servicios = [
        {
            'id': 1,
            'unidad': 'ABC-123',
            'tipo': 'Mantenimiento Preventivo',
            'descripcion': 'Cambio de aceite y filtros',
            'fecha': '2024-03-15',
            'estado': 'Completado'
        },
        {
            'id': 2,
            'unidad': 'XYZ-789',
            'tipo': 'Reparación',
            'descripcion': 'Cambio de frenos',
            'fecha': '2024-03-16',
            'estado': 'En Progreso'
        }
    ]
    return render_template('taller_servicios.html', servicios=servicios)

@app.route('/taller/inventario')
@login_required
def taller_inventario():
    inventario = [
        {
            'id': 1,
            'nombre': 'Aceite Motor',
            'cantidad': 50,
            'unidad': 'L',
            'minimo': 20
        },
        {
            'id': 2,
            'nombre': 'Filtros de Aire',
            'cantidad': 15,
            'unidad': 'Unidad',
            'minimo': 10
        }
    ]
    return render_template('taller_inventario.html', inventario=inventario)

@app.route('/taller/diagnosticos')
@login_required
def taller_diagnosticos():
    diagnosticos = [
        {
            'id': 1,
            'unidad': 'ABC-123',
            'fecha': '2024-03-15',
            'tecnico': 'Carlos Rodríguez',
            'tipo': 'Mecánico',
            'descripcion': 'Revisión general del motor',
            'estado': 'Completado'
        },
        {
            'id': 2,
            'unidad': 'XYZ-789',
            'fecha': '2024-03-16',
            'tecnico': 'Ana Martínez',
            'tipo': 'Eléctrico',
            'descripcion': 'Diagnóstico del sistema eléctrico',
            'estado': 'En Progreso'
        }
    ]
    return render_template('taller_diagnosticos.html', diagnosticos=diagnosticos)

# Rutas para el administrador
@app.route('/admin/usuarios')
@login_required
def admin_usuarios():
    usuarios = [
        {
            'id': 1,
            'username': 'admin',
            'nombre': 'Administrador',
            'rol': 'Administrador',
            'activo': True,
            'ultimo_acceso': '2024-03-15 10:30'
        },
        {
            'id': 2,
            'username': 'coordinador',
            'nombre': 'Coordinador',
            'rol': 'Coordinador',
            'activo': True,
            'ultimo_acceso': '2024-03-15 09:15'
        }
    ]
    return render_template('admin_usuarios.html', usuarios=usuarios)

@app.route('/admin/documentos')
@login_required
def admin_documentos():
    documentos = [
        {
            'id': 1,
            'nombre': 'Manual de Operaciones',
            'tipo': 'PDF',
            'categoria': 'Manuales',
            'usuario': 'admin',
            'fecha': '2024-03-15',
            'tamano': '2.5 MB'
        },
        {
            'id': 2,
            'nombre': 'Reporte Mensual',
            'tipo': 'XLS',
            'categoria': 'Reportes',
            'usuario': 'coordinador',
            'fecha': '2024-03-14',
            'tamano': '1.8 MB'
        }
    ]
    return render_template('admin_documentos.html', documentos=documentos)

@app.route('/admin/reportes')
@login_required
def admin_reportes():
    reportes = [
        {
            'id': 1,
            'tipo': 'Operaciones',
            'titulo': 'Reporte de Rutas Mensual',
            'usuario': 'coordinador',
            'fecha': '2024-03-15',
            'periodo': 'Marzo 2024',
            'estado': 'Completado',
            'resumen': 'Análisis de rendimiento de rutas y operadores'
        },
        {
            'id': 2,
            'tipo': 'Mantenimiento',
            'titulo': 'Reporte de Servicios',
            'usuario': 'taller',
            'fecha': '2024-03-14',
            'periodo': 'Marzo 2024',
            'estado': 'En Proceso',
            'resumen': 'Estado de servicios y mantenimientos realizados'
        }
    ]
    return render_template('admin_reportes.html', reportes=reportes)

# Datos falsos para el prototipo
OPERADORES = [
    {'id': 1, 'nombre': 'Juan Pérez', 'ruta': 'Ruta 1', 'estado': 'Activo'},
    {'id': 2, 'nombre': 'María García', 'ruta': 'Ruta 2', 'estado': 'Activo'},
    {'id': 3, 'nombre': 'Carlos López', 'ruta': 'Ruta 3', 'estado': 'Inactivo'}
]

UNIDADES = [
    {'id': 1, 'placas': 'ABC123', 'operador': 'Juan Pérez', 'ruta': 'Ruta 1', 'estado': 'Activo'},
    {'id': 2, 'placas': 'DEF456', 'operador': 'María García', 'ruta': 'Ruta 2', 'estado': 'Mantenimiento'},
    {'id': 3, 'placas': 'GHI789', 'operador': 'Carlos López', 'ruta': 'Ruta 3', 'estado': 'Inactivo'}
]

RUTAS = [
    {'id': 1, 'nombre': 'Ruta 1', 'origen': 'Ciudad A', 'destino': 'Ciudad B'},
    {'id': 2, 'nombre': 'Ruta 2', 'origen': 'Ciudad C', 'destino': 'Ciudad D'},
    {'id': 3, 'nombre': 'Ruta 3', 'origen': 'Ciudad E', 'destino': 'Ciudad F'}
]

SOLICITUDES = [
    {
        'id': 1,
        'tipo': 'cambio_ruta',
        'operador': 'Juan Pérez',
        'ruta_actual': 'Ruta 1',
        'ruta_solicitada': 'Ruta 2',
        'razon': 'Mejor ruta para mi residencia',
        'fecha': '2024-02-20',
        'estado': 'Pendiente'
    },
    {
        'id': 2,
        'tipo': 'cambio_unidad',
        'operador': 'María García',
        'unidad_actual': 'DEF456',
        'unidad_solicitada': 'ABC123',
        'razon': 'Problemas con el aire acondicionado',
        'fecha': '2024-02-21',
        'estado': 'Pendiente'
    },
    {
        'id': 3,
        'tipo': 'taller',
        'unidad': 'GHI789',
        'tipo_mantenimiento': 'Preventivo',
        'descripcion': 'Cambio de aceite y filtros',
        'fecha_estimada': '2024-02-25',
        'fecha': '2024-02-22',
        'estado': 'Pendiente'
    }
]

@app.route('/solicitud-cambio-ruta')
def solicitud_cambio_ruta():
    return render_template('solicitud_cambio_ruta.html', operadores=OPERADORES, rutas=RUTAS)

@app.route('/solicitud-cambio-unidad')
def solicitud_cambio_unidad():
    return render_template('solicitud_cambio_unidad.html', operadores=OPERADORES, unidades=UNIDADES)

@app.route('/solicitudes-pendientes')
def solicitudes_pendientes():
    return render_template('solicitudes_pendientes.html', solicitudes=SOLICITUDES)

@app.route('/enviar-solicitud', methods=['POST'])
def enviar_solicitud():
    data = request.get_json()
    # Simular éxito en el envío
    return jsonify({'success': True, 'message': 'Solicitud enviada correctamente'})

@app.route('/admin/modificar-operador')
def admin_modificar_operador():
    return render_template('admin_modificar_operador.html', operadores=OPERADORES)

# =============================
# Fin del archivo principal
# =============================

if __name__ == '__main__':
    app.run(debug=True)