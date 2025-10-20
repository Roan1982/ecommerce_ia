try:
    import pandas as pd
except Exception:
    pd = None

try:
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:
    cosine_similarity = None

try:
    import numpy as np
except Exception:
    np = None

# If sklearn is not available, provide a lightweight numpy-based fallback
if cosine_similarity is None:
    if np is not None:
        def _cosine_similarity(arr):
            # Accept pandas DataFrame or numpy array
            try:
                mat = arr.values if hasattr(arr, 'values') else np.array(arr)
            except Exception:
                mat = np.array(arr)

            # compute norms
            norms = np.linalg.norm(mat, axis=1)
            # avoid division by zero
            norms[norms == 0] = 1.0
            sim = mat.dot(mat.T) / (norms[:, None] * norms[None, :])
            return sim

        cosine_similarity = _cosine_similarity
    else:
        # Last-resort fallback: return identity-like similarity using pure python
        def _cosine_similarity_py(arr):
            # Try to get number of rows
            try:
                n = len(arr)
            except Exception:
                n = 0
            return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

        cosine_similarity = _cosine_similarity_py
from django.db import models
from .models import Pedido, PedidoProducto, Producto, User

class RecomendadorIA:
    def __init__(self):
        self.matriz_usuario_producto = None
        self.productos_dict = {}
        # No cargar datos en tiempo de import para evitar dependencias pesadas
        # Carga de datos cuando se necesite (primera llamada a recomendar o manualmente).
        self.df = None

    def _cargar_datos_reales(self):
        """Carga datos reales de compras desde la base de datos"""
        try:
            # Obtener todos los pedidos completados
            pedidos = Pedido.objects.filter(estado__in=['pagado', 'enviado', 'entregado'])

            # También obtener compras directas del modelo Compra
            from .models import Compra, CompraProducto
            compras_directas = Compra.objects.all()

            # Crear lista de interacciones usuario-producto
            interacciones = []
            usuarios_unicos = set()
            productos_unicos = set()

            # Procesar pedidos
            for pedido in pedidos:
                usuario_id = f"user_{pedido.usuario.id}"
                usuarios_unicos.add(usuario_id)

                productos_pedido = PedidoProducto.objects.filter(pedido=pedido)
                for prod_pedido in productos_pedido:
                    producto_id = f"prod_{prod_pedido.producto.id}"
                    productos_unicos.add(producto_id)

                    # Agregar múltiples entradas si la cantidad es mayor a 1 (para dar más peso)
                    for _ in range(prod_pedido.cantidad):
                        interacciones.append({
                            'usuario': usuario_id,
                            'producto': producto_id
                        })

                    # Guardar información del producto
                    self.productos_dict[producto_id] = {
                        'id': prod_pedido.producto.id,
                        'nombre': prod_pedido.producto.nombre,
                        'categoria': prod_pedido.producto.categoria
                    }

            # Procesar compras directas
            for compra in compras_directas:
                usuario_id = f"user_{compra.usuario.id}"
                usuarios_unicos.add(usuario_id)

                productos_compra = CompraProducto.objects.filter(compra=compra)
                for prod_compra in productos_compra:
                    producto_id = f"prod_{prod_compra.producto.id}"
                    productos_unicos.add(producto_id)

                    # Agregar múltiples entradas si la cantidad es mayor a 1
                    for _ in range(prod_compra.cantidad):
                        interacciones.append({
                            'usuario': usuario_id,
                            'producto': producto_id
                        })

                    # Guardar información del producto (si no existe ya)
                    if producto_id not in self.productos_dict:
                        self.productos_dict[producto_id] = {
                            'id': prod_compra.producto.id,
                            'nombre': prod_compra.producto.nombre,
                            'categoria': prod_compra.producto.categoria
                        }


            if not interacciones:
                # Si no hay pedidos ni compras, usar datos simulados como fallback
                self._usar_datos_simulados()
                return

            # Asegurarse de que pandas esté disponible
            if pd is None:
                raise RuntimeError('pandas no está instalado en el entorno')

            # Crear DataFrame
            self.df = pd.DataFrame(interacciones)

            # Crear matriz usuario-producto
            usuarios = list(usuarios_unicos)
            productos = list(productos_unicos)
            self.matriz_usuario_producto = pd.DataFrame(0, index=usuarios, columns=productos)

            # Llenar la matriz con las interacciones
            for _, row in self.df.iterrows():
                self.matriz_usuario_producto.loc[row['usuario'], row['producto']] += 1

        except Exception as e:
            print(f"Error cargando datos reales: {e}")
            self._usar_datos_simulados()

    def _usar_datos_simulados(self):
        """Fallback a datos simulados si no hay datos reales"""
        self.data = {
            'usuario': ['user1', 'user1', 'user2', 'user2', 'user3', 'user3'],
            'producto': ['laptop', 'mouse', 'laptop', 'auriculares', 'libro', 'mouse']
        }
        if pd is None:
            # Si pandas no está disponible, construir estructura mínima usando listas
            # para permitir que el recomendador funcione parcialmente.
            self.df = None
            # crear matriz básica
            usuarios = list({u for u in self.data['usuario']})
            productos = list({p for p in self.data['producto']})
            # matriz simulada usando dict of dicts
            matriz = {u: {p: 0 for p in productos} for u in usuarios}
            for u, p in zip(self.data['usuario'], self.data['producto']):
                matriz[u][p] = 1
            # guardar estructura mínima que usan otras funciones
            self.matriz_usuario_producto = None
        else:
            self.df = pd.DataFrame(self.data)
            self.matriz_usuario_producto = self._crear_matriz()
        self.matriz_usuario_producto = self._crear_matriz()
        self.productos_dict = {
            'laptop': {'id': 1, 'nombre': 'Laptop', 'categoria': 'Tecnología'},
            'mouse': {'id': 2, 'nombre': 'Mouse', 'categoria': 'Tecnología'},
            'auriculares': {'id': 4, 'nombre': 'Auriculares', 'categoria': 'Tecnología'},
            'libro': {'id': 3, 'nombre': 'Libro', 'categoria': 'Libros'}
        }

    def _crear_matriz(self):
        """Crear matriz usuario-producto para datos simulados"""
        if pd is None:
            return None
        usuarios = self.df['usuario'].unique()
        productos = self.df['producto'].unique()
        matriz = pd.DataFrame(0, index=usuarios, columns=productos)
        for _, row in self.df.iterrows():
            matriz.loc[row['usuario'], row['producto']] = 1
        return matriz

    def recomendar(self, usuario, top_n=4):
        """Recomendar productos basados en compras similares"""
        if self.matriz_usuario_producto is None or self.matriz_usuario_producto.empty:
            return self._recomendaciones_generales(top_n)

        usuario_id = f"user_{usuario.id}"

        # Si el usuario no tiene compras previas, mostrar recomendaciones generales
        if usuario_id not in self.matriz_usuario_producto.index:
            return self._recomendaciones_generales(top_n)

        try:
            # Calcular similitud coseno entre usuarios
            similitudes = cosine_similarity(self.matriz_usuario_producto)
            similitudes_df = pd.DataFrame(
                similitudes,
                index=self.matriz_usuario_producto.index,
                columns=self.matriz_usuario_producto.index
            )

            # Encontrar usuarios similares (excluir el mismo usuario)
            if usuario_id in similitudes_df.columns:
                usuarios_similares = similitudes_df[usuario_id].sort_values(ascending=False).index[1:]
            else:
                return self._recomendaciones_generales(top_n)

            # Obtener productos que ha comprado el usuario actual
            productos_usuario = set()
            if usuario_id in self.matriz_usuario_producto.index:
                productos_usuario = set(
                    self.matriz_usuario_producto.loc[usuario_id][
                        self.matriz_usuario_producto.loc[usuario_id] > 0
                    ].index
                )

            # Recomendar productos que compraron usuarios similares pero no el usuario actual
            recomendaciones = {}
            for u in usuarios_similares[:5]:  # Considerar solo los 5 usuarios más similares
                if u in self.matriz_usuario_producto.index:
                    productos_u = self.matriz_usuario_producto.loc[u]
                    productos_similares = productos_u[productos_u > 0].index

                    for prod in productos_similares:
                        if prod not in productos_usuario:
                            # Calcular score basado en similitud y frecuencia
                            similitud = similitudes_df.loc[usuario_id, u]
                            frecuencia = productos_u[prod]
                            score = similitud * frecuencia

                            if prod not in recomendaciones:
                                recomendaciones[prod] = score
                            else:
                                recomendaciones[prod] = max(recomendaciones[prod], score)

            # Ordenar por score y tomar top_n
            recomendaciones_ordenadas = sorted(
                recomendaciones.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]

            # Convertir IDs de productos a objetos Producto
            productos_recomendados = []
            for prod_id, score in recomendaciones_ordenadas:
                if prod_id in self.productos_dict:
                    prod_info = self.productos_dict[prod_id]
                    try:
                        producto = Producto.objects.get(id=prod_info['id'])
                        productos_recomendados.append({
                            'producto': producto,
                            'score': score,
                            'razon': f"Usuarios similares compraron este producto"
                        })
                    except Producto.DoesNotExist:
                        continue

            return productos_recomendados

        except Exception as e:
            print(f"Error en recomendaciones: {e}")
            return self._recomendaciones_generales(top_n)

    def _recomendaciones_generales(self, top_n=4):
        """Recomendaciones generales cuando no hay suficientes datos"""
        try:
            # Obtener productos populares (más vendidos)
            productos_populares = Producto.objects.filter(stock__gt=0).order_by('-stock')[:top_n]

            recomendaciones = []
            for producto in productos_populares:
                recomendaciones.append({
                    'producto': producto,
                    'score': 0.5,
                    'razon': "Producto popular"
                })

            return recomendaciones

        except Exception as e:
            print(f"Error en recomendaciones generales: {e}")
            return []

    def actualizar_datos(self):
        """Actualizar la matriz con los datos más recientes"""
        self._cargar_datos_reales()