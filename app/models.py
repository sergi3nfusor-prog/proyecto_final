from datetime import datetime, timezone
from flask_login import UserMixin
from . import db


# ─────────────────────────────────────────────
# AUTENTICACIÓN
# ─────────────────────────────────────────────

class UsuarioEmpleado(UserMixin, db.Model):
    """Tabla existente usuarioempleado + columna rol (nueva)."""
    __tablename__ = "usuarioempleado"

    IDUsuarioEmpleado = db.Column('idusuarioempleado', db.Integer, primary_key=True)
    nombreUsuario = db.Column('nombreusuario', db.String(45), nullable=False, unique=True)
    # Guardamos SIEMPRE el hash — la columna en BD es VARCHAR(255) tras el ALTER
    contraseniaUsuario = db.Column('contraseniausuario', db.String(255), nullable=False)
    # Columna nueva agregada por migración
    rol = db.Column('rol', db.String(20), nullable=False, default="vendedor")

    # Relación con empleado (backref permite user.empleado)
    empleado = db.relationship("Empleado", backref="usuario", uselist=False, lazy="select")

    # ── Flask-Login ──
    def get_id(self):
        return str(self.IDUsuarioEmpleado)

    @property
    def is_active(self):
        return True

    def has_role(self, role):
        return self.rol == role


# ─────────────────────────────────────────────
# EMPLEADOS Y SUCURSALES
# ─────────────────────────────────────────────

class Empleado(db.Model):
    __tablename__ = "empleado"

    IDEmpleado = db.Column('idempleado', db.Integer, primary_key=True)
    nombre = db.Column('nombre', db.String(45))
    apellidoMaterno = db.Column('apellidomaterno', db.String(45))
    apellidoPaterno = db.Column('apellidopaterno', db.String(45))
    IDUsuarioEmpleado = db.Column('idusuarioempleado', db.Integer, db.ForeignKey('usuarioempleado.idusuarioempleado'))

    # Relaciones
    ventas            = db.relationship("Venta", backref="empleado", lazy="dynamic")
    sucursales        = db.relationship("EmpleadoSucursal", backref="empleado", lazy="select")


class Sucursal(db.Model):
    __tablename__ = "sucursal"

    IDSucursal = db.Column('idsucursal', db.Integer, primary_key=True)
    horarioAtencion = db.Column('horarioatencion', db.Time)
    correo = db.Column('correo', db.String(45))
    telefono = db.Column('telefono', db.String(45))
    nombreSucursal = db.Column('nombresucursal', db.String(45))
    pais = db.Column('pais', db.String(45))
    calle = db.Column('calle', db.String(45))
    ciudad = db.Column('ciudad', db.String(45))
    numeroProvincia = db.Column('numeroprovincia', db.String(45))

    empleados = db.relationship("EmpleadoSucursal", backref="sucursal", lazy="select")


class EmpleadoSucursal(db.Model):
    __tablename__ = "empleadosucursal"

    IDEmpleadoSucursal = db.Column('idempleadosucursal', db.Integer, primary_key=True)
    IDEmpleado = db.Column('idempleado', db.Integer, db.ForeignKey('empleado.idempleado'))
    IDSucursal = db.Column('idsucursal', db.Integer, db.ForeignKey('sucursal.idsucursal'))


# ─────────────────────────────────────────────
# CLIENTES
# ─────────────────────────────────────────────

class Cliente(db.Model):
    __tablename__ = "cliente"

    IDCliente = db.Column('idcliente', db.Integer, primary_key=True)
    nombre = db.Column('nombre', db.String(100), nullable=False)
    apellidoPaterno = db.Column('apellidopaterno', db.String(100))
    apellidoMaterno = db.Column('apellidomaterno', db.String(100))
    genero = db.Column('genero', db.String(100))
    ci = db.Column('ci', db.String(100))

    ventas          = db.relationship("Venta", backref="cliente", lazy="dynamic")
    programa        = db.relationship("ProgramaFidelizacion", backref="cliente", uselist=False)


class ProgramaFidelizacion(db.Model):
    __tablename__ = "programafidelizacion"

    IDProgramaFidelizacion = db.Column('idprogramafidelizacion', db.Integer, primary_key=True)
    puntosAcumulados = db.Column('puntosacumulados', db.Integer)
    nivel = db.Column('nivel', db.String(45))
    fechaUltimaCompra = db.Column('fechaultimacompra', db.Date)
    puntosFidelizacion = db.Column('puntosfidelizacion', db.Integer)
    IDCliente = db.Column('idcliente', db.Integer, db.ForeignKey('cliente.idcliente'))


# ─────────────────────────────────────────────
# INVENTARIO Y PRODUCTOS
# ─────────────────────────────────────────────

class Inventario(db.Model):
    __tablename__ = "inventario"

    IDInventario = db.Column('idinventario', db.Integer, primary_key=True)
    stockActual = db.Column('stockactual', db.Integer)
    estado = db.Column('estado', db.String(10))
    stockMaximo = db.Column('stockmaximo', db.Integer)
    stockMinimo = db.Column('stockminimo', db.Integer)

    productos    = db.relationship("Producto", backref="inventario", lazy="select")


