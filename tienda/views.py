from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail, EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .services.email_service import EmailService
from .models import Producto, Compra, CompraProducto, Carrito, CarritoProducto, DireccionEnvio, MetodoPago, Pedido, PedidoProducto, Resena, Cupon, MovimientoInventario, ConfiguracionSistema, Profile, Wishlist, HistorialPuntos, ComparacionProductos, NewsletterSubscription, NewsletterCampaign, NewsletterLog, EmailTemplate, EmailNotification, EmailQueue, ContribucionWishlist, ReferidoWishlist, HistorialCompartir, ProductoImagen
from .forms import ProductoForm, ProductoAdminForm, CuponForm, ProfileForm, NewsletterSubscriptionForm, NewsletterUnsubscribeForm, NewsletterCampaignForm, NewsletterTestForm
from .services.email_service import EmailService
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import models, transaction
from django import forms
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth, TruncDay
from datetime import date, timedelta
import logging
import json

from .recomendador import RecomendadorIA

logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'tienda/home.html')

def acerca_de(request):
    """Vista para la página Acerca de Nosotros"""
    return render(request, 'tienda/acerca_de.html')

def registro(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)

            # Enviar email de bienvenida
            try:
                email_service = EmailService()
                email_service.enviar_bienvenida_registro(user)
            except Exception as e:
                # No fallar el registro si hay error con el email
                pass

            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'tienda/registro.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            if user:
                login(request, user)
                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'tienda/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def productos(request):
    """Vista para mostrar productos con funcionalidad de búsqueda"""
    # Obtener parámetros de búsqueda
    query = request.GET.get('q', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    ordenar_por = request.GET.get('ordenar', 'nombre')  # nombre, precio, precio_desc, fecha_desc

    # Base queryset
    productos = Producto.objects.filter(stock__gt=0)

    # Aplicar filtros de búsqueda
    if query:
        productos = productos.filter(
            models.Q(nombre__icontains=query) |
            models.Q(descripcion__icontains=query) |
            models.Q(categoria__icontains=query)
        )

    if categoria:
        productos = productos.filter(categoria__iexact=categoria)

    # Aplicar ordenamiento
    if ordenar_por == 'precio':
        productos = productos.order_by('precio')
    elif ordenar_por == 'precio_desc':
        productos = productos.order_by('-precio')
    elif ordenar_por == 'fecha_desc':
        productos = productos.order_by('-id')  # Usamos ID como aproximación de fecha de creación
    else:
        productos = productos.order_by('nombre')

    # Obtener categorías disponibles para el filtro
    categorias = Producto.objects.values_list('categoria', flat=True).distinct().order_by('categoria')

    # Obtener IDs de productos en wishlist del usuario para mostrar estado correcto
    wishlist_product_ids = set(Wishlist.objects.filter(usuario=request.user).values_list('producto_id', flat=True))

    # Obtener IDs de productos en comparación del usuario para mostrar estado correcto
    try:
        comparacion = ComparacionProductos.objects.get(usuario=request.user)
        comparacion_product_ids = set(comparacion.productos.values_list('id', flat=True))
    except ComparacionProductos.DoesNotExist:
        comparacion_product_ids = set()

    response = render(request, 'tienda/productos.html', {
        'productos': productos,
        'query': query,
        'categoria_seleccionada': categoria,
        'ordenar_por': ordenar_por,
        'categorias': categorias,
        'wishlist_product_ids': wishlist_product_ids,
        'comparacion_product_ids': comparacion_product_ids,
    })

    # Agregar headers para evitar cache del navegador
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response

def producto_detalle(request, producto_id):
    """Vista para mostrar el detalle completo de un producto"""
    producto = get_object_or_404(Producto, id=producto_id)

    # Obtener reseñas del producto
    resenas = Resena.objects.filter(producto=producto).select_related('usuario').order_by('-fecha_creacion')

    # Verificar si el usuario puede reseñar este producto
    puede_reseñar = False
    if request.user.is_authenticated:
        puede_reseñar = producto.puede_reseñar(request.user)

    # Obtener productos relacionados (misma categoría)
    productos_relacionados = Producto.objects.filter(
        categoria=producto.categoria
    ).exclude(id=producto.id).filter(stock__gt=0)[:4]

    # Verificar si el producto está en la wishlist del usuario
    en_wishlist = False
    if request.user.is_authenticated:
        en_wishlist = Wishlist.objects.filter(usuario=request.user, producto=producto).exists()

    # Obtener todas las imágenes del producto ordenadas
    imagenes = producto.imagenes_disponibles

    return render(request, 'tienda/producto_detalle.html', {
        'producto': producto,
        'resenas': resenas,
        'puede_reseñar': puede_reseñar,
        'productos_relacionados': productos_relacionados,
        'en_wishlist': en_wishlist,
        'imagenes': imagenes,
    })

@login_required
def comprar(request, producto_id):
    """Vista para compra directa de un producto - agrega al carrito y va al checkout"""
    producto = get_object_or_404(Producto, id=producto_id)

    # Verificar stock disponible
    if producto.stock <= 0:
        messages.error(request, _('Producto agotado.'))
        return redirect('producto_detalle', producto_id=producto.id)

    # Obtener o crear carrito del usuario
    carrito, created = Carrito.objects.get_or_create(usuario=request.user)

    # Verificar si el producto ya está en el carrito
    carrito_item, item_created = CarritoProducto.objects.get_or_create(
        carrito=carrito,
        producto=producto,
        defaults={'cantidad': 1}
    )

    if not item_created:
        # Si ya existe, incrementar cantidad si hay stock suficiente
        nueva_cantidad = carrito_item.cantidad + 1
        if nueva_cantidad <= producto.stock:
            carrito_item.cantidad = nueva_cantidad
            carrito_item.save()
            messages.success(request, _('Producto agregado al carrito.'))
        else:
            messages.warning(request, _('No hay suficiente stock disponible.'))
    else:
        messages.success(request, _('Producto agregado al carrito.'))

    # Redirigir al checkout
    return redirect('checkout')

@login_required
def recomendaciones(request):
    """Mostrar recomendaciones personalizadas usando IA"""
    from .recomendador import RecomendadorIA

    # Inicializar el recomendador (se cargan datos reales automáticamente)
    recomendador = RecomendadorIA()

    # Obtener recomendaciones para el usuario actual
    recomendaciones_data = recomendador.recomendar(request.user, top_n=6)

    # Si no hay recomendaciones basadas en IA, mostrar productos populares
    if not recomendaciones_data:
        productos_populares = Producto.objects.filter(stock__gt=0).order_by('-stock')[:6]
        recomendaciones_data = []
        for producto in productos_populares:
            recomendaciones_data.append({
                'producto': producto,
                'score': 0.5,
                'razon': "Producto popular en la tienda"
            })

    return render(request, 'tienda/recomendaciones.html', {
        'recomendaciones': recomendaciones_data
    })

@login_required
def ver_carrito(request):
    """Vista para mostrar el carrito de compras del usuario"""
    try:
        carrito = Carrito.objects.get(usuario=request.user)
        items = CarritoProducto.objects.filter(carrito=carrito).select_related('producto')

        # Calcular descuento si hay cupón aplicado
        descuento_cupon = 0
        cupon_aplicado = None
        if 'cupon_aplicado' in request.session:
            cupon_data = request.session['cupon_aplicado']
            try:
                cupon = Cupon.objects.get(codigo=cupon_data['codigo'])
                if cupon.es_valido() and carrito.total_precio >= cupon.minimo_compra:
                    descuento_cupon = cupon.calcular_descuento(carrito.total_precio)
                    cupon_aplicado = cupon
                else:
                    # Cupón no válido, remover de sesión
                    del request.session['cupon_aplicado']
            except Cupon.DoesNotExist:
                del request.session['cupon_aplicado']

        total_con_descuento = carrito.total_precio - descuento_cupon

    except Carrito.DoesNotExist:
        carrito = None
        items = []
        descuento_cupon = 0
        cupon_aplicado = None
        total_con_descuento = 0

    return render(request, 'tienda/carrito.html', {
        'carrito': carrito,
        'items': items,
        'descuento_cupon': descuento_cupon,
        'cupon_aplicado': cupon_aplicado,
        'total_con_descuento': total_con_descuento
    })

@login_required
def agregar_al_carrito(request, producto_id):
    """Vista para agregar un producto al carrito"""
    producto = get_object_or_404(Producto, id=producto_id)

    # Verificar stock disponible
    if producto.stock <= 0:
        messages.error(request, _('Producto agotado.'))
        return redirect('productos')

    # Obtener o crear carrito del usuario
    carrito, created = Carrito.objects.get_or_create(usuario=request.user)

    # Verificar si el producto ya está en el carrito
    carrito_item, item_created = CarritoProducto.objects.get_or_create(
        carrito=carrito,
        producto=producto,
        defaults={'cantidad': 1}
    )

    if not item_created:
        # Si ya existe, incrementar cantidad si hay stock suficiente
        nueva_cantidad = carrito_item.cantidad + 1
        if nueva_cantidad <= producto.stock:
            carrito_item.cantidad = nueva_cantidad
            carrito_item.save()
            messages.success(request, _('Producto agregado al carrito.'))
        else:
            messages.warning(request, _('No hay suficiente stock disponible.'))
    else:
        messages.success(request, _('Producto agregado al carrito.'))

    return redirect('productos')

@login_required
def eliminar_del_carrito(request, item_id):
    """Vista para eliminar un producto del carrito"""
    try:
        item = CarritoProducto.objects.get(id=item_id, carrito__usuario=request.user)
        item.delete()
        messages.success(request, _('Producto eliminado del carrito.'))
    except CarritoProducto.DoesNotExist:
        messages.error(request, _('Producto no encontrado en el carrito.'))

    # Si es una petición AJAX, devolver JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            items = CarritoProducto.objects.filter(carrito=carrito).select_related('producto')

            # Calcular descuento si hay cupón aplicado
            descuento_cupon = 0
            if 'cupon_aplicado' in request.session:
                cupon_data = request.session['cupon_aplicado']
                try:
                    cupon = Cupon.objects.get(codigo=cupon_data['codigo'])
                    if cupon.es_valido() and carrito.total_precio >= cupon.minimo_compra:
                        descuento_cupon = cupon.calcular_descuento(carrito.total_precio)
                except Cupon.DoesNotExist:
                    pass

            data = {
                'success': True,
                'total_productos': carrito.total_productos,
                'total_precio': float(carrito.total_precio),
                'descuento_cupon': float(descuento_cupon),
                'items': []
            }
            for item in items:
                data['items'].append({
                    'id': item.id,
                    'cantidad': item.cantidad,
                    'subtotal': float(item.subtotal),
                    'producto_stock': item.producto.stock
                })
            return JsonResponse(data)
        except Carrito.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Carrito no encontrado'})

    return redirect('ver_carrito')

@login_required
def actualizar_carrito(request, item_id):
    """Vista para actualizar la cantidad de un producto en el carrito"""
    if request.method == 'POST':
        try:
            item = CarritoProducto.objects.get(id=item_id, carrito__usuario=request.user)
            nueva_cantidad = int(request.POST.get('cantidad', 1))

            if nueva_cantidad <= 0:
                item.delete()
                # Solo mostrar mensaje si NO es AJAX
                if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    messages.success(request, _('Producto eliminado del carrito.'))
            elif nueva_cantidad <= item.producto.stock:
                item.cantidad = nueva_cantidad
                item.save()
                # Solo mostrar mensaje si NO es AJAX
                if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    messages.success(request, _('Cantidad actualizada.'))
            else:
                # Solo mostrar mensaje si NO es AJAX
                if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    messages.warning(request, _('Cantidad solicitada excede el stock disponible.'))

        except (CarritoProducto.DoesNotExist, ValueError):
            # Solo mostrar mensaje si NO es AJAX
            if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
                messages.error(request, _('Error al actualizar el carrito.'))

    # Si es una petición AJAX, devolver JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            items = CarritoProducto.objects.filter(carrito=carrito).select_related('producto')

            # Calcular descuento si hay cupón aplicado
            descuento_cupon = 0
            if 'cupon_aplicado' in request.session:
                cupon_data = request.session['cupon_aplicado']
                try:
                    cupon = Cupon.objects.get(codigo=cupon_data['codigo'])
                    if cupon.es_valido() and carrito.total_precio >= cupon.minimo_compra:
                        descuento_cupon = cupon.calcular_descuento(carrito.total_precio)
                except Cupon.DoesNotExist:
                    pass

            data = {
                'success': True,
                'total_productos': carrito.total_productos,
                'total_precio': float(carrito.total_precio),
                'descuento_cupon': float(descuento_cupon),
                'items': []
            }
            for item in items:
                data['items'].append({
                    'id': item.id,
                    'cantidad': item.cantidad,
                    'subtotal': float(item.subtotal),
                    'producto_stock': item.producto.stock
                })
            return JsonResponse(data)
        except Carrito.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Carrito no encontrado'})

    return redirect('ver_carrito')

@login_required
def vaciar_carrito(request):
    """Vista para vaciar completamente el carrito"""
    try:
        carrito = Carrito.objects.get(usuario=request.user)
        carrito.carritoproducto_set.all().delete()
        messages.success(request, _('Carrito vaciado exitosamente.'))
    except Carrito.DoesNotExist:
        messages.warning(request, _('El carrito ya está vacío.'))

    return redirect('ver_carrito')

# Formularios para Checkout
class DireccionEnvioForm(forms.ModelForm):
    class Meta:
        model = DireccionEnvio
        fields = ['nombre_direccion', 'nombre_completo', 'calle', 'numero', 'piso_departamento',
                 'ciudad', 'provincia', 'codigo_postal', 'telefono', 'es_predeterminada']
        widgets = {
            'nombre_direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Casa, Trabajo'}),
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'calle': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'piso_departamento': forms.TextInput(attrs={'class': 'form-control'}),
            'ciudad': forms.TextInput(attrs={'class': 'form-control'}),
            'provincia': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_postal': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'es_predeterminada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ResenaForm(forms.ModelForm):
    class Meta:
        model = Resena
        fields = ['calificacion', 'comentario']
        widgets = {
            'calificacion': forms.Select(attrs={'class': 'form-select'}),
            'comentario': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Comparte tu experiencia con este producto...'
            }),
        }

class MetodoPagoForm(forms.ModelForm):
    class Meta:
        model = MetodoPago
        fields = ['tipo', 'nombre_titular', 'numero_tarjeta', 'fecha_vencimiento', 'es_predeterminada']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'nombre_titular': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_tarjeta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1234 5678 9012 3456'}),
            'fecha_vencimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'es_predeterminada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

@login_required
def checkout(request):
    """Vista principal del checkout - Paso 1: Revisar carrito"""
    try:
        carrito = Carrito.objects.get(usuario=request.user)
        items = CarritoProducto.objects.filter(carrito=carrito).select_related('producto')

        if not items:
            messages.warning(request, _('Tu carrito está vacío. Agrega productos antes de proceder al checkout.'))
            return redirect('productos')

        # Calcular totales
        total_productos = carrito.total_productos
        subtotal = carrito.total_precio
        costo_envio = 0 if subtotal > 100 else 10  # Envío gratis para compras > $100
        descuento_cupon = 0

        # Verificar si hay cupón aplicado
        cupon_aplicado = None
        if 'cupon_aplicado' in request.session:
            cupon_data = request.session['cupon_aplicado']
            try:
                cupon = Cupon.objects.get(codigo=cupon_data['codigo'])
                if cupon.es_valido() and subtotal >= cupon.minimo_compra:
                    descuento_cupon = cupon.calcular_descuento(subtotal)
                    cupon_aplicado = cupon
                else:
                    # Cupón no válido, remover de sesión
                    del request.session['cupon_aplicado']
            except Cupon.DoesNotExist:
                del request.session['cupon_aplicado']

        total = subtotal + costo_envio - descuento_cupon

        return render(request, 'tienda/checkout.html', {
            'carrito': carrito,
            'items': items,
            'subtotal': subtotal,
            'costo_envio': costo_envio,
            'descuento_cupon': descuento_cupon,
            'cupon_aplicado': cupon_aplicado,
            'total': total,
            'paso': 1
        })

    except Carrito.DoesNotExist:
        messages.warning(request, _('Tu carrito está vacío. Agrega productos antes de proceder al checkout.'))
        return redirect('productos')

