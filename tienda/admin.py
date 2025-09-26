from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse, Http404
from django.db import models
from django.db.models import Count
from django.contrib.auth.models import User
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import Producto, MovimientoInventario, Pedido, PedidoProducto, Resena, Cupon, DireccionEnvio, MetodoPago
from .forms import ProductoAdminForm


# Crear instancia personalizada del sitio admin
class InventarioAdminSite(admin.AdminSite):
    site_header = "Administración E-commerce IA"
    site_title = "E-commerce IA Admin"
    index_title = "Panel de Administración"
    index_template = "admin/index.html"
    app_index_template = "admin/app_index.html"
    login_template = "admin/login.html"
    logout_template = "admin/logout.html"
    password_change_template = "admin/password_change.html"
    password_change_done_template = "admin/password_change_done.html"
    base_template = "admin/base.html"

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request)

        # Solo mostrar funcionalidades avanzadas para administradores
        if request.user.is_staff or request.user.is_superuser:
            # Crear lista ordenada de aplicaciones personalizadas
            custom_apps = []

            # 1. Dashboard
            dashboard_app = {
                "name": "📊 Dashboard",
                "app_label": "dashboard",
                "app_url": "/admin/dashboard/",
                "has_module_perms": True,
                "models": [
                    {
                        "name": "Estadísticas Generales",
                        "object_name": "estadisticas",
                        "perms": {"add": False, "change": False, "delete": False, "view": True},
                        "admin_url": "/admin/dashboard/",
                        "add_url": None,
                        "view_only": True,
                    }
                ]
            }
            custom_apps.append(dashboard_app)

            # 2. Gestión de Usuarios (PRIMERO después del dashboard)
            usuarios_app = {
                "name": "👥 Gestión de Usuarios",
                "app_label": "usuarios",
                "app_url": "/admin/usuarios/",
                "has_module_perms": True,
                "models": [
                    {
                        "name": "Usuarios del Sistema",
                        "object_name": "usuarios_sistema",
                        "perms": {"add": True, "change": True, "delete": True, "view": True},
                        "admin_url": "/admin/usuarios/",
                        "add_url": "/admin/usuarios/agregar/",
                        "view_only": False,
                    }
                ]
            }
            custom_apps.append(usuarios_app)

            # 3. Inventario
            inventario_app = {
                "name": "📦 Inventario",
                "app_label": "inventario",
                "app_url": "/admin/inventario/",
                "has_module_perms": True,
                "models": [
                    {
                        "name": "Gestión de Inventario",
                        "object_name": "inventario",
                        "perms": {"add": True, "change": True, "delete": True, "view": True},
                        "admin_url": "/admin/inventario/",
                        "add_url": None,
                        "view_only": False,
                    }
                ]
            }
            custom_apps.append(inventario_app)

            # 4. Gestión de Pedidos
            pedidos_app = {
                "name": "📦 Gestión de Pedidos",
                "app_label": "pedidos",
                "app_url": "/admin/pedidos/",
                "has_module_perms": True,
                "models": [
                    {
                        "name": "Pedidos Pendientes",
                        "object_name": "pedidos_pendientes",
                        "perms": {"add": False, "change": True, "delete": False, "view": True},
                        "admin_url": "/admin/pedidos/pendientes/",
                        "add_url": None,
                        "view_only": False,
                    }
                ]
            }
            custom_apps.append(pedidos_app)

            # 5. Cupones
            cupones_app = {
                "name": "🎫 Cupones",
                "app_label": "cupones",
                "app_url": "/admin/tienda/cupon/",
                "has_module_perms": True,
                "models": [
                    {
                        "name": "Gestión de Cupones",
                        "object_name": "cupones",
                        "perms": {"add": True, "change": True, "delete": True, "view": True},
                        "admin_url": "/admin/tienda/cupon/",
                        "add_url": "/admin/tienda/cupon/add/",
                        "view_only": False,
                    }
                ]
            }
            custom_apps.append(cupones_app)

            # 6. Configuración
            config_app = {
                "name": "⚙️ Configuración",
                "app_label": "configuracion",
                "app_url": "/admin/config/",
                "has_module_perms": True,
                "models": [
                    {
                        "name": "Configuración General",
                        "object_name": "config_general",
                        "perms": {"add": False, "change": True, "delete": False, "view": True},
                        "admin_url": "/admin/config/general/",
                        "add_url": None,
                        "view_only": False,
                    }
                ]
            }
            custom_apps.append(config_app)

            # Filtrar aplicaciones estándar para mostrar solo las relevantes
            filtered_app_list = []
            for app in app_list:
                # Mantener aplicaciones estándar importantes
                if app.get('app_label') in ['auth', 'contenttypes', 'sessions']:
                    # Renombrar aplicaciones estándar para que sean más descriptivas
                    if app['app_label'] == 'auth':
                        app['name'] = '🔐 Autenticación y Usuarios'
                    elif app['app_label'] == 'contenttypes':
                        app['name'] = '📋 Tipos de Contenido'
                    elif app['app_label'] == 'sessions':
                        app['name'] = '🕒 Sesiones'
                    filtered_app_list.append(app)

            # Combinar aplicaciones personalizadas con las filtradas del admin estándar
            return custom_apps + filtered_app_list

        # Para usuarios no staff, mostrar solo aplicaciones estándar filtradas
        filtered_app_list = []
        for app in app_list:
            if app.get('app_label') in ['auth', 'contenttypes', 'sessions']:
                if app['app_label'] == 'auth':
                    app['name'] = '🔐 Autenticación y Usuarios'
                elif app['app_label'] == 'contenttypes':
                    app['name'] = '📋 Tipos de Contenido'
                elif app['app_label'] == 'sessions':
                    app['name'] = '🕒 Sesiones'
                filtered_app_list.append(app)
        return filtered_app_list

    def each_context(self, request):
        """
        Agregar contexto común a todas las vistas del admin
        """
        context = super().each_context(request)
        context['app_list'] = self.get_app_list(request)

        # Determinar la aplicación actual basada en la URL
        current_path = request.path
        current_app = None

        # Buscar en las aplicaciones personalizadas
        for app in context['app_list']:
            if app.get('app_url') and current_path.startswith(app['app_url']):
                current_app = app.get('app_label')
                break

        # Si no se encontró en personalizadas, verificar aplicaciones estándar
        if not current_app:
            if current_path.startswith('/admin/auth/'):
                current_app = 'auth'
            elif current_path.startswith('/admin/contenttypes/'):
                current_app = 'contenttypes'
            elif current_path.startswith('/admin/sessions/'):
                current_app = 'sessions'
            elif current_path.startswith('/admin/tienda/'):
                current_app = 'tienda'

        context['current_app'] = current_app

        # Determinar el título de la página basado en la aplicación actual
        if current_app == 'auth':
            context['title'] = '🔐 Autenticación y Usuarios'
        elif current_app == 'contenttypes':
            context['title'] = '📋 Tipos de Contenido'
        elif current_app == 'sessions':
            context['title'] = '🕒 Sesiones'
        elif current_app == 'tienda':
            context['title'] = '🛒 Gestión de Tienda'
        else:
            context['title'] = '📊 Dashboard'

        return context

    def app_index(self, request, app_label, extra_context=None):
        """
        Vista de índice de aplicación personalizada que genera model_list correctamente
        """
        from django.apps import apps
        from django.contrib.admin.sites import site as default_site
        from django.core.exceptions import PermissionDenied
        from django.shortcuts import redirect

        # Verificar permisos básicos
        if not self.has_permission(request):
            raise PermissionDenied

        # Redirección automática para contenttypes y sessions - ir directamente a la lista
        if app_label == 'contenttypes':
            return redirect('admin:contenttypes_contenttype_changelist')
        elif app_label == 'sessions':
            return redirect('admin:sessions_session_changelist')

        # Obtener la aplicación
        try:
            app_config = apps.get_app_config(app_label)
        except LookupError:
            raise Http404("No se encontró la aplicación %r" % app_label)

        # Obtener modelos registrados en este admin site
        app_models = []
        for model, model_admin in self._registry.items():
            if model._meta.app_label == app_label:
                # Verificar permisos del usuario para este modelo
                perms = model_admin.get_model_perms(request)
                if True in perms.values():  # Si tiene al menos un permiso
                    model_dict = {
                        'model': model,
                        'name': model._meta.verbose_name_plural,
                        'object_name': model._meta.label_lower,
                        'perms': perms,
                        'admin_url': None,
                        'add_url': None,
                    }

                    # URLs si tiene permisos
                    if perms.get('change', False) or perms.get('view', False):
                        model_dict['admin_url'] = self.get_url_for_result(model_admin, 'changelist')
                    if perms.get('add', False):
                        model_dict['add_url'] = self.get_url_for_result(model_admin, 'add')

                    # Contar objetos
                    try:
                        model_dict['object_count'] = model.objects.count()
                    except:
                        model_dict['object_count'] = 0

                    app_models.append(model_dict)

        # Ordenar modelos por nombre
        app_models.sort(key=lambda x: x['name'].lower())

        # Contexto
        context = {
            **self.each_context(request),
            'title': self.get_app_title(app_label),
            'app_label': app_label,
            'app_models': app_models,
            'model_list': app_models,  # Para compatibilidad con el template
            'has_module_perms': self.has_permission(request),
            'subtitle': None,
        }

        if extra_context:
            context.update(extra_context)

        # Usar el template de app_index
        from django.shortcuts import render
        return render(request, self.app_index_template or 'admin/app_index.html', context)

    def get_app_title(self, app_label):
        """
        Obtener el título descriptivo de la aplicación
        """
        titles = {
            'auth': '🔐 Autenticación y Usuarios',
            'contenttypes': '📋 Tipos de Contenido',
            'sessions': '🕒 Sesiones',
            'tienda': '🛒 Gestión de Tienda',
        }
        return titles.get(app_label, app_label.title())

    def get_url_for_result(self, model_admin, action):
        """
        Generar URL para una acción específica del modelo
        """
        from django.urls import reverse
        app_label = model_admin.model._meta.app_label
        model_name = model_admin.model._meta.model_name

        try:
            return reverse(f'admin:{app_label}_{model_name}_{action}')
        except:
            return None

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('inventario/', self.admin_view(self.inventario_view), name='inventario'),
            path('movimientos/', self.admin_view(self.movimientos_view), name='movimientos'),
            path('alertas-stock/', self.admin_view(self.alertas_stock_view), name='alertas_stock'),
            path('dashboard/', self.admin_view(self.dashboard_view), name='dashboard'),
            path('reportes/', self.admin_view(self.reportes_view), name='reportes'),
            path('pedidos/', self.admin_view(self.pedidos_view), name='pedidos'),
            path('pedidos/pendientes/', self.admin_view(self.pedidos_pendientes_view), name='pedidos_pendientes'),
            path('pedidos/completados/', self.admin_view(self.pedidos_completados_view), name='pedidos_completados'),
            path('config/', self.admin_view(self.config_view), name='config'),
            path('config/general/', self.admin_view(self.config_general_view), name='config_general'),
            path('mantenimiento/', self.admin_view(self.mantenimiento_view), name='mantenimiento'),
            # URLs para gestión de usuarios personalizada
            path('usuarios/', self.admin_view(self.usuarios_view), name='usuarios'),
            path('usuarios/agregar/', self.admin_view(self.agregar_usuario_view), name='agregar_usuario'),
            path('usuarios/editar/<int:usuario_id>/', self.admin_view(self.editar_usuario_view), name='editar_usuario'),
            path('usuarios/<int:usuario_id>/', self.admin_view(self.detalle_usuario_view), name='detalle_usuario'),
            # URLs adicionales para funcionalidades personalizadas
            path('productos/', self.admin_view(self.productos_view), name='productos'),
            path('productos/agregar/', self.admin_view(self.agregar_producto_view), name='agregar_producto'),
            path('productos/editar/<int:producto_id>/', self.admin_view(self.editar_producto_view), name='editar_producto'),
            path('productos/eliminar/<int:producto_id>/', self.admin_view(self.eliminar_producto_view), name='eliminar_producto'),
            path('productos/actualizar-stock/', self.admin_view(self.actualizar_stock_view), name='actualizar_stock'),
            path('cupones/', self.admin_view(self.cupones_view), name='cupones'),
            path('cupones/agregar/', self.admin_view(self.agregar_cupon_view), name='agregar_cupon'),
            path('cupones/editar/<int:cupon_id>/', self.admin_view(self.editar_cupon_view), name='editar_cupon'),
            path('cupones/eliminar/<int:cupon_id>/', self.admin_view(self.eliminar_cupon_view), name='eliminar_cupon'),
            path('cupones/actualizar-estado/', self.admin_view(self.actualizar_estado_cupon_view), name='actualizar_estado_cupon'),
            path('configuracion/', self.admin_view(self.configuracion_view), name='configuracion'),
            path('configuracion/guardar/', self.admin_view(self.guardar_configuracion_view), name='guardar_configuracion'),
            path('configuracion/restaurar/', self.admin_view(self.restaurar_configuracion_view), name='restaurar_configuracion'),
            path('backup/', self.admin_view(self.crear_backup_view), name='crear_backup'),
            path('email/test/', self.admin_view(self.probar_email_view), name='probar_email'),
        ]
        return custom_urls + urls

    @method_decorator(staff_member_required)
    def inventario_view(self, request):
        """Vista de administración de inventario integrada en Django admin"""
        # Filtros
        categoria_filter = request.GET.get("categoria", "")
        stock_filter = request.GET.get("stock", "")
        estado_filter = request.GET.get("estado", "")

        productos = Producto.objects.all().order_by("nombre")

        # Aplicar filtros
        if categoria_filter:
            productos = productos.filter(categoria=categoria_filter)
        if stock_filter == "bajo":
            productos = productos.filter(stock__lte=models.F("stock_minimo"), stock__gt=0)
        elif stock_filter == "agotado":
            productos = productos.filter(stock=0)
        elif stock_filter == "disponible":
            productos = productos.filter(stock__gt=0)
        if estado_filter:
            productos = productos.filter(estado=estado_filter)

        # Estadísticas
        stats = {
            "total_productos": Producto.objects.count(),
            "productos_activos": Producto.objects.filter(estado="activo").count(),
            "productos_inactivos": Producto.objects.filter(estado="inactivo").count(),
            "productos_agotados": Producto.objects.filter(estado="agotado").count(),
            "stock_bajo": Producto.objects.filter(stock__lte=models.F("stock_minimo"), stock__gt=0).count(),
            "total_unidades": Producto.objects.aggregate(total=models.Sum("stock"))["total"] or 0,
        }

        categorias = Producto.objects.values_list("categoria", flat=True).distinct()

        context = {
            "productos": productos,
            "stats": stats,
            "categorias": categorias,
            "filtros": {
                "categoria": categoria_filter,
                "stock": stock_filter,
                "estado": estado_filter,
            },
            "title": "Administración de Inventario",
        }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/inventario.html", context)

    @method_decorator(staff_member_required)
    def movimientos_view(self, request):
        """Vista para ver movimientos de inventario"""
        movimientos = MovimientoInventario.objects.select_related("producto", "usuario").order_by("-fecha")[:100]

        context = {
            "movimientos": movimientos,
            "title": "Movimientos de Inventario",
        }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/movimientos.html", context)

    @method_decorator(staff_member_required)
    def alertas_stock_view(self, request):
        """Vista para ver alertas de stock bajo"""
        productos_stock_bajo = Producto.objects.filter(
            stock__lte=models.F("stock_minimo"),
            stock__gt=0,
            estado="activo"
        ).order_by("stock")

        productos_agotados = Producto.objects.filter(
            stock=0,
            estado="activo"
        ).order_by("nombre")

        context = {
            "productos_stock_bajo": productos_stock_bajo,
            "productos_agotados": productos_agotados,
            "title": "Alertas de Stock",
        }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/alertas_stock.html", context)

    @method_decorator(staff_member_required)
    def dashboard_view(self, request):
        """Vista del dashboard con estadísticas generales"""
        from django.contrib.auth.models import User
        from django.db.models import Sum, Count
        from django.db.models.functions import TruncMonth

        # Estadísticas generales
        stats = {
            "total_usuarios": User.objects.count(),
            "total_productos": Producto.objects.count(),
            "productos_activos": Producto.objects.filter(estado="activo").count(),
            "total_pedidos": Pedido.objects.count(),
            "pedidos_pendientes": Pedido.objects.filter(estado="pendiente").count(),
            "pedidos_completados": Pedido.objects.filter(estado="completado").count(),
            "total_ingresos": Pedido.objects.filter(estado="completado").aggregate(
                total=Sum("total_pedido")
            )["total"] or 0,
            "productos_stock_bajo": Producto.objects.filter(
                stock__lte=models.F("stock_minimo"),
                stock__gt=0
            ).count(),
            "productos_agotados": Producto.objects.filter(stock=0).count(),
        }

        # Pedidos recientes
        pedidos_recientes = Pedido.objects.select_related("usuario").order_by("-fecha_creacion")[:10]

        # Productos más vendidos (simulado)
        productos_populares = Producto.objects.filter(estado="activo").order_by("-stock")[:5]

        context = {
            "stats": stats,
            "pedidos_recientes": pedidos_recientes,
            "productos_populares": productos_populares,
            "title": "Dashboard - Estadísticas Generales",
        }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/dashboard.html", context)

    @method_decorator(staff_member_required)
    def reportes_view(self, request):
        """Vista de reportes de ventas"""
        from django.db.models.functions import TruncMonth, TruncDay
        from django.db.models import Sum

        # Filtros de fecha
        periodo = request.GET.get("periodo", "mes")

        if periodo == "dia":
            ventas = Pedido.objects.filter(estado="completado").annotate(
                periodo=TruncDay("fecha_creacion")
            ).values("periodo").annotate(
                total=Sum("total_pedido"),
                cantidad=Count("id")
            ).order_by("-periodo")[:30]
        else:
            ventas = Pedido.objects.filter(estado="completado").annotate(
                periodo=TruncMonth("fecha_creacion")
            ).values("periodo").annotate(
                total=Sum("total_pedido"),
                cantidad=Count("id")
            ).order_by("-periodo")[:12]

        # Productos más vendidos
        productos_mas_vendidos = PedidoProducto.objects.values(
            "producto__nombre"
        ).annotate(
            total_vendido=Sum("cantidad"),
            ingresos=Sum(models.F("cantidad") * models.F("precio_unitario"))
        ).order_by("-total_vendido")[:10]

        context = {
            "ventas": ventas,
            "productos_mas_vendidos": productos_mas_vendidos,
            "periodo": periodo,
            "title": "Reportes de Ventas",
        }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/reportes.html", context)

    @method_decorator(staff_member_required)
    def pedidos_view(self, request):
        """Vista general de gestión de pedidos"""
        # Estadísticas de pedidos
        stats = {
            "total_pedidos": Pedido.objects.count(),
            "pedidos_pendientes": Pedido.objects.filter(estado="pendiente").count(),
            "pedidos_procesando": Pedido.objects.filter(estado="procesando").count(),
            "pedidos_completados": Pedido.objects.filter(estado="completado").count(),
            "pedidos_cancelados": Pedido.objects.filter(estado="cancelado").count(),
        }

        # Pedidos recientes (últimos 20)
        pedidos_recientes = Pedido.objects.select_related("usuario").order_by("-fecha_creacion")[:20]

        context = {
            "stats": stats,
            "pedidos_recientes": pedidos_recientes,
            "title": "Gestión de Pedidos",
        }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/pedidos.html", context)

    @method_decorator(staff_member_required)
    def config_view(self, request):
        """Vista general de configuración"""
        # Configuraciones disponibles
        configuraciones = [
            {
                "titulo": "Configuración General",
                "descripcion": "Configuraciones básicas del sitio",
                "url": "/admin/config/general/",
                "icono": "⚙️"
            },
            {
                "titulo": "Mantenimiento",
                "descripcion": "Herramientas de mantenimiento del sistema",
                "url": "/admin/mantenimiento/",
                "icono": "🔧"
            }
        ]

        context = {
            "configuraciones": configuraciones,
            "title": "Configuración del Sistema",
        }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/config.html", context)

    @method_decorator(staff_member_required)
    def pedidos_pendientes_view(self, request):
        """Vista de pedidos pendientes"""
        pedidos = Pedido.objects.filter(
            estado__in=["pendiente", "procesando"]
        ).select_related("usuario").order_by("-fecha_creacion")

        context = {
            "pedidos": pedidos,
            "title": "Pedidos Pendientes",
        }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/pedidos_pendientes.html", context)

    @method_decorator(staff_member_required)
    def pedidos_completados_view(self, request):
        """Vista de pedidos completados"""
        pedidos = Pedido.objects.filter(
            estado="completado"
        ).select_related("usuario").order_by("-fecha_creacion")[:50]

        context = {
            "pedidos": pedidos,
            "title": "Pedidos Completados",
        }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/pedidos_completados.html", context)

    @method_decorator(staff_member_required)
    def config_general_view(self, request):
        """Vista de configuración general"""
        if request.method == "POST":
            # Aquí iría la lógica para guardar configuraciones
            pass

        # Configuraciones actuales (simuladas)
        configuraciones = {
            "sitio_activo": True,
            "registro_abierto": True,
            "envio_gratuito_minimo": 50000,
            "impuestos_activos": True,
            "moneda": "COP",
            "email_notificaciones": True,
        }

        context = {
            "configuraciones": configuraciones,
            "title": "Configuración General",
        }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/config_general.html", context)

    @method_decorator(staff_member_required)
    def mantenimiento_view(self, request):
        """Vista de mantenimiento del sistema"""
        from django.core.management import call_command
        from io import StringIO

        if request.method == "POST":
            accion = request.POST.get("accion")

            if accion == "limpiar_cache":
                # Simular limpieza de cache
                mensaje = "Cache limpiado exitosamente"
            elif accion == "optimizar_bd":
                # Simular optimización de BD
                mensaje = "Base de datos optimizada"
            elif accion == "backup":
                # Simular backup
                mensaje = "Backup creado exitosamente"
            else:
                mensaje = "Acción no reconocida"

            context = {
                "mensaje": mensaje,
                "title": "Mantenimiento del Sistema",
            }
        else:
            # Información del sistema
            info_sistema = {
                "version_django": "5.2.6",
                "productos_totales": Producto.objects.count(),
                "usuarios_totales": User.objects.count(),
                "pedidos_totales": Pedido.objects.count(),
                "db_size": "Estimado: 25MB",  # Simulado
            }

            context = {
                "info_sistema": info_sistema,
                "title": "Mantenimiento del Sistema",
            }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/mantenimiento.html", context)

    @method_decorator(staff_member_required)
    def usuarios_view(self, request):
        """Vista de gestión de usuarios personalizada"""
        from django.contrib.auth.models import User
        from django.db.models import Count

        # Filtros
        q = request.GET.get('q', '')
        estado = request.GET.get('estado', '')
        rol = request.GET.get('rol', '')

        usuarios = User.objects.all()

        # Aplicar filtros
        if q:
            usuarios = usuarios.filter(
                models.Q(username__icontains=q) |
                models.Q(first_name__icontains=q) |
                models.Q(last_name__icontains=q) |
                models.Q(email__icontains=q)
            )

        if estado == 'activos':
            usuarios = usuarios.filter(is_active=True)
        elif estado == 'inactivos':
            usuarios = usuarios.filter(is_active=False)

        if rol == 'staff':
            usuarios = usuarios.filter(is_staff=True)
        elif rol == 'superuser':
            usuarios = usuarios.filter(is_superuser=True)

        # Estadísticas
        stats = {
            'total': User.objects.count(),
            'activos': User.objects.filter(is_active=True).count(),
            'staff': User.objects.filter(is_staff=True).count(),
            'superuser': User.objects.filter(is_superuser=True).count(),
        }

        # Paginación
        from django.core.paginator import Paginator
        paginator = Paginator(usuarios.order_by('-date_joined'), 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'usuarios': page_obj,
            'stats': stats,
            'filtros': {
                'q': q,
                'estado': estado,
                'rol': rol,
            },
            'title': 'Gestión de Usuarios',
        }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/usuarios.html", context)

    @method_decorator(staff_member_required)
    def agregar_usuario_view(self, request):
        """Vista para agregar usuario"""
        from django.contrib.auth.forms import UserCreationForm
        from django.shortcuts import redirect

        if request.method == 'POST':
            form = UserCreationForm(request.POST)
            if form.is_valid():
                user = form.save()
                return redirect('admin:detalle_usuario', usuario_id=user.id)
        else:
            form = UserCreationForm()

        context = {
            'form': form,
            'title': 'Agregar Usuario',
        }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/usuario_form.html", context)

    @method_decorator(staff_member_required)
    def editar_usuario_view(self, request, usuario_id):
        """Vista para editar usuario"""
        from django.contrib.auth.forms import UserChangeForm
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib.auth.models import User

        user = get_object_or_404(User, id=usuario_id)

        if request.method == 'POST':
            form = UserChangeForm(request.POST, instance=user)
            if form.is_valid():
                form.save()
                return redirect('admin:detalle_usuario', usuario_id=user.id)
        else:
            form = UserChangeForm(instance=user)

        context = {
            'form': form,
            'usuario': user,
            'title': f'Editar Usuario: {user.username}',
        }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/usuario_form.html", context)

    @method_decorator(staff_member_required)
    def detalle_usuario_view(self, request, usuario_id):
        """Vista de detalle de usuario"""
        from django.contrib.auth.models import User
        from django.shortcuts import get_object_or_404
        from django.db.models import Sum

        usuario = get_object_or_404(User, id=usuario_id)

        # Estadísticas del usuario
        stats = {
            'total_pedidos': Pedido.objects.filter(usuario=usuario).count(),
            'pedidos_completados': Pedido.objects.filter(usuario=usuario, estado='completado').count(),
            'total_gastado': Pedido.objects.filter(usuario=usuario, estado='completado').aggregate(
                total=Sum('total_pedido')
            )['total'] or 0,
        }

        # Pedidos recientes
        pedidos_recientes = Pedido.objects.filter(usuario=usuario).order_by('-fecha_creacion')[:5]

        context = {
            'usuario': usuario,
            'stats': stats,
            'pedidos_recientes': pedidos_recientes,
            'title': f'Perfil de {usuario.get_full_name() or usuario.username}',
        }

        # Agregar contexto del admin site para la navegación lateral
        admin_context = self.each_context(request)
        context.update(admin_context)

        return render(request, "admin/tienda/usuario_detalle.html", context)

    @method_decorator(staff_member_required)
    def productos_view(self, request):
        """Vista de gestión de productos"""
        from django.shortcuts import redirect
        # Redirigir a la vista estándar de productos del admin
        return redirect('admin:tienda_producto_changelist')

    @method_decorator(staff_member_required)
    def agregar_producto_view(self, request):
        """Vista para agregar producto"""
        from django.shortcuts import redirect
        # Redirigir a la vista de agregar producto del admin
        return redirect('admin:tienda_producto_add')

    @method_decorator(staff_member_required)
    def editar_producto_view(self, request, producto_id):
        """Vista para editar producto"""
        from django.shortcuts import redirect
        # Redirigir a la vista de editar producto del admin
        return redirect('admin:tienda_producto_change', object_id=producto_id)

    @method_decorator(staff_member_required)
    def eliminar_producto_view(self, request, producto_id):
        """Vista para eliminar producto"""
        from django.shortcuts import redirect
        # Redirigir a la vista de eliminar producto del admin
        return redirect('admin:tienda_producto_delete', object_id=producto_id)

    @method_decorator(staff_member_required)
    def actualizar_stock_view(self, request):
        """Vista para actualizar stock de productos"""
        from django.shortcuts import redirect
        # Redirigir a la vista de productos
        return redirect('admin:tienda_producto_changelist')

    @method_decorator(staff_member_required)
    def cupones_view(self, request):
        """Vista de gestión de cupones"""
        from django.shortcuts import redirect
        # Redirigir a la vista estándar de cupones del admin
        return redirect('admin:tienda_cupon_changelist')

    @method_decorator(staff_member_required)
    def agregar_cupon_view(self, request):
        """Vista para agregar cupón"""
        from django.shortcuts import redirect
        # Redirigir a la vista de agregar cupón del admin
        return redirect('admin:tienda_cupon_add')

    @method_decorator(staff_member_required)
    def editar_cupon_view(self, request, cupon_id):
        """Vista para editar cupón"""
        from django.shortcuts import redirect
        # Redirigir a la vista de editar cupón del admin
        return redirect('admin:tienda_cupon_change', object_id=cupon_id)

    @method_decorator(staff_member_required)
    def eliminar_cupon_view(self, request, cupon_id):
        """Vista para eliminar cupón"""
        from django.shortcuts import redirect
        # Redirigir a la vista de eliminar cupón del admin
        return redirect('admin:tienda_cupon_delete', object_id=cupon_id)

    @method_decorator(staff_member_required)
    def actualizar_estado_cupon_view(self, request):
        """Vista para actualizar estado de cupones"""
        from django.shortcuts import redirect
        # Redirigir a la vista de cupones
        return redirect('admin:tienda_cupon_changelist')

    @method_decorator(staff_member_required)
    def configuracion_view(self, request):
        """Vista de configuración general"""
        # Redirigir a la vista de configuración existente
        return self.config_view(request)

    @method_decorator(staff_member_required)
    def guardar_configuracion_view(self, request):
        """Vista para guardar configuración"""
        from django.shortcuts import redirect
        # Redirigir a la configuración general
        return redirect('admin:config_general')

    @method_decorator(staff_member_required)
    def restaurar_configuracion_view(self, request):
        """Vista para restaurar configuración"""
        from django.shortcuts import redirect
        # Redirigir a la configuración general
        return redirect('admin:config_general')

    @method_decorator(staff_member_required)
    def crear_backup_view(self, request):
        """Vista para crear backup"""
        from django.shortcuts import redirect
        # Redirigir al mantenimiento
        return redirect('admin:mantenimiento')

    @method_decorator(staff_member_required)
    def probar_email_view(self, request):
        """Vista para probar envío de emails"""
        from django.shortcuts import redirect
        # Redirigir al mantenimiento
        return redirect('admin:mantenimiento')


