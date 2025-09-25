import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class RecomendadorIA:
    def __init__(self):
        # Dataset simulado: usuarios y productos comprados
        self.data = {
            'usuario': ['user1', 'user1', 'user2', 'user2', 'user3', 'user3'],
            'producto': ['laptop', 'mouse', 'laptop', 'auriculares', 'libro', 'mouse']
        }
        self.df = pd.DataFrame(self.data)
        self.matriz_usuario_producto = self._crear_matriz()

    def _crear_matriz(self):
        # Crear matriz usuario-producto
        usuarios = self.df['usuario'].unique()
        productos = self.df['producto'].unique()
        matriz = pd.DataFrame(0, index=usuarios, columns=productos)
        for _, row in self.df.iterrows():
            matriz.loc[row['usuario'], row['producto']] = 1
        return matriz

    def recomendar(self, usuario, top_n=2):
        if usuario not in self.matriz_usuario_producto.index:
            return ["Producto genérico 1", "Producto genérico 2"]  # Recomendaciones generales

        # Calcular similitud coseno entre usuarios
        similitudes = cosine_similarity(self.matriz_usuario_producto)
        similitudes_df = pd.DataFrame(similitudes, index=self.matriz_usuario_producto.index, columns=self.matriz_usuario_producto.index)

        # Encontrar usuarios similares
        usuarios_similares = similitudes_df[usuario].sort_values(ascending=False).index[1:]  # Excluir el mismo usuario

        # Recomendar productos que compraron usuarios similares pero no el usuario actual
        productos_usuario = set(self.matriz_usuario_producto.loc[usuario][self.matriz_usuario_producto.loc[usuario] == 1].index)
        recomendaciones = set()
        for u in usuarios_similares:
            productos_u = set(self.matriz_usuario_producto.loc[u][self.matriz_usuario_producto.loc[u] == 1].index)
            recomendaciones.update(productos_u - productos_usuario)
            if len(recomendaciones) >= top_n:
                break

        return list(recomendaciones)[:top_n]

# Ejemplo de uso
if __name__ == "__main__":
    rec = RecomendadorIA()
    print("Recomendaciones para user1:", rec.recomendar('user1'))
    print("Recomendaciones para user2:", rec.recomendar('user2'))