@login_required
def checkout_direccion(request):
    """Paso 2: Seleccionar o agregar dirección de envío"""
    direcciones = DireccionEnvio.objects.filter(usuario=request.user)
    form = DireccionEnvioForm()  # Initialize form by default

    if request.method == 'POST':
        if 'seleccionar_direccion' in request.POST:
            # Seleccionar dirección existente
            direccion_id = request.POST.get('direccion_id')
            if direccion_id:
                request.session['direccion_envio_id'] = direccion_id
                return redirect('checkout_pago')
            else:
                messages.error(request, _('Por favor selecciona una dirección de envío.'))
        else:
            # Agregar nueva dirección
            form = DireccionEnvioForm(request.POST)
            if form.is_valid():
                direccion = form.save(commit=False)
                direccion.usuario = request.user
                if direccion.es_predeterminada:
                    # Desmarcar otras direcciones como predeterminadas
                    DireccionEnvio.objects.filter(usuario=request.user).update(es_predeterminada=False)
                direccion.save()
                request.session['direccion_envio_id'] = direccion.id
                messages.success(request, _('Dirección de envío agregada exitosamente.'))
                return redirect('checkout_pago')
            # If form is invalid, it will be passed to the template with errors

    return render(request, 'tienda/checkout_direccion.html', {
        'direcciones': direcciones,
        'form': form,
        'paso': 2
    })

@login_required
def checkout_pago(request):
    """Paso 3: Seleccionar método de pago"""
    if 'direccion_envio_id' not in request.session:
        messages.error(request, _('Primero debes seleccionar una dirección de envío.'))
        return redirect('checkout_direccion')

    metodos_pago = MetodoPago.objects.filter(usuario=request.user)
    form = MetodoPagoForm()  # Initialize form by default

    if request.method == 'POST':
        if 'seleccionar_pago' in request.POST:
            # Seleccionar método de pago existente
            pago_id = request.POST.get('pago_id')
            if pago_id:
                request.session['metodo_pago_id'] = pago_id
                return redirect('checkout_confirmacion')
            else:
                messages.error(request, _('Por favor selecciona un método de pago.'))
        else:
            # Agregar nuevo método de pago
            form = MetodoPagoForm(request.POST)
            if form.is_valid():
                metodo = form.save(commit=False)
                metodo.usuario = request.user
                # Guardar solo los últimos 4 dígitos de la tarjeta por seguridad
                if metodo.numero_tarjeta:
                    metodo.numero_tarjeta = metodo.numero_tarjeta[-4:]
                if metodo.es_predeterminada:
                    # Desmarcar otros métodos como predeterminados
                    MetodoPago.objects.filter(usuario=request.user).update(es_predeterminada=False)
                metodo.save()
                request.session['metodo_pago_id'] = metodo.id
                messages.success(request, _('Método de pago agregado exitosamente.'))
                return redirect('checkout_confirmacion')
            # If form is invalid, it will be passed to the template with errors

    return render(request, 'tienda/checkout_pago.html', {
        'metodos_pago': metodos_pago,
        'form': form,
        'paso': 3
    })

@login_required
def checkout_confirmacion(request):
    """Paso 4: Confirmación final del pedido"""
    if 'direccion_envio_id' not in request.session or 'metodo_pago_id' not in request.session:
        messages.error(request, _('Información de envío o pago incompleta.'))
        return redirect('checkout')

    try:
        carrito = Carrito.objects.get(usuario=request.user)
        items = CarritoProducto.objects.filter(carrito=carrito).select_related('producto')
        direccion = DireccionEnvio.objects.get(id=request.session['direccion_envio_id'], usuario=request.user)
        metodo_pago = MetodoPago.objects.get(id=request.session['metodo_pago_id'], usuario=request.user)

        if not items:
            messages.warning(request, _('Tu carrito está vacío.'))
            return redirect('productos')

        # Calcular totales
        subtotal = carrito.total_precio
        costo_envio = 0 if subtotal > 100 else 10
        total = subtotal + costo_envio

        if request.method == 'POST':
            return redirect('procesar_pedido')

        return render(request, 'tienda/checkout_confirmacion.html', {
            'carrito': carrito,
            'items': items,
            'direccion': direccion,
            'metodo_pago': metodo_pago,
            'subtotal': subtotal,
            'costo_envio': costo_envio,
            'total': total,
            'paso': 4
        })

    except (Carrito.DoesNotExist, DireccionEnvio.DoesNotExist, MetodoPago.DoesNotExist):
        messages.error(request, _('Error al cargar la información del pedido.'))
        return redirect('checkout')

@login_required
@transaction.atomic
def procesar_pedido(request):
    """Procesar el pedido final"""
    if 'direccion_envio_id' not in request.session or 'metodo_pago_id' not in request.session:
        messages.error(request, _('Información de envío o pago incompleta.'))
        return redirect('checkout')

    try:
        carrito = Carrito.objects.get(usuario=request.user)
        items = CarritoProducto.objects.filter(carrito=carrito).select_related('producto')
        direccion = DireccionEnvio.objects.get(id=request.session['direccion_envio_id'], usuario=request.user)
        metodo_pago = MetodoPago.objects.get(id=request.session['metodo_pago_id'], usuario=request.user)

        if not items:
            messages.warning(request, _('Tu carrito está vacío.'))
            return redirect('productos')

        # Verificar stock disponible
        for item in items:
            if item.cantidad > item.producto.stock:
                messages.error(request, _('Stock insuficiente para %(producto)s. Disponible: %(stock)d') % {
                    'producto': item.producto.nombre,
                    'stock': item.producto.stock
                })
                return redirect('ver_carrito')

        # Calcular totales
        subtotal = carrito.total_precio
        costo_envio = 0 if subtotal > 100 else 10

        # Verificar cupón aplicado
        descuento_cupon = 0
        cupon_aplicado = None
        if 'cupon_aplicado' in request.session:
            cupon_data = request.session['cupon_aplicado']
            try:
                cupon = Cupon.objects.select_for_update().get(codigo=cupon_data['codigo'])
                if cupon.es_valido(request.user) and subtotal >= cupon.minimo_compra:
                    # Para cupones que requieren puntos, verificar que el usuario tenga suficientes
                    if cupon.tipo_cupon == 'comprado_puntos':
                        try:
                            profile = request.user.profile
                            if profile.puntos_disponibles >= cupon.puntos_requeridos:
                                descuento_cupon = cupon.calcular_descuento(subtotal)
                                cupon_aplicado = cupon
                            else:
                                del request.session['cupon_aplicado']
                        except Profile.DoesNotExist:
                            del request.session['cupon_aplicado']
                    else:
                        descuento_cupon = cupon.calcular_descuento(subtotal)
                        cupon_aplicado = cupon
                else:
                    del request.session['cupon_aplicado']
            except Cupon.DoesNotExist:
                del request.session['cupon_aplicado']

        total = subtotal + costo_envio - descuento_cupon

        # Crear pedido
        pedido = Pedido.objects.create(
            usuario=request.user,
            direccion_envio=direccion,
            metodo_pago=metodo_pago,
            costo_envio=costo_envio,
            total_productos=subtotal,
            descuento_cupon=descuento_cupon,
            total_pedido=total,
            estado='pagado'  # Simulamos que el pago fue exitoso
        )

        # Aplicar cupón si existe
        if cupon_aplicado:
            cupon_aplicado.usos_actuales += 1
            cupon_aplicado.save()

            # Si es un cupón que requiere puntos, restar los puntos del usuario
            if cupon_aplicado.tipo_cupon == 'comprado_puntos':
                try:
                    profile = request.user.profile
                    profile.puntos_disponibles -= cupon_aplicado.puntos_requeridos
                    profile.save()

                    # Registrar en historial de puntos
                    HistorialPuntos.objects.create(
                        usuario=request.user,
                        puntos=-cupon_aplicado.puntos_requeridos,
                        descripcion=f"Uso de cupón {cupon_aplicado.codigo} (requería {cupon_aplicado.puntos_requeridos} puntos)",
                        tipo='gastados'
                    )
                except Profile.DoesNotExist:
                    # No debería pasar, pero por si acaso
                    pass

            # Si es un cupón copiable usado, crear un nuevo cupón para el usuario
            if cupon_aplicado.tipo_cupon == 'codigo_copiable' and cupon_aplicado.usado_por_usuario != request.user:
                # Marcar que este usuario ya usó el cupón
                cupon_aplicado.usado_por_usuario = request.user
                cupon_aplicado.save()

                # Otorgar puntos al usuario por usar cupón copiable
                try:
                    profile, created = Profile.objects.get_or_create(usuario=request.user)
                    puntos_por_cupon = 50  # Puntos que otorga usar un cupón copiable
                    profile.agregar_puntos(puntos_por_cupon, f"Uso de cupón copiable {cupon_aplicado.codigo}")
                except Exception:
                    pass

        # Crear productos del pedido y actualizar stock
        for item in items:
            PedidoProducto.objects.create(
                pedido=pedido,
                producto=item.producto,
                cantidad=item.cantidad,
                precio_unitario=item.producto.precio
            )
            # Reducir stock con registro de movimiento
            item.producto.reducir_stock(item.cantidad, usuario=request.user, pedido=pedido)

        # Vaciar carrito
        items.delete()

        # Limpiar sesión
        del request.session['direccion_envio_id']
        del request.session['metodo_pago_id']
        if 'cupon_aplicado' in request.session:
            del request.session['cupon_aplicado']

        # Otorgar puntos de fidelidad por la compra
        try:
            profile, created = Profile.objects.get_or_create(usuario=request.user)
            # Otorgar puntos basado en el subtotal (ejemplo: 1 punto por cada $10)
            puntos_ganados = int(subtotal // 10)
            if puntos_ganados > 0:
                profile.agregar_puntos(puntos_ganados, f"Compra #{pedido.id}")
                messages.info(request, f'¡Has ganado {puntos_ganados} puntos de fidelidad por tu compra!')

                # Enviar email de notificación de puntos
                try:
                    email_service = EmailService()
                    email_service.enviar_notificacion_puntos(request.user, puntos_ganados, f"Compra #{pedido.id}")
                except Exception as e:
                    # No fallar si hay error con el email de puntos
                    pass
        except Exception as e:
            # No fallar el pedido si hay error con puntos
            pass

        # Enviar email de confirmación de pedido
        try:
            email_service = EmailService()
            email_service.enviar_confirmacion_pedido(pedido)
        except Exception as e:
            # No fallar el pedido si hay error con el email
            pass

        messages.success(request, _('¡Pedido realizado exitosamente! Número de pedido: %(pedido_id)d') % {'pedido_id': pedido.id})
        return redirect('pedido_detalle', pedido_id=pedido.id)

    except Exception as e:
        messages.error(request, _('Error al procesar el pedido. Por favor intenta nuevamente.'))
        return redirect('checkout')

@login_required
def cupones_canjear_puntos(request):
    """Vista para mostrar cupones disponibles para canjear con puntos"""
    try:
        perfil = request.user.profile
        puntos_disponibles = perfil.puntos_disponibles
    except Profile.DoesNotExist:
        puntos_disponibles = 0
        messages.warning(request, 'Necesitas tener un perfil para canjear puntos.')
        return redirect('puntos_fidelidad')

    # Obtener cupones disponibles para canjear con puntos
    cupones_disponibles = Cupon.objects.filter(
        tipo_cupon='comprado_puntos',
        activo=True,
        fecha_expiracion__gte=date.today()
    ).order_by('puntos_requeridos')

    # Preparar datos para mostrar
    cupones_data = []
    for cupon in cupones_disponibles:
        puede_comprar = puntos_disponibles >= cupon.puntos_requeridos
        cupones_data.append({
            'cupon': cupon,
            'puede_comprar': puede_comprar,
            'puntos_faltantes': max(0, cupon.puntos_requeridos - puntos_disponibles)
        })

    context = {
        'cupones_data': cupones_data,
        'puntos_disponibles': puntos_disponibles,
    }
    return render(request, 'tienda/cupones_canjear_puntos.html', context)

@login_required
def comprar_cupon_puntos(request, cupon_id):
    """Vista para comprar un cupón con puntos"""
    try:
        perfil = request.user.profile
        puntos_disponibles = perfil.puntos_disponibles
    except Profile.DoesNotExist:
        messages.error(request, 'Necesitas tener un perfil para comprar cupones.')
        return redirect('puntos_fidelidad')

    try:
        cupon = Cupon.objects.get(
            id=cupon_id,
            tipo_cupon='comprado_puntos',
            activo=True,
            fecha_expiracion__gte=date.today()
        )
    except Cupon.DoesNotExist:
        messages.error(request, 'Cupón no encontrado o no disponible.')
        return redirect('cupones_canjear_puntos')

    # Verificar si el usuario tiene suficientes puntos
    if puntos_disponibles < cupon.puntos_requeridos:
        messages.error(request, f'No tienes suficientes puntos. Necesitas {cupon.puntos_requeridos} puntos, tienes {puntos_disponibles}.')
        return redirect('cupones_canjear_puntos')

    # Verificar si el usuario ya compró este cupón
    if cupon.usuario_propietario == request.user:
        messages.warning(request, 'Ya tienes este cupón.')
        return redirect('cupones_disponibles')

    if request.method == 'POST':
        # Restar puntos del usuario
        perfil.puntos_disponibles -= cupon.puntos_requeridos
        perfil.save()

        # Registrar en historial de puntos
        HistorialPuntos.objects.create(
            usuario=request.user,
            puntos=-cupon.puntos_requeridos,
            descripcion=f"Compra de cupón '{cupon.codigo}'",
            tipo='gastados'
        )

        # Crear un nuevo cupón para el usuario
        nuevo_cupon = Cupon.objects.create(
            codigo=f"{cupon.codigo}_{request.user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}",
            descripcion=cupon.descripcion,
            tipo_descuento=cupon.tipo_descuento,
            valor_descuento=cupon.valor_descuento,
            minimo_compra=cupon.minimo_compra,
            fecha_expiracion=cupon.fecha_expiracion,
            usos_maximos=1,  # Los cupones comprados con puntos son de un solo uso
            activo=True,
            tipo_cupon='codigo_copiable',  # Cambiar a copiable para que pueda ser usado
            usuario_propietario=request.user  # Marcar como propiedad del usuario
        )

        messages.success(request, f'¡Cupón comprado exitosamente! Código: {nuevo_cupon.codigo}')
        return redirect('cupones_disponibles')

    context = {
        'cupon': cupon,
        'puntos_disponibles': puntos_disponibles,
        'puntos_requeridos': cupon.puntos_requeridos,
        'puntos_restantes': puntos_disponibles - cupon.puntos_requeridos
    }
    return render(request, 'tienda/comprar_cupon_puntos.html', context)

@login_required
def pedido_detalle(request, pedido_id):
    """Mostrar detalles de un pedido"""
    try:
        pedido = Pedido.objects.get(id=pedido_id, usuario=request.user)
        productos = PedidoProducto.objects.filter(pedido=pedido).select_related('producto')

        # Verificar si el pedido puede ser enviado
        if not pedido.puede_ser_enviado:
            messages.warning(request, _('Tu dirección de envío está incompleta. Completa tu dirección para que podamos procesar el envío de este pedido.'))

        return render(request, 'tienda/pedido_detalle.html', {
            'pedido': pedido,
            'productos': productos
        })

    except Pedido.DoesNotExist:
        messages.error(request, _('Pedido no encontrado.'))
        return redirect('home')

@login_required
def agregar_resena(request, producto_id):
    """Vista para agregar o editar una reseña de un producto"""
    producto = get_object_or_404(Producto, id=producto_id)

    # Verificar si el usuario puede reseñar este producto
    if not producto.puede_reseñar(request.user):
        messages.error(request, _('Debes comprar este producto antes de poder reseñarlo.'))
        return redirect('productos')

    # Verificar si ya existe una reseña
    resena_existente = Resena.objects.filter(usuario=request.user, producto=producto).first()

    if request.method == 'POST':
        form = ResenaForm(request.POST, instance=resena_existente)
        if form.is_valid():
            resena = form.save(commit=False)
            resena.usuario = request.user
            resena.producto = producto
            resena.save()
            messages.success(request, _('¡Reseña guardada exitosamente!'))
            return redirect('comprar', producto_id=producto.id)
    else:
        form = ResenaForm(instance=resena_existente)

    return render(request, 'tienda/agregar_resena.html', {
        'form': form,
        'producto': producto,
        'resena_existente': resena_existente
    })

@login_required
def ver_resenas(request, producto_id):
    """Vista para ver todas las reseñas de un producto"""
    producto = get_object_or_404(Producto, id=producto_id)
    resenas = Resena.objects.filter(producto=producto).select_related('usuario').order_by('-fecha_creacion')

    return render(request, 'tienda/ver_resenas.html', {
        'producto': producto,
        'resenas': resenas
    })

@login_required
def aplicar_cupon(request):
    """Vista para aplicar un cupón de descuento"""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        codigo_cupon = request.POST.get('codigo', '').strip().upper()

        try:
            carrito = Carrito.objects.get(usuario=request.user)
            subtotal = carrito.total_precio

            try:
                cupon = Cupon.objects.get(codigo=codigo_cupon)

                # Validar cupón según su tipo
                if not cupon.es_valido(request.user):
                    return JsonResponse({
                        'success': False,
                        'error': 'Cupón expirado, inactivo o no válido para ti'
                    })

                if subtotal < cupon.minimo_compra:
                    return JsonResponse({
                        'success': False,
                        'error': f'Monto mínimo de compra: ${cupon.minimo_compra}'
                    })

                # Para cupones que requieren puntos, verificar que el usuario tenga suficientes
                if cupon.tipo_cupon == 'comprado_puntos':
                    try:
                        profile = request.user.profile
                        if profile.puntos_disponibles < cupon.puntos_requeridos:
                            return JsonResponse({
                                'success': False,
                                'error': f'Necesitas {cupon.puntos_requeridos} puntos para usar este cupón. Tienes {profile.puntos_disponibles}.'
                            })
                    except Profile.DoesNotExist:
                        return JsonResponse({
                            'success': False,
                            'error': 'Necesitas una cuenta con puntos para usar este cupón.'
                        })

                descuento = cupon.calcular_descuento(subtotal)
                total_con_descuento = subtotal - descuento

                # Guardar cupón en la sesión
                request.session['cupon_aplicado'] = {
                    'codigo': cupon.codigo,
                    'descuento': float(descuento),
                    'descripcion': cupon.descripcion,
                    'tipo_cupon': cupon.tipo_cupon,
                    'puntos_requeridos': cupon.puntos_requeridos if cupon.tipo_cupon == 'comprado_puntos' else 0
                }

                return JsonResponse({
                    'success': True,
                    'descuento': float(descuento),
                    'total_con_descuento': float(total_con_descuento),
                    'descripcion': cupon.descripcion,
                    'tipo_cupon': cupon.tipo_cupon,
                    'puntos_requeridos': cupon.puntos_requeridos if cupon.tipo_cupon == 'comprado_puntos' else 0
                })

            except Cupon.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Cupón no encontrado'
                })

        except Carrito.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Carrito no encontrado'
            })

    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
