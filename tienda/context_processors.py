from .models import Carrito, Wishlist

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

        return {
            'carrito_total_productos': carrito_total_productos,
            'carrito_total_precio': carrito_total_precio,
            'wishlist_count': wishlist_count,
        }
    return {
        'carrito_total_productos': 0,
        'carrito_total_precio': 0,
        'wishlist_count': 0,
    }