# Crear instancia del sitio admin personalizado
admin_site = InventarioAdminSite(name="admin")
admin.site = admin_site


@admin.register(Producto, site=admin_site)
class ProductoAdmin(admin.ModelAdmin):
    form = ProductoAdminForm
    list_display = ["nombre", "sku", "precio", "stock", "stock_minimo", "estado", "categoria", "stock_status"]
    list_filter = ["estado", "categoria"]
    search_fields = ["nombre", "sku", "descripcion"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    list_editable = ["stock", "estado"]
    ordering = ["nombre"]

    fieldsets = (
        ("Información Básica", {
            "fields": ("nombre", "descripcion", "precio", "categoria", "imagen_url")
        }),
        ("Inventario", {
            "fields": ("stock", "stock_minimo", "sku", "estado"),
            "classes": ("collapse",)
        }),
        ("Especificaciones", {
            "fields": ("peso", "dimensiones"),
            "classes": ("collapse",)
        }),
        ("Metadata", {
            "fields": ("fecha_creacion", "fecha_actualizacion"),
            "classes": ("collapse",)
        }),
    )

    def stock_status(self, obj):
        if obj.agotado:
            return " Agotado"
        elif obj.stock_bajo:
            return " Stock Bajo"
        else:
            return " Disponible"
    stock_status.short_description = "Estado Stock"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("actualizar/<int:producto_id>/", admin_site.admin_view(self.actualizar_stock_view), name="tienda_producto_actualizar_stock"),
        ]
        return custom_urls + urls

    @method_decorator(staff_member_required)
    def actualizar_stock_view(self, request, producto_id):
        """Vista AJAX para actualizar stock de un producto"""
        if not request.method == "POST":
            return JsonResponse({"success": False, "error": "Método no permitido"})

        try:
            producto = Producto.objects.get(id=producto_id)
            nuevo_stock = int(request.POST.get("stock", 0))
            descripcion = request.POST.get("descripcion", "Ajuste manual desde admin")

            if nuevo_stock < 0:
                return JsonResponse({"success": False, "error": "El stock no puede ser negativo"})

            # Calcular la diferencia
            diferencia = nuevo_stock - producto.stock

            if diferencia > 0:
                # Aumento de stock
                MovimientoInventario.objects.create(
                    producto=producto,
                    tipo="entrada",
                    cantidad=diferencia,
                    descripcion=descripcion,
                    usuario=request.user
                )
            elif diferencia < 0:
                # Reducción de stock
                MovimientoInventario.objects.create(
                    producto=producto,
                    tipo="salida",
                    cantidad=diferencia,  # Negativo
                    descripcion=descripcion,
                    usuario=request.user
                )

            # Actualizar stock
            producto.stock = nuevo_stock
            producto.save()

            return JsonResponse({
                "success": True,
                "nuevo_stock": producto.stock,
                "stock_bajo": producto.stock_bajo,
                "agotado": producto.agotado
            })

        except Producto.DoesNotExist:
            return JsonResponse({"success": False, "error": "Producto no encontrado"})
        except ValueError:
            return JsonResponse({"success": False, "error": "Valor de stock inválido"})


