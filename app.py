from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FileField, SubmitField
from wtforms.validators import DataRequired
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import os
from models import db, Vehiculo, Servicios
import pandas as pd
from io import BytesIO


app = Flask(__name__)
app.config.from_object('config.Config')

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login_logistica'

@login_manager.user_loader
def load_user(user_id):
    from models import AdminUser
    return AdminUser.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login_coordinador', methods=['GET', 'POST'])
def login_coordinador():
    if request.method == 'POST':
        return redirect(url_for('coordinador_select'))
    return render_template('login_coordinador.html')


@app.route('/coordinador/select', methods=['GET', 'POST'])
def coordinador_select():
    # Solo los vehículos que cumplen los filtros del admin
    vehiculos = Vehiculo.query.filter(
        Vehiculo.Gpo_estatus == 'Activo',
        Vehiculo.Uso == 'Operaciones',
        Vehiculo.Estatus == 'Operando',
        Vehiculo.Descripcion != None,
        Vehiculo.Descripcion != ''
    ).all()
    # Clientes únicos
    clientes = sorted(set(v.Descripcion for v in vehiculos))
    selected_cliente = request.form.get('cliente')
    unidades = []
    if selected_cliente:
        unidades = [v for v in vehiculos if v.Descripcion == selected_cliente]
        for v in unidades:
            v.revisado = all(getattr(v, campo) not in [None, '', ' '] for campo in ['aire', 'jala', 'mochila', 'conversion_reparacion'])
    if request.method == 'POST' and request.form.get('id_vehiculo'):
        return redirect(url_for('coordinador', id_vehiculo=request.form.get('id_vehiculo')))
    return render_template('coordinador_select.html', clientes=clientes, unidades=unidades, selected_cliente=selected_cliente)

@app.route('/coordinador', methods=['GET', 'POST'])
def coordinador():
    id_vehiculo = request.args.get('id_vehiculo') if request.method == 'GET' else request.form.get('id_vehiculo')
    datos = None
    error = None
    msg = None
    if id_vehiculo:
        vehiculo = Vehiculo.query.filter_by(IdVehiculo=id_vehiculo).first()
        if not vehiculo:
            error = "Vehículo no encontrado"
        elif request.method == 'POST':
            vehiculo.aire = request.form.get('aire')
            vehiculo.jala = request.form.get('jala')
            vehiculo.mochila = request.form.get('mochila')
            vehiculo.conversion_reparacion = request.form.get('conversion_reparacion')
            vehiculo.reinsidente = request.form.get('reinsidente')
            db.session.commit()
            msg = "Datos actualizados correctamente."
        datos = {
            'id_vehiculo': vehiculo.IdVehiculo,
            'Serial': vehiculo.Serial,
            'Marca': vehiculo.Marca,
            'Modelo': vehiculo.Modelo,
            'Asientos': vehiculo.Asientos,
            'Año': vehiculo.Año,
            'Tipo vehiculo': vehiculo.Tipo_vehiculo,
            'Gpo. estatus': vehiculo.Gpo_estatus,
            'Estatus': vehiculo.Estatus,
            'Descripcion': vehiculo.Descripcion,
            'aire': vehiculo.aire,
            'jala': vehiculo.jala,
            'mochila': vehiculo.mochila,
            'conversion_reparacion': vehiculo.conversion_reparacion,
            'reinsidente': vehiculo.reinsidente
        }
    return render_template('coordinador.html', datos=datos, error=error, msg=msg)

@app.route('/login_logistica', methods=['GET', 'POST'])
def login_logistica():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'BLOVILLO':
            session['admin_autenticado'] = True
            return redirect(url_for('admin_panel'))
        else:
            error = "Contraseña incorrecta" 
            return render_template('login_logistica.html', error=error)
    return render_template('login_logistica.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('admin_autenticado'):
        return redirect(url_for('login_logistica'))
    vehiculos = Vehiculo.query.all()
    filtrados = []
    for v in vehiculos:
        v.revisado = all(getattr(v, campo) not in [None, '', ' '] for campo in ['aire', 'jala', 'mochila', 'conversion_reparacion'])
        if (
            v.Gpo_estatus == 'Activo' and
            v.Uso == 'Operaciones' and
            v.Estatus == 'Operando' and
            v.Descripcion not in [None, '', ' ']
        ):
            filtrados.append(v)
    filtrados = sorted(filtrados, key=lambda v: (v.Descripcion or '').lower())
    return render_template('admin.html', vehiculos=filtrados)

@app.route('/admin/upload', methods=['POST'])
#@login_required
def upload_excel():
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
                vehiculo = Vehiculo.query.filter_by(IdVehiculo=row['IdVehiculo']).first()
                if vehiculo:
                    for col in ['Serial', 'Marca', 'Modelo', 'Asientos', 'Motor', 'Año', 'Tipo_vehiculo', 'Gpo_estatus', 'Uso', 'Estatus', 'Combustible', 'Eco', 'Placas', 'Placas_federales', 'Descripcion', 'aire', 'jala', 'mochila', 'conversion_reparacion', 'reinsidente']:
                        if col in row:
                            setattr(vehiculo, col, clean_nan(row[col]))
                else:
                    vehiculo = Vehiculo(**{col: clean_nan(row.get(col)) for col in ['IdVehiculo', 'Serial', 'Marca', 'Modelo', 'Asientos', 'Motor', 'Año', 'Tipo_vehiculo', 'Gpo_estatus', 'Uso', 'Estatus', 'Combustible', 'Eco', 'Placas', 'Placas_federales', 'Descripcion', 'aire', 'jala', 'mochila', 'conversion_reparacion', 'reinsidente']})
                    db.session.add(vehiculo)
            db.session.commit()
            flash('Vehículos actualizados correctamente.', 'success')
        elif 'servicios' in filename:
            for _, row in df.iterrows():
                servicio = Servicios.query.filter_by(ID=row['ID']).first()
                if servicio:
                    for col in ['Marca_AC']:
                        if col in row:
                            setattr(servicio, col, row[col])
                else:
                    servicio = Servicios(**{col: row.get(col) for col in ['ID', 'Marca_AC']})
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
    # JOIN entre Vehiculos y Servicios
    results = db.session.query(
        Vehiculo,
        Servicios.Marca_AC
    ).join(Servicios, Vehiculo.IdVehiculo == Servicios.ID).all()
    # Convierte a DataFrame
    data = []
    for v, marca_ac in results:
        row = {col: getattr(v, col) for col in [
            'IdVehiculo', 'Serial', 'Marca', 'Modelo', 'Asientos', 'Motor', 'Año', 'Tipo_vehiculo', 'Gpo_estatus', 'Uso', 'Estatus', 'Combustible', 'Eco', 'Placas', 'Placas_federales', 'Descripcion', 'aire', 'jala', 'mochila', 'conversion_reparacion', 'reinsidente']}
        row['Marca_AC'] = marca_ac
        data.append(row)
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return send_file(output, download_name='sigo_climas.xlsx', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)