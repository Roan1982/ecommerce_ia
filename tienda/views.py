from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Producto, Compra, CompraProducto
from .recomendador import RecomendadorIA
from django.utils.translation import gettext_lazy as _
import pandas as pd

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
    productos = Producto.objects.all()
    return render(request, 'tienda/productos.html', {'productos': productos})

@login_required
def comprar(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        # Crear compra
        compra = Compra.objects.create(usuario=request.user, total=producto.precio)
        CompraProducto.objects.create(compra=compra, producto=producto, cantidad=1)
        messages.success(request, _('Compra de %(producto)s realizada exitosamente.') % {'producto': producto.nombre})
        return redirect('productos')
    return render(request, 'tienda/comprar.html', {'producto': producto})

@login_required
def recomendaciones(request):
    # Obtener historial de compras del usuario
    compras_usuario = Compra.objects.filter(usuario=request.user)
    productos_comprados = []
    for compra in compras_usuario:
        productos_compra = CompraProducto.objects.filter(compra=compra)
        for pc in productos_compra:
            productos_comprados.append(pc.producto.nombre.lower())

    # Crear dataset simulado con compras del usuario
    data = {'usuario': [request.user.username] * len(productos_comprados), 'producto': productos_comprados}
    df = pd.DataFrame(data)
    recomendador.df = pd.concat([recomendador.df, df], ignore_index=True)
    recomendador.matriz_usuario_producto = recomendador._crear_matriz()

    recs = recomendador.recomendar(request.user.username)
    productos_recomendados = Producto.objects.filter(nombre__in=[r.capitalize() for r in recs])
    return render(request, 'tienda/recomendaciones.html', {'recomendaciones': productos_recomendados})
