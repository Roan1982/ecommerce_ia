#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.models import Producto
from tienda.forms import ProductoAdminForm

def test_product_creation():
    try:
        print("=== TEST DE CREACIÓN Y EDICIÓN DE PRODUCTOS ===\n")

        # 1. Probar creación de producto desde cero
        print("1. Probando creación de producto nuevo...")
        data_nuevo = {
            'nombre': 'Producto Nuevo de Prueba',
            'descripcion': 'Descripción del producto nuevo',
            'precio': '200.00',
            'categoria': 'Electrónica',
            'stock': '25',
            'stock_minimo': '5',
            'estado': 'activo'
            # peso, dimensiones, sku son opcionales
        }

        form_nuevo = ProductoAdminForm(data=data_nuevo)
        print(f"Formulario para producto nuevo válido: {form_nuevo.is_valid()}")
        if not form_nuevo.is_valid():
            print(f"Errores: {form_nuevo.errors}")
        else:
            producto_nuevo = form_nuevo.save()
            print(f"Producto creado exitosamente: {producto_nuevo.nombre} (ID: {producto_nuevo.id})")

        # 2. Probar edición de producto existente
        print("\n2. Probando edición de producto existente...")
        producto_existente = Producto.objects.filter(nombre='Producto de Prueba Edición').first()
        if not producto_existente:
            producto_existente = Producto.objects.create(
                nombre='Producto de Prueba Edición',
                precio=100.00,
                categoria='Prueba',
                stock=10,
                stock_minimo=5
            )

        data_edicion = {
            'nombre': 'Producto Editado con Éxito',
            'descripcion': 'Descripción actualizada',
            'precio': '150.00',
            'categoria': 'Prueba Editada',
            'stock': '20',
            'stock_minimo': '8',
            'estado': 'activo',
            'peso': '1.5',
            'dimensiones': '10x15x5 cm'
        }

        form_edicion = ProductoAdminForm(data=data_edicion, instance=producto_existente)
        print(f"Formulario de edición válido: {form_edicion.is_valid()}")
        if not form_edicion.is_valid():
            print(f"Errores: {form_edicion.errors}")
        else:
            producto_editado = form_edicion.save()
            print(f"Producto editado exitosamente: {producto_editado.nombre}")
            print(f"Precio: {producto_editado.precio}, Peso: {producto_editado.peso}, Dimensiones: {producto_editado.dimensiones}")

        # 3. Verificar valores por defecto
        print("\n3. Verificando valores por defecto...")
        producto_defaults = Producto.objects.create(
            nombre='Producto con Defaults',
            precio=50.00,
            categoria='Test'
        )
        print(f"Producto con defaults - Stock: {producto_defaults.stock}, Peso: {producto_defaults.peso}")

        print("\n=== TODOS LOS TESTS COMPLETADOS ===")

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_product_creation()