@admin.register(MovimientoInventario, site=admin_site)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ["producto", "tipo", "cantidad", "descripcion", "usuario", "fecha"]
    list_filter = ["tipo", "fecha", "usuario"]
    search_fields = ["producto__nombre", "descripcion"]
    readonly_fields = ["fecha"]
    ordering = ["-fecha"]


@admin.register(Pedido, site=admin_site)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ["id", "usuario", "estado", "total_pedido", "fecha_creacion"]
    list_filter = ["estado", "fecha_creacion"]
    search_fields = ["usuario__username", "id"]
    readonly_fields = ["fecha_creacion"]


@admin.register(PedidoProducto, site=admin_site)
class PedidoProductoAdmin(admin.ModelAdmin):
    list_display = ["pedido", "producto", "cantidad", "precio_unitario"]
    search_fields = ["pedido__id", "producto__nombre"]


@admin.register(Resena, site=admin_site)
class ResenaAdmin(admin.ModelAdmin):
    list_display = ["producto", "usuario", "calificacion", "fecha_creacion"]
    list_filter = ["calificacion", "fecha_creacion"]
    search_fields = ["producto__nombre", "usuario__username", "comentario"]


@admin.register(Cupon, site=admin_site)
class CuponAdmin(admin.ModelAdmin):
    list_display = ["codigo", "descripcion", "tipo_cupon", "tipo_descuento", "valor_descuento", "activo", "fecha_expiracion", "usos_display", "usuario_propietario_display"]
    list_filter = ["activo", "tipo_descuento", "tipo_cupon", "fecha_expiracion"]
    search_fields = ["codigo", "descripcion"]
    change_list_template = "admin/tienda/cupones.html"

    # Agregar acciones en lote para activar/desactivar cupones
    actions = ['activate_coupons', 'deactivate_coupons', 'create_copiable_coupons', 'create_points_coupons']

    fieldsets = (
        ("Información Básica", {
            "fields": ("codigo", "descripcion", "tipo_cupon"),
        }),
        ("Configuración de Descuento", {
            "fields": ("tipo_descuento", "valor_descuento", "minimo_compra"),
        }),
        ("Uso y Vigencia", {
            "fields": ("usos_maximos", "fecha_expiracion", "activo"),
        }),
        ("Configuración Avanzada", {
            "fields": ("puntos_requeridos", "usuario_propietario"),
            "classes": ("collapse",)
        }),
    )

    def usos_display(self, obj):
        return f"{obj.usos_actuales}/{obj.usos_maximos}"
    usos_display.short_description = "Usos"

    def usuario_propietario_display(self, obj):
        if obj.usuario_propietario:
            return obj.usuario_propietario.username
        return "-"
    usuario_propietario_display.short_description = "Propietario"

    def activate_coupons(self, request, queryset):
        """Activar cupones seleccionados"""
        updated = queryset.update(activo=True)
        self.message_user(request, f'{updated} cupón(es) activado(s) correctamente.')
    activate_coupons.short_description = "Activar cupones seleccionados"

    def deactivate_coupons(self, request, queryset):
        """Desactivar cupones seleccionados"""
        updated = queryset.update(activo=False)
        self.message_user(request, f'{updated} cupón(es) desactivado(s) correctamente.')
    deactivate_coupons.short_description = "Desactivar cupones seleccionados"

    def create_copiable_coupons(self, request, queryset):
        """Crear cupones copiables basados en los seleccionados"""
        created_count = 0
        for cupon in queryset:
            # Crear un cupón copiable basado en el original
            from tienda.models import Cupon
            import secrets
            import string

            # Generar código único
            while True:
                codigo = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                if not Cupon.objects.filter(codigo=codigo).exists():
                    break

            Cupon.objects.create(
                codigo=codigo,
                descripcion=f"Copiable - {cupon.descripcion}",
                tipo_cupon='codigo_copiable',
                tipo_descuento=cupon.tipo_descuento,
                valor_descuento=cupon.valor_descuento,
                fecha_expiracion=cupon.fecha_expiracion,
                usos_maximos=1,  # Los copiables se usan solo una vez
                minimo_compra=cupon.minimo_compra,
            )
            created_count += 1

        self.message_user(request, f'Se crearon {created_count} cupones copiables.')
    create_copiable_coupons.short_description = "Crear cupones copiables"

    def create_points_coupons(self, request, queryset):
        """Crear cupones que se compran con puntos"""
        created_count = 0
        for cupon in queryset:
            # Crear un cupón que requiere puntos
            from tienda.models import Cupon
            import secrets
            import string

            # Generar código único
            while True:
                codigo = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                if not Cupon.objects.filter(codigo=codigo).exists():
                    break

            # Calcular puntos requeridos basado en el valor del descuento
            puntos_requeridos = int(cupon.valor_descuento * 10)  # 10 puntos por cada peso de descuento

            Cupon.objects.create(
                codigo=codigo,
                descripcion=f"Con puntos - {cupon.descripcion}",
                tipo_cupon='comprado_puntos',
                tipo_descuento=cupon.tipo_descuento,
                valor_descuento=cupon.valor_descuento,
                fecha_expiracion=cupon.fecha_expiracion,
                usos_maximos=1,
                minimo_compra=cupon.minimo_compra,
                puntos_requeridos=puntos_requeridos,
            )
            created_count += 1

        self.message_user(request, f'Se crearon {created_count} cupones que requieren puntos.')
    create_points_coupons.short_description = "Crear cupones con puntos"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('toggle-status/<int:cupon_id>/', admin_site.admin_view(self.toggle_status_view), name='tienda_cupon_toggle_status'),
        ]
        return custom_urls + urls

    @method_decorator(staff_member_required)
    def toggle_status_view(self, request, cupon_id):
        """Vista para cambiar el estado de un cupón individual"""
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages

        cupon = get_object_or_404(Cupon, pk=cupon_id)

        # Guardar el estado anterior
        estado_anterior = "activo" if cupon.activo else "inactivo"

        # Cambiar el estado
        cupon.activo = not cupon.activo
        cupon.save()

        # Estado nuevo
        estado_nuevo = "activo" if cupon.activo else "inactivo"

        # Mensaje de éxito más detallado
        messages.success(
            request,
            f'✅ Cupón "{cupon.codigo}" cambió de {estado_anterior} a {estado_nuevo}.\n'
            f'📝 {cupon.descripcion[:50]}{"..." if len(cupon.descripcion) > 50 else ""}'
        )

        # Redirigir de vuelta a la lista
        return redirect('admin:tienda_cupon_changelist')

    def changelist_view(self, request, extra_context=None):
        """Vista personalizada para la lista de cupones"""
        response = super().changelist_view(request, extra_context)

        if hasattr(response, 'context_data'):
            context = response.context_data

            # Obtener todos los cupones con filtros aplicados
            cl = context.get('cl')
            if cl:
                cupones = cl.get_queryset(request)
            else:
                cupones = self.get_queryset(request)

            # Aplicar filtros adicionales desde la URL
            activo_filter = request.GET.get('activo')
            tipo_filter = request.GET.get('tipo_descuento')
            q_filter = request.GET.get('q')

            if activo_filter is not None:
                cupones = cupones.filter(activo=activo_filter == '1')
            if tipo_filter:
                cupones = cupones.filter(tipo_descuento=tipo_filter)
            if q_filter:
                cupones = cupones.filter(
                    models.Q(codigo__icontains=q_filter) |
                    models.Q(descripcion__icontains=q_filter)
                )

            # Estadísticas
            from django.utils import timezone
            ahora = timezone.now()

            cupones_activos = cupones.filter(activo=True, fecha_expiracion__gt=ahora)
            cupones_expirados = cupones.filter(fecha_expiracion__lte=ahora)
            cupones_inactivos = cupones.filter(activo=False)

            # Agregar datos al contexto
            context.update({
                'cupones': cupones,
                'cupones_activos': cupones_activos,
                'cupones_expirados': cupones_expirados,
                'cupones_inactivos': cupones_inactivos,
            })

        return response


