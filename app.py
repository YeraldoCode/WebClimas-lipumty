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
    return render_template('index.html')

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
    
    # Obtener reportes aprobados y en proceso
    reportes = db.session.query(ReporteClima).filter(
        ReporteClima.estado.in_(['aprobado', 'en_proceso'])
    ).all()
        # Obtener reportes de clima pendientes
    reportes_pendientes = ReporteClima.query.filter_by(estado='pendiente').order_by(ReporteClima.fecha_reporte.desc()).all()
    
    # Obtener vehículos en espera
    vehiculos_espera = Vehiculo.query.filter_by(estatus='Espera').all()
    
    return render_template('taller/index.html', 
                         reportes_pendientes=reportes_pendientes,
                         vehiculos_espera=vehiculos_espera,
                         reportes=reportes)

@app.route('/coordinador')
def coordinador():
    # Obtener solo las unidades con estatus 'Operando'
    unidades_activas = Vehiculo.query.filter_by(estatus='Operando').all()
    return render_template('coordinador/index.html', unidades_activas=unidades_activas)

@app.route('/coordinador/reportar-clima', methods=['GET', 'POST'])
def reportar_clima():
    if request.method == 'POST':
        try:
            # Obtener y validar datos del formulario
            print("Datos recibidos:", request.form)
            vehiculo_id = request.form.get('vehiculo_id')
            descripcion = request.form.get('descripcion')
            
            print(f"Recibido - vehiculo_id: {vehiculo_id}, descripcion: {descripcion}")
            
            if not vehiculo_id or not descripcion:
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
                estado='pendiente',
                fecha_reporte=datetime.now()
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

@app.route('/admin')
@login_required
def admin():
    if current_user.rol != 'logistica':
        flash('No tienes permiso para acceder a esta página', 'error')
        return redirect(url_for('index'))
    
    # Obtener reportes de clima pendientes
    reportes_pendientes = ReporteClima.query.filter_by(estado='pendiente').order_by(ReporteClima.fecha_reporte.desc()).all()
    
    # Obtener vehículos en espera
    vehiculos_espera = Vehiculo.query.filter_by(estatus='Espera').all()
    
    return render_template('logistica/index.html', 
                         reportes_pendientes=reportes_pendientes,
                         vehiculos_espera=vehiculos_espera)

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
        
        reporte.estado = 'completado'
        reporte.fecha_completado = datetime.now()
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

@app.route('/crear-usuario-prueba')
def crear_usuario_prueba():
    # Solo para pruebas, eliminar en producción
    if not Usuario.query.filter_by(username='admin').first():
        usuario = Usuario(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            rol='logistica'
        )
        db.session.add(usuario)
        db.session.commit()
        return 'Usuario creado: admin/admin123'
    return 'Usuario ya existe'

@app.route('/fix-password/<username>')
def fix_password(username):
    user = Usuario.query.filter_by(username=username).first()
    if user:
        # Guardamos la contraseña actual
        current_password = user.password_hash
        # Generamos el hash correcto
        user.password_hash = generate_password_hash(current_password)
        db.session.commit()
        return f'Hash corregido para {username}'
    return 'Usuario no encontrado'

@app.route('/check-user/<username>')
def check_user(username):
    user = Usuario.query.filter_by(username=username).first()
    if user:
        return f'''
        Usuario encontrado:
        ID: {user.id}
        Username: {user.username}
        Password Hash: {user.password_hash}
        Rol: {user.rol}
        '''
    return 'Usuario no encontrado'

@app.route('/create-test-user')
def create_test_user():
    try:
        # Eliminar usuario de prueba si existe
        test_user = Usuario.query.filter_by(username='test').first()
        if test_user:
            db.session.delete(test_user)
            db.session.commit()
        
        # Crear nuevo usuario de prueba
        password = 'test123'
        password_hash = generate_password_hash(password)
        
        new_user = Usuario(
            username='test',
            password_hash=password_hash,
            rol='logistica'
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Verificar que se creó correctamente
        created_user = Usuario.query.filter_by(username='test').first()
        if created_user:
            return f'''
            Usuario de prueba creado exitosamente:
            Username: {created_user.username}
            Password: {password}
            Rol: {created_user.rol}
            Hash: {created_user.password_hash}
            '''
        else:
            return 'Error: Usuario no se creó correctamente'
            
    except Exception as e:
        db.session.rollback()
        return f'Error al crear usuario: {str(e)}'

@app.route('/crear-usuario-taller')
def crear_usuario_taller():
    print("\n=== Creando Usuario Taller ===")
    # Verificar si ya existe el usuario
    user = Usuario.query.filter_by(username='taller').first()
    if user:
        print("Eliminando usuario existente")
        db.session.delete(user)
        db.session.commit()
    
    # Crear nuevo usuario
    user = Usuario(
        username='taller',
        rol='taller',
        email='taller@empresa.com'
    )
    user.set_password('taller123')
    
    print(f"Usuario creado: {user.username}")
    print(f"Rol: {user.rol}")
    print(f"Hash: {user.password_hash}")
    
    db.session.add(user)
    db.session.commit()
    
    return "Usuario de taller creado. Username: taller, Password: taller123"

@app.route('/admin/db-view')
@login_required
def db_view():
    if current_user.rol != 'logistica':
        flash('No tienes permiso para acceder a esta sección')
        return redirect(url_for('index'))
    
    # Obtener datos de cada tabla
    usuarios = Usuario.query.all()
    vehiculos = Vehiculo.query.all()
    reportes = ReporteClima.query.all()
    
    # Preparar datos para mostrar
    data = {
        'usuarios': [{
            'id': u.id,
            'username': u.username,
            'rol': u.rol,
            'email': u.email
        } for u in usuarios],
        'vehiculos': [{
            'id': v.idvehiculo,
            'serial': v.serial,
            'marca': v.marca,
            'modelo': v.modelo,
            'estatus': v.estatus
        } for v in vehiculos],
        'reportes': [{
            'id': r.id,
            'vehiculo_id': r.vehiculo_id,
            'fecha': r.fecha_reporte.strftime('%Y-%m-%d %H:%M') if r.fecha_reporte else None,
            'descripcion': r.descripcion,
            'estado': r.estado,
            'tecnico': r.tecnico.username if r.tecnico else None
        } for r in reportes]
    }
    
    return render_template('admin/db_view.html', data=data)

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