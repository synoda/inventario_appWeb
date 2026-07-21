import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_migrate import Migrate
# 1. Agregamos 'Usuario' a los modelos
from models import db, Categoria, Proveedor, Producto, Cliente, Venta, VentaDetalle, Usuario
# 2. Agregamos 'LoginForm' y 'RegistroForm' a los formularios
from forms import CategoriaForm, ProveedorForm, ProductoForm, ClienteForm, LoginForm, RegistroForm
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
from flask import abort

app = Flask(__name__)

# SECRET_KEY: en Railway se define como variable de entorno.
# Si no existe (ej. desarrollo local), se usa un valor por defecto.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mi_llave_secreta_muy_segura')

basedir = os.path.abspath(os.path.dirname(__file__))

# Base de datos: si Railway provee DATABASE_URL (ej. al agregar un plugin de
# PostgreSQL) se usa esa; si no, se usa SQLite local como hasta ahora.
database_url = os.environ.get(
    'DATABASE_URL',
    'sqlite:///' + os.path.join(basedir, 'inventario.db')
)
# Railway (y Heroku) entregan la URL como "postgres://", pero SQLAlchemy 1.4+
# exige el prefijo "postgresql://". Se corrige automáticamente si aplica.
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)
with app.app_context():
    # 1. Crea las tablas si el archivo .db no existe
    db.create_all()
    
    # 2. Crea el admin si no existe
    if not Usuario.query.filter_by(username='admin').first():
        admin = Usuario(username='admin', rol='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print(">>> Base de datos SQLite creada e inicializada con usuario 'admin'")


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Nombre de la ruta de login
login_manager.login_message = "Por favor inicia sesión para acceder."



# --- Login ---
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Decorador personalizado para proteger rutas de administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Acceso denegado: Se requieren permisos de administrador.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = Usuario.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Bienvenido de nuevo.', 'success')
            return redirect(url_for('index'))
        flash('Usuario o contraseña incorrectos.', 'danger')
    return render_template('auth/login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/usuarios/registro', methods=['GET', 'POST'])
@admin_required # Solo un admin puede registrar nuevos usuarios
def registro():
    form = RegistroForm()
    if form.validate_on_submit():
        nuevo_u = Usuario(username=form.username.data, rol=form.rol.data)
        nuevo_u.set_password(form.password.data)
        db.session.add(nuevo_u)
        db.session.commit()
        flash('Usuario registrado.', 'success')
        return redirect(url_for('index'))
    return render_template('auth/registro.html', form=form)

# --- DASHBOARD ---
@app.route('/')
@login_required
def index():
    total_prod = Producto.query.count()
    total_cli = Cliente.query.count()
    total_prov = Proveedor.query.count()
    stock_bajo = Producto.query.filter(Producto.stock <= Producto.stock_minimo).all()
    ultimas_ventas = Venta.query.order_by(Venta.fecha.desc()).limit(5).all()
    
    return render_template('index.html', total_prod=total_prod, total_cli=total_cli, 
                           total_prov=total_prov, stock_bajo=stock_bajo, ultimas_ventas=ultimas_ventas)

# --- CRUD CATEGORIAS ---
@app.route('/categorias')
@admin_required
def categorias():
    cats = Categoria.query.all()
    return render_template('categories/index.html', categorias=cats)

@app.route('/categorias/nuevo', methods=['GET', 'POST'])
@admin_required
def categoria_form(id=None):
    cat = Categoria.query.get(id) if id else Categoria()
    form = CategoriaForm(obj=cat)
    if form.validate_on_submit():
        form.populate_obj(cat)
        try:
            if not id: db.session.add(cat)
            db.session.commit()
            flash('Categoría guardada con éxito', 'success')
            return redirect(url_for('categorias'))
        except IntegrityError:
            db.session.rollback()
            flash('El nombre de la categoría ya existe', 'danger')
    return render_template('categories/form.html', form=form, edit=(id is not None))

@app.route('/categorias/eliminar/<int:id>')
@admin_required
def eliminar_categoria(id):
    cat = Categoria.query.get_or_404(id)
    if cat.productos:
        flash('No se puede eliminar: tiene productos asociados', 'danger')
    else:
        db.session.delete(cat)
        db.session.commit()
        flash('Categoría eliminada', 'success')
    return redirect(url_for('categorias'))

# --- CRUD PRODUCTOS ---
@app.route('/productos')
@admin_required
def productos():
    prods = Producto.query.all()
    return render_template('products/index.html', productos=prods)

@app.route('/productos/nuevo', methods=['GET', 'POST'])
@app.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def producto_form(id=None):
    prod = Producto.query.get(id) if id else Producto()
    form = ProductoForm(obj=prod)
    form.categoria_id.choices = [(c.id, c.nombre) for c in Categoria.query.all()]
    form.proveedor_id.choices = [(p.id, p.nombre) for p in Proveedor.query.all()]
    
    if form.validate_on_submit():
        form.populate_obj(prod)
        try:
            if not id: db.session.add(prod)
            db.session.commit()
            flash('Producto guardado', 'success')
            return redirect(url_for('productos'))
        except IntegrityError:
            db.session.rollback()
            flash('El código del producto ya existe', 'danger')
    return render_template('products/form.html', form=form, edit=(id is not None))

# --- MÓDULO DE VENTAS ---
@app.route('/ventas')
@login_required
def ventas():
    cliente_id = request.args.get('cliente_id')
    fecha = request.args.get('fecha')
    query = Venta.query
    if cliente_id:
        query = query.filter_by(cliente_id=cliente_id)
    if fecha:
        query = query.filter(db.func.date(Venta.fecha) == fecha)
    
    ventas_list = query.order_by(Venta.fecha.desc()).all()
    clientes = Cliente.query.all()
    return render_template('sales/index.html', ventas=ventas_list, clientes=clientes)

@app.route('/ventas/nueva', methods=['GET', 'POST'])
@login_required
def nueva_venta():
    if request.method == 'POST':
        # Procesamiento de la venta (JSON enviado vía Fetch o Form POST)
        data = request.form
        cliente_id = data.get('cliente_id')
        productos_ids = request.form.getlist('producto_id[]')
        cantidades = request.form.getlist('cantidad[]')
        
        if not productos_ids:
            flash('Debe agregar al menos un producto', 'danger')
            return redirect(url_for('nueva_venta'))

        try:
            nueva_v = Venta(cliente_id=cliente_id, fecha=datetime.now())
            db.session.add(nueva_v)
            total_venta = 0
            
            for p_id, cant in zip(productos_ids, cantidades):
                p_id = int(p_id)
                cant = int(cant)
                prod = Producto.query.get(p_id)
                
                if prod.stock < cant:
                    db.session.rollback()
                    flash(f'Stock insuficiente para {prod.nombre}', 'danger')
                    return redirect(url_for('nueva_venta'))
                
                # Descontar Stock
                prod.stock -= cant
                subtotal = prod.precio * cant
                detalle = VentaDetalle(venta=nueva_v, producto_id=p_id, 
                                       cantidad=cant, precio_unitario=prod.precio, 
                                       subtotal=subtotal)
                db.session.add(detalle)
                total_venta += subtotal
            
            nueva_v.total = total_venta
            db.session.commit()
            flash(f'Venta #{nueva_v.id} realizada con éxito', 'success')
            return redirect(url_for('ventas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al procesar la venta: {str(e)}', 'danger')
            
    clientes = Cliente.query.all()
    productos = Producto.query.filter(Producto.stock > 0).all()
    return render_template('sales/create.html', clientes=clientes, productos=productos)

@app.route('/ventas/<int:id>')
@login_required
def detalle_venta(id):
    venta = Venta.query.get_or_404(id)
    return render_template('sales/detail.html', venta=venta)

# Rutas CRUD para Clientes y Proveedores se implementan de forma similar...
# (Omitidas por brevedad pero siguen el patrón de categorías)
@app.route('/clientes')
@login_required
def clientes():
    cls = Cliente.query.all()
    return render_template('customers/index.html', clientes=cls)

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
@login_required
def cliente_form(id=None):
    cli = Cliente()
    form = ClienteForm(obj=cli)
    if form.validate_on_submit():
        form.populate_obj(cli)
        db.session.add(cli)
        db.session.commit()
        flash('Cliente registrado', 'success')
        return redirect(url_for('clientes'))
    return render_template('customers/form.html', form=form)


@app.route('/proveedores')
@admin_required
def proveedores():
    provs = Proveedor.query.all()
    return render_template('suppliers/index.html', proveedores=provs)

@app.route('/proveedores/nuevo', methods=['GET', 'POST'])
@app.route('/proveedores/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def proveedor_form(id=None):
    prov = Proveedor.query.get(id) if id else Proveedor()
    form = ProveedorForm(obj=prov)
    
    if form.validate_on_submit():
        form.populate_obj(prov)
        if not id:
            db.session.add(prov)
        try:
            db.session.commit()
            flash('Proveedor guardado con éxito', 'success')
            return redirect(url_for('proveedores'))
        except Exception as e:
            db.session.rollback()
            flash('Error al guardar el proveedor', 'danger')
            
    return render_template('suppliers/form.html', form=form, edit=(id is not None))

@app.route('/proveedores/eliminar/<int:id>')
@admin_required
def eliminar_proveedor(id):
    prov = Proveedor.query.get_or_404(id)
    if prov.productos:
        flash('No se puede eliminar: este proveedor tiene productos asociados', 'danger')
    else:
        db.session.delete(prov)
        db.session.commit()
        flash('Proveedor eliminado', 'success')
    return redirect(url_for('proveedores'))


# --- Utilidad de emergencia: crear/resetear el usuario admin ---
# Visita esta URL una sola vez para garantizar que el usuario admin exista:
#   https://TU-APP.up.railway.app/setup-admin?token=EL_VALOR_QUE_PUSISTE_EN_SETUP_TOKEN
# Requiere la variable de entorno SETUP_TOKEN configurada en Railway.
# Opcionalmente puedes definir ADMIN_USERNAME y ADMIN_PASSWORD para elegir
# el usuario/clave; si no los defines, usa admin / admin123.
@app.route('/setup-admin')
def setup_admin():
    setup_token = os.environ.get('SETUP_TOKEN')
    token_recibido = request.args.get('token')

    if not setup_token or token_recibido != setup_token:
        abort(404)

    username = os.environ.get('ADMIN_USERNAME', 'admin')
    password = os.environ.get('ADMIN_PASSWORD', 'admin123')

    usuario = Usuario.query.filter_by(username=username).first()
    if usuario:
        usuario.set_password(password)
        usuario.rol = 'admin'
        db.session.commit()
        return f'Usuario "{username}" ya existía: se actualizó su contraseña y rol a admin.'
    else:
        usuario = Usuario(username=username, rol='admin')
        usuario.set_password(password)
        db.session.add(usuario)
        db.session.commit()
        return f'Usuario "{username}" creado con rol admin.'


if __name__ == '__main__':
    # Este bloque solo se ejecuta cuando corres "python app.py" en local.
    # En Railway, gunicorn (ver Procfile) importa la app directamente y
    # este bloque nunca se ejecuta.
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', '1') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)