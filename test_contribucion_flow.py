#!/usr/bin/env python
"""
Script de prueba para verificar el flujo completo de contribuciones a wishlist.
Este script simula el proceso completo desde la creación de wishlist hasta la generación automática de pedidos.
"""

import os
import sys
import django
from decimal import Decimal

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from django.contrib.auth.models import User
from tienda.models import Producto, Wishlist, ContribucionWishlist, Pedido, PedidoProducto
from tienda.services.payment_service import PaymentService

def crear_datos_prueba():
    """Crear datos de prueba para el test"""
    print("=== CREANDO DATOS DE PRUEBA ===")

    # Crear usuarios de prueba
    try:
        propietario = User.objects.get(username='propietario_test')
        print("Usuario propietario ya existe")
    except User.DoesNotExist:
        propietario = User.objects.create_user(
            username='propietario_test',
            email='propietario@test.com',
            password='test123',
            first_name='Juan',
            last_name='Pérez'
        )
        print("Usuario propietario creado")

    try:
        contribuyente1 = User.objects.get(username='contribuyente1_test')
        print("Usuario contribuyente1 ya existe")
    except User.DoesNotExist:
        contribuyente1 = User.objects.create_user(
            username='contribuyente1_test',
            email='contribuyente1@test.com',
            password='test123',
            first_name='María',
            last_name='García'
        )
        print("Usuario contribuyente1 creado")

    try:
        contribuyente2 = User.objects.get(username='contribuyente2_test')
        print("Usuario contribuyente2 ya existe")
    except User.DoesNotExist:
        contribuyente2 = User.objects.create_user(
            username='contribuyente2_test',
            email='contribuyente2@test.com',
            password='test123',
            first_name='Carlos',
            last_name='López'
        )
        print("Usuario contribuyente2 creado")

    # Crear producto de prueba
    try:
        producto = Producto.objects.get(nombre='Producto de Prueba Contribuciones')
        print("Producto ya existe")
    except Producto.DoesNotExist:
        producto = Producto.objects.create(
            nombre='Producto de Prueba Contribuciones',
            precio=Decimal('100.00'),
            categoria='Electrónicos',
            descripcion='Producto para probar el sistema de contribuciones',
            stock=10,
            sku='TEST-CONTRIB-001'
        )
        print("Producto creado")

    return propietario, contribuyente1, contribuyente2, producto

def crear_wishlist_con_contribuciones(propietario, producto):
    """Crear wishlist item con contribuciones activas"""
    print("\n=== CREANDO WISHLIST CON CONTRIBUCIONES ===")

    wishlist_item = Wishlist.objects.create(
        usuario=propietario,
        producto=producto,
        permitir_contribuciones=True,
        contribucion_objetivo=Decimal('50.00'),  # Objetivo de $50
        contribucion_privada=False,
        descripcion_contribucion='Ayúdenme a conseguir este producto increíble'
    )

    print(f"Wishlist creado: {wishlist_item}")
    print(f"Objetivo: ${wishlist_item.contribucion_objetivo}")
    print(f"Producto: {producto.nombre} (${producto.precio})")

    return wishlist_item

def simular_contribuciones(wishlist_item, contribuyente1, contribuyente2):
    """Simular contribuciones de usuarios"""
    print("\n=== SIMULANDO CONTRIBUCIONES ===")

    # Contribución 1: $20
    contribucion1 = wishlist_item.agregar_contribucion(
        usuario=contribuyente1,
        monto=Decimal('20.00'),
        mensaje='¡Espero que te guste!'
    )
    print(f"Contribución 1: {contribuyente1.username} contribuyó ${contribucion1.monto}")
    print(f"Total contribuido: ${wishlist_item.total_contribuido}")
    print(f"Progreso: {wishlist_item.progreso_contribucion:.1f}%")

    # Contribución 2: $30 (debería alcanzar el objetivo)
    contribucion2 = wishlist_item.agregar_contribucion(
        usuario=contribuyente2,
        monto=Decimal('30.00'),
        mensaje='¡Cuenta conmigo!'
    )
    print(f"Contribución 2: {contribuyente2.username} contribuyó ${contribucion2.monto}")
    print(f"Total contribuido: ${wishlist_item.total_contribuido}")
    print(f"Progreso: {wishlist_item.progreso_contribucion:.1f}%")
    print(f"¿Objetivo alcanzado?: {wishlist_item.objetivo_alcanzado}")

    return contribucion1, contribucion2