class Proveedor(db.Model):
    __tablename__ = "proveedor"

    IDProveedor = db.Column('idproveedor', db.Integer, primary_key=True)
    tipoProveedor = db.Column('tipoproveedor', db.String(100))
    nombreProveedor = db.Column('nombreproveedor', db.String(100))
    personaContacto = db.Column('personacontacto', db.String(100))
    tiempoEntrega = db.Column('tiempoentrega', db.String(100))

    productos = db.relationship("Producto", backref="proveedor", lazy="select")


class Producto(db.Model):
    __tablename__ = "producto"

    IDProducto = db.Column('idproducto', db.Integer, primary_key=True)
    accesorios = db.Column('accesorios', db.String(45))
    precio = db.Column('precio', db.Numeric(18, 2))
    temporada = db.Column('temporada', db.String(45))
    fechaIngreso = db.Column('fechaingreso', db.Date)
    nombreProducto = db.Column('nombreproducto', db.String(45))
    marca = db.Column('marca', db.String(45))
    estado = db.Column('estado', db.String(45))
    material = db.Column('material', db.String(45))
    talla = db.Column('talla', db.String(45))
    descripcion = db.Column('descripcion', db.String(100))
    IDProveedor = db.Column('idproveedor', db.Integer, db.ForeignKey('proveedor.idproveedor'))
    IDInventario = db.Column('idinventario', db.Integer, db.ForeignKey('inventario.idinventario'))

    categorias     = db.relationship("Categoria", backref="producto", lazy="select")
    detalles_venta = db.relationship("DetalleVenta", backref="producto", lazy="dynamic")


class Categoria(db.Model):
    __tablename__ = "categoria"

    IDCategoria = db.Column('idcategoria', db.Integer, primary_key=True)
    nombreCategoria = db.Column('nombrecategoria', db.String(45))
    descripcion = db.Column('descripcion', db.String(45))
    IDProducto = db.Column('idproducto', db.Integer, db.ForeignKey('producto.idproducto'))


# ─────────────────────────────────────────────
# PAGOS, FACTURAS Y VENTAS
# ─────────────────────────────────────────────

class Pago(db.Model):
    __tablename__ = "pago"

    IDPago = db.Column('idpago', db.Integer, primary_key=True)
    fechaPago = db.Column('fechapago', db.Date)
    montoPago = db.Column('montopago', db.Numeric(18, 2))
    estadoPago = db.Column('estadopago', db.String(45))

    ventas = db.relationship("Venta", backref="pago", lazy="select")


class Factura(db.Model):
    __tablename__ = "factura"

    IDFactura = db.Column('idfactura', db.Integer, primary_key=True)
    numeroFactura = db.Column('numerofactura', db.Integer)
    cuf = db.Column('cuf', db.String(45))
    nit = db.Column('nit', db.String(45))
    razonSocial = db.Column('razonsocial', db.String(45))
    total = db.Column('total', db.Numeric(18, 2))

    ventas = db.relationship("Venta", backref="factura", lazy="select")


class Venta(db.Model):
    __tablename__ = "venta"

    IDVenta = db.Column('idventa', db.Integer, primary_key=True)
    montoTotal = db.Column('montototal', db.Numeric(18, 2))
    impuesto = db.Column('impuesto', db.Numeric(18, 2))
    descuentoAplicado = db.Column('descuentoaplicado', db.Numeric(18, 2))
    fechaVenta = db.Column('fechaventa', db.Date)
    precioMomento = db.Column('preciomomento', db.Numeric(18, 2))
    IDPago = db.Column('idpago', db.Integer, db.ForeignKey('pago.idpago'))
    IDEmpleado = db.Column('idempleado', db.Integer, db.ForeignKey('empleado.idempleado'))
    IDFactura = db.Column('idfactura', db.Integer, db.ForeignKey('factura.idfactura'))
    IDCliente = db.Column('idcliente', db.Integer, db.ForeignKey('cliente.idcliente'))

    detalles = db.relationship("DetalleVenta", backref="venta", lazy="select")


class DetalleVenta(db.Model):
    __tablename__ = "detalleventa"

    IDDetalleVenta = db.Column('iddetalleventa', db.Integer, primary_key=True)
    cantidad = db.Column('cantidad', db.Integer)
    precioUnitario = db.Column('preciounitario', db.Numeric(18, 2))
    descuento = db.Column('descuento', db.Numeric(18, 2))
    subtotal = db.Column('subtotal', db.Numeric(18, 2))
    fechaPedido = db.Column('fechapedido', db.Date)
    IDVenta = db.Column('idventa', db.Integer, db.ForeignKey('venta.idventa'))
    # Columna añadida por ALTER TABLE
    IDProducto = db.Column('idproducto', db.Integer, db.ForeignKey('producto.idproducto'))


# ─────────────────────────────────────────────
# BITÁCORA — tabla NUEVA creada por migración
# ─────────────────────────────────────────────

class BitacoraAcceso(db.Model):
    __tablename__ = "bitacora_acceso"

    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    usuario_id = db.Column('usuario_id', db.Integer, db.ForeignKey('usuarioempleado.idusuarioempleado'), nullable=True)
    fecha_hora = db.Column('fecha_hora', db.DateTime, default=lambda: datetime.now(timezone.utc))
    ip = db.Column('ip', db.String(64))
    accion = db.Column('accion', db.String(80))
    detalle = db.Column('detalle', db.String(255))