@admin.register(DireccionEnvio, site=admin_site)
class DireccionEnvioAdmin(admin.ModelAdmin):
    list_display = ["usuario", "nombre_direccion", "ciudad", "provincia", "es_predeterminada"]
    list_filter = ["provincia", "es_predeterminada"]
    search_fields = ["usuario__username", "nombre_direccion", "calle"]


@admin.register(MetodoPago, site=admin_site)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ["usuario", "tipo", "nombre_titular", "es_predeterminada"]
    list_filter = ["tipo", "es_predeterminada"]
    search_fields = ["usuario__username", "nombre_titular"]


# Registrar modelos de autenticación en el admin personalizado
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group

@admin.register(User, site=admin_site)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "email", "first_name", "last_name", "is_staff", "is_active", "date_joined"]
    list_filter = ["is_staff", "is_superuser", "is_active", "date_joined"]
    search_fields = ["username", "first_name", "last_name", "email"]
    ordering = ["username"]
    change_list_template = "admin/auth/user/change_list.html"
    change_form_template = "admin/change_form.html"

    # Agregar acciones en lote para activar/desactivar usuarios
    actions = [UserAdmin.actions[0]] if UserAdmin.actions else []  # Mantener la acción de eliminar si existe
    actions.extend(['activate_users', 'deactivate_users'])

    fieldsets = (
        ("Información de la Cuenta", {
            "fields": ("username", "password"),
            "description": "Credenciales de acceso del usuario."
        }),
        ("Información Personal", {
            "fields": ("first_name", "last_name", "email"),
            "description": "Datos personales del usuario."
        }),
        ("Permisos", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            "description": "Permisos y roles del usuario en el sistema.",
            "classes": ("collapse",)
        }),
        ("Fechas Importantes", {
            "fields": ("last_login", "date_joined"),
            "description": "Fechas de registro y último acceso.",
            "classes": ("collapse",)
        }),
    )

    filter_horizontal = ("groups", "user_permissions")

    def activate_users(self, request, queryset):
        """Activar usuarios seleccionados"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} usuario(s) activado(s) correctamente.')
    activate_users.short_description = "Activar usuarios seleccionados"

    def deactivate_users(self, request, queryset):
        """Desactivar usuarios seleccionados"""
        # No permitir desactivar al propio usuario
        current_user = request.user
        queryset = queryset.exclude(pk=current_user.pk)
        updated = queryset.update(is_active=False)
        if updated < queryset.count():
            self.message_user(request, f'No puedes desactivar tu propia cuenta. {updated} usuario(s) desactivado(s).')
        else:
            self.message_user(request, f'{updated} usuario(s) desactivado(s) correctamente.')
    deactivate_users.short_description = "Desactivar usuarios seleccionados"

    # Agregar enlace a la gestión personalizada de usuarios
    def get_urls(self):
        urls = super().get_urls()
        from django.urls import path
        custom_urls = [
            path('gestion/', admin_site.admin_view(admin_site.usuarios_view), name='usuarios_gestion'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        """Vista personalizada para la lista de usuarios con estadísticas"""
        response = super().changelist_view(request, extra_context)

        if hasattr(response, 'context_data'):
            context = response.context_data

            # Obtener queryset filtrado
            cl = context.get('cl')
            if cl:
                users = cl.get_queryset(request)
            else:
                users = self.get_queryset(request)

            # Aplicar filtros adicionales desde la URL
            is_active_filter = request.GET.get('is_active')
            user_type_filter = request.GET.get('user_type')
            q_filter = request.GET.get('q')

            if is_active_filter is not None:
                users = users.filter(is_active=is_active_filter == '1')

            if user_type_filter == 'staff':
                users = users.filter(is_staff=True)
            elif user_type_filter == 'superuser':
                users = users.filter(is_superuser=True)
            elif user_type_filter == 'regular':
                users = users.filter(is_staff=False, is_superuser=False)

            if q_filter:
                users = users.filter(
                    models.Q(username__icontains=q_filter) |
                    models.Q(first_name__icontains=q_filter) |
                    models.Q(last_name__icontains=q_filter) |
                    models.Q(email__icontains=q_filter)
                )

            # Estadísticas
            from django.contrib.auth.models import User
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()
            staff_users = User.objects.filter(is_staff=True).count()
            superuser_users = User.objects.filter(is_superuser=True).count()

            # Agregar datos al contexto
            context.update({
                'users': users,
                'total_users': total_users,
                'active_users': active_users,
                'staff_users': staff_users,
                'superuser_users': superuser_users,
            })

        return response

@admin.register(Group, site=admin_site)
class CustomGroupAdmin(GroupAdmin):
    change_list_template = "admin/auth/group/change_list.html"
    change_form_template = "admin/change_form.html"

    fieldsets = (
        ("Información del Grupo", {
            "fields": ("name",),
            "description": "Nombre del grupo de usuarios."
        }),
        ("Permisos", {
            "fields": ("permissions",),
            "description": "Permisos asignados a este grupo de usuarios.",
            "classes": ("collapse",)
        }),
    )

    filter_horizontal = ("permissions",)

    def changelist_view(self, request, extra_context=None):
        """Vista personalizada para la lista de grupos con estadísticas"""
        response = super().changelist_view(request, extra_context)

        if hasattr(response, 'context_data'):
            context = response.context_data

            # Obtener queryset filtrado
            cl = context.get('cl')
            if cl:
                groups = cl.get_queryset(request)
            else:
                groups = self.get_queryset(request)

            # Aplicar filtros adicionales desde la URL
            q_filter = request.GET.get('q')

            if q_filter:
                groups = groups.filter(name__icontains=q_filter)

            # Estadísticas
            from django.contrib.auth.models import Group
            total_groups = Group.objects.count()
            total_users_in_groups = Group.objects.annotate(user_count=models.Count('user')).aggregate(total=models.Sum('user_count'))['total'] or 0
            total_permissions = 0
            for group in Group.objects.all():
                total_permissions += group.permissions.count()

            # Agregar datos al contexto
            context.update({
                'groups': groups,
                'total_groups': total_groups,
                'total_users_in_groups': total_users_in_groups,
                'total_permissions': total_permissions,
            })

        return response


# Registrar modelos adicionales de aplicaciones estándar
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session

@admin.register(Permission, site=admin_site)
class CustomPermissionAdmin(admin.ModelAdmin):
    list_display = ["name", "codename", "content_type", "get_app_model"]
    list_filter = ["content_type"]
    search_fields = ["name", "codename"]
    change_list_template = "admin/change_list.html"
    change_form_template = "admin/change_form.html"
    readonly_fields = ["codename"]

    def get_app_model(self, obj):
        return f"{obj.content_type.app_label}.{obj.content_type.model}"
    get_app_model.short_description = "Aplicación.Modelo"

    fieldsets = (
        ("Información del Permiso", {
            "fields": ("name", "codename"),
            "description": "Información básica del permiso de acceso al sistema."
        }),
        ("Tipo de Contenido", {
            "fields": ("content_type",),
            "description": "Modelo y aplicación a la que pertenece este permiso."
        }),
    )

@admin.register(ContentType, site=admin_site)
class CustomContentTypeAdmin(admin.ModelAdmin):
    list_display = ["app_label", "model", "name", "get_object_count", "get_permissions_count"]
    list_filter = ["app_label"]
    search_fields = ["app_label", "model", "name"]
    change_list_template = "admin/contenttypes/contenttype/change_list.html"
    change_form_template = "admin/contenttypes/contenttype/change_form.html"
    add_form_template = "admin/contenttypes/contenttype/add_form.html"
    delete_confirmation_template = "admin/contenttypes/contenttype/delete_confirmation.html"

    # Acciones en lote con advertencias de seguridad
    actions = [
        'delete_selected_contenttypes',
        'export_contenttypes_csv',
    ]

    def delete_selected_contenttypes(self, request, queryset):
        """
        Acción personalizada para eliminar ContentTypes seleccionados con validaciones de seguridad
        """
        # Verificar que el usuario sea superusuario
        if not request.user.is_superuser:
            self.message_user(
                request,
                "Solo los superusuarios pueden eliminar ContentTypes.",
                level='ERROR'
            )
            return

        # Contar objetos relacionados
        total_objects = 0
        contenttypes_with_objects = []

        for ct in queryset:
            try:
                model_class = ct.model_class()
                if model_class:
                    count = model_class.objects.count()
                    total_objects += count
                    if count > 0:
                        contenttypes_with_objects.append(f"{ct.app_label}.{ct.model} ({count} objetos)")
            except:
                pass

        # Advertencias de seguridad
        if total_objects > 0:
            self.message_user(
                request,
                f"ADVERTENCIA: Los ContentTypes seleccionados contienen {total_objects} objetos en total. "
                f"Eliminarlos puede causar pérdida de datos irreversible.",
                level='WARNING'
            )

        if contenttypes_with_objects:
            self.message_user(
                request,
                f"ContentTypes con datos: {', '.join(contenttypes_with_objects[:3])}{'...' if len(contenttypes_with_objects) > 3 else ''}",
                level='WARNING'
            )

        # Proceder con eliminación estándar
        return self.delete_selected(request, queryset)

    delete_selected_contenttypes.short_description = "🗑️ Eliminar ContentTypes seleccionados (REQUIERE SUPERUSUARIO)"
    delete_selected_contenttypes.allowed_permissions = ('delete',)

    def export_contenttypes_csv(self, request, queryset):
        """
        Exportar ContentTypes seleccionados a CSV
        """
        import csv
        from django.http import HttpResponse
        from django.utils import timezone

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="contenttypes_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Aplicación', 'Modelo', 'Nombre', 'Objetos', 'Permisos'])

        for ct in queryset:
            writer.writerow([
                ct.app_label,
                ct.model,
                ct.name,
                self.get_object_count(ct),
                self.get_permissions_count(ct)
            ])

        self.message_user(request, f"Exportados {queryset.count()} ContentTypes a CSV.")
        return response

    export_contenttypes_csv.short_description = "📊 Exportar a CSV"

    # Campos que se pueden agregar (solo para nuevos ContentTypes)
    add_fields = ["app_label", "model"]

    def get_fields(self, request, obj=None):
        """Definir campos según si estamos agregando o editando"""
        if obj is None:  # Agregando nuevo
            return self.add_fields
        else:  # Editando existente
            return ["app_label", "model"]  # Solo campos reales, 'name' se muestra en el template

    def get_readonly_fields(self, request, obj=None):
        """Campos readonly según si estamos agregando o editando"""
        if obj is None:  # Agregando nuevo ContentType
            return []  # No hay campos readonly al agregar
        else:  # Editando ContentType existente
            return ["app_label", "model"]  # Campos reales readonly al editar

    # Permitir agregar ContentTypes manualmente (para uso avanzado)
    def has_add_permission(self, request):
        # Solo permitir agregar a superusuarios con una advertencia clara
        return request.user.is_superuser

    def add_view(self, request, form_url='', extra_context=None):
        """Vista personalizada para agregar ContentTypes con advertencias"""
        # Agregar contexto adicional para la página de agregar
        extra_context = extra_context or {}
        extra_context.update({
            'show_advanced_warning': True,
            'title': 'Agregar ContentType (Función Avanzada)',
        })

        return super().add_view(request, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        """Validar antes de guardar un nuevo ContentType"""
        if not change:  # Solo para nuevos ContentTypes
            # Verificar si ya existe un ContentType con estos datos
            if ContentType.objects.filter(
                app_label=obj.app_label,
                model=obj.model
            ).exists():
                from django.contrib import messages
                messages.error(
                    request,
                    f'Ya existe un ContentType para {obj.app_label}.{obj.model}'
                )
                return

            # Verificar si el modelo existe realmente
            try:
                # Intentar obtener la clase del modelo
                model_class = obj.model_class()
                if not model_class:
                    from django.contrib import messages
                    messages.warning(
                        request,
                        f'Atención: No se encontró el modelo {obj.app_label}.{obj.model} en el código. '
                        'Asegúrate de que el modelo existe antes de crear el ContentType.'
                    )
            except Exception as e:
                from django.contrib import messages
                messages.warning(
                    request,
                    f'Advertencia: Error al verificar el modelo - {str(e)}'
                )

        super().save_model(request, obj, form, change)

    def get_object_count(self, obj):
        """Cuenta los objetos de este tipo de contenido"""
        try:
            model_class = obj.model_class()
            if model_class:
                return model_class.objects.count()
            return 0
        except:
            return 0
    get_object_count.short_description = "Objetos"

    def get_permissions_count(self, obj):
        """Cuenta los permisos asociados a este tipo de contenido"""
        return obj.permission_set.count()
    get_permissions_count.short_description = "Permisos"

    def delete_view(self, request, object_id, extra_context=None):
        """Vista personalizada para la eliminación con estadísticas adicionales"""
        # Llamar al método padre para obtener la respuesta estándar
        response = super().delete_view(request, object_id, extra_context)

        if hasattr(response, 'context_data') and object_id:
            context = response.context_data

            # Obtener el objeto ContentType
            try:
                content_type = self.get_queryset(request).get(pk=object_id)

                # Calcular estadísticas
                object_count = self.get_object_count(content_type)
                permissions_count = self.get_permissions_count(content_type)

                # Obtener permisos asociados
                permissions = content_type.permission_set.all().order_by('codename')

                # Obtener modelo relacionado si existe
                model_class = content_type.model_class()
                related_models = []

                if model_class:
                    # Buscar modelos que referencian a este modelo
                    for app_config in apps.get_app_configs():
                        for model in app_config.get_models():
                            for field in model._meta.get_fields():
                                if hasattr(field, 'related_model') and field.related_model == model_class:
                                    try:
                                        related_ct = ContentType.objects.get_for_model(model)
                                        if related_ct != content_type:  # Evitar auto-referencia
                                            related_models.append(related_ct)
                                    except:
                                        pass

                # Agregar datos al contexto
                context.update({
                    'object_count': object_count,
                    'permissions_count': permissions_count,
                    'permissions': permissions,
                    'model_class': model_class,
                    'model_module': model_class.__module__ if model_class else None,
                    'model_name': model_class.__name__ if model_class else None,
                    'related_models': related_models[:10],  # Limitar a 10 modelos relacionados
                })

            except Exception as e:
                # En caso de error, agregar valores por defecto
                context.update({
                    'object_count': 0,
                    'permissions_count': 0,
                    'permissions': [],
                    'model_class': None,
                    'related_models': [],
                })

        return response

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Vista personalizada para el formulario de edición con estadísticas adicionales"""
        # Llamar al método padre para obtener la respuesta estándar
        response = super().changeform_view(request, object_id, form_url, extra_context)

        if hasattr(response, 'context_data') and object_id:
            context = response.context_data

            # Obtener el objeto ContentType
            try:
                content_type = self.get_queryset(request).get(pk=object_id)

                # Calcular estadísticas
                object_count = self.get_object_count(content_type)
                permissions_count = self.get_permissions_count(content_type)

                # Obtener permisos asociados
                permissions = content_type.permission_set.all().order_by('codename')

                # Obtener modelo relacionado si existe
                model_class = content_type.model_class()
                related_models = []

                if model_class:
                    # Buscar modelos que referencian a este modelo
                    for app_config in apps.get_app_configs():
                        for model in app_config.get_models():
                            for field in model._meta.get_fields():
                                if hasattr(field, 'related_model') and field.related_model == model_class:
                                    try:
                                        related_ct = ContentType.objects.get_for_model(model)
                                        if related_ct != content_type:  # Evitar auto-referencia
                                            related_models.append(related_ct)
                                    except:
                                        pass

                # Agregar datos al contexto
                context.update({
                    'object_count': object_count,
                    'permissions_count': permissions_count,
                    'permissions': permissions,
                    'model_class': model_class,
                    'model_module': model_class.__module__ if model_class else None,
                    'model_name': model_class.__name__ if model_class else None,
                    'related_models': related_models[:5],  # Limitar a 5 modelos relacionados
                })

            except Exception as e:
                # En caso de error, agregar valores por defecto
                context.update({
                    'object_count': 0,
                    'permissions_count': 0,
                    'permissions': [],
                    'model_class': None,
                    'related_models': [],
                })

        return response

    def changelist_view(self, request, extra_context=None):
        """Vista personalizada para la lista de content types con estadísticas"""
        response = super().changelist_view(request, extra_context)

        if hasattr(response, 'context_data'):
            context = response.context_data

            # Obtener queryset filtrado
            cl = context.get('cl')
            if cl:
                content_types = cl.get_queryset(request)
            else:
                content_types = self.get_queryset(request)

            # Aplicar filtros adicionales desde la URL
            app_filter = request.GET.get('app_label')
            q_filter = request.GET.get('q')

            if app_filter:
                content_types = content_types.filter(app_label=app_filter)
            if q_filter:
                content_types = content_types.filter(
                    models.Q(app_label__icontains=q_filter) |
                    models.Q(model__icontains=q_filter) |
                    models.Q(name__icontains=q_filter)
                )

            # Calcular estadísticas
            all_content_types = ContentType.objects.all()
            apps_list = all_content_types.values_list('app_label', flat=True).distinct().order_by('app_label')

            # Calcular totales
            total_objects = 0
            total_permissions = 0

            for ct in all_content_types:
                try:
                    model_class = ct.model_class()
                    if model_class:
                        total_objects += model_class.objects.count()
                except:
                    pass
                total_permissions += ct.permission_set.count()

            # Agregar estadísticas a cada content type
            content_types_with_stats = []
            for ct in content_types:
                ct.object_count = self.get_object_count(ct)
                ct.permissions_count = self.get_permissions_count(ct)
                
                # Agregar información de la clase del modelo
                try:
                    model_class = ct.model_class()
                    if model_class:
                        ct.model_class_name = f"{model_class.__module__}.{model_class.__name__}"
                        ct.model_class_exists = True
                    else:
                        ct.model_class_name = "No encontrado"
                        ct.model_class_exists = False
                except:
                    ct.model_class_name = "Error"
                    ct.model_class_exists = False
                
                content_types_with_stats.append(ct)

            # Agregar datos al contexto
            context.update({
                'content_types': content_types_with_stats,
                'apps': apps_list,
                'total_objects': total_objects,
                'total_permissions': total_permissions,
            })

        return response

    def get_fieldsets(self, request, obj=None):
        """Definir fieldsets según si estamos agregando o editando"""
        if obj is None:  # Agregando nuevo
            return (
                ("Información del Modelo", {
                    "fields": ("app_label", "model"),
                    "description": "Información del modelo a registrar en el sistema."
                }),
            )
        else:  # Editando existente
            return (
                ("Información del Modelo", {
                    "fields": ("app_label", "model"),
                    "description": "Información del modelo registrado en el sistema (solo lectura)."
                }),
            )

