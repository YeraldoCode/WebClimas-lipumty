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

# =============================
# Configuración e inicialización
# =============================
app = Flask(__name__)
app.config.from_object(Config)

# Inicializar extensiones
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
csrf = CSRFProtect(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

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
        flash('No tienes permiso para acceder a esta sección')
        return redirect('/')
    
    reportes = ReporteClima.query.filter_by(estado='pendiente').all()
    return render_template('taller/index.html', reportes=reportes)

@app.route('/coordinador')
def coordinador():
    vehiculos = Vehiculo.query.all()
    return render_template('coordinador/index.html', vehiculos=vehiculos)

@app.route('/coordinador/reportar')
def reportar():
    vehiculos = Vehiculo.query.all()
    return render_template('coordinador/reportar.html', vehiculos=vehiculos)

@app.route('/coordinador/reportar-clima', methods=['POST'])
@csrf.exempt
def reportar_clima():
    print("\n=== Datos recibidos en reportar-clima ===")
    print(f"Form data completo: {request.form}")
    print(f"Headers: {request.headers}")
    
    vehiculo_id = request.form.get('vehiculo_id')
    descripcion = request.form.get('descripcion')
    
    if not vehiculo_id or not descripcion:
        print("Error: Faltan datos requeridos")
        return jsonify({
            'success': False, 
            'error': 'Faltan datos requeridos'
        }), 400
    
    try:
        # Verificar que el vehículo existe usando Session.get()
        vehiculo = db.session.get(Vehiculo, vehiculo_id)
        if not vehiculo:
            print(f"Error: Vehículo {vehiculo_id} no encontrado")
            return jsonify({
                'success': False,
                'error': 'Vehículo no encontrado'
            }), 404
        
        # Ahora que sabemos que el vehículo existe, podemos acceder a sus propiedades
        print(f"Vehículo ID: {vehiculo_id}")
        print(f"Planta: {vehiculo.descripcion}")
        print(f"Descripción del problema: {descripcion}")
        
        reporte = ReporteClima(
            vehiculo_id=vehiculo_id,
            descripcion=descripcion,
            estado='pendiente'
        )
        
        db.session.add(reporte)
        db.session.commit()
        print("Reporte guardado exitosamente")
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error al guardar reporte: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/admin')
@login_required
def admin():
    if current_user.rol != 'logistica':
        flash('No tienes permiso para acceder a esta sección')
        return redirect('/')
    
    return render_template('logistica/index.html')

@app.route('/taller/revisar/<int:reporte_id>')
@login_required
def revisar_reporte(reporte_id):
    if current_user.rol != 'taller':
        flash('No tienes permiso para acceder a esta sección')
        return redirect(url_for('index'))
    
    reporte = ReporteClima.query.get_or_404(reporte_id)
    return render_template('taller/revisar.html', reporte=reporte)

@app.route('/taller/completar/<int:reporte_id>', methods=['POST'])
@login_required
def completar_reporte(reporte_id):
    print("\n=== Datos recibidos en completar-reporte ===")
    print(f"Form data completo: {request.form}")
    print(f"Reporte ID: {reporte_id}")
    
    if current_user.rol != 'taller':
        print("Acceso denegado: Usuario no es de taller")
        return jsonify({'success': False, 'error': 'No autorizado'})
    
    reporte = ReporteClima.query.get_or_404(reporte_id)
    solucion = request.form.get('solucion')
    print(f"Solución: {solucion}")
    
    try:
        reporte.estado = 'completado'
        reporte.solucion = solucion
        reporte.tecnico_id = current_user.id
        reporte.fecha_revision = datetime.utcnow()
        
        db.session.commit()
        print("Reporte completado exitosamente")
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error al completar reporte: {str(e)}")
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

# =============================
# Fin del archivo principal
# =============================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)