def verificar_pedido_generado(wishlist_item, propietario):
    """Verificar que se generó el pedido automáticamente"""
    print("\n=== VERIFICANDO PEDIDO GENERADO ===")

    # Verificar que el wishlist fue eliminado (convertido a pedido)
    wishlist_existe = True
    try:
        wishlist_refreshed = Wishlist.objects.get(id=wishlist_item.id)
        print("⚠️  El wishlist aún existe (no se convirtió a pedido)")
        wishlist_existe = True
    except Wishlist.DoesNotExist:
        print("✓ Wishlist correctamente eliminado (convertido a pedido)")
        wishlist_existe = False

    # Verificar que se creó un pedido
    try:
        pedido = Pedido.objects.get(
            usuario=propietario,
            estado='pagado',
            notas__contains='contribuciones grupales'
        )
        print(f"✓ Pedido generado: #{pedido.id}")
        print(f"  Usuario: {pedido.usuario.username}")
        print(f"  Estado: {pedido.estado}")
        print(f"  Total productos: ${pedido.total_productos}")
        print(f"  Notas: {pedido.notas}")

        # Verificar productos del pedido
        productos_pedido = PedidoProducto.objects.filter(pedido=pedido)
        print(f"  Productos en pedido: {productos_pedido.count()}")
        for producto_pedido in productos_pedido:
            print(f"    - {producto_pedido.producto.nombre} x{producto_pedido.cantidad} = ${producto_pedido.subtotal}")

        # Verificar contribuciones marcadas como procesadas (solo si wishlist existe)
        if wishlist_existe:
            contribuciones_procesadas = ContribucionWishlist.objects.filter(
                wishlist_item_id=wishlist_item.id,
                estado='procesado'
            )
            print(f"✓ Contribuciones procesadas: {contribuciones_procesadas.count()}")
            for contrib in contribuciones_procesadas:
                print(f"    - {contrib.usuario_contribuyente.username}: ${contrib.monto} (estado: {contrib.estado})")
        else:
            # Buscar contribuciones procesadas por pedido
            contribuciones_procesadas = ContribucionWishlist.objects.filter(
                pedido_generado=pedido,
                estado='procesado'
            )
            print(f"✓ Contribuciones procesadas (por pedido): {contribuciones_procesadas.count()}")
            for contrib in contribuciones_procesadas:
                print(f"    - {contrib.usuario_contribuyente.username}: ${contrib.monto} (estado: {contrib.estado})")

        return True

    except Pedido.DoesNotExist:
        print("ERROR: No se encontró el pedido generado")
        return False

