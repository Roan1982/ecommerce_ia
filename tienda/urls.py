from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('registro/', views.registro, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('productos/', views.productos, name='productos'),
    path('producto/<int:producto_id>/', views.producto_detalle, name='producto_detalle'),
    path('comprar/<int:producto_id>/', views.comprar, name='comprar'),
    path('recomendaciones/', views.recomendaciones, name='recomendaciones'),
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/eliminar/<int:item_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('carrito/actualizar/<int:item_id>/', views.actualizar_carrito, name='actualizar_carrito'),
    path('carrito/vaciar/', views.vaciar_carrito, name='vaciar_carrito'),
    # Checkout
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/direccion/', views.checkout_direccion, name='checkout_direccion'),
    path('checkout/pago/', views.checkout_pago, name='checkout_pago'),
    path('checkout/confirmacion/', views.checkout_confirmacion, name='checkout_confirmacion'),
    path('checkout/procesar/', views.procesar_pedido, name='procesar_pedido'),
    path('pedido/<int:pedido_id>/', views.pedido_detalle, name='pedido_detalle'),
    path('historial-pedidos/', views.historial_pedidos, name='historial_pedidos'),
    # Reseñas
    path('producto/<int:producto_id>/resena/', views.agregar_resena, name='agregar_resena'),
    path('producto/<int:producto_id>/resenas/', views.ver_resenas, name='ver_resenas'),
    # Cupones
    path('aplicar-cupon/', views.aplicar_cupon, name='aplicar_cupon'),
    path('remover-cupon/', views.remover_cupon, name='remover_cupon'),
    path('cupones/', views.cupones_disponibles, name='cupones_disponibles'),
]