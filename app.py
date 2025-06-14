# App principal para el control y mantenimiento de climas de unidades de transporte.
# Roles: coordinador (sin login), logística (admin), próximamente taller.
# Funcionalidades: revisión, edición, trazabilidad, carga/exportación Excel.

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, FileField, SubmitField
from wtforms.validators import DataRequired
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from forms import LoginForm
import os
from models import db, Vehiculo, Servicio, Usuario, ReporteClima
import pandas as pd
from io import BytesIO
from datetime import datetime
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

@app.route('/taller')
@login_required
def taller():
    if current_user.rol != 'taller':
        flash('No tienes permiso para acceder a esta sección', 'error')
        return redirect(url_for('index'))

    # Obtener reportes aceptados por logística
    reportes_aceptados = ReporteClima.query.filter_by(estado='aprobado').order_by(ReporteClima.fecha_reporte.desc()).all()

    # Depurar datos de los reportes
    for reporte in reportes_aceptados:
        print(f"Reporte ID: {reporte.id}, Coordinador: {reporte.coordinador.username if reporte.coordinador else 'Desconocido'}, Tipo de Problema: {reporte.tipo_problema}")

    return render_template('taller/index.html', 
                        reportes_aceptados=reportes_aceptados)

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
    

@app.route('/taller/revisar/<int:reporte_id>')
@login_required
def revisar_reporte(reporte_id):
    if current_user.rol != 'taller':
        flash('No tienes permiso para acceder a esta sección')
        return redirect(url_for('index'))
    
    reporte = ReporteClima.query.get_or_404(reporte_id)
    return render_template('taller/revisar.html', reporte=reporte)

@app.route('/taller/reporte/<int:reporte_id>/en-proceso', methods=['POST'])
@login_required
def taller_en_proceso(reporte_id):
    if current_user.rol != 'taller':
        return jsonify({'success': False, 'error': 'No autorizado'})
    
    try:
        reporte = db.session.query(ReporteClima).get(reporte_id)
        if not reporte:
            return jsonify({'success': False, 'error': 'Reporte no encontrado'})
        
        if reporte.estado != 'aprobado':
            return jsonify({'success': False, 'error': 'El reporte no está aprobado'})
        
        reporte.estado = 'en_proceso'
        reporte.fecha_inicio = datetime.now()
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
        
        if reporte.estado not in ['aprobado', 'en_proceso']:
            return jsonify({'success': False, 'error': 'El reporte no está en un estado válido'})
        
        # Cambiar el estado del reporte a "completado"
        reporte.estado = 'completado'
        reporte.fecha_completado = datetime.now()
        
        # Cambiar el estatus del vehículo asociado a "Operando"
        vehiculo = Vehiculo.query.get(reporte.vehiculo_id)
        if vehiculo:
            vehiculo.estatus = 'Operando'
        
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
    




@app.route('/admin/upload', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        flash('No se ha seleccionado ningún archivo.', 'danger')
        return redirect(url_for('admin'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No se ha seleccionado ningún archivo.', 'danger')
        return redirect(url_for('admin'))
    
    if file and file.filename.endswith('.xlsx'):
        try:
            df = pd.read_excel(file)
            
            for _, row in df.iterrows():
                vehiculo = Vehiculo.query.filter_by(idvehiculo=row['IdVehiculo']).first()
                
                if vehiculo:
                    # Actualizar vehículo existente
                    for col in df.columns:
                        if col in row and not pd.isna(row[col]):
                            setattr(vehiculo, col.lower().replace(' ', '_'), row[col])
                else:
                    # Crear nuevo vehículo
                    vehiculo_data = {}
                    for col in df.columns:
                        if col in row and not pd.isna(row[col]):
                            vehiculo_data[col.lower().replace(' ', '_')] = row[col]
                    
                    vehiculo = Vehiculo(**vehiculo_data)
                    db.session.add(vehiculo)
            
            db.session.commit()
            flash('Datos cargados correctamente.', 'success')
            
        except Exception as e:
            flash(f'Error al procesar el archivo: {str(e)}', 'danger')
            
    return redirect(url_for('admin'))

@app.route('/admin/export')
def export():
    # Exporta la información consolidada de vehículos y servicios a Excel
    results = db.session.query(
        Vehiculo,
        Servicio.marca_ac
    ).join(Servicio, Vehiculo.idvehiculo == Servicio.id).all()
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

# =============================
# Fin del archivo principal
# =============================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)