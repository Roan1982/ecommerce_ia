#!/usr/bin/env python3
"""
Script de prueba para verificar el funcionamiento de las notificaciones
en el carrito de compras y que no interfieran con el layout del navbar.
"""

import os

def test_template_notificaciones():
    """Prueba que el template del carrito tenga las notificaciones correctas"""
    print("🧪 Verificando template de notificaciones...")

    # Leer el archivo del template
    template_path = 'tienda/templates/tienda/carrito.html'
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verificar que contiene la función showMessage
        if 'function showMessage' in content:
            print("✅ Función showMessage encontrada en el template")
        else:
            print("❌ Función showMessage NO encontrada en el template")

        # Verificar que usa Bootstrap Toast
        if 'bootstrap.Toast' in content:
            print("✅ Bootstrap Toast implementado correctamente")
        else:
            print("❌ Bootstrap Toast NO implementado")

        # Verificar que no usa alert() nativo
        if 'alert(' in content:
            print("❌ Todavía usa alert() nativo - debe ser removido")
        else:
            print("✅ No usa alert() nativo")

        # Verificar que el toast tiene la posición correcta
        if 'top: 80px' in content and 'right: 20px' in content:
            print("✅ Toast posicionado correctamente (no interfiere con navbar)")
        else:
            print("❌ Posición del toast podría interferir con el navbar")

        # Verificar que tiene z-index alto
        if 'z-index: 1050' in content:
            print("✅ Z-index alto para aparecer sobre otros elementos")
        else:
            print("❌ Z-index podría ser insuficiente")

        # Verificar que el toast se remueve automáticamente
        if 'hidden.bs.toast' in content and 'remove()' in content:
            print("✅ Toast se remueve automáticamente después de ocultarse")
        else:
            print("❌ Toast podría no removerse correctamente")

    else:
        print(f"❌ Template no encontrado en {template_path}")

    print("🎉 Verificación completada!")

if __name__ == '__main__':
    test_template_notificaciones()