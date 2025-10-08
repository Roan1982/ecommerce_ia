#!/usr/bin/env python
"""
Asigna contribucion_objetivo = producto.precio para todas las wishlists con contribucion_objetivo == 0.
Ejecútalo desde la raíz del proyecto: python scripts/asignar_metas_wishlist.py
"""
import os
import sys
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
import django
django.setup()

from tienda.models import Wishlist

qs = Wishlist.objects.filter(contribucion_objetivo=0)
print('Wishlists con contribucion_objetivo=0 (conteo):', qs.count())
updated = 0
skipped = 0
for w in qs:
    precio = w.producto.precio or Decimal('0')
    if precio > 0:
        w.contribucion_objetivo = precio
        w.save()
        updated += 1
        print(f'Updated id={w.id} user={w.usuario.username} producto={w.producto.nombre} meta={precio}')
    else:
        skipped += 1
        print(f'Skipped id={w.id} producto={w.producto.nombre} precio={precio}')

print('\nResumen:')
print('Total encontrados:', qs.count())
print('Actualizados:', updated)
print('Skipped (precio 0):', skipped)
print('Ahora contribucion_objetivo=0:', Wishlist.objects.filter(contribucion_objetivo=0).count())
print('Ahora contribucion_objetivo>0:', Wishlist.objects.filter(contribucion_objetivo__gt=0).count())
