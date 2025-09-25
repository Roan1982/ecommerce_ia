#!/usr/bin/env python
import os
import sys
import django
from django.utils import timezone
import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from tienda.models import Cupon

def main():
    # Crear algunos cupones de prueba si no existen
    if Cupon.objects.count() == 0:
        Cupon.objects.create(
            codigo='BIENVENIDO10',
            descripcion='Descuento de bienvenida',
            tipo_descuento='porcentaje',
            valor_descuento=10,
            fecha_expiracion=timezone.now() + datetime.timedelta(days=30),
            usos_maximos=100,
            minimo_compra=50000
        )

        Cupon.objects.create(
            codigo='BLACKFRIDAY',
            descripcion='Descuento Black Friday',
            tipo_descuento='monto_fijo',
            valor_descuento=25000,
            fecha_expiracion=timezone.now() + datetime.timedelta(days=7),
            usos_maximos=50,
            minimo_compra=100000
        )

        Cupon.objects.create(
            codigo='EXPIRED',
            descripcion='Cupón expirado',
            tipo_descuento='porcentaje',
            valor_descuento=15,
            fecha_expiracion=timezone.now() - datetime.timedelta(days=1),
            usos_maximos=10,
            activo=False
        )

        print('Cupones de prueba creados')
    else:
        print(f'Ya existen {Cupon.objects.count()} cupones')

    print('Cupones en BD:')
    for c in Cupon.objects.all():
        print(f'- {c.codigo}: {c.descripcion} ({c.tipo_descuento}) - Activo: {c.activo} - Válido: {c.es_valido()}')

if __name__ == '__main__':
    main()