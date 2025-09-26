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
from .models import Producto, Compra, CompraProducto, Carrito, CarritoProducto, DireccionEnvio, MetodoPago, Pedido, PedidoProducto, Resena, Cupon, MovimientoInventario, ConfiguracionSistema, Profile, Wishlist, HistorialPuntos, ComparacionProductos, NewsletterSubscription, NewsletterCampaign, NewsletterLog, EmailTemplate, EmailNotification, EmailQueue
from .forms import ProductoForm, CuponForm, ProfileForm, NewsletterSubscriptionForm, NewsletterUnsubscribeForm, NewsletterCampaignForm, NewsletterTestForm
from .recomendador import RecomendadorIA
from .services.email_service import EmailService
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import models, transaction
from django import forms
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth, TruncDay
import pandas as pd
from datetime import date, timedelta

recomendador = RecomendadorIA()

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

@login_required
def producto_detalle(request, producto_id):
    """Vista para mostrar el detalle completo de un producto"""
    producto = get_object_or_404(Producto, id=producto_id)

    # Obtener reseñas del producto
    resenas = Resena.objects.filter(producto=producto).select_related('usuario').order_by('-fecha_creacion')

    # Verificar si el usuario puede reseñar este producto
    puede_reseñar = producto.puede_reseñar(request.user)

    # Obtener productos relacionados (misma categoría)
    productos_relacionados = Producto.objects.filter(
        categoria=producto.categoria
    ).exclude(id=producto.id).filter(stock__gt=0)[:4]

    # Verificar si el producto está en la wishlist del usuario
    en_wishlist = Wishlist.objects.filter(usuario=request.user, producto=producto).exists()

    return render(request, 'tienda/producto_detalle.html', {
        'producto': producto,
        'resenas': resenas,
        'puede_reseñar': puede_reseñar,
        'productos_relacionados': productos_relacionados,
        'en_wishlist': en_wishlist,
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
                messages.success(request, _('Producto eliminado del carrito.'))
            elif nueva_cantidad <= item.producto.stock:
                item.cantidad = nueva_cantidad
                item.save()
                messages.success(request, _('Cantidad actualizada.'))
            else:
                messages.warning(request, _('Cantidad solicitada excede el stock disponible.'))

        except (CarritoProducto.DoesNotExist, ValueError):
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
                if cupon.es_valido() and subtotal >= cupon.minimo_compra:
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
            puntos_ganados = profile.otorgar_puntos_por_compra(subtotal, f"Compra #{pedido.id}")
            if puntos_ganados > 0:
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
def pedido_detalle(request, pedido_id):
    """Mostrar detalles de un pedido"""
    try:
        pedido = Pedido.objects.get(id=pedido_id, usuario=request.user)
        productos = PedidoProducto.objects.filter(pedido=pedido).select_related('producto')

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

                if not cupon.es_valido():
                    return JsonResponse({
                        'success': False,
                        'error': 'Cupón expirado o no válido'
                    })

                if subtotal < cupon.minimo_compra:
                    return JsonResponse({
                        'success': False,
                        'error': f'Monto mínimo de compra: ${cupon.minimo_compra}'
                    })

                descuento = cupon.calcular_descuento(subtotal)
                total_con_descuento = subtotal - descuento

                # Guardar cupón en la sesión
                request.session['cupon_aplicado'] = {
                    'codigo': cupon.codigo,
                    'descuento': float(descuento),
                    'descripcion': cupon.descripcion
                }

                return JsonResponse({
                    'success': True,
                    'descuento': float(descuento),
                    'total_con_descuento': float(total_con_descuento),
                    'descripcion': cupon.descripcion
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
        'pedidos_completados': Pedido.objects.filter(estado='completado').count(),
        'total_ingresos': Pedido.objects.filter(estado='completado').aggregate(
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
        'completados': Pedido.objects.filter(estado='completado').count(),
        'cancelados': Pedido.objects.filter(estado='cancelado').count(),
        'total_ingresos': Pedido.objects.filter(estado='completado').aggregate(
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
        ventas = Pedido.objects.filter(estado='completado').annotate(
            periodo=TruncDay('fecha_creacion')
        ).values('periodo').annotate(
            total=Sum('total_pedido'),
            cantidad=Count('id')
        ).order_by('-periodo')[:30]
    else:
        ventas = Pedido.objects.filter(estado='completado').annotate(
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
        'pedidos_completados': Pedido.objects.filter(estado='completado').count(),
        'total_ingresos': Pedido.objects.filter(estado='completado').aggregate(
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
        descripcion = request.POST.get('descripcion', 'Ajuste manual desde admin')

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

        if nuevo_estado not in ['pendiente', 'procesando', 'completado', 'cancelado']:
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
            'estado_class': f'badge-{"success" if nuevo_estado == "completado" else "warning" if nuevo_estado == "pendiente" else "info" if nuevo_estado == "procesando" else "danger"}'
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
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            producto = form.save()
            messages.success(request, f'Producto "{producto.nombre}" actualizado exitosamente.')
            return redirect('admin_productos')
    else:
        form = ProductoForm(instance=producto)

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
        'pedidos_completados': pedidos_usuario.filter(estado='completado').count(),
        'total_gastado': pedidos_usuario.filter(estado='completado').aggregate(
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
    return render(request, 'tienda/wishlist.html', {
        'wishlist_items': wishlist_items,
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

            # Intentar obtener el item de wishlist
            wishlist_item = Wishlist.objects.filter(
                usuario=request.user,
                producto=producto
            ).first()

            if wishlist_item:
                # Si existe, lo eliminamos
                wishlist_item.delete()
                return JsonResponse({
                    'success': True,
                    'action': 'removed',
                    'message': f'"{producto.nombre}" removido de tu lista de deseos.'
                })
            else:
                # Si no existe, lo creamos

                Wishlist.objects.create(
                    usuario=request.user,
                    producto=producto
                )
                return JsonResponse({
                    'success': True,
                    'action': 'added',
                    'message': f'"{producto.nombre}" agregado a tu lista de deseos.'
                })

        except Producto.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Producto no encontrado.'
            })

    return JsonResponse({
        'success': False,
        'error': 'Método no permitido.'
    })

@login_required
def wishlist_count(request):
    """Vista AJAX para obtener el conteo de items en wishlist"""
    if request.method == 'GET':
        count = Wishlist.objects.filter(usuario=request.user).count()
        return JsonResponse({'count': count})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


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
    """Vista AJAX para agregar/quitar producto de comparación"""
    if request.method == 'POST':
        try:
            producto = Producto.objects.get(id=producto_id)

            # Obtener o crear comparación para el usuario
            comparacion, created = ComparacionProductos.objects.get_or_create(
                usuario=request.user,
                defaults={}
            )

            if comparacion.productos.filter(id=producto.id).exists():
                # Si existe, lo quitamos
                comparacion.quitar_producto(producto)
                return JsonResponse({
                    'success': True,
                    'action': 'removed',
                    'message': f'"{producto.nombre}" removido de comparación.',
                    'count': comparacion.productos.count()
                })
            else:
                # Si no existe, lo agregamos (si hay espacio)
                try:
                    comparacion.agregar_producto(producto)
                    return JsonResponse({
                        'success': True,
                        'action': 'added',
                        'message': f'"{producto.nombre}" agregado a comparación.',
                        'count': comparacion.productos.count(),
                        'can_add_more': comparacion.puede_agregar_mas
                    })
                except ValueError as e:
                    return JsonResponse({
                        'success': False,
                        'error': str(e)
                    })

        except Producto.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Producto no encontrado.'
            })

    return JsonResponse({
        'success': False,
        'error': 'Método no permitido.'
    })

@login_required
def comparacion_count(request):
    """Vista AJAX para obtener el conteo de productos en comparación"""
    if request.method == 'GET':
        try:
            count = request.user.comparacion.productos.count()
        except ComparacionProductos.DoesNotExist:
            count = 0
        return JsonResponse({'count': count})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ===== SISTEMA DE PUNTOS DE FIDELIDAD =====

@login_required
def puntos_fidelidad(request):
    """Vista para mostrar los puntos de fidelidad del usuario"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(usuario=request.user)

    # Historial reciente de puntos
    historial_reciente = HistorialPuntos.objects.filter(usuario=request.user)[:10]

    # Estadísticas
    puntos_ganados = HistorialPuntos.objects.filter(
        usuario=request.user, tipo='ganados'
    ).aggregate(total=Sum('puntos'))['total'] or 0

    puntos_canjeados = abs(HistorialPuntos.objects.filter(
        usuario=request.user, tipo='canjeados'
    ).aggregate(total=Sum('puntos'))['total'] or 0)

    context = {
        'profile': profile,
        'historial_reciente': historial_reciente,
        'puntos_ganados': puntos_ganados,
        'puntos_canjeados': puntos_canjeados,
        'nivel_actual': profile.get_nivel_membresia_display(),
        'puntos_para_siguiente': profile.puntos_para_siguiente_nivel,
        'siguiente_nivel': profile.get_siguiente_nivel(),
    }

    return render(request, 'tienda/puntos_fidelidad.html', context)

@login_required
def historial_puntos(request):
    """Vista para mostrar el historial completo de puntos"""
    historial = HistorialPuntos.objects.filter(usuario=request.user).order_by('-fecha')

    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(historial, 20)  # 20 items por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'tienda/historial_puntos.html', {
        'page_obj': page_obj,
    })

@login_required
def canjear_puntos(request):
    """Vista para canjear puntos por descuentos"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(usuario=request.user)

    if request.method == 'POST':
        puntos_a_canjear = int(request.POST.get('puntos', 0))
        tipo_canje = request.POST.get('tipo_canje')

        try:
            if tipo_canje == 'descuento':
                # Crear un cupón de descuento basado en puntos
                descuento = puntos_a_canjear // 10  # 10 puntos = $1 de descuento
                if descuento > 0:
                    cupon = Cupon.objects.create(
                        codigo=f"DESCUENTO_{request.user.username}_{timezone.now().strftime('%Y%m%d_%H%M%S')}",

                        descripcion=f"Descuento generado por canje de {puntos_a_canjear} puntos",
                        tipo_descuento='fijo',
                        valor_descuento=descuento,
                        fecha_expiracion=timezone.now() + timezone.timedelta(days=30),
                        usos_maximos=1,
                        activo=True
                    )

                    profile.canjear_puntos(puntos_a_canjear, f"Canje por descuento de ${descuento}")
                    messages.success(request, f'¡Has canjeado {puntos_a_canjear} puntos por un descuento de ${descuento}!')
                    messages.info(request, f'Usa el código: {cupon.codigo}')
                else:
                    messages.error(request, 'Los puntos mínimos para canjear son 10.')

            elif tipo_canje == 'envio_gratis':
                costo_envio_gratis = 200  # 200 puntos para envío gratis
                if puntos_a_canjear >= costo_envio_gratis:
                    cupon = Cupon.objects.create(
                        codigo=f"ENVIO_GRATIS_{request.user.username}_{timezone.now().strftime('%Y%m%d_%H%M%S')}",

                        descripcion=f"Envío gratis generado por canje de {puntos_a_canjear} puntos",
                        tipo_descuento='envio_gratis',
                        valor_descuento=0,
                        fecha_expiracion=timezone.now() + timezone.timedelta(days=30),
                        usos_maximos=1,
                        activo=True
                    )

                    profile.canjear_puntos(costo_envio_gratis, "Canje por envío gratis")
                    messages.success(request, f'¡Has canjeado {costo_envio_gratis} puntos por envío gratis!')
                    messages.info(request, f'Usa el código: {cupon.codigo}')
                else:
                    messages.error(request, f'Necesitas al menos {costo_envio_gratis} puntos para envío gratis.')

        except ValueError as e:
            messages.error(request, str(e))

        return redirect('canjear_puntos')

    # Opciones de canje disponibles
    opciones_canje = [
        {
            'tipo': 'descuento',
            'titulo': 'Descuento en Compra',
            'descripcion': '10 puntos = $1 de descuento',
            'puntos_minimos': 10,
            'valor_maximo': profile.puntos_disponibles // 10,
        },
        {
            'tipo': 'envio_gratis',
            'titulo': 'Envío Gratis',
            'descripcion': 'Envío gratis en tu próxima compra',
            'puntos_minimos': 200,
            'valor_maximo': 1 if profile.puntos_disponibles >= 200 else 0,
        },
    ]

    return render(request, 'tienda/canjear_puntos.html', {
        'profile': profile,
        'opciones_canje': opciones_canje,
    })


# ===== VISTAS DE NEWSLETTER =====

from .forms import NewsletterSubscriptionForm, NewsletterUnsubscribeForm, NewsletterCampaignForm, NewsletterTestForm
from .models import NewsletterSubscription, NewsletterCampaign, NewsletterLog
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
import threading


def suscribir_newsletter(request):
    """Vista para suscribirse al newsletter"""
    if request.method == 'POST':
        form = NewsletterSubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.generar_token_confirmacion()
            subscription.save()

            # Enviar email de confirmación
            enviar_email_confirmacion(subscription)

            messages.success(request, '¡Suscripción registrada! Revisa tu email para confirmar.')
            return redirect('home')
    else:
        form = NewsletterSubscriptionForm()

    return render(request, 'tienda/newsletter_suscribir.html', {
        'form': form,
    })


def confirmar_newsletter(request, token):
    """Vista para confirmar suscripción al newsletter"""
    try:
        subscription = NewsletterSubscription.objects.get(token_confirmacion=token, activo=True)
        subscription.confirmar_suscripcion()
        messages.success(request, '¡Suscripción confirmada! Ahora recibirás nuestros newsletters.')
    except NewsletterSubscription.DoesNotExist:
        messages.error(request, 'Enlace de confirmación inválido o expirado.')

    return redirect('home')


def cancelar_newsletter(request):
    """Vista para cancelar suscripción al newsletter"""
    if request.method == 'POST':
        form = NewsletterUnsubscribeForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            subscription = NewsletterSubscription.objects.get(email=email, activo=True)
            subscription.cancelar_suscripcion()
            messages.success(request, 'Suscripción cancelada exitosamente.')
            return redirect('home')
    else:
        form = NewsletterUnsubscribeForm()

    return render(request, 'tienda/newsletter_cancelar.html', {
        'form': form,
    })


def newsletter_unsubscribe_direct(request, email_b64):
    """Vista para cancelar suscripción directamente desde email (enlace único)"""
    import base64
    try:
        email = base64.b64decode(email_b64).decode('utf-8')
        subscription = NewsletterSubscription.objects.get(email=email, activo=True)
        subscription.cancelar_suscripcion()
        messages.success(request, 'Suscripción cancelada exitosamente.')
    except Exception:
        messages.error(request, 'Error al cancelar la suscripción.')

    return redirect('home')


@login_required
def admin_newsletter(request):
    """Vista administrativa para gestionar newsletter"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    # Estadísticas generales
    stats = {
        'total_suscriptores': NewsletterSubscription.objects.filter(activo=True).count(),
        'suscriptores_confirmados': NewsletterSubscription.objects.filter(activo=True, confirmado=True).count(),
        'campanas_totales': NewsletterCampaign.objects.count(),
        'campanas_enviadas': NewsletterCampaign.objects.filter(estado='enviado').count(),
    }

    # Campañas recientes
    campanas_recientes = NewsletterCampaign.objects.all()[:5]

    return render(request, 'tienda/admin_newsletter.html', {
        'stats': stats,
        'campanas_recientes': campanas_recientes,
    })


@login_required
def admin_newsletter_suscriptores(request):
    """Vista para gestionar suscriptores"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    # Filtros
    estado_filter = request.GET.get('estado', 'todos')
    frecuencia_filter = request.GET.get('frecuencia', 'todos')

    suscriptores = NewsletterSubscription.objects.all()

    if estado_filter == 'activos':
        suscriptores = suscriptores.filter(activo=True, confirmado=True)
    elif estado_filter == 'pendientes':
        suscriptores = suscriptores.filter(activo=True, confirmado=False)
    elif estado_filter == 'inactivos':
        suscriptores = suscriptores.filter(activo=False)

    if frecuencia_filter != 'todos':
        suscriptores = suscriptores.filter(frecuencia=frecuencia_filter)

    return render(request, 'tienda/admin_newsletter_suscriptores.html', {
        'suscriptores': suscriptores,
        'filtros': {
            'estado': estado_filter,
            'frecuencia': frecuencia_filter,
        }
    })


@login_required
def admin_newsletter_campanas(request):
    """Vista para gestionar campañas"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    campanas = NewsletterCampaign.objects.all().order_by('-fecha_creacion')

    return render(request, 'tienda/admin_newsletter_campanas.html', {
        'campanas': campanas,
    })


@login_required
def admin_crear_campana(request):
    """Vista para crear nueva campaña"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        asunto = request.POST.get('asunto')
        descripcion = request.POST.get('descripcion', '')
        contenido_html = request.POST.get('contenido_html')
        contenido_texto = request.POST.get('contenido_texto', '')
        fecha_envio = request.POST.get('fecha_envio')
        segmento = request.POST.get('segmento', 'todos')
        prioridad = request.POST.get('prioridad', 'normal')
        tracking_aperturas = request.POST.get('tracking_aperturas') == 'on'
        tracking_clics = request.POST.get('tracking_clics') == 'on'
        accion = request.POST.get('accion')

        # Validación básica
        if not titulo or not asunto or not contenido_html:
            messages.error(request, 'Los campos título, asunto y contenido HTML son obligatorios.')
            return redirect('admin_crear_campana')

        # Crear campaña
        campana = NewsletterCampaign.objects.create(
            titulo=titulo,
            asunto=asunto,
            descripcion=descripcion,
            contenido_html=contenido_html,
            contenido_texto=contenido_texto,
            segmento=segmento,
            prioridad=prioridad,
            tracking_aperturas=tracking_aperturas,
            tracking_clics=tracking_clics,
            creado_por=request.user
        )

        if fecha_envio:
            try:
                campana.fecha_envio = fecha_envio
                campana.estado = 'programado'
                campana.save()
                messages.success(request, f'Campaña "{campana.titulo}" programada para envío.')
            except ValueError:
                messages.error(request, 'Fecha de envío inválida.')
                return redirect('admin_crear_campana')
        elif accion == 'enviar_ahora':
            # Iniciar envío inmediato
            campana.iniciar_envio()
            campana.save()
            messages.success(request, f'Campaña "{campana.titulo}" creada y envío iniciado.')
            # Aquí se debería iniciar el envío en background
        else:
            messages.success(request, f'Campaña "{campana.titulo}" guardada como borrador.')

        return redirect('admin_newsletter_campanas')

    return render(request, 'tienda/admin_campana_form.html', {
        'campana': None
    })


@login_required
def admin_editar_campana(request, campana_id):
    """Vista para editar campaña existente"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    try:
        campana = NewsletterCampaign.objects.get(id=campana_id)
    except NewsletterCampaign.DoesNotExist:
        messages.error(request, 'Campaña no encontrada.')
        return redirect('admin_newsletter_campanas')

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        asunto = request.POST.get('asunto')
        descripcion = request.POST.get('descripcion', '')
        contenido_html = request.POST.get('contenido_html')
        contenido_texto = request.POST.get('contenido_texto', '')
        fecha_envio = request.POST.get('fecha_envio')
        segmento = request.POST.get('segmento', 'todos')
        prioridad = request.POST.get('prioridad', 'normal')
        tracking_aperturas = request.POST.get('tracking_aperturas') == 'on'
        tracking_clics = request.POST.get('tracking_clics') == 'on'
        accion = request.POST.get('accion')

        # Validación básica
        if not titulo or not asunto or not contenido_html:
            messages.error(request, 'Los campos título, asunto y contenido HTML son obligatorios.')
            return redirect('admin_editar_campana', campana_id=campana_id)

        # Solo permitir edición si está en borrador
        if campana.estado not in ['borrador', 'programado']:
            messages.error(request, 'No se puede editar una campaña que ya se está enviando o ha sido enviada.')
            return redirect('admin_newsletter_campanas')

        # Actualizar campaña
        campana.titulo = titulo
        campana.asunto = asunto
        campana.descripcion = descripcion
        campana.contenido_html = contenido_html
        campana.contenido_texto = contenido_texto
        campana.segmento = segmento
        campana.prioridad = prioridad
        campana.tracking_aperturas = tracking_aperturas
        campana.tracking_clics = tracking_clics

        if fecha_envio and accion == 'programar':
            try:
                campana.fecha_envio = fecha_envio
                campana.estado = 'programado'
                messages.success(request, f'Campaña "{campana.titulo}" programada para envío.')
            except ValueError:
                messages.error(request, 'Fecha de envío inválida.')
                return redirect('admin_editar_campana', campana_id=campana_id)
        elif accion == 'enviar_ahora' and campana.estado == 'borrador':
            campana.fecha_envio = None
            campana.estado = 'enviando'
            campana.fecha_envio = timezone.now()
            messages.success(request, f'Campaña "{campana.titulo}" enviada.')
            # Aquí se debería iniciar el envío en background
        else:
            messages.success(request, f'Campaña "{campana.titulo}" actualizada.')

        campana.save()
        return redirect('admin_newsletter_campanas')

    return render(request, 'tienda/admin_campana_form.html', {
        'campana': campana
    })


@login_required
def admin_enviar_campana(request, campana_id):
    """Vista para enviar campaña en background"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        campana = NewsletterCampaign.objects.get(id=campana_id)
        if campana.estado not in ['borrador', 'programado']:
            return JsonResponse({'success': False, 'error': 'La campaña no está en estado válido para envío'})

        # Iniciar envío en background
        campana.iniciar_envio()
        campana.save()

        thread = threading.Thread(target=enviar_campana_background, args=[campana.id])
        thread.daemon = True
        thread.start()

        return JsonResponse({'success': True, 'mensaje': 'Envío de campaña iniciado en background'})

    except NewsletterCampaign.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Campaña no encontrada'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def admin_enviar_campana_directo(request, campana_id):
    """Vista para enviar campaña de newsletter de forma directa (síncrona)"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        campana = NewsletterCampaign.objects.get(id=campana_id)

        if campana.estado not in ['borrador', 'programado']:
            return JsonResponse({'success': False, 'error': 'La campaña no está en estado válido para envío'})

        # Usar el método send_campaign del modelo
        resultado = campana.send_campaign()

        if resultado['success']:
            return JsonResponse({
                'success': True,
                'mensaje': f'Campaña enviada exitosamente. {resultado["emails_enviados"]} emails enviados.',
                'emails_enviados': resultado['emails_enviados'],
                'emails_fallidos': resultado['emails_fallidos'],
                'total_suscriptores': resultado['total_suscriptores']
            })
        else:
            # Marcar como fallida si hubo error
            campana.estado = 'fallido'
            campana.save()
            return JsonResponse({
                'success': False,
                'error': f'Error enviando campaña: {resultado.get("error", "Error desconocido")}'
            })

    except NewsletterCampaign.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Campaña no encontrada'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def admin_test_campana(request, campana_id):
    """Vista para enviar campaña de prueba"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    if request.method == 'POST':
        form = NewsletterTestForm(request.POST)
        if form.is_valid():
            try:
                campana = NewsletterCampaign.objects.get(id=campana_id)
                email_prueba = form.cleaned_data['email_prueba']

                # Enviar email de prueba
                enviar_newsletter_individual(campana, email_prueba, es_prueba=True)

                return JsonResponse({'success': True, 'mensaje': f'Email de prueba enviado a {email_prueba}'})

            except NewsletterCampaign.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Campaña no encontrada'})
        else:
            return JsonResponse({'success': False, 'error': 'Email inválido'})

    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required
def admin_eliminar_campana(request, campana_id):
    """Vista AJAX para eliminar campaña"""
    if not request.user.is_staff or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        campana = NewsletterCampaign.objects.get(id=campana_id)
        if campana.estado == 'enviando':
            return JsonResponse({'success': False, 'error': 'No se puede eliminar una campaña que se está enviando'})

        titulo = campana.titulo
        campana.delete()

        return JsonResponse({'success': True, 'mensaje': f'Campaña "{titulo}" eliminada'})

    except NewsletterCampaign.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Campaña no encontrada'})


# ===== FUNCIONES AUXILIARES PARA NEWSLETTER =====

def enviar_email_confirmacion(subscription):
    """Envía email de confirmación de suscripción"""
    subject = 'Confirma tu suscripción al newsletter'
    confirm_url = reverse('confirmar_newsletter', kwargs={'token': subscription.token_confirmacion})
    full_confirm_url = f"{settings.SITE_URL}{confirm_url}"

    context = {
        'subscription': subscription,
        'confirm_url': full_confirm_url,
    }

    html_message = render_to_string('tienda/emails/newsletter_confirmacion.html', context)
    plain_message = strip_tags(html_message)

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[subscription.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        # Log error but don't break the flow
        print(f"Error enviando email de confirmación: {e}")


def enviar_campana_background(campana_id):
    """Función para enviar campaña en background"""
    try:
        campana = NewsletterCampaign.objects.get(id=campana_id)

        # Usar el método send_campaign del modelo
        resultado = campana.send_campaign()

        if resultado['success']:
            print(f"Campaña '{campana.titulo}' enviada exitosamente. {resultado['emails_enviados']} emails enviados, {resultado['emails_fallidos']} fallidos.")
        else:
            print(f"Error enviando campaña '{campana.titulo}': {resultado.get('error', 'Error desconocido')}")

    except Exception as e:
        print(f"Error en envío de campaña: {e}")


def enviar_newsletter_individual(campana, email, es_prueba=False):
    """Envía newsletter individual"""
    try:
        # Obtener suscriptor si no es prueba
        suscriptor = None
        if not es_prueba:
            try:
                suscriptor = NewsletterSubscription.objects.get(email=email)
            except NewsletterSubscription.DoesNotExist:
                return

        # Generar URLs de tracking
        unsubscribe_url = generar_unsubscribe_url(email)

        context = {
            'campana': campana,
            'suscriptor': suscriptor,
            'unsubscribe_url': unsubscribe_url,
            'es_prueba': es_prueba,
        }

        html_content = render_to_string('tienda/emails/newsletter_template.html', context)
        text_content = strip_tags(html_content)

        # Crear email
        email_msg = EmailMultiAlternatives(
            subject=campana.asunto,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )
        email_msg.attach_alternative(html_content, "text/html")

        # Enviar
        email_msg.send()

    except Exception as e:
        print(f"Error enviando newsletter a {email}: {e}")


def enviar_newsletter_campana(campana):
    """Envía newsletter a todos los suscriptores de una campaña"""
    try:
        # Obtener suscriptores según el segmento de la campaña
        suscriptores = campana.obtener_suscriptores_target()

        emails_enviados = 0
        emails_fallidos = 0

        for suscriptor in suscriptores:
            try:
                # Generar URLs de tracking
                unsubscribe_url = generar_unsubscribe_url(suscriptor.email)

                context = {
                    'campana': campana,
                    'suscriptor': suscriptor,
                    'unsubscribe_url': unsubscribe_url,
                    'es_prueba': False,
                }

                # Renderizar contenido
                html_content = render_to_string('tienda/emails/newsletter_template.html', context)
                text_content = strip_tags(html_content)

                # Crear email con tracking si está habilitado
                subject = campana.asunto
                if campana.tracking_aperturas or campana.tracking_clics:
                    # Agregar tracking de apertura (pixel transparente)
                    if campana.tracking_aperturas:
                        # Crear log de envío para tracking
                        log_envio = NewsletterLog.objects.create(
                            campaign=campana,
                            suscriptor=suscriptor,
                            tipo='envio'
                        )
                        # Agregar pixel de tracking al HTML
                        tracking_pixel = f'<img src="{settings.SITE_URL}/newsletter/tracking/open/{log_envio.id}/" width="1" height="1" style="display:none;" alt="" />'
                        html_content = html_content.replace('</body>', f'{tracking_pixel}</body>')

                    # Agregar tracking de clics si está habilitado
                    if campana.tracking_clics:
                        # Aquí se podrían procesar los links para agregar tracking
                        # Por simplicidad, se omite en esta implementación básica
                        pass

                # Crear y enviar email
                email_msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[suscriptor.email]
                )
                email_msg.attach_alternative(html_content, "text/html")

                # Enviar email
                email_msg.send()

                # Registrar envío exitoso
                NewsletterLog.objects.create(
                    campaign=campana,
                    suscriptor=suscriptor,
                    tipo='envio'
                )

                emails_enviados += 1

                # Actualizar contador en campaña
                campana.enviados += 1
                campana.save()

            except Exception as e:
                print(f"Error enviando newsletter a {suscriptor.email}: {e}")
                emails_fallidos += 1
                continue

        # Completar campaña
        campana.completar_envio()

        return {
            'success': True,
            'emails_enviados': emails_enviados,
            'emails_fallidos': emails_fallidos,
            'total_suscriptores': len(suscriptores)
        }

    except Exception as e:
        print(f"Error enviando campaña de newsletter: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def generar_unsubscribe_url(email):
    """Genera URL de cancelación de suscripción"""
    import base64
    email_b64 = base64.b64encode(email.encode()).decode()
    return reverse('newsletter_unsubscribe_direct', kwargs={'email_b64': email_b64})


def tracking_newsletter_open(request, log_id):
    """Tracking de apertura de newsletter (pixel transparente)"""
    try:
        log = NewsletterLog.objects.get(id=log_id)
        if log.tipo == 'envio':
            # Registrar apertura
            NewsletterLog.objects.create(
                campaign=log.campaign,
                suscriptor=log.suscriptor,
                tipo='apertura',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            # Incrementar contador
            log.campaign.abiertos += 1
            log.campaign.save()
    except NewsletterLog.DoesNotExist:
        pass

    # Devolver pixel transparente
    from django.http import HttpResponse
    response = HttpResponse(content_type='image/gif')
    response.write(b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
    return response


def tracking_newsletter_click(request, log_id, url):
    """Tracking de clics en newsletter"""
    try:
        log = NewsletterLog.objects.get(id=log_id)
        if log.tipo == 'envio':
            # Registrar clic
            NewsletterLog.objects.create(
                campaign=log.campaign,
                suscriptor=log.suscriptor,
                tipo='clic',
                url_clic=url,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            # Incrementar contador
            log.campaign.clics += 1
            log.campaign.save()
    except NewsletterLog.DoesNotExist:
        pass

    # Redirigir a URL original
    from django.http import HttpResponseRedirect
    return HttpResponseRedirect(url)


def get_client_ip(request):
    """Obtiene la IP del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def admin_cancelar_campana(request, campana_id):
    """Vista AJAX para cancelar campaña programada"""
    if not request.user.is_staff or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        campana = NewsletterCampaign.objects.get(id=campana_id)
        if campana.estado != 'programado':
            return JsonResponse({'success': False, 'error': 'Solo se pueden cancelar campañas programadas'})

        campana.estado = 'cancelado'
        campana.save()

        return JsonResponse({'success': True, 'mensaje': f'Campaña "{campana.titulo}" cancelada'})

    except NewsletterCampaign.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Campaña no encontrada'})


@login_required
def admin_duplicar_campana(request, campana_id):
    """Vista AJAX para duplicar campaña"""
    if not request.user.is_staff or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        campana_original = NewsletterCampaign.objects.get(id=campana_id)

        # Crear copia
        campana = NewsletterCampaign.objects.create(
            titulo=f"{campana_original.titulo} (Copia)",
            asunto=campana_original.asunto,
            descripcion=campana_original.descripcion,
            contenido_html=campana_original.contenido_html,
            contenido_texto=campana_original.contenido_texto,
            segmento=campana_original.segmento,
            prioridad=campana_original.prioridad,
            tracking_aperturas=campana_original.tracking_aperturas,
            tracking_clics=campana_original.tracking_clics,
            creado_por=request.user,
            estado='borrador'
        )

        return JsonResponse({'success': True, 'mensaje': f'Campaña duplicada como "{campana.titulo}"'})

    except NewsletterCampaign.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Campaña no encontrada'})


@login_required
def admin_activar_suscriptor(request, suscriptor_id):
    """Vista AJAX para activar suscriptor"""
    if not request.user.is_staff or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        suscriptor = NewsletterSubscription.objects.get(id=suscriptor_id)
        suscriptor.activo = True
        suscriptor.save()

        return JsonResponse({'success': True, 'mensaje': f'Suscriptor {suscriptor.email} activado'})

    except NewsletterSubscription.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Suscriptor no encontrado'})


@login_required
def admin_desactivar_suscriptor(request, suscriptor_id):
    """Vista AJAX para desactivar suscriptor"""
    if not request.user.is_staff or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        suscriptor = NewsletterSubscription.objects.get(id=suscriptor_id)
        suscriptor.activo = False
        suscriptor.save()

        return JsonResponse({'success': True, 'mensaje': f'Suscriptor {suscriptor.email} desactivado'})

    except NewsletterSubscription.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Suscriptor no encontrado'})


@login_required
def admin_eliminar_suscriptor(request, suscriptor_id):
    """Vista AJAX para eliminar suscriptor"""
    if not request.user.is_staff or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        suscriptor = NewsletterSubscription.objects.get(id=suscriptor_id)
        email = suscriptor.email
        suscriptor.delete()

        return JsonResponse({'success': True, 'mensaje': f'Suscriptor {email} eliminado'})

    except NewsletterSubscription.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Suscriptor no encontrado'})


@login_required
def admin_reenviar_confirmacion(request, suscriptor_id):
    """Vista AJAX para reenviar confirmación"""
    if not request.user.is_staff or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        suscriptor = NewsletterSubscription.objects.get(id=suscriptor_id)
        if suscriptor.confirmado:
            return JsonResponse({'success': False, 'error': 'El suscriptor ya está confirmado'})

        # Reenviar email de confirmación
        enviar_email_confirmacion(suscriptor)

        return JsonResponse({'success': True, 'mensaje': f'Email de confirmación reenviado a {suscriptor.email}'})

    except NewsletterSubscription.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Suscriptor no encontrado'})


@login_required
def admin_exportar_suscriptores(request):
    """Vista para exportar suscriptores a CSV"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    # Aplicar filtros similares a la vista de suscriptores
    suscriptores = NewsletterSubscription.objects.all()

    busqueda = request.GET.get('busqueda')
    if busqueda:
        suscriptores = suscriptores.filter(
            models.Q(email__icontains=busqueda) | models.Q(nombre__icontains=busqueda)
        )

    estado = request.GET.get('estado')
    if estado == 'activo':
        suscriptores = suscriptores.filter(activo=True)
    elif estado == 'inactivo':
        suscriptores = suscriptores.filter(activo=False)

    confirmado = request.GET.get('confirmado')
    if confirmado == 'si':
        suscriptores = suscriptores.filter(confirmado=True)
    elif confirmado == 'no':
        suscriptores = suscriptores.filter(confirmado=False)

    frecuencia = request.GET.get('frecuencia')
    if frecuencia:
        suscriptores = suscriptores.filter(frecuencia=frecuencia)

    # Crear respuesta CSV
    from django.http import HttpResponse
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="suscriptores_newsletter.csv"'

    import csv
    writer = csv.writer(response)
    writer.writerow(['Email', 'Nombre', 'Activo', 'Confirmado', 'Frecuencia', 'Fecha Suscripción'])

    for suscriptor in suscriptores:
        writer.writerow([
            suscriptor.email,
            suscriptor.nombre or '',
            'Sí' if suscriptor.activo else 'No',
            'Sí' if suscriptor.confirmado else 'No',
            suscriptor.frecuencia,
            suscriptor.fecha_suscripcion.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response


@login_required
def admin_enviar_test_newsletter(request):
    """Vista AJAX para enviar email de prueba"""
    if not request.user.is_staff or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        email = request.POST.get('email')
        asunto = request.POST.get('asunto')
        contenido_html = request.POST.get('contenido_html')

        if not email or not asunto or not contenido_html:
            return JsonResponse({'success': False, 'error': 'Faltan datos requeridos'})

        # Enviar email de prueba
        email_msg = EmailMultiAlternatives(
            subject=f"[PRUEBA] {asunto}",
            body=strip_tags(contenido_html),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )
        email_msg.attach_alternative(contenido_html, "text/html")
        email_msg.send()

        return JsonResponse({'success': True, 'mensaje': f'Email de prueba enviado a {email}'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ========================================
# VISTAS DE RECUPERACIÓN DE CONTRASEÑA
# ========================================

def password_reset_request(request):
    """Vista para solicitar recuperación de contraseña"""
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                # Generar token y UID
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)

                # Construir URL de recuperación
                reset_url = request.build_absolute_uri(
                    reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
                )

                # Enviar email de recuperación
                try:
                    email_service = EmailService()
                    email_service.enviar_recuperacion_password(user, reset_url)
                    messages.success(request, _('Se ha enviado un email con instrucciones para recuperar tu contraseña.'))
                except Exception as e:
                    messages.error(request, _('Error al enviar el email. Por favor intenta nuevamente.'))

            except User.DoesNotExist:
                # No revelar si el email existe o no por seguridad
                messages.success(request, _('Si existe una cuenta con ese email, recibirás instrucciones para recuperar tu contraseña.'))

            return redirect('password_reset_done')
    else:
        form = PasswordResetForm()

    return render(request, 'tienda/password_reset.html', {'form': form})


def password_reset_done(request):
    """Vista mostrada después de solicitar recuperación de contraseña"""
    return render(request, 'tienda/password_reset_done.html')


def password_reset_confirm(request, uidb64=None, token=None):
    """Vista para confirmar recuperación de contraseña y establecer nueva contraseña"""
    try:
        # Decodificar UID
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Verificar token
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, _('Tu contraseña ha sido cambiada exitosamente.'))
                return redirect('password_reset_complete')
        else:
            form = SetPasswordForm(user)
    else:
        messages.error(request, _('El enlace de recuperación es inválido o ha expirado.'))
        return redirect('password_reset_request')

    return render(request, 'tienda/password_reset_confirm.html', {'form': form})


def password_reset_complete(request):
    """Vista mostrada después de completar recuperación de contraseña"""
    return render(request, 'tienda/password_reset_complete.html')


# ========================================
# DASHBOARD DE REPORTES DE EMAIL
# ========================================

@login_required
def admin_email_dashboard(request):
    """Dashboard principal de reportes de email"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    # Filtros de fecha
    periodo = request.GET.get('periodo', '7d')
    fecha_hasta = timezone.now()

    if periodo == '1d':
        fecha_desde = fecha_hasta - timedelta(days=1)
    elif periodo == '7d':
        fecha_desde = fecha_hasta - timedelta(days=7)
    elif periodo == '30d':
        fecha_desde = fecha_hasta - timedelta(days=30)
    else:
        fecha_desde = fecha_hasta - timedelta(days=7)

    # Estadísticas generales
    stats = {
        'total_emails': EmailNotification.objects.filter(fecha_creacion__gte=fecha_desde).count(),
        'emails_enviados': EmailNotification.objects.filter(
            fecha_creacion__gte=fecha_desde, estado='enviado'
        ).count(),
        'emails_pendientes': EmailNotification.objects.filter(
            fecha_creacion__gte=fecha_desde, estado='pendiente'
        ).count(),
        'emails_fallidos': EmailNotification.objects.filter(
            fecha_creacion__gte=fecha_desde, estado='fallido'
        ).count(),
        'tasa_exito': 0,
    }

    if stats['total_emails'] > 0:
        stats['tasa_exito'] = round((stats['emails_enviados'] / stats['total_emails']) * 100, 1)

    # Estadísticas por tipo de email
    tipos_email = EmailNotification.objects.filter(
        fecha_creacion__gte=fecha_desde
    ).values('tipo').annotate(
        total=Count('id'),
        enviados=Count('id', filter=models.Q(estado='enviado')),
        fallidos=Count('id', filter=models.Q(estado='fallido'))
    ).order_by('-total')

    # Emails por día (últimos 7 días)
    emails_por_dia = []
    for i in range(7):
        fecha = fecha_hasta - timedelta(days=i)
        fecha_inicio = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_fin = fecha.replace(hour=23, minute=59, second=59, microsecond=999999)

        emails_dia = EmailNotification.objects.filter(
            fecha_creacion__gte=fecha_inicio,
            fecha_creacion__lte=fecha_fin
        ).aggregate(
            total=Count('id'),
            enviados=Count('id', filter=models.Q(estado='enviado')),
            fallidos=Count('id', filter=models.Q(estado='fallido'))
        )

        emails_por_dia.append({
            'fecha': fecha.strftime('%Y-%m-%d'),
            'dia': fecha.strftime('%a'),
            'total': emails_dia['total'],
            'enviados': emails_dia['enviados'],
            'fallidos': emails_dia['fallidos']
        })

    emails_por_dia.reverse()

    # Emails más recientes
    emails_recientes = EmailNotification.objects.select_related('usuario').order_by('-fecha_creacion')[:10]

    # Estadísticas de newsletter
    newsletter_stats = {
        'campanas_activas': NewsletterCampaign.objects.filter(estado='enviando').count(),
        'campanas_completadas': NewsletterCampaign.objects.filter(
            estado='enviado', fecha_creacion__gte=fecha_desde
        ).count(),
        'total_suscriptores': NewsletterSubscription.objects.filter(activo=True).count(),
        'suscriptores_confirmados': NewsletterSubscription.objects.filter(
            activo=True, confirmado=True
        ).count(),
    }

    return render(request, 'tienda/admin_email_dashboard.html', {
        'stats': stats,
        'tipos_email': tipos_email,
        'emails_por_dia': emails_por_dia,
        'emails_recientes': emails_recientes,
        'newsletter_stats': newsletter_stats,
        'periodo': periodo,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    })


@login_required
def admin_email_detalle(request, email_id):
    """Vista detallada de un email específico"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    try:
        email = EmailNotification.objects.select_related('usuario', 'pedido', 'producto').get(id=email_id)
    except EmailNotification.DoesNotExist:
        messages.error(request, 'Email no encontrado.')
        return redirect('admin_email_dashboard')

    # Historial de envíos para este usuario y tipo
    historial_similar = EmailNotification.objects.filter(
        usuario=email.usuario,
        tipo=email.tipo
    ).exclude(id=email.id).order_by('-fecha_creacion')[:5]

    return render(request, 'tienda/admin_email_detalle.html', {
        'email': email,
        'historial_similar': historial_similar,
    })


@login_required
def admin_email_reenviar(request, email_id):
    """Reenviar un email específico"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'No autorizado'})

    try:
        email_original = EmailNotification.objects.get(id=email_id)

        # Crear nueva notificación
        email_service = EmailService()
        nueva_notificacion = EmailNotification.objects.create(
            usuario=email_original.usuario,
            tipo=email_original.tipo,
            email_destino=email_original.email_destino,
            asunto=f"REENVÍO: {email_original.asunto}",
            contenido_html=email_original.contenido_html,
            contenido_texto=email_original.contenido_texto,
            prioridad=email_original.prioridad,
        )

        # Agregar a cola
        EmailQueue.objects.create(
            notificacion=nueva_notificacion,
            prioridad=EmailService._get_prioridad_numero(email_original.prioridad)
        )

        return JsonResponse({
            'success': True,
            'mensaje': 'Email agregado a la cola de envío'
        })

    except EmailNotification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Email no encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def admin_newsletter_dashboard(request):
    """Dashboard específico para newsletter"""
    if not request.user.is_staff:
        messages.error(request, _('No tienes permisos para acceder a esta página.'))
        return redirect('home')

    # Estadísticas de newsletter
    stats = {
        'total_suscriptores': NewsletterSubscription.objects.count(),
        'suscriptores_activos': NewsletterSubscription.objects.filter(activo=True).count(),
        'suscriptores_confirmados': NewsletterSubscription.objects.filter(activo=True, confirmado=True).count(),
        'campanas_total': NewsletterCampaign.objects.count(),
        'campanas_activas': NewsletterCampaign.objects.filter(estado='enviando').count(),
        'emails_newsletter_enviados': NewsletterLog.objects.filter(tipo='envio').count(),
        'tasa_apertura_promedio': 0,
        'tasa_clic_promedio': 0,
    }

    # Calcular tasas promedio
    campanas_con_metricas = NewsletterCampaign.objects.exclude(enviados=0)
    if campanas_con_metricas.exists():
        stats['tasa_apertura_promedio'] = round(
            campanas_con_metricas.aggregate(avg=models.Avg('abiertos'))['avg'] or 0, 1
        )
        stats['tasa_clic_promedio'] = round(
            campanas_con_metricas.aggregate(avg=models.Avg('clics'))['avg'] or 0, 1
        )

    # Campañas recientes
    campanas_recientes = NewsletterCampaign.objects.order_by('-fecha_creacion')[:5]

    # Suscriptores recientes
    suscriptores_recientes = NewsletterSubscription.objects.order_by('-fecha_suscripcion')[:10]

    # Actividad por día (últimos 7 días)
    actividad_dias = []
    for i in range(7):
        fecha = timezone.now() - timedelta(days=i)
        fecha_inicio = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_fin = fecha.replace(hour=23, minute=59, second=59, microsecond=999999)

        actividad = NewsletterLog.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).values('tipo').annotate(count=Count('id'))

        actividad_dias.append({
            'fecha': fecha.strftime('%Y-%m-%d'),
            'dia': fecha.strftime('%a'),
            'envios': next((item['count'] for item in actividad if item['tipo'] == 'envio'), 0),
            'aperturas': next((item['count'] for item in actividad if item['tipo'] == 'apertura'), 0),
            'clics': next((item['count'] for item in actividad if item['tipo'] == 'clic'), 0),
        })

    actividad_dias.reverse()

    return render(request, 'tienda/admin_newsletter_dashboard.html', {
        'stats': stats,
        'campanas_recientes': campanas_recientes,
        'suscriptores_recientes': suscriptores_recientes,
        'actividad_dias': actividad_dias,
    })
