class Usuario:
    def __init__(self, id, nombre, email, password):
        self.id = id
        self.nombre = nombre
        self.email = email
        self.password = password
        self.historial_compras = []

    def agregar_compra(self, compra):
        self.historial_compras.append(compra)

class Producto:
    def __init__(self, id, nombre, precio, categoria):
        self.id = id
        self.nombre = nombre
        self.precio = precio
        self.categoria = categoria

class Compra:
    def __init__(self, id, usuario_id, productos, total):
        self.id = id
        self.usuario_id = usuario_id
        self.productos = productos  # lista de productos
        self.total = total

class Carrito:
    def __init__(self, usuario_id):
        self.usuario_id = usuario_id
        self.productos = []

    def agregar_producto(self, producto):
        self.productos.append(producto)

    def calcular_total(self):
        return sum(p.precio for p in self.productos)