def remover_cupon(request):
    """Vista para remover un cupón aplicado"""
    if 'cupon_aplicado' in request.session:
        del request.session['cupon_aplicado']

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            return JsonResponse({
                'success': True,
                'total_original': float(carrito.total_precio)
            })
        except Carrito.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Carrito no encontrado'})

    return redirect('checkout')

@login_required
def historial_pedidos(request):
    """Vista para mostrar el historial de pedidos del usuario"""
    pedidos = Pedido.objects.filter(usuario=request.user).select_related('direccion_envio', 'metodo_pago').order_by('-fecha_creacion')

    # Verificar si hay pedidos que no pueden ser enviados
    pedidos_sin_envio = [pedido for pedido in pedidos if not pedido.puede_ser_enviado]
    if pedidos_sin_envio:
        messages.warning(request, _('Algunos de tus pedidos tienen direcciones de envío incompletas. Completa tu dirección para que podamos procesar los envíos.'))

    return render(request, 'tienda/historial_pedidos.html', {
        'pedidos': pedidos
    })

@login_required
def perfil_usuario(request):
    """Vista para mostrar y editar el perfil del usuario"""
    profile, created = Profile.objects.get_or_create(usuario=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _('Perfil actualizado exitosamente.'))
            return redirect('perfil_usuario')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'tienda/perfil.html', {
        'form': form,
        'profile': profile
    })

@login_required
def cambiar_password(request):
    """Vista para cambiar la contraseña del usuario"""
    from django.contrib.auth.forms import PasswordChangeForm

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Actualizar la sesión para evitar logout
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            messages.success(request, _('Tu contraseña ha sido cambiada exitosamente.'))
            return redirect('perfil_usuario')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'tienda/cambiar_password.html', {
        'form': form
    })

def cupones_disponibles(request):
    """Vista para mostrar los cupones de descuento disponibles"""
    cupones = Cupon.objects.filter(activo=True, fecha_expiracion__gte=date.today()).order_by('minimo_compra')

    return render(request, 'tienda/cupones.html', {
        'cupones': cupones
    })

@login_required
def admin_inventario(request):
    """Vista de administración de inventario"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    # Filtros
    categoria_filter = request.GET.get('categoria', '')
    stock_filter = request.GET.get('stock', '')
    estado_filter = request.GET.get('estado', '')

    productos = Producto.objects.all().order_by('nombre')

    # Aplicar filtros
    if categoria_filter:
        productos = productos.filter(categoria=categoria_filter)
    if stock_filter == 'bajo':
        productos = productos.filter(stock__lte=models.F('stock_minimo'), stock__gt=0)
    elif stock_filter == 'agotado':
        productos = productos.filter(stock=0)
    elif stock_filter == 'disponible':
        productos = productos.filter(stock__gt=0)
    if estado_filter:
        productos = productos.filter(estado=estado_filter)

    # Estadísticas
    stats = {
        'total_productos': Producto.objects.count(),
        'productos_activos': Producto.objects.filter(estado='activo').count(),
        'productos_inactivos': Producto.objects.filter(estado='inactivo').count(),
        'productos_agotados': Producto.objects.filter(estado='agotado').count(),
        'stock_bajo': Producto.objects.filter(stock__lte=models.F('stock_minimo'), stock__gt=0).count(),
        'total_unidades': Producto.objects.aggregate(total=models.Sum('stock'))['total'] or 0,
    }

    categorias = Producto.objects.values_list('categoria', flat=True).distinct()

    return render(request, 'tienda/admin_inventario.html', {
        'productos': productos,
        'stats': stats,
        'categorias': categorias,
        'filtros': {
            'categoria': categoria_filter,
            'stock': stock_filter,
            'estado': estado_filter,
        }
    })

@login_required
def actualizar_stock(request, producto_id):
    """Vista AJAX para actualizar stock de un producto"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        producto = Producto.objects.get(id=producto_id)
        nuevo_stock = int(request.POST.get('stock', 0))
        descripcion = request.POST.get('descripcion', 'Ajuste manual')

        if nuevo_stock < 0:
            return JsonResponse({'success': False, 'error': 'El stock no puede ser negativo'})

        # Calcular la diferencia
        diferencia = nuevo_stock - producto.stock

        if diferencia > 0:
            # Aumento de stock
            MovimientoInventario.objects.create(
                producto=producto,
                tipo='entrada',
                cantidad=diferencia,
                descripcion=descripcion,
                usuario=request.user
            )
        elif diferencia < 0:
            # Reducción de stock
            MovimientoInventario.objects.create(
                producto=producto,
                tipo='salida',
                cantidad=diferencia,  # Negativo
                descripcion=descripcion,
                usuario=request.user
            )

        # Actualizar stock
        producto.stock = nuevo_stock
        producto.save()

        return JsonResponse({
            'success': True,
            'nuevo_stock': producto.stock,
            'stock_bajo': producto.stock_bajo,
            'agotado': producto.agotado
        })

    except Producto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'})
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Valor de stock inválido'})

@login_required
def movimientos_inventario(request):
    """Vista para ver movimientos de inventario"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    movimientos = MovimientoInventario.objects.select_related('producto', 'usuario').order_by('-fecha')[:100]

    return render(request, 'tienda/movimientos_inventario.html', {
        'movimientos': movimientos
    })

# ========================================
# VISTAS DE ADMINISTRACIÓN PERSONALIZADAS
# ========================================

@login_required
def admin_dashboard(request):
    """Dashboard administrativo principal"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder al panel de administración.'))
        return redirect('home')

    # Estadísticas generales
    stats = {
        'total_usuarios': User.objects.count(),
        'total_productos': Producto.objects.count(),
        'productos_activos': Producto.objects.filter(estado='activo').count(),
        'total_pedidos': Pedido.objects.count(),
        'pedidos_pendientes': Pedido.objects.filter(estado='pendiente').count(),
        'pedidos_entregados': Pedido.objects.filter(estado='entregado').count(),
        'total_ingresos': Pedido.objects.filter(estado='entregado').aggregate(
            total=Sum('total_pedido')
        )['total'] or 0,
        'productos_stock_bajo': Producto.objects.filter(
            stock__lte=models.F('stock_minimo'),
            stock__gt=0
        ).count(),
        'productos_agotados': Producto.objects.filter(stock=0).count(),
    }

    # Pedidos recientes
    pedidos_recientes = Pedido.objects.select_related('usuario').order_by('-fecha_creacion')[:5]

    # Productos más vendidos
    productos_populares = Producto.objects.filter(estado='activo').order_by('-stock')[:5]

    # Alertas
    alertas = []
    if stats['productos_stock_bajo'] > 0:
        alertas.append({
            'tipo': 'warning',
            'icono': 'bi-exclamation-triangle',
            'titulo': f"{stats['productos_stock_bajo']} productos con stock bajo",
            'mensaje': 'Revisa el inventario para evitar faltantes.'
        })
    if stats['productos_agotados'] > 0:
        alertas.append({
            'tipo': 'danger',
            'icono': 'bi-x-circle',
            'titulo': f"{stats['productos_agotados']} productos agotados",
            'mensaje': 'Estos productos no se pueden vender actualmente.'
        })

    return render(request, 'tienda/admin_dashboard.html', {
        'stats': stats,
        'pedidos_recientes': pedidos_recientes,
        'productos_populares': productos_populares,
        'alertas': alertas,
    })

@login_required
def admin_productos(request):
    """Gestión de productos administrativos"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    # Filtros
    categoria_filter = request.GET.get('categoria', '')
    estado_filter = request.GET.get('estado', '')
    stock_filter = request.GET.get('stock', '')
    query = request.GET.get('q', '')

    productos = Producto.objects.all().order_by('nombre')

    # Aplicar filtros
    if categoria_filter:
        productos = productos.filter(categoria=categoria_filter)
    if estado_filter:
        productos = productos.filter(estado=estado_filter)
    if stock_filter == 'bajo':
        productos = productos.filter(stock__lte=models.F('stock_minimo'), stock__gt=0)
    elif stock_filter == 'agotado':
        productos = productos.filter(stock=0)
    elif stock_filter == 'disponible':
        productos = productos.filter(stock__gt=0)
    if query:
        productos = productos.filter(
            models.Q(nombre__icontains=query) |
            models.Q(descripcion__icontains=query) |
            models.Q(sku__icontains=query)
        )

    # Estadísticas
    stats = {
        'total': Producto.objects.count(),
        'activos': Producto.objects.filter(estado='activo').count(),
        'inactivos': Producto.objects.filter(estado='inactivo').count(),
        'agotados': Producto.objects.filter(stock=0).count(),
        'stock_bajo': Producto.objects.filter(stock__lte=models.F('stock_minimo'), stock__gt=0).count(),
    }

    categorias = Producto.objects.values_list('categoria', flat=True).distinct()

    return render(request, 'tienda/admin_productos.html', {
        'productos': productos,
        'stats': stats,
        'categorias': categorias,
        'filtros': {
            'categoria': categoria_filter,
            'estado': estado_filter,
            'stock': stock_filter,
            'q': query,
        }
    })

@login_required
def admin_pedidos(request):
    """Gestión de pedidos administrativos"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    # Filtros
    estado_filter = request.GET.get('estado', '')
    fecha_filter = request.GET.get('fecha', '')
    usuario_filter = request.GET.get('usuario', '')

    pedidos = Pedido.objects.select_related('usuario').order_by('-fecha_creacion')

    # Aplicar filtros
    if estado_filter:
        pedidos = pedidos.filter(estado=estado_filter)
    if usuario_filter:
        pedidos = pedidos.filter(
            models.Q(usuario__username__icontains=usuario_filter) |
            models.Q(usuario__email__icontains=usuario_filter)
        )

    # Estadísticas
    stats = {
        'total': Pedido.objects.count(),
        'pendientes': Pedido.objects.filter(estado='pendiente').count(),
        'procesando': Pedido.objects.filter(estado='procesando').count(),
        'entregados': Pedido.objects.filter(estado='entregado').count(),
        'cancelados': Pedido.objects.filter(estado='cancelado').count(),
        'total_ingresos': Pedido.objects.filter(estado='entregado').aggregate(
            total=Sum('total_pedido')
        )['total'] or 0,
    }

    return render(request, 'tienda/admin_pedidos.html', {
        'pedidos': pedidos,
        'stats': stats,
        'filtros': {
            'estado': estado_filter,
            'usuario': usuario_filter,
        }
    })

@login_required
def admin_pedidos_pendientes(request):
    """Vista específica para pedidos pendientes"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    pedidos = Pedido.objects.filter(estado='pendiente').select_related('usuario').order_by('-fecha_creacion')

    # Estadísticas específicas para pedidos pendientes
    stats = {
        'total_pendientes': pedidos.count(),
        'pendientes_hoy': pedidos.filter(fecha_creacion__date=date.today()).count(),
        'pendientes_semana': pedidos.filter(fecha_creacion__date__gte=date.today() - timedelta(days=7)).count(),
        'valor_total_pendientes': pedidos.aggregate(total=Sum('total_pedido'))['total'] or 0,
    }

    return render(request, 'tienda/admin_pedidos_pendientes.html', {
        'pedidos': pedidos,
        'stats': stats,
        'titulo': 'Pedidos Pendientes',
        'estado_actual': 'pendiente'
    })

@login_required
def admin_pedidos_procesando(request):
    """Vista específica para pedidos en proceso"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    pedidos = Pedido.objects.filter(estado='procesando').select_related('usuario').order_by('-fecha_creacion')

    # Estadísticas específicas para pedidos procesando
    stats = {
        'total_procesando': pedidos.count(),
        'procesando_hoy': pedidos.filter(fecha_creacion__date=date.today()).count(),
        'procesando_semana': pedidos.filter(fecha_creacion__date__gte=date.today() - timedelta(days=7)).count(),
        'valor_total_procesando': pedidos.aggregate(total=Sum('total_pedido'))['total'] or 0,
    }

    return render(request, 'tienda/admin_pedidos_procesando.html', {
        'pedidos': pedidos,
        'stats': stats,
        'titulo': 'Pedidos en Proceso',
        'estado_actual': 'procesando'
    })

