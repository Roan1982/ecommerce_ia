#!/usr/bin/env python
import os
import django
from datetime import date, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.models import Cupon

def crear_cupones_prueba():
    """Crear cupones de prueba para testing"""
    cupones_data = [
        {'codigo': 'DESC10', 'tipo_descuento': 'porcentaje', 'valor_descuento': 10, 'descripcion': '10% de descuento', 'minimo_compra': 50, 'usos_maximos': 100},
        {'codigo': 'DESC20', 'tipo_descuento': 'porcentaje', 'valor_descuento': 20, 'descripcion': '20% de descuento', 'minimo_compra': 100, 'usos_maximos': 50},
        {'codigo': 'FIJO15', 'tipo_descuento': 'monto_fijo', 'valor_descuento': 15, 'descripcion': '$15 de descuento', 'minimo_compra': 75, 'usos_maximos': 25},
    ]

    for data in cupones_data:
        cupon, created = Cupon.objects.get_or_create(
            codigo=data['codigo'],
            defaults={
                'tipo_descuento': data['tipo_descuento'],
                'valor_descuento': data['valor_descuento'],
                'descripcion': data['descripcion'],
                'minimo_compra': data['minimo_compra'],
                'usos_maximos': data['usos_maximos'],
                'fecha_expiracion': date.today() + timedelta(days=30),
                'activo': True
            }
        )
        if created:
            print(f'✓ Creado cupón: {cupon.codigo} - {cupon.descripcion}')
        else:
            print(f'ℹ Cupón ya existe: {cupon.codigo}')

if __name__ == '__main__':
    crear_cupones_prueba()
    print('\n🎉 Cupones de prueba creados exitosamente!')
    print('\nCupones disponibles:')
    print('- DESC10: 10% de descuento (mínimo $50)')
    print('- DESC20: 20% de descuento (mínimo $100)')
    print('- FIJO15: $15 de descuento fijo (mínimo $75)')