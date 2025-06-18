# App principal para el control y mantenimiento de climas de unidades de transporte.
# Roles: coordinador (sin login), logística (admin), próximamente taller.
# Funcionalidades: revisión, edición, trazabilidad, carga/exportación Excel.

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify, Blueprint
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, FileField, SubmitField
from wtforms.validators import DataRequired
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from forms import LoginForm
import os
from models import db, Vehiculo, Servicio, Usuario, ReporteClima, HistorialReporte
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from werkzeug.utils import secure_filename
import json
from flask_sqlalchemy import SQLAlchemy

# =============================
# Configuración e inicialización
# =============================
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['SECRET_KEY'] = 'tu_clave_secreta'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://lipu_admin:XTHV02bIaM8kXSVuMsZ2Sg7FzZQ5HoQr@dpg-d0qvdpripnbc73ept3m0-a.oregon-postgres.render.com/lipuclimas'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'static/uploads'

    # Deshabilitar CSRF para rutas del coordinador
    app.config['WTF_CSRF_ENABLED'] = False

    # Inicializar extensiones
    db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    csrf = CSRFProtect(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    # Manejador de errores global
    @app.errorhandler(Exception)
    def handle_error(error):
        print(f"Error global: {str(error)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        if request.is_json or request.path.startswith('/coordinador/'):
            return jsonify({
                'success': False,
                'error': str(error)
            }), getattr(error, 'code', 500)
        
        flash(str(error), 'error')
        return redirect(url_for('index'))

    return app

app = create_app()

# =============================
# Cierre de sesión de base de datos
# =============================
@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

# =============================
# Rutas principales
# =============================

@app.route('/')
def index():
    form = LoginForm()
    return render_template('login.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', form=LoginForm())
    
    form = LoginForm()
    if not form.validate():
        flash('Por favor complete todos los campos')
        return render_template('login.html', form=form)
    
    user = Usuario.query.filter_by(username=form.username.data).first()
    if not user or not user.check_password(form.password.data):
        flash('Usuario o contraseña incorrectos')
        return render_template('login.html', form=form)
    
    login_user(user)
    session['role'] = user.rol
    
    if user.rol == 'logistica':
        return redirect('/admin')
    elif user.rol == 'taller':
        return redirect('/taller')
    elif user.rol == 'coordinador':  # Agregar esta condición
        return redirect('/coordinador')
    
    return redirect('/')

@app.route('/logout')
@login_required
def logout():
    session.pop('role', None)
    logout_user()
    return redirect('/')

@app.route('/taller', methods=['GET', 'POST'])
@login_required
def panel_taller():
    if current_user.rol != 'taller':
        flash('No tienes permiso para acceder a esta sección')
        return redirect(url_for('index'))

    # Filtrar reportes aceptados por logística
    reportes_aceptados = ReporteClima.query.filter_by(estado='aprobado').all()

    # Dividir reportes por tipo
    reportes_por_tipo = {}
    eventos = []
    for reporte in reportes_aceptados:
        tipo = reporte.tipo_problema
        if tipo not in reportes_por_tipo:
            reportes_por_tipo[tipo] = []
        reportes_por_tipo[tipo].append(reporte)

        # Crear eventos para el calendario
        eventos.append({
            "titulo": f"{tipo.capitalize()} - Unidad {reporte.vehiculo_id}",
            "fecha_inicio": reporte.fecha_reporte.strftime('%Y-%m-%dT%H:%M:%S'),
            "fecha_fin": (reporte.fecha_reporte + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%S'),
            "descripcion": reporte.descripcion,
            "tipo": tipo,
            "estado": reporte.estado
        })

    # Estadísticas
    estadisticas = {
        'reparacion': len(reportes_por_tipo.get('reparacion', [])),
        'conversion': len(reportes_por_tipo.get('conversion', []))
    }

    # Planificación: manejar datos del calendario
    if request.method == 'POST':
        try:
            fecha_planificada = request.form.get('fecha_planificada')
            tareas = request.form.get('tareas')

            # Validar campos requeridos
            if not fecha_planificada or not tareas:
                flash('Todos los campos son requeridos', 'error')
                return redirect(url_for('panel_taller'))

            # Guardar planificación en la base de datos (ejemplo)
            nueva_planificacion = HistorialReporte(
                usuario_id=current_user.id,
                accion='planificacion',
                descripcion=f"Tareas: {tareas}, Fecha: {fecha_planificada}"
            )
            db.session.add(nueva_planificacion)
            db.session.commit()

            flash('Planificación guardada exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar la planificación: {str(e)}', 'error')

    return render_template('taller/index.html', 
                            reportes_por_tipo=reportes_por_tipo,
                            estadisticas=estadisticas,
                            eventos=eventos)


@app.route('/coordinador')
@login_required
def coordinador():
    print(f"Usuario actual: {current_user.username}, Rol: {current_user.rol}")
    if current_user.rol != 'coordinador':
        flash('No tienes permiso para acceder a esta sección', 'error')
        return redirect(url_for('index'))
    
    unidades_operando = Vehiculo.query.filter_by(estatus='Operando').all()
    total_unidades_operando = len(unidades_operando)
    print(f"Total de unidades operando: {total_unidades_operando}")
    
    return render_template('coordinador/index.html', unidades_operando=unidades_operando, total_unidades_operando=total_unidades_operando)

@app.route('/api/vehiculos')
@login_required
def api_vehiculos():
    vehiculos = Vehiculo.query.all()
    return jsonify([
        {
            "id": v.idvehiculo,
            "descripcion": v.descripcion,
            "placas": v.placas,
            "serial": v.serial,
            "estatus": v.estatus
        }
        for v in vehiculos
    ])


@app.route('/coordinador/reportar-clima', methods=['GET', 'POST'])
@login_required
def reportar_clima():
    if request.method == 'POST':
        try:
            # Obtener y validar datos del formulario
            print("Datos recibidos:", request.form)
            vehiculo_id = request.form.get('vehiculo_id')
            descripcion = request.form.get('descripcion')
            tipo_problema = request.form.get('tipo_problema')  # Nuevo campo
            
            print(f"Recibido - vehiculo_id: {vehiculo_id}, descripcion: {descripcion}, tipo_problema: {tipo_problema}")
            
            # Validar campos requeridos
            if not vehiculo_id or not descripcion or not tipo_problema:
                print("Error: Campos vacíos")
                return jsonify({
                    'success': False, 
                    'error': 'Todos los campos son requeridos'
                }), 400
            
            try:
                vehiculo_id = int(vehiculo_id)
            except ValueError as e:
                print(f"Error: ID de vehículo inválido - {vehiculo_id}")
                print(f"Error detallado: {str(e)}")
                return jsonify({
                    'success': False, 
                    'error': 'ID de vehículo inválido'
                }), 400
            
            # Verificar que el vehículo existe y está operando
            vehiculo = Vehiculo.query.filter_by(idvehiculo=vehiculo_id, estatus='Operando').first()
            print(f"Vehículo encontrado: {vehiculo}")
            
            if not vehiculo:
                print(f"Error: Vehículo no encontrado o no está operando - {vehiculo_id}")
                return jsonify({
                    'success': False, 
                    'error': 'Vehículo no encontrado o no está operando'
                }), 400
            
            # Actualizar estatus del vehículo a 'Espera'
            vehiculo.estatus = 'Espera'
            print(f"Estatus del vehículo actualizado a Espera")
            
            # Crear nuevo reporte
            nuevo_reporte = ReporteClima(
                vehiculo_id=vehiculo_id,
                descripcion=descripcion,
                tipo_problema=tipo_problema,  # Guardar el tipo de problema
                estado='pendiente',
                fecha_reporte=datetime.now(),
                coordinador_id=current_user.id  # Asignar automáticamente el coordinador actual
            )
            
            db.session.add(nuevo_reporte)
            db.session.commit()
            
            print(f"Reporte creado exitosamente para vehículo {vehiculo_id} y estatus actualizado a Espera")
            return jsonify({
                'success': True, 
                'message': 'Reporte creado exitosamente y vehículo puesto en espera'
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Error al crear reporte: {str(e)}")
            print(f"Tipo de error: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'success': False, 
                'error': f'Error al crear el reporte: {str(e)}'
            }), 500
    
    # GET request - mostrar formulario
    try:
        vehiculos = Vehiculo.query.filter_by(estatus='Operando').all()
        print(f"Vehículos operando encontrados: {len(vehiculos)}")
        return render_template('coordinador/reportar.html', vehiculos=vehiculos)
    except Exception as e:
        print(f"Error al cargar vehículos: {str(e)}")
        flash('Error al cargar la lista de vehículos', 'error')
        return redirect(url_for('coordinador'))

@app.route('/admin', methods=['GET'])
@login_required
def admin():
    try:
        if not current_user.is_authenticated:
            flash('Debes iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('login'))

        if current_user.rol != 'logistica':
            flash('No tienes permiso para acceder a esta página', 'error')
            return redirect(url_for('index'))

        # Obtener el número de página actual desde los parámetros de la URL
        page_reparacion = request.args.get('page_reparacion', 1, type=int)
        page_conversion = request.args.get('page_conversion', 1, type=int)
        per_page = 25  # Número de reportes por página

        # Filtrar reportes con estado pendiente
        reportes_reparacion = ReporteClima.query.filter_by(tipo_problema='reparacion', estado='pendiente').order_by(ReporteClima.fecha_reporte.desc()).paginate(page=page_reparacion, per_page=per_page)
        reportes_conversion = ReporteClima.query.filter_by(tipo_problema='conversion', estado='pendiente').order_by(ReporteClima.fecha_reporte.desc()).paginate(page=page_conversion, per_page=per_page)

        return render_template('logistica/index.html', 
                                reportes_reparacion=reportes_reparacion,
                                reportes_conversion=reportes_conversion)
    except Exception as e:
        print(f"Error en la ruta /admin: {str(e)}")
        flash('Ocurrió un error al cargar la página de administración', 'error')
        return redirect(url_for('index'))
    
@app.route('/admin/unidades/<int:unidad_id>/editar', methods=['POST'])
@login_required
def editar_unidad(unidad_id):
    if current_user.rol != 'logistica':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403

    data = request.get_json()
    descripcion = data.get('descripcion')
    estatus = data.get('estatus')

    # Busca el vehículo por ID
    unidad = Vehiculo.query.get(unidad_id)
    if not unidad:
        return jsonify({'success': False, 'error': 'Unidad no encontrada'}), 404

    # Actualiza los campos permitidos
    if descripcion is not None:
        unidad.descripcion = descripcion
    if estatus is not None:
        unidad.estatus = estatus

    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/taller/reporte/<int:reporte_id>/en-proceso', methods=['POST'])
@login_required
def taller_en_proceso(reporte_id):
    if current_user.rol != 'taller':
        return jsonify({'success': False, 'error': 'No autorizado'})

    try:
        reporte = db.session.query(ReporteClima).get(reporte_id)
        if not reporte:
            return jsonify({'success': False, 'error': 'Reporte no encontrado'})

        # Validar que el estado actual sea 'aprobado'
        if reporte.estado != 'aprobado':
            return jsonify({'success': False, 'error': 'El reporte no está aprobado'})

        # Actualizar estado del reporte
        reporte.estado = 'en_proceso'
        reporte.fecha_inicio = datetime.now()

        # Actualizar estado de la unidad asociada
        vehiculo = Vehiculo.query.get(reporte.vehiculo_id)
        if vehiculo:
            vehiculo.estatus = 'Mantenimiento'

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


    
@app.route('/taller/planificar', methods=['POST'])
@login_required
def planificar_taller():
    if current_user.rol != 'taller':
        return jsonify({'success': False, 'error': 'No autorizado'})

    try:
        data = request.json
        reportes = data.get('reportes', [])
        fecha_inicio = data.get('fecha_inicio')

        if not reportes or not fecha_inicio:
            return jsonify({'success': False, 'error': 'Todos los campos son requeridos'})

        # Acepta formato 'YYYY-MM-DDTHH:MM'
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%dT%H:%M')
        except ValueError:
            return jsonify({'success': False, 'error': 'Formato de fecha/hora inválido'})

        for reporte_id in reportes:
            reporte = ReporteClima.query.get(reporte_id)
            if reporte:
                reporte.fecha_inicio = fecha_inicio_dt
                reporte.estado = 'planificado'

        db.session.commit()
        return jsonify({'success': True, 'message': 'Planeación guardada exitosamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
        
@app.route('/taller/reporte/<int:reporte_id>/finalizar', methods=['POST'])
@login_required
def finalizar_mantenimiento(reporte_id):
    if current_user.rol != 'taller':
        return jsonify({'success': False, 'error': 'No autorizado'})
    try:
        reporte = ReporteClima.query.get(reporte_id)
        if not reporte:
            return jsonify({'success': False, 'error': 'Reporte no encontrado'})

        # Actualizar estado y asignar fecha de finalización
        reporte.estado = 'completado'
        reporte.fecha_fin = datetime.now()

        # Cambiar el estatus del vehículo asociado a "Operando"
        vehiculo = Vehiculo.query.get(reporte.vehiculo_id)
        if vehiculo:
            vehiculo.estatus = 'Operando'

        historial = HistorialReporte(
            reporte_id=reporte.id,
            usuario_id=current_user.id,
            accion='completado'
        )
        db.session.add(historial)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Mantenimiento finalizado exitosamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/taller/reporte/<int:reporte_id>/pendiente', methods=['POST'])
@login_required
def marcar_pendiente(reporte_id):
    if current_user.rol != 'taller':
        return jsonify({'success': False, 'error': 'No autorizado'})
    motivo = request.json.get('motivo')
    try:
        reporte = ReporteClima.query.get(reporte_id)
        if not reporte:
            return jsonify({'success': False, 'error': 'Reporte no encontrado'})
        reporte.estado = 'pendiente'
        reporte.descripcion = f"{reporte.descripcion}\nMotivo pendiente: {motivo}"
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
    

@app.route('/taller/reporte/<int:reporte_id>/completado', methods=['POST'])
@login_required
def taller_completado(reporte_id):
    if current_user.rol != 'taller':
        return jsonify({'success': False, 'error': 'No autorizado'})

    try:
        reporte = db.session.query(ReporteClima).get(reporte_id)
        if not reporte:
            return jsonify({'success': False, 'error': 'Reporte no encontrado'})

        # Validar que el estado actual sea 'en_proceso'
        if reporte.estado != 'en_proceso':
            return jsonify({'success': False, 'error': 'El reporte no está en proceso'})

        # Actualizar estado del reporte
        reporte.estado = 'completado'
        reporte.fecha_completado = datetime.now()

        # Cambiar el estatus del vehículo asociado a "Operando"
        vehiculo = Vehiculo.query.get(reporte.vehiculo_id)
        if vehiculo:
            vehiculo.estatus = 'Operando'

        # Registrar en el historial
        historial = HistorialReporte(
            reporte_id=reporte.id,
            usuario_id=current_user.id,
            accion='completado'
        )
        db.session.add(historial)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/export', methods=['GET'])
@login_required
def export():
    if current_user.rol != 'logistica':
        flash('No tienes permiso para acceder a esta sección', 'error')
        return redirect(url_for('index'))
    
    try:
        # Exportar datos de reportes y unidades
        reportes = ReporteClima.query.all()
        vehiculos = Vehiculo.query.all()
        
        # Crear DataFrame para reportes
        reportes_data = [{
            'ID Reporte': r.id,
            'ID Vehículo': r.vehiculo_id,
            'Descripción': r.descripcion,
            'Tipo Problema': r.tipo_problema,
            'Estado': r.estado,
            'Fecha Reporte': r.fecha_reporte
        } for r in reportes]
        df_reportes = pd.DataFrame(reportes_data)
        
        # Crear DataFrame para vehículos
        vehiculos_data = [{
            'ID Vehículo': v.idvehiculo,
            'Descripción': v.descripcion,
            'Estado Actual': v.estatus
        } for v in vehiculos]
        df_vehiculos = pd.DataFrame(vehiculos_data)
        
        # Escribir ambos DataFrames en un archivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_reportes.to_excel(writer, sheet_name='Reportes', index=False)
            df_vehiculos.to_excel(writer, sheet_name='Vehículos', index=False)
        output.seek(0)
        
        return send_file(output, download_name='logistica_datos.xlsx', as_attachment=True)
    except Exception as e:
        flash(f'Error al exportar datos: {str(e)}', 'error')
        return redirect(url_for('admin'))


@app.route('/admin/reportes-clima', methods=['GET'])
@login_required
def admin_reportes_clima():
    if current_user.rol != 'logistica':
        flash('No tienes permiso para acceder a esta sección', 'error')
        return redirect(url_for('index'))
    
    # Obtener todos los reportes pendientes
    reportes = db.session.query(ReporteClima).filter_by(estado='pendiente').all()
    return render_template('logistica/reportes_clima.html', reportes=reportes)


@app.route('/admin/reportes-clima/<int:reporte_id>/aprobar', methods=['POST'])
@login_required
def aprobar_reporte_clima(reporte_id):
    if current_user.rol != 'logistica':
        return jsonify({'success': False, 'error': 'No autorizado'})
    
    try:
        reporte = db.session.query(ReporteClima).get(reporte_id)
        if not reporte:
            return jsonify({'success': False, 'error': 'Reporte no encontrado'})
        
        reporte.estado = 'aprobado'
        reporte.fecha_aprobacion = datetime.now()
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})



@app.route('/admin/reportes-clima/<int:reporte_id>/rechazar', methods=['POST'])
@login_required
def rechazar_reporte_clima(reporte_id):
    if current_user.rol != 'logistica':
        return jsonify({'success': False, 'error': 'No autorizado'})
    
    try:
        reporte = db.session.query(ReporteClima).get(reporte_id)
        if not reporte:
            return jsonify({'success': False, 'error': 'Reporte no encontrado'})
        
        reporte.estado = 'rechazado'
        reporte.fecha_aprobacion = datetime.now()
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})



@app.route('/admin/unidades', methods=['GET'])
@login_required
def admin_unidades():
    if current_user.rol != 'logistica':
        flash('No tienes permiso para acceder a esta sección', 'error')
        return redirect(url_for('index'))

    # Obtener parámetros de búsqueda
    id_vehiculo = request.args.get('id_vehiculo', type=int)
    planta = request.args.get('planta', type=str)
    estado_actual = request.args.get('estado_actual', type=str)

    # Filtrar unidades según los parámetros 
    query = Vehiculo.query.filter(Vehiculo.estatus.in_(['Operando', 'Espera', 'Mantenimiento']))
    if id_vehiculo:
        query = query.filter_by(idvehiculo=id_vehiculo)
    if planta:
        query = query.filter(Vehiculo.descripcion.ilike(f'%{planta}%'))
    if estado_actual:
        query = query.filter_by(estatus=estado_actual)

    unidades = query.all()  # Obtener todos los registros sin paginación
    return render_template('logistica/unidades.html', unidades=unidades)

@app.route('/api/eventos', methods=['GET'])
@login_required
def api_eventos():
    reportes = ReporteClima.query.filter(
        ReporteClima.estado.in_(['planificado', 'completado'])
    ).all()
    eventos = []
    for reporte in reportes:
        if not reporte.fecha_inicio:
            continue  # Ignora reportes sin fecha de inicio
        eventos.append({
            "id": reporte.id,
            "title": f"Reporte {reporte.id}",
            "start": reporte.fecha_inicio.strftime('%Y-%m-%dT%H:%M:%S'),
            "descripcion": reporte.descripcion,
            "vehiculo_id": reporte.vehiculo_id,
            "vehiculo_descripcion": reporte.vehiculo.descripcion if reporte.vehiculo else "",
            "coordinador_username": reporte.coordinador.username if reporte.coordinador else "",
            "estado": reporte.estado,
            "color": "green" if reporte.estado == 'completado' else "orange"
        })
    return jsonify(eventos)

@app.route('/api/reportes')
@login_required
def api_reportes():
    fecha = request.args.get('fecha')
    tipo = request.args.get('tipo', 'dia')
    query = ReporteClima.query

    if fecha:
        from datetime import datetime, timedelta
        fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
        if tipo == 'semana':
            fin_semana = fecha_dt + timedelta(days=6)
            query = query.filter(ReporteClima.fecha_inicio >= fecha_dt, ReporteClima.fecha_inicio <= fin_semana)
        else:
            query = query.filter(db.func.date(ReporteClima.fecha_inicio) == fecha_dt.date())
    reportes = query.order_by(ReporteClima.fecha_inicio).all()
    return jsonify([
    {
        'vehiculo_id': r.vehiculo_id,
        'vehiculo_descripcion': r.vehiculo.descripcion if r.vehiculo else '',
        'descripcion': r.descripcion,
        'fecha_inicio': r.fecha_inicio.isoformat() if r.fecha_inicio else '',
        'estado': r.estado
    } for r in reportes
])

@app.route('/taller/lista-reportes')
@login_required
def taller_lista_reportes():
    if current_user.rol != 'taller':
        return redirect(url_for('index'))
    return render_template('taller/lista_reportes.html')

# =============================
# Fin del archivo principal
# =============================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)