@login_required
def admin_pedidos_enviados(request):
    """Vista específica para pedidos enviados"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    pedidos = Pedido.objects.filter(estado='enviado').select_related('usuario').order_by('-fecha_creacion')

    # Estadísticas específicas para pedidos enviados
    stats = {
        'total_enviados': pedidos.count(),
        'enviados_hoy': pedidos.filter(fecha_creacion__date=date.today()).count(),
        'enviados_semana': pedidos.filter(fecha_creacion__date__gte=date.today() - timedelta(days=7)).count(),
        'valor_total_enviados': pedidos.aggregate(total=Sum('total_pedido'))['total'] or 0,
    }

    return render(request, 'tienda/admin_pedidos_enviados.html', {
        'pedidos': pedidos,
        'stats': stats,
        'titulo': 'Pedidos Enviados',
        'estado_actual': 'enviado'
    })

@login_required
def admin_pedidos_entregados(request):
    """Vista específica para pedidos entregados"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    # Filtros
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    usuario_filter = request.GET.get('usuario')

    pedidos = Pedido.objects.filter(estado='entregado').select_related('usuario').order_by('-fecha_creacion')

    # Aplicar filtros
    if fecha_desde:
        pedidos = pedidos.filter(fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        pedidos = pedidos.filter(fecha_creacion__date__lte=fecha_hasta)
    if usuario_filter:
        pedidos = pedidos.filter(
            models.Q(usuario__username__icontains=usuario_filter) |
            models.Q(usuario__email__icontains=usuario_filter)
        )

    # Estadísticas específicas para pedidos entregados
    stats = {
        'total_entregados': pedidos.count(),
        'entregados_hoy': pedidos.filter(fecha_creacion__date=date.today()).count(),
        'entregados_semana': pedidos.filter(fecha_creacion__date__gte=date.today() - timedelta(days=7)).count(),
        'valor_total_entregados': pedidos.aggregate(total=Sum('total_pedido'))['total'] or 0,
    }

    return render(request, 'tienda/admin_pedidos_entregados.html', {
        'pedidos': pedidos,
        'stats': stats,
        'titulo': 'Pedidos Entregados',
        'estado_actual': 'entregado'
    })

@login_required
def admin_pedidos_cancelados(request):
    """Vista específica para pedidos cancelados"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    # Filtros
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    usuario_filter = request.GET.get('usuario')

    pedidos = Pedido.objects.filter(estado='cancelado').select_related('usuario').order_by('-fecha_creacion')

    # Aplicar filtros
    if fecha_desde:
        pedidos = pedidos.filter(fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        pedidos = pedidos.filter(fecha_creacion__date__lte=fecha_hasta)
    if usuario_filter:
        pedidos = pedidos.filter(
            models.Q(usuario__username__icontains=usuario_filter) |
            models.Q(usuario__email__icontains=usuario_filter)
        )

    # Estadísticas específicas para pedidos cancelados
    stats = {
        'total_cancelados': pedidos.count(),
        'cancelados_hoy': pedidos.filter(fecha_creacion__date=date.today()).count(),
        'cancelados_semana': pedidos.filter(fecha_creacion__date__gte=date.today() - timedelta(days=7)).count(),
        'valor_total_cancelados': pedidos.aggregate(total=Sum('total_pedido'))['total'] or 0,
    }

    return render(request, 'tienda/admin_pedidos_cancelados.html', {
        'pedidos': pedidos,
        'stats': stats,
        'titulo': 'Pedidos Cancelados',
        'estado_actual': 'cancelado'
    })

@login_required
def admin_usuarios(request):
    """Gestión de usuarios administrativos"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    # Filtros
    query = request.GET.get('q', '')
    estado_filter = request.GET.get('estado', '')
    rol_filter = request.GET.get('rol', '')

    usuarios = User.objects.all().order_by('-date_joined')

    # Aplicar filtros
    if query:
        usuarios = usuarios.filter(
            models.Q(username__icontains=query) |
            models.Q(email__icontains=query) |
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query)
        )
    if estado_filter == 'activos':
        usuarios = usuarios.filter(is_active=True)
    elif estado_filter == 'inactivos':
        usuarios = usuarios.filter(is_active=False)
    if rol_filter == 'staff':
        usuarios = usuarios.filter(is_staff=True)
    elif rol_filter == 'superuser':
        usuarios = usuarios.filter(is_superuser=True)

    # Estadísticas
    stats = {
        'total': User.objects.count(),
        'activos': User.objects.filter(is_active=True).count(),
        'staff': User.objects.filter(is_staff=True).count(),
        'superuser': User.objects.filter(is_superuser=True).count(),
    }

    return render(request, 'tienda/admin_usuarios.html', {
        'usuarios': usuarios,
        'stats': stats,
        'filtros': {
            'q': query,
            'estado': estado_filter,
            'rol': rol_filter,
        }
    })

@login_required
def admin_cupones(request):
    """Gestión de cupones administrativos"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    # Filtros
    estado_filter = request.GET.get('estado', '')
    tipo_filter = request.GET.get('tipo', '')

    cupones = Cupon.objects.all().order_by('-id')

    # Aplicar filtros
    if estado_filter == 'activos':
        cupones = cupones.filter(activo=True, fecha_expiracion__gte=date.today())
    elif estado_filter == 'expirados':
        cupones = cupones.filter(fecha_expiracion__lt=date.today())
    elif estado_filter == 'inactivos':
        cupones = cupones.filter(activo=False)
    if tipo_filter:
        cupones = cupones.filter(tipo_descuento=tipo_filter)

    # Estadísticas
    stats = {
        'total': Cupon.objects.count(),
        'activos': Cupon.objects.filter(activo=True, fecha_expiracion__gte=date.today()).count(),
        'expirados': Cupon.objects.filter(fecha_expiracion__lt=date.today()).count(),
        'usados': Cupon.objects.filter(activo=False).count(),
    }

    return render(request, 'tienda/admin_cupones.html', {
        'cupones': cupones,
        'stats': stats,
        'filtros': {
            'estado': estado_filter,
            'tipo': tipo_filter,
        }
    })

@login_required
def admin_inventario(request):
    """Vista de inventario administrativo"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    # Filtros
    categoria_filter = request.GET.get('categoria', '')
    stock_filter = request.GET.get('stock', '')

    productos = Producto.objects.all().order_by('nombre')

    # Aplicar filtros
    if categoria_filter:
        productos = productos.filter(categoria=categoria_filter)
    if stock_filter == 'bajo':
        productos = productos.filter(stock__lte=models.F('stock_minimo'), stock__gt=0)
    elif stock_filter == 'agotado':
        productos = productos.filter(stock=0)
    elif stock_filter == 'disponible':
        productos = productos.filter(stock__gt=0)

    # Estadísticas de inventario
    stats = {
        'total_productos': Producto.objects.count(),
        'productos_activos': Producto.objects.filter(estado='activo').count(),
        'total_unidades': Producto.objects.aggregate(total=Sum('stock'))['total'] or 0,
        'productos_stock_bajo': Producto.objects.filter(stock__lte=models.F('stock_minimo'), stock__gt=0).count(),
        'productos_agotados': Producto.objects.filter(stock=0).count(),
        'valor_inventario': Producto.objects.filter(estado='activo').aggregate(
            total=Sum(models.F('stock') * models.F('precio'))
        )['total'] or 0,
    }

    # Movimientos recientes
    movimientos_recientes = MovimientoInventario.objects.select_related('producto', 'usuario').order_by('-fecha')[:10]

    categorias = Producto.objects.values_list('categoria', flat=True).distinct()

    return render(request, 'tienda/admin_inventario.html', {
        'productos': productos,
        'stats': stats,
        'movimientos_recientes': movimientos_recientes,
        'categorias': categorias,
        'filtros': {
            'categoria': categoria_filter,
            'stock': stock_filter,
        }
    })

@login_required
def admin_reportes(request):
    """Vista de reportes administrativos"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    # Filtros de fecha
    periodo = request.GET.get('periodo', 'mes')

    if periodo == 'dia':
        ventas = Pedido.objects.filter(estado='entregado').annotate(
            periodo=TruncDay('fecha_creacion')
        ).values('periodo').annotate(
            total=Sum('total_pedido'),
            cantidad=Count('id')
        ).order_by('-periodo')[:30]
    else:
        ventas = Pedido.objects.filter(estado='entregado').annotate(
            periodo=TruncMonth('fecha_creacion')
        ).values('periodo').annotate(
            total=Sum('total_pedido'),
            cantidad=Count('id')
        ).order_by('-periodo')[:12]

    # Productos más vendidos
    productos_mas_vendidos = PedidoProducto.objects.values(
        'producto__nombre'
    ).annotate(
        total_vendido=Sum('cantidad'),
        ingresos=Sum(models.F('cantidad') * models.F('precio_unitario'))
    ).order_by('-total_vendido')[:10]

    # Estadísticas generales
    stats = {
        'total_pedidos': Pedido.objects.count(),
        'pedidos_entregados': Pedido.objects.filter(estado='entregado').count(),
        'total_ingresos': Pedido.objects.filter(estado='entregado').aggregate(
            total=Sum('total_pedido')
        )['total'] or 0,
        'productos_vendidos': PedidoProducto.objects.aggregate(
            total=Sum('cantidad')
        )['total'] or 0,
        'usuarios_activos': User.objects.filter(is_active=True).count(),
    }

    return render(request, 'tienda/admin_reportes.html', {
        'ventas': ventas,
        'productos_mas_vendidos': productos_mas_vendidos,
        'stats': stats,
        'periodo': periodo,
    })

@login_required
def admin_configuracion(request):
    """Vista de configuración del sistema"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    if request.method == 'POST':
        # Aquí iría la lógica para guardar configuraciones
        messages.success(request, _('Configuración guardada exitosamente.'))
        return redirect('admin_configuracion')

    # Obtener configuración actual del sistema
    configuracion = ConfiguracionSistema.get_configuracion()

    return render(request, 'tienda/admin_configuracion.html', {
        'configuraciones': configuracion,
    })

# ========================================
# VISTAS AJAX PARA ADMINISTRACIÓN
# ========================================

@login_required
def admin_actualizar_stock(request, producto_id):
    """Vista AJAX para actualizar stock de un producto"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        producto = Producto.objects.get(id=producto_id)
        nuevo_stock = int(request.POST.get('stock', 0))
        descripcion = request.POST.get('descripcion', 'Ajuste manual')

        if nuevo_stock < 0:
            return JsonResponse({'success': False, 'error': 'El stock no puede ser negativo'})

        # Calcular la diferencia
        diferencia = nuevo_stock - producto.stock

        if diferencia > 0:
            # Aumento de stock
            MovimientoInventario.objects.create(
                producto=producto,
                tipo='entrada',
                cantidad=diferencia,
                descripcion=descripcion,
                usuario=request.user
            )
        elif diferencia < 0:
            # Reducción de stock
            MovimientoInventario.objects.create(
                producto=producto,
                tipo='salida',
                cantidad=abs(diferencia),
                descripcion=descripcion,
                usuario=request.user
            )

        # Actualizar stock
        producto.stock = nuevo_stock
        producto.save()

        return JsonResponse({
            'success': True,
            'nuevo_stock': producto.stock,
            'stock_bajo': producto.stock_bajo,
            'agotado': producto.agotado
        })

    except Producto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'})
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Valor de stock inválido'})

@login_required
def admin_cambiar_estado_pedido(request, pedido_id):
    """Vista AJAX para cambiar estado de un pedido"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        pedido = Pedido.objects.get(id=pedido_id)
        nuevo_estado = request.POST.get('estado', '')

        if nuevo_estado not in ['pendiente', 'procesando', 'pagado', 'enviado', 'entregado', 'cancelado']:
            return JsonResponse({'success': False, 'error': 'Estado inválido'})

        pedido.estado = nuevo_estado
        pedido.save()

        # Enviar email de actualización de estado de pedido
        try:
            email_service = EmailService()
            email_service.enviar_actualizacion_pedido(pedido)
        except Exception as e:
            # No fallar la actualización si hay error con el email
            pass

        return JsonResponse({
            'success': True,
            'nuevo_estado': pedido.get_estado_display(),
            'estado_class': f'badge-{"success" if nuevo_estado == "entregado" else "warning" if nuevo_estado == "pendiente" else "info" if nuevo_estado == "procesando" else "danger"}'
        })

    except Pedido.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Pedido no encontrado'})

@login_required
def admin_cambiar_estado_usuario(request, usuario_id):
    """Vista AJAX para cambiar estado de un usuario"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        usuario = User.objects.get(id=usuario_id)
        nuevo_estado = request.POST.get('estado', '')

        if nuevo_estado not in ['activo', 'inactivo']:
            return JsonResponse({'success': False, 'error': 'Estado inválido'})

        usuario.is_active = (nuevo_estado == 'activo')
        usuario.save()

        return JsonResponse({
            'success': True,
            'nuevo_estado': 'Activo' if usuario.is_active else 'Inactivo',
            'estado_class': 'badge-success' if usuario.is_active else 'badge-danger'
        })

    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Usuario no encontrado'})

@login_required
def admin_cambiar_estado_cupon(request, cupon_id):
    """Vista AJAX para cambiar estado de un cupón"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        cupon = Cupon.objects.get(id=cupon_id)
        nuevo_estado = request.POST.get('estado', '')

        if nuevo_estado not in ['activo', 'inactivo']:
            return JsonResponse({'success': False, 'error': 'Estado inválido'})

        cupon.activo = (nuevo_estado == 'activo')
        cupon.save()

        return JsonResponse({
            'success': True,
            'nuevo_estado': 'Activo' if cupon.activo else 'Inactivo',
            'estado_class': 'badge-success' if cupon.activo else 'badge-danger'
        })

    except Cupon.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Cupón no encontrado'})

@login_required
def admin_actualizar_estado_pedido(request):
    """Vista AJAX para actualizar estado de pedido"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        pedido_id = request.POST.get('pedido_id')
        nuevo_estado = request.POST.get('estado')

        pedido = Pedido.objects.get(id=pedido_id)
        pedido.estado = nuevo_estado
        pedido.save()

        return JsonResponse({
            'success': True,
            'estado_display': pedido.get_estado_display()
        })

    except Pedido.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Pedido no encontrado'})

@login_required
def admin_actualizar_estado_usuario(request):
    """Vista AJAX para actualizar estado de usuario"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:

        usuario_id = request.POST.get('usuario_id')
        nuevo_estado = request.POST.get('estado')

        usuario = User.objects.get(id=usuario_id)
        usuario.is_active = (nuevo_estado == 'activo')
        usuario.save()

        return JsonResponse({
            'success': True,
            'estado_display': 'Activo' if usuario.is_active else 'Inactivo'
        })

    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Usuario no encontrado'})

@login_required
def admin_actualizar_estado_cupon(request):
    """Vista AJAX para actualizar estado de cupón"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        cupon_id = request.POST.get('cupon_id')
        nuevo_estado = request.POST.get('estado')

        cupon = Cupon.objects.get(id=cupon_id)
        cupon.activo = (nuevo_estado == 'activo')
        cupon.save()

        return JsonResponse({
            'success': True,
            'estado_display': 'Activo' if cupon.activo else 'Inactivo'
        })

    except Cupon.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Cupón no encontrado'})

@login_required
def admin_actualizar_inventario(request):
    """Vista AJAX para actualizar inventario"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        producto_id = request.POST.get('producto_id')
        nuevo_stock = int(request.POST.get('stock', 0))
        descripcion = request.POST.get('descripcion', 'Ajuste desde admin')

        producto = Producto.objects.get(id=producto_id)

        if nuevo_stock < 0:
            return JsonResponse({'success': False, 'error': 'El stock no puede ser negativo'})

        # Calcular diferencia y crear movimiento
        diferencia = nuevo_stock - producto.stock

        if diferencia != 0:
            MovimientoInventario.objects.create(
                producto=producto,
                tipo='entrada' if diferencia > 0 else 'salida',
                cantidad=abs(diferencia),
                descripcion=descripcion,
                usuario=request.user
            )

        producto.stock = nuevo_stock
        producto.save()

        return JsonResponse({
            'success': True,
            'nuevo_stock': producto.stock,
            'stock_bajo': producto.stock_bajo,
            'agotado': producto.agotado
        })

    except Producto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'})
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Valor de stock inválido'})

