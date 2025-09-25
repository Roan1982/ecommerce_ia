from .models import Carrito

def carrito_context(request):
    """Context processor para agregar información del carrito a todos los templates"""
    if request.user.is_authenticated:
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            return {
                'carrito_total_productos': carrito.total_productos,
                'carrito_total_precio': carrito.total_precio,
            }
        except Carrito.DoesNotExist:
            return {
                'carrito_total_productos': 0,
                'carrito_total_precio': 0,
            }
    return {
        'carrito_total_productos': 0,
        'carrito_total_precio': 0,
    }