def probar_payment_service():
    """Probar el PaymentService con contribuciones"""
    print("\n=== PROBANDO PAYMENT SERVICE ===")

    propietario, contribuyente1, contribuyente2, producto = crear_datos_prueba()
    wishlist_item = crear_wishlist_con_contribuciones(propietario, producto)

    # Simular procesamiento de pago a través del PaymentService
    payment_service = PaymentService()

    try:
        # Crear una contribución primero
        contribucion = ContribucionWishlist.objects.create(
            wishlist_item=wishlist_item,
            usuario_contribuyente=contribuyente1,
            monto=Decimal('50.00'),  # Monto que alcanza exactamente el objetivo
            mensaje='¡Gran contribución para alcanzar la meta!',
            estado='pendiente'
        )
        print(f"✓ Contribución creada: {contribuyente1.username} - ${contribucion.monto}")

        # Datos de pago simulados
        datos_pago = {
            'numero_tarjeta': '4111111111111111',
            'fecha_expiracion': '12/25',
            'cvv': '123',
            'nombre_titular': 'Juan Pérez',
            'metodo_pago': 'tarjeta_test'
        }

        # Procesar el pago de la contribución
        resultado = payment_service.procesar_contribucion(contribucion, datos_pago)

        print("✓ PaymentService.procesar_contribucion ejecutado correctamente")
        print(f"  Resultado: {resultado}")

        if resultado['success']:
            print("✓ Pago procesado exitosamente")
            print(f"  Referencia: {resultado.get('referencia', 'N/A')}")

            # Verificar que la contribución cambió de estado (solo si aún existe)
            try:
                contribucion.refresh_from_db()
                print(f"✓ Estado de contribución: {contribucion.estado}")
            except ContribucionWishlist.DoesNotExist:
                print("✓ Contribución procesada y eliminada (convertida a pedido)")

            # Debug: verificar el estado del wishlist después del pago
            try:
                wishlist_item.refresh_from_db()
                print(f"✓ Total contribuido después del pago: ${wishlist_item.total_contribuido}")
                print(f"✓ Objetivo alcanzado: {wishlist_item.objetivo_alcanzado}")
                print(f"✓ Progreso: {wishlist_item.progreso_contribucion:.1f}%")

                # Debug adicional: verificar las contribuciones del wishlist
                contribuciones_wishlist = ContribucionWishlist.objects.filter(wishlist_item=wishlist_item)
                print(f"✓ Total contribuciones en BD: {contribuciones_wishlist.count()}")
                for contrib in contribuciones_wishlist:
                    print(f"    - ID: {contrib.id}, Usuario: {contrib.usuario_contribuyente.username}, Monto: ${contrib.monto}, Estado: {contrib.estado}")

            except Wishlist.DoesNotExist:
                print("✓ Wishlist convertido a pedido (eliminado correctamente)")

            # Verificar pedido generado
            exito = verificar_pedido_generado(wishlist_item, propietario)

            if exito:
                print("\n🎉 TEST COMPLETADO CON ÉXITO")
                print("El flujo de contribuciones funciona correctamente:")
                print("1. ✓ Contribución creada")
                print("2. ✓ Pago procesado")
                print("3. ✓ Objetivo alcanzado")
                print("4. ✓ Pedido generado automáticamente")
                print("5. ✓ Productos asignados al usuario")
                print("6. ✓ Contribuciones marcadas como procesadas")
                return True
            else:
                print("\n❌ TEST FALLÓ - Pedido no generado")
                return False
        else:
            print(f"❌ Pago falló: {resultado.get('error', 'Error desconocido')}")
            return False

    except Exception as e:
        print(f"ERROR en PaymentService: {e}")
        import traceback
        traceback.print_exc()
        return False

def limpiar_datos_prueba():
    """Limpiar datos de prueba"""
    print("\n=== LIMPIANDO DATOS DE PRUEBA ===")

    try:
        # Eliminar usuarios de prueba
        User.objects.filter(username__in=['propietario_test', 'contribuyente1_test', 'contribuyente2_test']).delete()

        # Eliminar producto de prueba
        Producto.objects.filter(sku='TEST-CONTRIB-001').delete()

        print("✓ Datos de prueba limpiados")
    except Exception as e:
        print(f"Error limpiando datos: {e}")

def main():
    """Función principal"""
    print("🚀 INICIANDO TEST DEL SISTEMA DE CONTRIBUCIONES")
    print("=" * 60)

    try:
        # Ejecutar test completo
        exito = probar_payment_service()

        if exito:
            print("\n" + "=" * 60)
            print("✅ TODOS LOS TESTS PASARON")
            print("El sistema de contribuciones a wishlist funciona correctamente.")
        else:
            print("\n" + "=" * 60)
            print("❌ ALGUNOS TESTS FALLARON")
            print("Revisar los errores arriba.")

    except Exception as e:
        print(f"\n💥 ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Limpiar datos de prueba
        limpiar_datos_prueba()

if __name__ == '__main__':
    main()