@admin.register(Session, site=admin_site)
class CustomSessionAdmin(admin.ModelAdmin):
    list_display = ["session_key", "get_user_display", "get_status_display", "expire_date", "get_session_data_preview"]
    readonly_fields = ["session_key", "session_data", "expire_date"]
    search_fields = ["session_key"]
    list_filter = ["expire_date"]
    change_list_template = "admin/sessions/session/change_list.html"
    change_form_template = "admin/change_form.html"

    # Acciones en lote con advertencias de seguridad
    actions = [
        'delete_selected_sessions',
        'export_sessions_csv',
        'clear_expired_sessions',
    ]

    def has_add_permission(self, request):
        """
        Deshabilitar la creación manual de sesiones desde el admin
        Las sesiones se crean automáticamente por Django
        """
        return False

    def delete_selected_sessions(self, request, queryset):
        """
        Acción personalizada para eliminar sesiones seleccionadas con validaciones de seguridad
        """
        # Verificar que el usuario sea superusuario para eliminar sesiones activas
        active_sessions = queryset.filter(expire_date__gt=timezone.now())
        if active_sessions.exists() and not request.user.is_superuser:
            self.message_user(
                request,
                "Solo los superusuarios pueden eliminar sesiones activas.",
                level='ERROR'
            )
            return

        # Contar sesiones con usuarios autenticados
        authenticated_count = 0
        for session in queryset:
            try:
                data = session.get_decoded()
                if '_auth_user_id' in data:
                    authenticated_count += 1
            except:
                pass

        # Advertencias de seguridad
        if authenticated_count > 0:
            self.message_user(
                request,
                f"ADVERTENCIA: {authenticated_count} de las sesiones seleccionadas pertenecen a usuarios autenticados. "
                f"Eliminarlas desconectará a estos usuarios.",
                level='WARNING'
            )

        if active_sessions.exists():
            self.message_user(
                request,
                f"ADVERTENCIA: {active_sessions.count()} sesiones activas serán eliminadas.",
                level='WARNING'
            )

        # Proceder con eliminación estándar
        return self.delete_selected(request, queryset)

    delete_selected_sessions.short_description = "🗑️ Eliminar sesiones seleccionadas"
    delete_selected_sessions.allowed_permissions = ('delete',)

    def export_sessions_csv(self, request, queryset):
        """
        Exportar sesiones seleccionadas a CSV
        """
        import csv
        from django.http import HttpResponse
        from django.utils import timezone

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="sessions_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Clave de Sesión', 'Usuario', 'Estado', 'Fecha de Expiración', 'Datos'])

        for session in queryset:
            try:
                data = session.get_decoded()
                user_id = data.get('_auth_user_id', 'Anónimo')
                status = 'Activa' if session.expire_date > timezone.now() else 'Expirada'
                data_preview = str(data)[:200] + '...' if len(str(data)) > 200 else str(data)
            except:
                user_id = 'Error'
                status = 'Error'
                data_preview = 'No disponible'

            writer.writerow([
                session.session_key,
                user_id,
                status,
                session.expire_date.strftime('%Y-%m-%d %H:%M:%S'),
                data_preview
            ])

        self.message_user(request, f"Exportadas {queryset.count()} sesiones a CSV.")
        return response

    export_sessions_csv.short_description = "📊 Exportar a CSV"

    def clear_expired_sessions(self, request, queryset):
        """
        Limpiar solo las sesiones expiradas
        """
        from django.utils import timezone

        expired_sessions = queryset.filter(expire_date__lte=timezone.now())
        deleted_count = expired_sessions.count()

        if deleted_count > 0:
            expired_sessions.delete()
            self.message_user(request, f"Eliminadas {deleted_count} sesiones expiradas.")
        else:
            self.message_user(request, "No hay sesiones expiradas para eliminar.")

    clear_expired_sessions.short_description = "🧹 Limpiar sesiones expiradas"

    def get_user_display(self, obj):
        """Muestra información del usuario de la sesión"""
        try:
            data = obj.get_decoded()
            user_id = data.get('_auth_user_id')
            if user_id:
                return f"Usuario {user_id}"
            else:
                return "Anónimo"
        except:
            return "Error"
    get_user_display.short_description = "Usuario"
    get_user_display.admin_order_field = "session_key"

    def get_status_display(self, obj):
        """Muestra el estado de la sesión"""
        from django.utils import timezone
        if obj.expire_date > timezone.now():
            return "Activa"
        else:
            return "Expirada"
    get_status_display.short_description = "Estado"
    get_status_display.admin_order_field = "expire_date"

    def get_session_data_preview(self, obj):
        """Muestra una vista previa de los datos de la sesión"""
        try:
            import json
            data = obj.get_decoded()
            if not data:
                return "Sin datos"
            preview = json.dumps(data, indent=2)[:150]
            if len(json.dumps(data, indent=2)) > 150:
                preview += "..."
            return preview
        except:
            return "Datos no disponibles"
    get_session_data_preview.short_description = "Vista previa de datos"

    def changelist_view(self, request, extra_context=None):
        """Vista personalizada para la lista de sesiones con estadísticas"""
        from django.utils import timezone

        response = super().changelist_view(request, extra_context)

        if hasattr(response, 'context_data'):
            context = response.context_data

            # Obtener queryset filtrado
            cl = context.get('cl')
            if cl:
                sessions = cl.get_queryset(request)
            else:
                sessions = self.get_queryset(request)

            # Aplicar filtros adicionales desde la URL
            status_filter = request.GET.get('status')
            auth_filter = request.GET.get('auth')
            q_filter = request.GET.get('q')

            if status_filter == 'active':
                sessions = sessions.filter(expire_date__gt=timezone.now())
            elif status_filter == 'expired':
                sessions = sessions.filter(expire_date__lte=timezone.now())

            if q_filter:
                sessions = sessions.filter(session_key__icontains=q_filter)

            # Procesar sesiones para agregar información adicional
            sessions_with_info = []
            active_sessions = 0
            expired_sessions = 0
            authenticated_sessions = 0

            for session in sessions:
                # Verificar si está expirada
                session.is_expired = session.expire_date <= timezone.now()
                if session.is_expired:
                    expired_sessions += 1
                else:
                    active_sessions += 1

                # Verificar si tiene usuario autenticado
                try:
                    data = session.get_decoded()
                    session.user_id = data.get('_auth_user_id')
                    if session.user_id:
                        authenticated_sessions += 1
                except:
                    session.user_id = None

                # Agregar preview de datos
                session.session_data_preview = self.get_session_data_preview(session)

                sessions_with_info.append(session)

            # Estadísticas totales
            total_sessions = Session.objects.count()
            total_active = Session.objects.filter(expire_date__gt=timezone.now()).count()
            total_expired = total_sessions - total_active
            total_authenticated = 0

            for s in Session.objects.all():
                try:
                    data = s.get_decoded()
                    if data.get('_auth_user_id'):
                        total_authenticated += 1
                except:
                    pass

            # Agregar datos al contexto
            context.update({
                'sessions': sessions_with_info,
                'active_sessions': total_active,
                'expired_sessions': total_expired,
                'authenticated_sessions': total_authenticated,
            })

        return response


# Asignar nuestro admin personalizado como el admin por defecto
admin.site = admin_site
