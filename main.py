from modelos import Usuario, Producto, Compra, Carrito
from tienda.recomendador import RecomendadorIA

# Datos simulados
usuarios = []
productos = [
    Producto(1, "Laptop", 1000, "Tecnología"),
    Producto(2, "Mouse", 50, "Tecnología"),
    Producto(3, "Libro", 20, "Libros"),
    Producto(4, "Auriculares", 80, "Tecnología")
]
compras = []
recomendador = RecomendadorIA()

def registrar_usuario():
    nombre = input("Nombre: ")
    email = input("Email: ")
    password = input("Password: ")
    id = len(usuarios) + 1
    usuario = Usuario(id, nombre, email, password)
    usuarios.append(usuario)
    print("Usuario registrado.")

def login():
    email = input("Email: ")
    password = input("Password: ")
    for u in usuarios:
        if u.email == email and u.password == password:
            return u
    print("Credenciales incorrectas.")
    return None

def mostrar_productos():
    for p in productos:
        print(f"{p.id}. {p.nombre} - ${p.precio} ({p.categoria})")

def comprar(usuario):
    carrito = Carrito(usuario.id)
    while True:
        mostrar_productos()
        id_prod = int(input("ID del producto a agregar (0 para finalizar): "))
        if id_prod == 0:
            break
        prod = next((p for p in productos if p.id == id_prod), None)
        if prod:
            carrito.agregar_producto(prod)
        else:
            print("Producto no encontrado.")
    if carrito.productos:
        total = carrito.calcular_total()
        print(f"Total: ${total}")
        confirmar = input("Confirmar compra? (s/n): ")
        if confirmar.lower() == 's':
            id_compra = len(compras) + 1
            compra = Compra(id_compra, usuario.id, carrito.productos, total)
            compras.append(compra)
            usuario.agregar_compra(compra)
            print("Compra realizada.")
    else:
        print("Carrito vacío.")

def ver_recomendaciones(usuario):
    recs = recomendador.recomendar(usuario.nombre.lower())
    print("Recomendaciones:")
    for r in recs:
        print(f"- {r}")

def menu_principal():
    usuario_actual = None
    while True:
        if not usuario_actual:
            print("\n1. Registrarse\n2. Iniciar Sesión\n3. Salir")
            opcion = input("Opción: ")
            if opcion == '1':
                registrar_usuario()
            elif opcion == '2':
                usuario_actual = login()
            elif opcion == '3':
                break
        else:
            print(f"\nBienvenido {usuario_actual.nombre}")
            print("1. Ver Productos\n2. Comprar\n3. Ver Recomendaciones\n4. Cerrar Sesión")
            opcion = input("Opción: ")
            if opcion == '1':
                mostrar_productos()
            elif opcion == '2':
                comprar(usuario_actual)
            elif opcion == '3':
                ver_recomendaciones(usuario_actual)
            elif opcion == '4':
                usuario_actual = None

if __name__ == "__main__":
    menu_principal()