@login_required
def admin_guardar_configuracion(request):
    """Vista AJAX para guardar configuración del sistema"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        # Aquí iría la lógica para guardar configuraciones en la base de datos
        # Por ahora solo simulamos el guardado
        configuracion_data = {
            'sitio_activo': request.POST.get('sitio_activo') == 'true',
            'registro_abierto': request.POST.get('registro_abierto') == 'true',
            'envio_gratuito_minimo': float(request.POST.get('envio_gratuito_minimo', 0)),
            'impuestos_activos': request.POST.get('impuestos_activos') == 'true',
            'moneda': request.POST.get('moneda'),
            'email_notificaciones': request.POST.get('email_notificaciones') == 'true',
            'productos_por_pagina': int(request.POST.get('productos_por_pagina', 12)),
            'stock_minimo_alerta': int(request.POST.get('stock_minimo_alerta', 5)),
        }

        # Simular guardado exitoso
        return JsonResponse({
            'success': True,
            'mensaje': 'Configuración guardada exitosamente'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def admin_restaurar_configuracion(request):
    """Vista AJAX para restaurar configuración predeterminada"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        # Aquí iría la lógica para restaurar configuraciones predeterminadas
        return JsonResponse({
            'success': True,
            'mensaje': 'Configuración restaurada a valores predeterminados'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def admin_crear_backup(request):
    """Vista AJAX para crear backup del sistema"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        # Aquí iría la lógica para crear backup
        # Por ahora solo simulamos
        return JsonResponse({
            'success': True,
            'mensaje': 'Backup creado exitosamente',
            'archivo': f'backup_{date.today().strftime("%Y%m%d")}.sql'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def admin_probar_email(request):
    """Vista AJAX para probar configuración de email"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        # Aquí iría la lógica para probar envío de email
        # Por ahora solo simulamos
        return JsonResponse({
            'success': True,
            'mensaje': 'Email de prueba enviado exitosamente'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def admin_agregar_producto(request):
    """Vista para agregar un nuevo producto"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save()
            messages.success(request, f'Producto "{producto.nombre}" agregado exitosamente.')
            return redirect('admin_productos')
    else:
        form = ProductoForm()

    return render(request, 'tienda/admin_producto_form.html', {
        'form': form,
        'titulo': 'Agregar Producto',
        'accion': 'Agregar'
    })

@login_required
def admin_editar_producto(request, producto_id):
    """Vista para editar un producto existente"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    try:
        producto = Producto.objects.get(id=producto_id)
    except Producto.DoesNotExist:
        messages.error(request, 'Producto no encontrado.')
        return redirect('admin_productos')

    if request.method == 'POST':
        print(f"DEBUG: Archivos subidos: {request.FILES}")
        form = ProductoAdminForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            print("DEBUG: Formulario válido")
            producto = form.save()
            messages.success(request, f'Producto "{producto.nombre}" actualizado exitosamente.')
            return redirect('admin_productos')
        else:
            print(f"DEBUG: Errores del formulario: {form.errors}")
    else:
        form = ProductoAdminForm(instance=producto)

    return render(request, 'tienda/admin_producto_form.html', {
        'form': form,
        'titulo': 'Editar Producto',
        'accion': 'Actualizar',
        'producto': producto
    })

@login_required
def admin_eliminar_producto(request, producto_id):
    """Vista AJAX para eliminar un producto"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        producto = Producto.objects.get(id=producto_id)

        # Verificar si el producto tiene pedidos asociados
        if PedidoProducto.objects.filter(producto=producto).exists():
            return JsonResponse({
                'success': False,
                'error': 'No se puede eliminar el producto porque tiene pedidos asociados.'
            })

        nombre = producto.nombre
        producto.delete()

        return JsonResponse({
            'success': True,
            'mensaje': f'Producto "{nombre}" eliminado exitosamente.'
        })

    except Producto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'})

@login_required
def admin_agregar_cupon(request):
    """Vista para agregar un nuevo cupón"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    if request.method == 'POST':
        form = CuponForm(request.POST)
        if form.is_valid():
            cupon = form.save()
            messages.success(request, f'Cupón "{cupon.codigo}" creado exitosamente.')
            return redirect('admin_cupones')
    else:
        form = CuponForm()

    return render(request, 'tienda/admin_cupon_form.html', {
        'form': form,
        'titulo': 'Crear Cupón',
        'accion': 'Crear'
    })

@login_required
def admin_editar_cupon(request, cupon_id):
    """Vista para editar un cupón existente"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    try:
        cupon = Cupon.objects.get(id=cupon_id)
    except Cupon.DoesNotExist:
        messages.error(request, 'Cupón no encontrado.')
        return redirect('admin_cupones')

    if request.method == 'POST':
        form = CuponForm(request.POST, instance=cupon)
        if form.is_valid():
            cupon = form.save()
            messages.success(request, f'Cupón "{cupon.codigo}" actualizado exitosamente.')
            return redirect('admin_cupones')
    else:
        form = CuponForm(instance=cupon)

    return render(request, 'tienda/admin_cupon_form.html', {
        'form': form,
        'titulo': 'Editar Cupón',
        'accion': 'Actualizar',
        'cupon': cupon
    })

@login_required
def admin_eliminar_cupon(request, cupon_id):
    """Vista AJAX para eliminar un cupón"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        cupon = Cupon.objects.get(id=cupon_id)

        # Verificar si el cupón ha sido usado
        if cupon.usos_actuales > 0:
            return JsonResponse({
                'success': False,
                'error': 'No se puede eliminar el cupón porque ya ha sido usado.'
            })

        codigo = cupon.codigo
        cupon.delete()

        return JsonResponse({
            'success': True,
            'mensaje': f'Cupón "{codigo}" eliminado exitosamente.'
        })

    except Cupon.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Cupón no encontrado'})

@login_required
def admin_detalle_pedido(request, pedido_id):
    """Vista para ver el detalle completo de un pedido"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    try:
        pedido = Pedido.objects.select_related('usuario').prefetch_related('pedidoproducto_set__producto').get(id=pedido_id)
    except Pedido.DoesNotExist:
        messages.error(request, 'Pedido no encontrado.')
        return redirect('admin_pedidos')

    # Calcular totales
    productos_pedido = pedido.pedidoproducto_set.all()
    subtotal = sum(item.precio_unitario * item.cantidad for item in productos_pedido)

    # Información de envío (simulada por ahora)
    info_envio = {
        'direccion': getattr(pedido, 'direccion_envio', 'Dirección no especificada'),
        'ciudad': getattr(pedido, 'ciudad_envio', 'Ciudad no especificada'),
        'codigo_postal': getattr(pedido, 'codigo_postal_envio', 'Código postal no especificado'),
        'telefono': getattr(pedido, 'telefono_envio', 'Teléfono no especificado'),
    }

    return render(request, 'tienda/admin_pedido_detalle.html', {
        'pedido': pedido,
        'productos_pedido': productos_pedido,
        'subtotal': subtotal,
        'info_envio': info_envio,
    })

@login_required
def admin_agregar_usuario(request):
    """Vista para agregar un nuevo usuario"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Usuario "{user.username}" creado exitosamente.')
            return redirect('admin_usuarios')
    else:
        form = UserCreationForm()

    return render(request, 'tienda/admin_usuario_form.html', {
        'form': form,
        'titulo': 'Agregar Usuario',
        'accion': 'Agregar'
    })

@login_required
def admin_editar_usuario(request, usuario_id):
    """Vista para editar un usuario existente"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    try:
        usuario = User.objects.get(id=usuario_id)
    except User.DoesNotExist:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('admin_usuarios')

    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f'Usuario "{usuario.username}" actualizado exitosamente.')
            return redirect('admin_usuarios')
    else:
        form = UserChangeForm(instance=usuario)

    return render(request, 'tienda/admin_usuario_form.html', {
        'form': form,
        'titulo': 'Editar Usuario',
        'accion': 'Actualizar',
        'usuario': usuario
    })

@login_required
def admin_cambiar_permisos_usuario(request, usuario_id):
    """Vista AJAX para cambiar permisos de un usuario"""
    if not request.user.is_staff or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        usuario = User.objects.get(id=usuario_id)

        # No permitir cambiar permisos de superusuarios desde aquí
        if usuario.is_superuser:
            return JsonResponse({
                'success': False,
                'error': 'No se pueden cambiar los permisos de un superusuario.'
            })

        is_staff = request.POST.get('is_staff') == 'true'

        usuario.is_staff = is_staff
        usuario.save()

        return JsonResponse({
            'success': True,
            'mensaje': f'Permisos de "{usuario.username}" actualizados exitosamente.',
            'is_staff': usuario.is_staff
        })

    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Usuario no encontrado'})

@login_required
def admin_detalle_usuario(request, usuario_id):
    """Vista para ver el detalle completo de un usuario"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    try:
               usuario = User.objects.get(id=usuario_id)
    except User.DoesNotExist:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('admin_usuarios')

    # Estadísticas del usuario
    pedidos_usuario = Pedido.objects.filter(usuario=usuario)
    stats = {
        'total_pedidos': pedidos_usuario.count(),
        'pedidos_entregados': pedidos_usuario.filter(estado='entregado').count(),
        'total_gastado': pedidos_usuario.filter(estado='entregado').aggregate(
            total=Sum('total_pedido')
        )['total'] or 0,
        'ultimo_pedido': pedidos_usuario.order_by('-fecha_creacion').first(),
    }

    return render(request, 'tienda/admin_usuario_detalle.html', {
        'usuario': usuario,
        'stats': stats,
        'pedidos_recientes': pedidos_usuario.order_by('-fecha_creacion')[:5],
    })


# ===== SISTEMA DE LISTA DE DESEOS (WISHLIST) =====

@login_required
def wishlist(request):
    """Vista para mostrar la lista de deseos del usuario"""
    wishlist_items = Wishlist.objects.filter(usuario=request.user).select_related('producto')

    # Preparar datos adicionales para cada item de wishlist
    wishlist_data = []
    for item in wishlist_items:
        # Calcular estadísticas de contribuciones si están activas
        contribuciones_data = None
        if item.permitir_contribuciones:
            contribuciones = ContribucionWishlist.objects.filter(
                wishlist_item=item,
                estado='completado'
            )
            total_contribuido = contribuciones.aggregate(total=Sum('monto'))['total'] or 0
            num_contribuidores = contribuciones.values('usuario_contribuyente').distinct().count()

            progreso = (total_contribuido / item.contribucion_objetivo) * 100 if item.contribucion_objetivo > 0 else 0

            contribuciones_data = {
                'total_contribuido': total_contribuido,
                'num_contribuidores': num_contribuidores,
                'progreso': progreso,
                'faltante': max(0, item.contribucion_objetivo - total_contribuido),
                'meta_alcanzada': total_contribuido >= item.contribucion_objetivo,
                'contribuciones': contribuciones.select_related('usuario_contribuyente')[:5],  # Últimas 5 contribuciones
            }

        wishlist_data.append({
            'item': item,
            'contribuciones_data': contribuciones_data,
        })

    return render(request, 'tienda/wishlist.html', {
        'wishlist_data': wishlist_data,
        'wishlist_items': wishlist_items,  # Mantener compatibilidad con templates existentes
    })

@login_required
def agregar_a_wishlist(request, producto_id):
    """Vista para agregar un producto a la lista de deseos"""
    if request.method == 'POST':
        try:
            producto = Producto.objects.get(id=producto_id)

            # Verificar si ya está en la wishlist
            wishlist_item, created = Wishlist.objects.get_or_create(
                usuario=request.user,
                producto=producto,
                defaults={'fecha_agregado': timezone.now()}
            )

            if created:
                messages.success(request, f'"{producto.nombre}" ha sido agregado a tu lista de deseos.')
            else:
                messages.info(request, f'"{producto.nombre}" ya está en tu lista de deseos.')

        except Producto.DoesNotExist:
            messages.error(request, 'Producto no encontrado.')

    return redirect(request.META.get('HTTP_REFERER', 'productos'))

@login_required
def quitar_de_wishlist(request, producto_id):
    """Vista para quitar un producto de la lista de deseos"""
    if request.method == 'POST':
        try:
            wishlist_item = Wishlist.objects.get(
                usuario=request.user,
                producto_id=producto_id
            )
            producto_nombre = wishlist_item.producto.nombre
            wishlist_item.delete()
            messages.success(request, f'"{producto_nombre}" ha sido removido de tu lista de deseos.')

        except Wishlist.DoesNotExist:
            messages.error(request, 'El producto no está en tu lista de deseos.')

    return redirect('wishlist')

@login_required
def toggle_wishlist(request, producto_id):
    """Vista AJAX para agregar/quitar producto de wishlist"""
    if request.method == 'POST':
        try:
            producto = Producto.objects.get(id=producto_id)

            # Verificar si el producto ya está en la wishlist
            wishlist_item = Wishlist.objects.filter(usuario=request.user, producto=producto).first()

            if wishlist_item:
                # Quitar de wishlist
                wishlist_item.delete()
                action = 'removed'
                message = f'{producto.nombre} eliminado de tu lista de deseos'
            else:
                # Agregar a wishlist
                Wishlist.objects.create(usuario=request.user, producto=producto)
                action = 'added'
                message = f'{producto.nombre} agregado a tu lista de deseos'

            # Obtener nuevo conteo
            count = Wishlist.objects.filter(usuario=request.user).count()

            return JsonResponse({
                'success': True,
                'action': action,
                'message': message,
                'count': count
            })

        except Producto.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Producto no encontrado'})
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
def wishlist_count(request):
    """Vista AJAX para obtener el número de productos en la wishlist del usuario"""
    count = Wishlist.objects.filter(usuario=request.user).count()
    return JsonResponse({'count': count})

@login_required
def toggle_contribuciones_wishlist(request, wishlist_id):
    """Vista AJAX para activar/desactivar contribuciones en una wishlist"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        wishlist = Wishlist.objects.get(id=wishlist_id, usuario=request.user)
    except Wishlist.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lista de deseos no encontrada'})

    action = request.POST.get('action')

    if action == 'enable':
        # Activar contribuciones - pedir meta de contribución
        meta_contribucion = request.POST.get('meta_contribucion')
        descripcion = request.POST.get('descripcion', '')

        if not meta_contribucion:
            return JsonResponse({'success': False, 'error': 'Debe especificar una meta de contribución'})

        try:
            meta_contribucion = float(meta_contribucion)
            if meta_contribucion <= 0:
                raise ValueError("La meta debe ser mayor a cero")
            if meta_contribucion < wishlist.producto.precio:
                return JsonResponse({'success': False, 'error': f'La meta debe ser al menos ${wishlist.producto.precio}'})
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Meta de contribución inválida'})

        wishlist.permitir_contribuciones = True
        wishlist.contribucion_objetivo = meta_contribucion
        wishlist.descripcion_contribucion = descripcion
        wishlist.fecha_modificacion = timezone.now()
        wishlist.save()

        messages.success(request, f'Contribuciones activadas para "{wishlist.producto.nombre}". Meta: ${meta_contribucion}')

    elif action == 'disable':
        # Desactivar contribuciones
        wishlist.permitir_contribuciones = False
        wishlist.save()

        messages.success(request, f'Contribuciones desactivadas para "{wishlist.producto.nombre}"')

    else:
        return JsonResponse({'success': False, 'error': 'Acción no válida'})

    return JsonResponse({'success': True})

# ===== SISTEMA DE CONTRIBUCIONES A WISHLIST =====

@login_required
def wishlists_con_contribuciones(request):
    """Vista para mostrar wishlists con contribuciones activas disponibles para contribuir"""
    # Obtener wishlists que tienen contribuciones activas y no son del usuario actual
    wishlists_con_contribuciones = Wishlist.objects.filter(
        permitir_contribuciones=True
    ).exclude(usuario=request.user).select_related('usuario', 'producto').order_by('-fecha_agregado')

    # Preparar datos para mostrar
    wishlists_data = []
    for wishlist in wishlists_con_contribuciones:
        # Calcular estadísticas de contribuciones
        total_contribuido = ContribucionWishlist.objects.filter(
            wishlist_item=wishlist,
            estado='completado'
        ).aggregate(total=Sum('monto'))['total'] or 0

        num_contribuidores = ContribucionWishlist.objects.filter(
            wishlist_item=wishlist,
            estado='completado'
        ).values('usuario_contribuyente').distinct().count()

        # Evitar errores si contribucion_objetivo es None
        objetivo = wishlist.contribucion_objetivo or 0
        try:
            progreso = (total_contribuido / objetivo) * 100 if objetivo > 0 else 0
        except Exception:
            progreso = 0

        faltante = max(0, objetivo - total_contribuido) if objetivo > 0 else 0

        wishlists_data.append({
            'wishlist': wishlist,
            'total_contribuido': total_contribuido,
            'num_contribuidores': num_contribuidores,
            'progreso': progreso,
            'faltante': faltante,
        })

    return render(request, 'tienda/wishlists_contribuciones.html', {
        'wishlists_data': wishlists_data,
    })

@login_required
def wishlist_detalle_contribucion(request, wishlist_id):
    """Vista detallada de una wishlist con información de contribuciones"""
    try:
        wishlist = Wishlist.objects.select_related('usuario', 'producto').get(id=wishlist_id)
    except Wishlist.DoesNotExist:
        # Verificar si el wishlist fue convertido a pedido
        try:
            pedido = Pedido.objects.filter(
                notas__contains='contribuciones grupales'
            ).select_related('usuario').filter(
                usuario=request.user
            ).latest('fecha_creacion')

            messages.success(request, '¡La meta de contribución se alcanzó! Se generó automáticamente un pedido con el producto.')
            return redirect('wishlist_detalle_contribucion', wishlist_id=wishlist_id)
        except Pedido.DoesNotExist:
            messages.error(request, 'Lista de deseos no encontrada.')
            return redirect('wishlists_con_contribuciones')

    # Verificar que tenga contribuciones activas
    if not wishlist.permitir_contribuciones:
        messages.error(request, 'Esta lista de deseos no tiene contribuciones activas.')
        return redirect('wishlists_con_contribuciones')

    # Obtener todas las contribuciones
    contribuciones = ContribucionWishlist.objects.filter(
        wishlist_item=wishlist
    ).select_related('usuario_contribuyente').order_by('-fecha_contribucion')

    # Calcular estadísticas
    total_contribuido = contribuciones.filter(estado='completado').aggregate(
        total=Sum('monto')
    )['total'] or 0

    num_contribuidores = contribuciones.filter(estado='completado').values('usuario_contribuyente').distinct().count()

    progreso = (total_contribuido / wishlist.contribucion_objetivo) * 100 if wishlist.contribucion_objetivo > 0 else 0

    # Verificar si el usuario ya contribuyó
    contribucion_usuario = contribuciones.filter(
        usuario_contribuyente=request.user,
        estado='completado'
    ).first()

    # Verificar si la meta ya se alcanzó
    meta_alcanzada = total_contribuido >= wishlist.contribucion_objetivo

    return render(request, 'tienda/wishlist_contribucion_detalle.html', {
        'wishlist': wishlist,
        'contribuciones': contribuciones,
        'total_contribuido': total_contribuido,
        'num_contribuidores': num_contribuidores,
        'progreso': progreso,
        'faltante': max(0, wishlist.contribucion_objetivo - total_contribuido),
        'meta': wishlist.contribucion_objetivo,
        'contribucion_usuario': contribucion_usuario,
        'meta_alcanzada': meta_alcanzada,
        'es_propietario': wishlist.usuario == request.user,
    })

@login_required
def contribuir_wishlist(request, wishlist_id):
    """Vista para hacer una contribución a una wishlist"""
    try:
        wishlist = Wishlist.objects.select_related('usuario', 'producto').get(id=wishlist_id)
    except Wishlist.DoesNotExist:
        messages.error(request, 'Lista de deseos no encontrada.')
        return redirect('wishlists_con_contribuciones')

    # Verificar que tenga contribuciones activas
    if not wishlist.permitir_contribuciones:
        messages.error(request, 'Esta lista de deseos no acepta contribuciones actualmente.')
        return redirect('wishlist_detalle_contribucion', wishlist_id=wishlist_id)

    # No permitir que el propietario contribuya a su propia wishlist
    if wishlist.usuario == request.user:
        messages.error(request, 'No puedes contribuir a tu propia lista de deseos.')
        return redirect('wishlist_detalle_contribucion', wishlist_id=wishlist_id)

    # Calcular cuánto falta para completar la meta
    total_contribuido = ContribucionWishlist.objects.filter(
        wishlist_item=wishlist,
        estado='completado'
    ).aggregate(total=Sum('monto'))['total'] or 0

    faltante = max(0, wishlist.contribucion_objetivo - total_contribuido)

    if request.method == 'POST':
        monto = request.POST.get('monto')
        metodo_pago = request.POST.get('metodo_pago')

        try:
            monto = float(monto)
            if monto <= 0:
                raise ValueError("El monto debe ser positivo")

            if monto > faltante and faltante > 0:
                messages.warning(request, f'El monto máximo que puedes contribuir es ${faltante:.2f} para completar la meta.')
                monto = faltante

            # Crear contribución pendiente
            contribucion = ContribucionWishlist.objects.create(
                wishlist_item=wishlist,
                usuario_contribuyente=request.user,
                monto=monto,
                metodo_pago=metodo_pago,
                estado='pendiente'
            )

            # Redirigir a la página de pago
            messages.info(request, f'Contribución creada. Procede al pago para completarla.')
            return redirect('pago_contribucion', contribucion_id=contribucion.id)

        except ValueError as e:
            messages.error(request, f'Error en el monto: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al procesar la contribución: {str(e)}')

    return render(request, 'tienda/contribuir_wishlist.html', {
        'wishlist': wishlist,
        'faltante': faltante,
        'meta': wishlist.contribucion_objetivo,
        'contribucion_existente': False,
    })

@login_required
def historial_contribuciones(request):
    """Vista para mostrar el historial de contribuciones del usuario"""
    from django.core.paginator import Paginator
    from django.db.models import Q

    # Obtener parámetros de filtrado
    estado_filtro = request.GET.get('estado', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')

    # Contribuciones realizadas
    contribuciones_realizadas = ContribucionWishlist.objects.filter(
        usuario_contribuyente=request.user
    ).select_related('wishlist_item__usuario', 'wishlist_item__producto').order_by('-fecha_contribucion')

    # Contribuciones recibidas (en wishlists propias)
    contribuciones_recibidas = ContribucionWishlist.objects.filter(
        wishlist_item__usuario=request.user
    ).select_related('usuario_contribuyente', 'wishlist_item__producto').order_by('-fecha_contribucion')

    # Aplicar filtros si existen
    filtros = Q()

    # Filtro por estado
    if estado_filtro:
        filtros &= Q(estado=estado_filtro)

    # Filtro por fecha desde
    if fecha_desde:
        filtros &= Q(fecha_contribucion__date__gte=fecha_desde)

    # Filtro por fecha hasta
    if fecha_hasta:
        filtros &= Q(fecha_contribucion__date__lte=fecha_hasta)

    # Aplicar filtros a ambas querysets
    if filtros:
        contribuciones_realizadas = contribuciones_realizadas.filter(filtros)
        contribuciones_recibidas = contribuciones_recibidas.filter(filtros)

    # Combinar todas las contribuciones para mostrar en la tabla
    contribuciones_ids = set()
    contribuciones = []

    # Agregar contribuciones realizadas
    for contrib in contribuciones_realizadas:
        if contrib.id not in contribuciones_ids:
            contribuciones.append(contrib)
            contribuciones_ids.add(contrib.id)

    # Agregar contribuciones recibidas
    for contrib in contribuciones_recibidas:
        if contrib.id not in contribuciones_ids:
            contribuciones.append(contrib)
            contribuciones_ids.add(contrib.id)

    # Ordenar por fecha descendente
    contribuciones.sort(key=lambda x: x.fecha_contribucion, reverse=True)

    # Implementar paginación
    paginator = Paginator(contribuciones, 20)  # 20 contribuciones por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Estadísticas TOTALES (sin filtros)
    stats_totales = {
        'total_contribuido': contribuciones_realizadas.filter(estado='completado').aggregate(
            total=Sum('monto')
        )['total'] or 0,
        'num_contribuciones_realizadas': contribuciones_realizadas.filter(estado='completado').count(),
        'total_recibido': contribuciones_recibidas.filter(estado='completado').aggregate(
            total=Sum('monto')
        )['total'] or 0,
        'num_contribuciones_recibidas': contribuciones_recibidas.filter(estado='completado').count(),
    }

    # Estadísticas FILTRADAS (con filtros aplicados)
    stats_filtradas = {
        'total_contribuido': contribuciones_realizadas.filter(estado='completado').aggregate(
            total=Sum('monto')
        )['total'] or 0,
        'num_contribuciones_realizadas': contribuciones_realizadas.filter(estado='completado').count(),
        'total_recibido': contribuciones_recibidas.filter(estado='completado').aggregate(
            total=Sum('monto')
        )['total'] or 0,
        'num_contribuciones_recibidas': contribuciones_recibidas.filter(estado='completado').count(),
    }

    # Estadísticas para la plantilla (usar totales para mostrar siempre las estadísticas generales)
    total_contribuciones = len(contribuciones)  # Cantidad de contribuciones FILTRADAS
    total_contribuciones_totales = stats_totales['num_contribuciones_realizadas'] + stats_totales['num_contribuciones_recibidas']  # Cantidad TOTAL
    total_monto = stats_totales['total_contribuido']  # Total contribuido (siempre total)
    wishlists_unicas = contribuciones_realizadas.values('wishlist_item').distinct().count()  # Wishlists únicas TOTALES
    contribuciones_exitosas = stats_totales['num_contribuciones_realizadas']  # Contribuciones exitosas TOTALES

    return render(request, 'tienda/historial_contribuciones.html', {
        'contribuciones': page_obj.object_list,  # Lista de contribuciones de la página actual
        'contribuciones_realizadas': contribuciones_realizadas,
        'contribuciones_recibidas': contribuciones_recibidas,
        'stats': stats_totales,  # Estadísticas totales para mostrar siempre
        'total_contribuciones': total_contribuciones,
        'total_contribuciones_totales': total_contribuciones_totales,
        'total_monto': total_monto,
        'wishlists_unicas': wishlists_unicas,
        'contribuciones_exitosas': contribuciones_exitosas,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
    })

@login_required
def gestionar_contribuciones_wishlist(request, wishlist_id):
    """Vista para que el propietario gestione las contribuciones de su wishlist"""
    try:
        wishlist = Wishlist.objects.select_related('usuario', 'producto').get(
            id=wishlist_id,
            usuario=request.user
        )
    except Wishlist.DoesNotExist:
        messages.error(request, 'Lista de deseos no encontrada o no tienes permisos para acceder.')
        return redirect('wishlist')

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'activar_contribuciones':
            meta_contribucion = request.POST.get('meta_contribucion')
            descripcion_contribucion = request.POST.get('descripcion_contribucion', '')

            try:
                meta_contribucion = float(meta_contribucion)
                if meta_contribucion <= 0:
                    raise ValueError("La meta debe ser un valor positivo")

                wishlist.permitir_contribuciones = True
                wishlist.contribucion_objetivo = meta_contribucion
                wishlist.descripcion_contribucion = descripcion_contribucion
                wishlist.fecha_modificacion = timezone.now()
                wishlist.save()

                messages.success(request, f'Contribuciones activadas para "{wishlist.producto.nombre}". Meta: ${meta_contribucion}')

            except ValueError as e:
                messages.error(request, f'Error en la meta: {str(e)}')

        elif accion == 'desactivar_contribuciones':
            wishlist.permitir_contribuciones = False
            wishlist.save()
            messages.success(request, f'Contribuciones desactivadas para "{wishlist.producto.nombre}"')

        elif accion == 'actualizar_meta':
            nueva_meta = request.POST.get('meta_contribucion')

            try:
                nueva_meta = float(nueva_meta)
                if nueva_meta <= 0:
                    raise ValueError("La meta debe ser un valor positivo")

                wishlist.contribucion_objetivo = nueva_meta
                wishlist.fecha_modificacion = timezone.now()
                wishlist.save()

                messages.success(request, 'Meta de contribución actualizada exitosamente.')

            except ValueError as e:
                messages.error(request, f'Error en la meta: {str(e)}')

        return redirect('gestionar_contribuciones_wishlist', wishlist_id=wishlist_id)

    # Obtener estadísticas de contribuciones
    contribuciones = ContribucionWishlist.objects.filter(
        wishlist_item=wishlist
    ).select_related('usuario_contribuyente').order_by('-fecha_contribucion')

    total_contribuido = contribuciones.filter(estado='completado').aggregate(
        total=Sum('monto')
    )['total'] or 0

    num_contribuidores = contribuciones.filter(estado='completado').values('usuario_contribuyente').distinct().count()

    progreso = (total_contribuido / wishlist.contribucion_objetivo) * 100 if wishlist.contribucion_objetivo > 0 else 0

    return render(request, 'tienda/gestionar_contribuciones.html', {
        'wishlist': wishlist,
        'contribuciones': contribuciones,
        'total_contribuido': total_contribuido,
        'num_contribuidores': num_contribuidores,
        'progreso': progreso,
        'faltante': max(0, wishlist.contribucion_objetivo - total_contribuido),
        'meta_alcanzada': total_contribuido >= wishlist.contribucion_objetivo,
    })

@login_required
def pago_contribucion(request, contribucion_id):
    """Vista para procesar el pago de una contribución pendiente"""
    try:
        contribucion = ContribucionWishlist.objects.select_related('wishlist_item__usuario', 'wishlist_item__producto').get(
            id=contribucion_id,
            usuario_contribuyente=request.user,
            estado='pendiente'
        )
    except ContribucionWishlist.DoesNotExist:
        messages.error(request, 'Contribución no encontrada o no tienes permisos para acceder.')
        return redirect('historial_contribuciones')

    if request.method == 'POST':
        # Los datos de pago se procesan vía AJAX en procesar_pago_contribucion
        # Esta vista solo muestra el formulario
        pass

    return render(request, 'tienda/pago_contribucion.html', {
        'contribucion': contribucion,
    })

@login_required
def procesar_pago_contribucion(request, contribucion_id):
    """Vista AJAX para procesar el pago de una contribución"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        # Obtener la contribución
        contribucion = ContribucionWishlist.objects.select_related('wishlist_item', 'usuario_contribuyente').get(
            id=contribucion_id,
            usuario_contribuyente=request.user,
            estado='pendiente'
        )

        # Obtener datos de pago del formulario
        datos_pago = {
            'numero_tarjeta': request.POST.get('numero_tarjeta'),
            'fecha_expiracion': request.POST.get('fecha_expiracion'),
            'cvv': request.POST.get('cvv'),
            'nombre_titular': request.POST.get('nombre_titular'),
        }

        # Validar datos de pago
        from tienda.services.payment_service import PaymentService
        validacion = PaymentService.validar_datos_pago(datos_pago)

        if not validacion['valido']:
            return JsonResponse({
                'success': False,
                'error': 'Datos de pago inválidos',
                'detalles': validacion['errores']
            })

        # Procesar el pago
        resultado = PaymentService.procesar_contribucion(contribucion, datos_pago)

        if resultado['success']:
            # Verificar si se completó la meta
            wishlist = contribucion.wishlist_item
            meta_completada = wishlist.objetivo_alcanzado and not hasattr(wishlist, '_pedido_generado')

            return JsonResponse({
                'success': True,
                'mensaje': resultado['mensaje'],
                'referencia': resultado.get('referencia'),
                'meta_completada': meta_completada
            })
        else:
            return JsonResponse({
                'success': False,
                'error': resultado.get('error', 'Error al procesar el pago')
            })

    except ContribucionWishlist.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Contribución no encontrada'})
    except Exception as e:
        logger.error(f"Error procesando contribución {contribucion_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Error interno del servidor'})


# ===== SISTEMA DE COMPARACIÓN DE PRODUCTOS =====

@login_required
def comparacion_productos(request):
    """Vista para mostrar la comparación de productos"""
    try:
        comparacion = request.user.comparacion
        productos = comparacion.productos_ordenados
    except ComparacionProductos.DoesNotExist:
        comparacion = None
        productos = []

    # Si no hay productos suficientes para comparar, mostrar mensaje
    if len(productos) < 2:
        return render(request, 'tienda/comparacion.html', {
            'productos': productos,
            'mensaje': 'Agrega al menos 2 productos para comparar.',
            'puede_agregar_mas': True,
        })

    # Preparar datos para comparación
    productos_comparacion = []
    for producto in productos:
        productos_comparacion.append({
            'producto': producto,
            'caracteristicas': {
                'Precio': f"${producto.precio}",
                'Categoría': producto.categoria,
                'Stock': producto.stock,
                'Estado': producto.get_estado_display(),
                'Peso': f"{producto.peso} kg" if producto.peso else "N/A",
                'Dimensiones': producto.dimensiones or "N/A",
                'SKU': producto.sku or "N/A",
                'Calificación': f"{producto.promedio_calificacion}★ ({producto.total_resenas} reseñas)" if producto.total_resenas > 0 else "Sin reseñas",
            }
        })

    return render(request, 'tienda/comparacion.html', {
        'productos_comparacion': productos_comparacion,
        'productos': productos,
        'puede_agregar_mas': comparacion.puede_agregar_mas if comparacion else True,
    })

@login_required
def agregar_a_comparacion(request, producto_id):
    """Vista para agregar un producto a la comparación"""
    if request.method == 'POST':
        try:
            producto = Producto.objects.get(id=producto_id)

            # Obtener o crear comparación para el usuario
            comparacion, created = ComparacionProductos.objects.get_or_create(
                usuario=request.user,
                defaults={}
            )

            try:
                comparacion.agregar_producto(producto)
                messages.success(request, f'"{producto.nombre}" agregado a comparación.')
            except ValueError as e:
                messages.warning(request, str(e))

        except Producto.DoesNotExist:
            messages.error(request, 'Producto no encontrado.')

    return redirect(request.META.get('HTTP_REFERER', 'productos'))

@login_required
def quitar_de_comparacion(request, producto_id):
    """Vista para quitar un producto de la comparación"""
    if request.method == 'POST':
        try:
            comparacion = request.user.comparacion
            producto = Producto.objects.get(id=producto_id)
            comparacion.quitar_producto(producto)
            messages.success(request, f'"{producto.nombre}" removido de comparación.')

        except (ComparacionProductos.DoesNotExist, Producto.DoesNotExist):
            messages.error(request, 'Error al remover producto de comparación.')

    return redirect('comparacion_productos')

@login_required
def limpiar_comparacion(request):
    """Vista para limpiar todos los productos de la comparación"""
    if request.method == 'POST':
        try:
            comparacion = request.user.comparacion
            comparacion.limpiar()
            messages.success(request, 'Comparación limpiada exitosamente.')
        except ComparacionProductos.DoesNotExist:
            messages.warning(request, 'No hay productos para limpiar.')

    return redirect('comparacion_productos')

@login_required
def toggle_comparacion(request, producto_id):
    """Vista AJAX para agregar/quitar productos de comparación"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        producto = Producto.objects.get(id=producto_id)

        # Obtener o crear comparación para el usuario
        comparacion, created = ComparacionProductos.objects.get_or_create(usuario=request.user)

        if comparacion.productos.filter(id=producto_id).exists():
            # Quitar de comparación
            comparacion.quitar_producto(producto)
            action = 'removed'
            message = f'{producto.nombre} eliminado de comparación'
        else:
            # Verificar límite de 4 productos
            if comparacion.productos.count() >= 4:
                return JsonResponse({
                    'success': False,
                    'error': 'No puedes comparar más de 4 productos'
                })

            # Agregar a comparación
            comparacion.agregar_producto(producto)
            action = 'added'
            message = f'{producto.nombre} agregado a comparación'

        # Obtener nuevo conteo
        count = comparacion.productos.count()

        return JsonResponse({
            'success': True,
            'action': action,
            'message': message,
            'count': count
        })

    except Producto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def comparacion_count(request):
    """Vista AJAX para obtener el número de productos en comparación del usuario"""
    try:
        comparacion = ComparacionProductos.objects.get(usuario=request.user)
        count = comparacion.productos.count()
    except ComparacionProductos.DoesNotExist:
        count = 0
    return JsonResponse({'count': count})
    
@login_required
def puntos_fidelidad(request):
    """Vista para mostrar los puntos de fidelidad del usuario"""
    try:
        perfil = request.user.profile
        puntos_actuales = perfil.puntos_disponibles
        historial = HistorialPuntos.objects.filter(usuario=request.user).order_by('-fecha')[:10]
    except Profile.DoesNotExist:
        puntos_actuales = 0
        historial = []

    context = {
        'puntos_actuales': puntos_actuales,
        'historial': historial,
    }
    return render(request, 'tienda/puntos_fidelidad.html', context)

@login_required
def historial_puntos(request):
    """Vista para mostrar el historial completo de puntos"""
    historial = HistorialPuntos.objects.filter(usuario=request.user).order_by('-fecha')
    context = {
        'historial': historial,
    }
    return render(request, 'tienda/historial_puntos.html', context)

@login_required
def canjear_puntos(request):
    """Vista para canjear puntos por descuentos"""
    try:
        perfil = request.user.profile
        puntos_disponibles = perfil.puntos_disponibles
    except Profile.DoesNotExist:
        puntos_disponibles = 0

    if request.method == 'POST':
        tipo_canje = request.POST.get('tipo_canje')
        puntos = int(request.POST.get('puntos', 0))

        try:
            perfil = request.user.profile
            if perfil.puntos_disponibles >= puntos:
                if tipo_canje == 'descuento':
                    # Canjear por descuento: 10 puntos = $1
                    descuento = puntos // 10
                    if descuento > 0:
                        cupon = Cupon.objects.create(
                            codigo=f"DESCUENTO_{request.user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}",
                            descripcion=f"Descuento de ${descuento} por canje de {puntos} puntos",
                            tipo_descuento='monto_fijo',
                            valor_descuento=descuento,
                            fecha_expiracion=timezone.now() + timedelta(days=30),
                            usos_maximos=1,
                            activo=True
                        )

                        # Restar puntos del usuario
                        perfil.puntos_disponibles -= puntos
                        perfil.save()

                        # Registrar en historial
                        HistorialPuntos.objects.create(
                            usuario=request.user,
                            puntos=-puntos,
                            descripcion=f"Canje por descuento ${descuento} (cupón {cupon.codigo})",
                            tipo='canjeados'
                        )

                        messages.success(request, f'¡Canje exitoso! Se creó el cupón {cupon.codigo} con ${descuento} de descuento.')
                        return redirect('cupones_disponibles')
                    else:
                        messages.error(request, 'Los puntos mínimos para descuento son 10.')

                elif tipo_canje == 'envio_gratis':
                    # Canjear por envío gratis: 200 puntos
                    if puntos >= 200:
                        cupon = Cupon.objects.create(
                            codigo=f"ENVIO_{request.user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}",
                            descripcion=f"Envío gratis por canje de {puntos} puntos",
                            tipo_descuento='monto_fijo',
                            valor_descuento=0,
                            fecha_expiracion=timezone.now() + timedelta(days=30),
                            usos_maximos=1,
                            activo=True
                        )

                        # Restar puntos del usuario
                        perfil.puntos_disponibles -= puntos
                        perfil.save()

                        # Registrar en historial
                        HistorialPuntos.objects.create(
                            usuario=request.user,
                            puntos=-puntos,
                            descripcion=f"Canje por envío gratis (cupón {cupon.codigo})",
                            tipo='canjeados'
                        )

                        messages.success(request, f'¡Canje exitoso! Se creó el cupón {cupon.codigo} para envío gratis.')
                        return redirect('cupones_disponibles')
                    else:
                        messages.error(request, 'Necesitas al menos 200 puntos para envío gratis.')

                elif tipo_canje == 'producto_gratis':
                    # Canjear por producto gratis: 500 puntos
                    if puntos >= 500:
                        cupon = Cupon.objects.create(
                            codigo=f"PRODUCTO_{request.user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}",
                            descripcion=f"Producto gratis por canje de {puntos} puntos",
                            tipo_descuento='monto_fijo',
                            valor_descuento=0,
                            fecha_expiracion=timezone.now() + timedelta(days=30),
                            usos_maximos=1,
                            activo=True
                        )

                        # Restar puntos del usuario
                        perfil.puntos_disponibles -= puntos
                        perfil.save()

                        # Registrar en historial
                        HistorialPuntos.objects.create(
                            usuario=request.user,
                            puntos=-puntos,
                            descripcion=f"Canje por producto gratis (cupón {cupon.codigo})",
                            tipo='canjeados'
                        )

                        messages.success(request, f'¡Canje exitoso! Se creó el cupón {cupon.codigo} para producto gratis.')
                        return redirect('cupones_disponibles')
                    else:
                        messages.error(request, 'Necesitas al menos 500 puntos para producto gratis.')
                else:
                    messages.error(request, 'Tipo de canje no válido.')
            else:
                messages.error(request, 'No tienes suficientes puntos para este canje.')
        except Profile.DoesNotExist:
            messages.error(request, 'Error al acceder a tu perfil.')

    # Definir opciones de canje
    opciones_canje = [
        {
            'tipo': 'descuento',
            'titulo': 'Descuento en Compra',
            'descripcion': 'Canjea tus puntos por descuento en tu próxima compra. 10 puntos = $1 de descuento.',
            'puntos_minimos': 10,
            'valor_maximo': puntos_disponibles // 10 if puntos_disponibles >= 10 else 0,
        },
        {
            'tipo': 'envio_gratis',
            'titulo': 'Envío Gratis',
            'descripcion': 'Canjea 200 puntos por envío gratis en tu próxima compra.',
            'puntos_minimos': 200,
            'valor_maximo': 1 if puntos_disponibles >= 200 else 0,
        },
        {
            'tipo': 'producto_gratis',
            'titulo': 'Producto Gratis',
            'descripcion': 'Canjea 500 puntos por un producto gratis de tu elección.',
            'puntos_minimos': 500,
            'valor_maximo': 1 if puntos_disponibles >= 500 else 0,
        },
    ]

    context = {
        'profile': perfil if 'perfil' in locals() else None,
        'opciones_canje': opciones_canje,
    }
    return render(request, 'tienda/canjear_puntos.html', context)

def suscribir_newsletter(request):
    """Vista para suscribirse al newsletter"""
    if request.method == 'POST':
        form = NewsletterSubscriptionForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # Verificar si ya existe suscripción
            if NewsletterSubscription.objects.filter(email=email).exists():
                messages.warning(request, 'Este email ya está suscrito al newsletter.')
                return redirect('home')

                # Crear suscripción
            subscription = form.save()

            # Enviar email de confirmación
            try:
                email_service = EmailService()
                email_service.enviar_confirmacion_newsletter(subscription)
                messages.success(request, '¡Suscripción exitosa! Revisa tu email para confirmar.')
            except Exception as e:
                messages.error(request, 'Error al enviar email de confirmación.')

            return redirect('home')
    else:
        form = NewsletterSubscriptionForm()

    return render(request, 'tienda/suscribir_newsletter.html', {'form': form})

def confirmar_newsletter(request, token):
    """Vista para confirmar suscripción al newsletter"""
    try:
        subscription = NewsletterSubscription.objects.get(token_confirmacion=token)
        if not subscription.confirmado:
            subscription.confirmado = True
            subscription.fecha_confirmacion = timezone.now()
            subscription.save()
            messages.success(request, '¡Suscripción confirmada exitosamente!')
        else:
            messages.info(request, 'Esta suscripción ya estaba confirmada.')
    except NewsletterSubscription.DoesNotExist:
        messages.error(request, 'Token de confirmación inválido.')

    return redirect('home')

def cancelar_newsletter(request):
    """Vista para cancelar suscripción al newsletter"""
    if request.method == 'POST':
        form = NewsletterUnsubscribeForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                subscription = NewsletterSubscription.objects.get(email=email)
                subscription.activo = False
                subscription.save()
                messages.success(request, 'Suscripción cancelada exitosamente.')
            except NewsletterSubscription.DoesNotExist:
                messages.warning(request, 'No se encontró una suscripción con ese email.')
        return redirect('home')
    else:
        form = NewsletterUnsubscribeForm()

    return render(request, 'tienda/cancelar_newsletter.html', {'form': form})

def newsletter_unsubscribe_direct(request, email_b64):
    """Vista para cancelar suscripción directamente desde email"""
    import base64
    try:
        email = base64.b64decode(email_b64).decode('utf-8')
        subscription = NewsletterSubscription.objects.get(email=email)
        subscription.activo = False
        subscription.save()
        messages.success(request, 'Suscripción cancelada exitosamente.')
    except Exception as e:
        messages.error(request, 'Error al cancelar la suscripción.')

    return redirect('home')

@login_required
def admin_newsletter(request):
    """Vista administrativa del newsletter"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    campanas = NewsletterCampaign.objects.all().order_by('-fecha_creacion')[:10]
    suscriptores = NewsletterSubscription.objects.filter(activo=True).count()
    context = {
        'campanas': campanas,
        'total_suscriptores': suscriptores,
    }
    return render(request, 'tienda/admin_newsletter.html', context)

@login_required
def admin_newsletter_suscriptores(request):
    """Vista para administrar suscriptores del newsletter"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    suscriptores = NewsletterSubscription.objects.all().order_by('-fecha_suscripcion')
    context = {
        'suscriptores': suscriptores,
    }
    return render(request, 'tienda/admin_newsletter_suscriptores.html', context)

@login_required
def admin_newsletter_campanas(request):
    """Vista para administrar campañas del newsletter"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    campanas = NewsletterCampaign.objects.all().order_by('-fecha_creacion')
    context = {
        'campanas': campanas,
    }
    return render(request, 'tienda/admin_newsletter_campanas.html', context)

@login_required
def admin_crear_campana(request):
    """Vista para crear nueva campaña de newsletter"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    if request.method == 'POST':
        form = NewsletterCampaignForm(request.POST)
        if form.is_valid():
            campana = form.save(commit=False)
            campana.creado_por = request.user
            campana.save()
            messages.success(request, 'Campaña creada exitosamente.')
            return redirect('admin_newsletter_campanas')
    else:
        form = NewsletterCampaignForm()

    return render(request, 'tienda/admin_crear_campana.html', {'form': form})

@login_required
def admin_editar_campana(request, campana_id):
    """Vista para editar campaña de newsletter"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    campana = get_object_or_404(NewsletterCampaign, id=campana_id)

    if request.method == 'POST':
        form = NewsletterCampaignForm(request.POST, instance=campana)
        if form.is_valid():
            form.save()
            messages.success(request, 'Campaña actualizada exitosamente.')
            return redirect('admin_newsletter_campanas')
    else:
        form = NewsletterCampaignForm(instance=campana)

    return render(request, 'tienda/admin_editar_campana.html', {'form': form, 'campana': campana})

@login_required
def admin_enviar_campana(request, campana_id):
    """Vista para enviar campaña de newsletter"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    campana = get_object_or_404(NewsletterCampaign, id=campana_id)

    if request.method == 'POST':
        try:
            email_service = EmailService()
            email_service.enviar_newsletter(campana)
            messages.success(request, 'Campaña enviada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al enviar campaña: {str(e)}')

    return redirect('admin_newsletter_campanas')

@login_required
def admin_enviar_campana_directo(request, campana_id):
    """Vista para enviar campaña inmediatamente"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    campana = get_object_or_404(NewsletterCampaign, id=campana_id)

    try:
        email_service = EmailService()
        email_service.enviar_newsletter_inmediato(campana)
        messages.success(request, 'Campaña enviada exitosamente.')
    except Exception as e:
        messages.error(request, f'Error al enviar campaña: {str(e)}')

    return redirect('admin_newsletter_campanas')

@login_required
def admin_test_campana(request, campana_id):
    """Vista para enviar campaña de prueba"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    campana = get_object_or_404(NewsletterCampaign, id=campana_id)

    if request.method == 'POST':
        form = NewsletterTestForm(request.POST)
        if form.is_valid():
            email_prueba = form.cleaned_data['email']
            try:
                email_service = EmailService()
                email_service.enviar_newsletter_prueba(campana, email_prueba)
                messages.success(request, f'Email de prueba enviado a {email_prueba}.')
            except Exception as e:
                messages.error(request, f'Error al enviar email de prueba: {str(e)}')
    else:
        form = NewsletterTestForm()

    return render(request, 'tienda/admin_test_campana.html', {'form': form, 'campana': campana})

@login_required
def admin_eliminar_campana(request, campana_id):
    """Vista para eliminar campaña de newsletter"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    campana = get_object_or_404(NewsletterCampaign, id=campana_id)

    if request.method == 'POST':
        campana.delete()
        messages.success(request, 'Campaña eliminada exitosamente.')
        return redirect('admin_newsletter_campanas')

    return render(request, 'tienda/admin_eliminar_campana.html', {'campana': campana})

@login_required
def admin_cancelar_campana(request, campana_id):
    """Vista para cancelar envío de campaña"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    campana = get_object_or_404(NewsletterCampaign, id=campana_id)
    campana.estado = 'cancelada'
    campana.save()
    messages.success(request, 'Envío de campaña cancelado.')
    return redirect('admin_newsletter_campanas')

@login_required
def admin_duplicar_campana(request, campana_id):
    """Vista para duplicar campaña de newsletter"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    campana_original = get_object_or_404(NewsletterCampaign, id=campana_id)

    # Crear copia
    campana = NewsletterCampaign.objects.create(
        titulo=f"Copia de {campana_original.titulo}",
        asunto=campana_original.asunto,
        contenido=campana_original.contenido,
        creado_por=request.user,
        estado='borrador'
    )

    messages.success(request, f'Campaña duplicada como "{campana.titulo}".')
    return redirect('admin_editar_campana', campana_id=campana.id)

@login_required
def admin_activar_suscriptor(request, suscriptor_id):
    """Vista para activar suscriptor"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    suscriptor = get_object_or_404(NewsletterSubscription, id=suscriptor_id)
    suscriptor.activo = True
    suscriptor.save()
    messages.success(request, 'Suscriptor activado exitosamente.')
    return redirect('admin_newsletter_suscriptores')

@login_required
def admin_desactivar_suscriptor(request, suscriptor_id):
    """Vista para desactivar suscriptor"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    suscriptor = get_object_or_404(NewsletterSubscription, id=suscriptor_id)
    suscriptor.activo = False
    suscriptor.save()
    messages.success(request, 'Suscriptor desactivado exitosamente.')
    return redirect('admin_newsletter_suscriptores')

@login_required
def admin_eliminar_suscriptor(request, suscriptor_id):
    """Vista para eliminar suscriptor"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    suscriptor = get_object_or_404(NewsletterSubscription, id=suscriptor_id)
    suscriptor.delete()
    messages.success(request, 'Suscriptor eliminado exitosamente.')
    return redirect('admin_newsletter_suscriptores')

@login_required
def admin_reenviar_confirmacion(request, suscriptor_id):
    """Vista para reenviar email de confirmación"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    suscriptor = get_object_or_404(NewsletterSubscription, id=suscriptor_id)

    try:
        email_service = EmailService()
        email_service.enviar_confirmacion_newsletter(suscriptor)
        messages.success(request, 'Email de confirmación reenviado.')
    except Exception as e:
        messages.error(request, f'Error al reenviar confirmación: {str(e)}')

    return redirect('admin_newsletter_suscriptores')

@login_required
def admin_exportar_suscriptores(request):
    """Vista para exportar lista de suscriptores"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    suscriptores = NewsletterSubscription.objects.filter(activo=True)

    # Crear respuesta CSV
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="suscriptores_newsletter.csv"'

    writer = csv.writer(response)
    writer.writerow(['Email', 'Fecha de Suscripción', 'Confirmado', 'Activo'])

    for suscriptor in suscriptores:
        writer.writerow([
            suscriptor.email,
            suscriptor.fecha_suscripcion.strftime('%Y-%m-%d %H:%M:%S'),
            'Sí' if suscriptor.confirmado else 'No',
            'Sí' if suscriptor.activo else 'No'
        ])

    return response

@login_required
def admin_enviar_test_newsletter(request):
    """Vista para enviar newsletter de prueba"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    if request.method == 'POST':
        form = NewsletterTestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                email_service = EmailService()
                email_service.enviar_test_newsletter(email)
                messages.success(request, f'Newsletter de prueba enviado a {email}.')
            except Exception as e:
                messages.error(request, f'Error al enviar newsletter de prueba: {str(e)}')
    else:
        form = NewsletterTestForm()

    return render(request, 'tienda/admin_enviar_test_newsletter.html', {'form': form})

def tracking_newsletter_open(request, log_id):
    """Vista para tracking de apertura de newsletter"""
    try:
        log = NewsletterLog.objects.get(id=log_id)
        if not log.abierto:
            log.abierto = True
            log.fecha_apertura = timezone.now()
            log.save()
    except NewsletterLog.DoesNotExist:
        pass

    # Devolver pixel transparente
    from django.http import HttpResponse
    response = HttpResponse(content_type='image/gif')
    response.write(b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
    return response

def tracking_newsletter_click(request, log_id, url):
    """Vista para tracking de clicks en newsletter"""
    try:
        log = NewsletterLog.objects.get(id=log_id)
        log.clicks += 1
        log.save()
    except NewsletterLog.DoesNotExist:
        pass

    # Redirigir a la URL original
    from django.http import HttpResponseRedirect
    return HttpResponseRedirect(url)

def password_reset_request(request):
    """Vista para solicitar recuperación de contraseña"""
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            users = User.objects.filter(email=email)
            if users.exists():
                for user in users:
                    # Generar token
                    token = default_token_generator.make_token(user)
                    uid = urlsafe_base64_encode(force_bytes(user.pk))

                    # Enviar email
                    try:
                        email_service = EmailService()
                        email_service.enviar_recuperacion_password(user, uid, token)
                    except Exception as e:
                        pass

            messages.success(request, 'Si existe una cuenta con ese email, recibirás instrucciones para recuperar tu contraseña.')
            return redirect('password_reset_done')
    else:
        form = PasswordResetForm()

    return render(request, 'tienda/password_reset_request.html', {'form': form})

def password_reset_done(request):
    """Vista después de solicitar recuperación de contraseña"""
    return render(request, 'tienda/password_reset_done.html')

def password_reset_confirm(request, uidb64, token):
    """Vista para confirmar recuperación de contraseña"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Tu contraseña ha sido cambiada exitosamente.')
                return redirect('password_reset_complete')
        else:
            form = SetPasswordForm(user)
    else:
        messages.error(request, 'El enlace de recuperación es inválido o ha expirado.')
        return redirect('password_reset_request')

    return render(request, 'tienda/password_reset_confirm.html', {'form': form})

def password_reset_complete(request):
    """Vista después de completar recuperación de contraseña"""
    return render(request, 'tienda/password_reset_complete.html')

@login_required
def admin_email_dashboard(request):
    """Dashboard administrativo de emails"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    # Estadísticas de emails
    total_emails = EmailNotification.objects.count()
    emails_enviados = EmailNotification.objects.filter(enviado=True).count()
    emails_pendientes = EmailNotification.objects.filter(enviado=False).count()

    context = {
        'total_emails': total_emails,
        'emails_enviados': emails_enviados,
        'emails_pendientes': emails_pendientes,
    }
    return render(request, 'tienda/admin_email_dashboard.html', context)

@login_required
def admin_email_detalle(request, email_id):
    """Vista detallada de un email"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    email = get_object_or_404(EmailNotification, id=email_id)
    context = {
        'email': email,
    }
    return render(request, 'tienda/admin_email_detalle.html', context)

@login_required
def admin_email_reenviar(request, email_id):
    """Vista para reenviar un email"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    email = get_object_or_404(EmailNotification, id=email_id)

    try:
        email_service = EmailService()
        email_service.reenviar_email(email)
        messages.success(request, 'Email reenviado exitosamente.')
    except Exception as e:
        messages.error(request, f'Error al reenviar email: {str(e)}')

    return redirect('admin_email_detalle', email_id=email.id)

@login_required
def admin_newsletter_dashboard(request):
    """Dashboard administrativo del newsletter"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    # Estadísticas del newsletter
    total_suscriptores = NewsletterSubscription.objects.filter(activo=True).count()
    suscriptores_confirmados = NewsletterSubscription.objects.filter(activo=True, confirmado=True).count()
    campanas_enviadas = NewsletterCampaign.objects.filter(estado='enviada').count()

    context = {
        'total_suscriptores': total_suscriptores,
        'suscriptores_confirmados': suscriptores_confirmados,
        'campanas_enviadas': campanas_enviadas,
    }
    return render(request, 'tienda/admin_newsletter_dashboard.html', context)

@login_required
def compartir_wishlist(request, wishlist_id):
    """Vista para compartir una wishlist en redes sociales"""
    try:
        wishlist = Wishlist.objects.select_related('usuario', 'producto').get(id=wishlist_id)
    except Wishlist.DoesNotExist:
        messages.error(request, 'Lista de deseos no encontrada.')
        return redirect('wishlists_con_contribuciones')

    # Verificar que el usuario tenga permisos para compartir esta wishlist
    if wishlist.usuario != request.user:
        messages.error(request, 'No tienes permisos para compartir esta lista de deseos.')
        return redirect('wishlist_detalle_contribucion', wishlist_id=wishlist_id)

    if request.method == 'POST':
        plataforma = request.POST.get('plataforma')

        if plataforma in ['whatsapp', 'telegram', 'twitter', 'facebook', 'instagram', 'tiktok', 'email']:
            # Registrar el compartir
            wishlist.registrar_compartir(plataforma)
            messages.success(request, f'¡Lista compartida en {plataforma.title()}!')

            # Devolver enlaces de compartir como JSON para AJAX
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                enlaces = wishlist.generar_enlaces_compartir()
                return JsonResponse({
                   
                    'success': True,
                    'enlaces': enlaces,
                    'mensaje': f'Lista compartida en {plataforma.title()}'
                })
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Plataforma no válida'})
            messages.error(request, 'Plataforma no válida.')

    # Generar enlaces de compartir
    enlaces_compartir = wishlist.generar_enlaces_compartir()

    return render(request, 'tienda/compartir_wishlist.html', {
        'wishlist': wishlist,
        'enlaces_compartir': enlaces_compartir,
    })

@login_required
def procesar_referido_wishlist(request, wishlist_id):
    """Vista para procesar cuando alguien llega por un enlace de referido"""
    try:
        wishlist = Wishlist.objects.select_related('usuario', 'producto').get(id=wishlist_id)
    except Wishlist.DoesNotExist:
        messages.error(request, 'Lista de deseos no encontrada.')
        return redirect('wishlists_con_contribuciones')

    # Procesar parámetro de referido
    codigo_ref = request.GET.get('ref')
    usuario_referidor = None

    if codigo_ref:
        try:
            # Buscar el usuario referidor por el código
            wishlist_referidor = Wishlist.objects.filter(codigo_referido=codigo_ref).first()
            if wishlist_referidor and wishlist_referidor.usuario != request.user:
                usuario_referidor = wishlist_referidor.usuario

                # Registrar la visita por referido
                wishlist.registrar_visita_referido(usuario_referidor)

                # Guardar en sesión para tracking de contribuciones futuras
                request.session['referido_por'] = usuario_referidor.id
                request.session['wishlist_referida'] = wishlist.id

        except Exception as e:
            # Si hay error, continuar sin registrar el referido
            pass

    # Redirigir a la vista normal de la wishlist
    return redirect('wishlist_detalle_contribucion', wishlist_id=wishlist_id)

@login_required
def obtener_enlaces_compartir(request, wishlist_id):
    """Vista AJAX para obtener enlaces de compartir de una wishlist"""
    try:
        wishlist = Wishlist.objects.get(id=wishlist_id, usuario=request.user)
        enlaces = wishlist.generar_enlaces_compartir()

        return JsonResponse({
            'success': True,
            'enlaces': enlaces
        })

    except Wishlist.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lista de deseos no encontrada'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def estadisticas_compartir_wishlist(request, wishlist_id):
    """Vista para mostrar estadísticas de compartidos de una wishlist"""
    try:
        wishlist = Wishlist.objects.select_related('usuario', 'producto').get(
            id=wishlist_id,
            usuario=request.user
        )
    except Wishlist.DoesNotExist:
        messages.error(request, 'Lista de deseos no encontrada o no tienes permisos.')
        return redirect('wishlist')

    # Obtener estadísticas de referidos
    referidos = ReferidoWishlist.objects.filter(wishlist=wishlist).select_related('usuario_referidor', 'usuario_referido')

    # Estadísticas por plataforma
    estadisticas_plataforma = HistorialCompartir.objects.filter(wishlist=wishlist).values('plataforma').annotate(
        total=Count('id')
    ).order_by('-total')

    # Estadísticas de contribuciones por referido
    contribuciones_referidas = ContribucionWishlist.objects.filter(
        wishlist_item=wishlist,
        estado='completado'
    ).exclude(referido_origen__isnull=True).select_related('usuario_contribuyente', 'referido_origen')

    return render(request, 'tienda/estadisticas_compartir.html', {
        'wishlist': wishlist,
        'referidos': referidos,
        'estadisticas_plataforma': estadisticas_plataforma,
        'contribuciones_referidas': contribuciones_referidas,
        'total_visitas_referidas': wishlist.veces_visitado_via_referido,
        'total_contribuciones_referidas': wishlist.veces_contribuido_via_referido,
    })

def servir_imagen_producto(request, producto_id, imagen_id):
    """Vista para servir imágenes de productos desde la base de datos"""
    try:
        # Buscar la imagen específica del producto
        imagen = ProductoImagen.objects.get(
            producto_id=producto_id,
            id=imagen_id
        )

        # Determinar el tipo MIME basado en el tipo almacenado o por defecto
        content_type = imagen.imagen_tipo_mime or 'image/jpeg'

        # Crear respuesta HTTP con el contenido binario
        response = HttpResponse(imagen.imagen_blob, content_type=content_type)

        # Agregar headers para cache
        response['Cache-Control'] = 'public, max-age=86400'  # Cache por 24 horas

        # Si hay nombre de archivo, agregarlo al header
        if imagen.imagen_nombre:
            response['Content-Disposition'] = f'inline; filename="{imagen.imagen_nombre}"'

        return response

    except ProductoImagen.DoesNotExist:
        from django.http import Http404
        raise Http404("Imagen no encontrada")


# ========================================
# VISTAS AJAX PARA GESTIÓN DE IMÁGENES
# ========================================

@login_required
def eliminar_imagen(request, imagen_id):
    """Vista AJAX para eliminar una imagen de producto"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        imagen = ProductoImagen.objects.get(id=imagen_id)
        producto_id = imagen.producto.id
        imagen.delete()

        return JsonResponse({
            'success': True,
            'message': 'Imagen eliminada exitosamente',
            'producto_id': producto_id
        })

    except ProductoImagen.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Imagen no encontrada'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def establecer_principal(request, imagen_id):
    """Vista AJAX para establecer una imagen como principal"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        imagen = ProductoImagen.objects.get(id=imagen_id)

        # Quitar el flag principal de otras imágenes del mismo producto
        ProductoImagen.objects.filter(
            producto=imagen.producto,
            es_principal=True
        ).exclude(pk=imagen.pk).update(es_principal=False)

        # Establecer esta imagen como principal
        imagen.es_principal = True
        imagen.save()

        return JsonResponse({
            'success': True,
            'message': 'Imagen establecida como principal',
            'producto_id': imagen.producto.id
        })

    except ProductoImagen.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Imagen no encontrada'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def reordenar_imagenes(request):
    """Vista AJAX para reordenar imágenes de un producto"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        data = json.loads(request.body)
        orden = data.get('orden', [])

        if not orden:
            return JsonResponse({'success': False, 'error': 'No se proporcionó orden'})

        # Actualizar el orden de las imágenes
        for index, imagen_id in enumerate(orden):
            try:
                imagen = ProductoImagen.objects.get(id=int(imagen_id))
                imagen.orden = index
                imagen.save()
            except (ProductoImagen.DoesNotExist, ValueError):
                continue

        return JsonResponse({
            'success': True,
            'message': 'Imágenes reordenadas exitosamente'
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
