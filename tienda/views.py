from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Producto, Compra, CompraProducto, Carrito, CarritoProducto, DireccionEnvio, MetodoPago, Pedido, PedidoProducto, Resena, Cupon
from .recomendador import RecomendadorIA
from django.utils.translation import gettext_lazy as _
from django.db import models, transaction
from django import forms
from django.http import JsonResponse
import pandas as pd
from datetime import date

recomendador = RecomendadorIA()

def home(request):
    return render(request, 'tienda/home.html')

def registro(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
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

    return render(request, 'tienda/productos.html', {
        'productos': productos,
        'query': query,
        'categoria_seleccionada': categoria,
        'ordenar_por': ordenar_por,
        'categorias': categorias
    })

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

    return render(request, 'tienda/producto_detalle.html', {
        'producto': producto,
        'resenas': resenas,
        'puede_reseñar': puede_reseñar,
        'productos_relacionados': productos_relacionados
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
            # Reducir stock
            item.producto.stock -= item.cantidad
            item.producto.save()

        # Vaciar carrito
        items.delete()

        # Limpiar sesión
        del request.session['direccion_envio_id']
        del request.session['metodo_pago_id']
        if 'cupon_aplicado' in request.session:
            del request.session['cupon_aplicado']

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

def cupones_disponibles(request):
    """Vista para mostrar los cupones de descuento disponibles"""
    cupones = Cupon.objects.filter(activo=True, fecha_expiracion__gte=date.today()).order_by('minimo_compra')

    return render(request, 'tienda/cupones.html', {
        'cupones': cupones
    })
