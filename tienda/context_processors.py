from .models import Carrito, Wishlist, ComparacionProductos

def carrito_context(request):
    """Context processor para agregar información del carrito a todos los templates"""
    if request.user.is_authenticated:
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            carrito_total_productos = carrito.total_productos
            carrito_total_precio = carrito.total_precio
        except Carrito.DoesNotExist:
            carrito_total_productos = 0
            carrito_total_precio = 0

        # Información del wishlist
        wishlist_count = Wishlist.objects.filter(usuario=request.user).count()

        # Información de comparación de productos
        try:
            comparacion = ComparacionProductos.objects.get(usuario=request.user)
            comparacion_count = comparacion.productos.count()
            puede_agregar_mas = comparacion.puede_agregar_mas
        except ComparacionProductos.DoesNotExist:
            comparacion_count = 0
            puede_agregar_mas = True

        return {
            'carrito_total_productos': carrito_total_productos,
            'carrito_total_precio': carrito_total_precio,
            'wishlist_count': wishlist_count,
            'comparacion_count': comparacion_count,
            'puede_agregar_mas': puede_agregar_mas,
        }
    return {
        'carrito_total_productos': 0,
        'carrito_total_precio': 0,
        'wishlist_count': 0,
        'comparacion_count': 0,
        'puede_agregar_mas': False,
    }