# Trabajo Práctico: Sistema de E-commerce con Recomendación de Productos

## 1. Selección del Sistema
Hemos elegido el sistema de **E-commerce: recomendación de productos a partir de compras previas**. Este sistema permite a los usuarios comprar productos en línea y recibir recomendaciones personalizadas basadas en su historial de compras, utilizando un módulo de IA simple.

## 2. Metodología Ágil
### Metodología Elegida: Scrum
Justificación: Scrum es una metodología ágil ampliamente utilizada en el desarrollo de software que permite gestionar proyectos complejos de manera iterativa e incremental. Es ideal para este trabajo práctico porque facilita la adaptación a cambios, la entrega de valor en cada iteración y la colaboración en equipo. Además, permite integrar fácilmente componentes de IA en el proceso de desarrollo.

### Roles
- **Product Owner (PO)**: Responsable de definir y priorizar las historias de usuario, asegurando que el producto cumpla con las necesidades del cliente. En este caso, el PO representaría al administrador del e-commerce.
- **Scrum Master**: Facilita el proceso Scrum, elimina impedimentos y asegura que el equipo siga las prácticas ágiles. Actúa como coach del equipo.
- **Development Team**: Equipo de desarrollo compuesto por programadores, diseñadores y testers que implementan las funcionalidades. En este trabajo, el equipo desarrollará el prototipo.

### Iteraciones (Sprints)
Los sprints serán de 2 semanas de duración, permitiendo entregas incrementales del producto. Cada sprint incluye:
- Sprint Planning: Planificación de las tareas a realizar.
- Daily Scrum: Reuniones diarias de 15 minutos para sincronizar el progreso.
- Sprint Review: Revisión del trabajo completado y feedback.
- Sprint Retrospective: Reflexión sobre el proceso para mejorar en el siguiente sprint.

### Flujo de Trabajo
1. Backlog del Producto: Lista de historias de usuario priorizadas.
2. Sprint Planning: Selección de historias para el sprint.
3. Desarrollo: Implementación de las funcionalidades.
4. Daily Scrum: Actualización diaria.
5. Sprint Review: Demostración del incremento.
6. Sprint Retrospective: Mejora continua.
7. Repetición para el siguiente sprint.

## 3. Análisis de Requisitos con Historias de Usuario

### Historias de Usuario
1. **Como usuario, quiero poder registrarme en el sistema para crear una cuenta y acceder a las funcionalidades.**
2. **Como usuario registrado, quiero iniciar sesión en el sistema para acceder a mi cuenta.**
3. **Como usuario, quiero buscar productos por nombre o categoría para encontrar lo que necesito.**
4. **Como usuario, quiero agregar productos al carrito de compras para prepararme para la compra.**
5. **Como usuario, quiero realizar una compra de los productos en mi carrito para adquirirlos.**
6. **Como usuario, quiero ver mi historial de compras para revisar mis adquisiciones anteriores.**
7. **Como usuario, quiero recibir recomendaciones de productos basados en mis compras anteriores para descubrir cosas que me interesen.** (Historia vinculada a IA)

### Casos de Uso Expandidos

#### Caso de Uso 1: Realizar una Compra
- **Nombre**: Realizar una Compra
- **Actores**: Usuario registrado
- **Precondiciones**: El usuario debe estar registrado e iniciar sesión. Debe tener productos en el carrito.
- **Postcondiciones**: La compra se registra en el historial del usuario, el inventario se actualiza, y se genera una confirmación.
- **Flujo Principal**:
  1. El usuario selecciona "Comprar" desde el carrito.
  2. El sistema muestra un resumen de la compra.
  3. El usuario confirma la compra.
  4. El sistema procesa el pago (simulado).
  5. El sistema actualiza el inventario y registra la compra en el historial.
  6. El sistema muestra una confirmación de compra.
- **Flujos Alternativos**:
  - Si el pago falla (simulado), el sistema informa al usuario y cancela la compra.
  - Si un producto no está disponible, el sistema informa y permite removerlo del carrito.

#### Caso de Uso 2: Recibir Recomendaciones de Productos
- **Nombre**: Recibir Recomendaciones de Productos
- **Actores**: Usuario registrado, Sistema de IA
- **Precondiciones**: El usuario debe tener al menos una compra previa registrada.
- **Postcondiciones**: El usuario recibe una lista de productos recomendados.
- **Flujo Principal**:
  1. El usuario accede a la página principal o de recomendaciones.
  2. El sistema analiza el historial de compras del usuario.
  3. El módulo de IA genera recomendaciones basadas en patrones de compras similares.
  4. El sistema muestra las recomendaciones al usuario.
- **Flujos Alternativos**:
  - Si el usuario no tiene historial suficiente, el sistema muestra recomendaciones generales.

## 4. Diseño del Sistema

### Diagrama de Clases
```
+----------------+     +----------------+
|     Usuario    |     |    Producto    |
+----------------+     +----------------+
| - id: int      |     | - id: int      |
| - nombre: str  |     | - nombre: str  |
| - email: str   |     | - precio: float|
| - password: str|     | - categoria: str|
+----------------+     +----------------+
| + registrar()  |     | + actualizar() |
| + login()      |     +----------------+
+----------------+
          |
          | 1..*
          |
+----------------+     +----------------+
|    Carrito     |     |    Compra      |
+----------------+     +----------------+
| - id: int      |     | - id: int      |
| - usuario_id: int|   | - usuario_id: int|
| - productos: list|   | - fecha: date  |
+----------------+     | - total: float |
| + agregar_prod()|     +----------------+
| + remover_prod()|
+----------------+
          |
          | 1
          |
+----------------+
|RecomendadorIA  |
+----------------+
| - modelo: obj  |
+----------------+
| + entrenar()   |
| + recomendar() |
+----------------+
```

### Diagrama ER
```
Usuario (id, nombre, email, password)
Producto (id, nombre, precio, categoria)
Compra (id, usuario_id, fecha, total)
Compra_Producto (compra_id, producto_id, cantidad)
```

### Arquitectura del Sistema
- **Capa de Presentación**: Interfaz de usuario (consola simple en este prototipo).
- **Capa de Lógica de Negocio**: Manejo de usuarios, productos, compras. Incluye el módulo de IA para recomendaciones.
- **Capa de Datos**: Almacenamiento en memoria (listas) o archivos CSV.

**Integración del Módulo IA**: El RecomendadorIA se integra en la capa de lógica, accediendo al historial de compras para generar recomendaciones. Se llama desde la interfaz cuando el usuario solicita recomendaciones.

### Mockups de Pantallas
1. **Pantalla de Inicio de Sesión**:
   ```
   Bienvenido al E-commerce
   Email: [___________]
   Password: [___________]
   [Iniciar Sesión] [Registrarse]
   ```

2. **Pantalla de Productos**:
   ```
   Productos Disponibles:
   1. Laptop - $1000 (Tecnología)
   2. Libro - $20 (Libros)
   [Buscar: ___________] [Agregar al Carrito: ID]
   ```

3. **Pantalla de Recomendaciones**:
   ```
   Recomendaciones para ti:
   Basado en tus compras previas...
   1. Mouse - $50 (Tecnología)
   2. Auriculares - $80 (Tecnología)
   ```

## 5. Módulo de Inteligencia Artificial
El módulo de IA implementa un sistema de recomendación simple basado en filtrado colaborativo. Utiliza similitud coseno para encontrar usuarios similares y recomendar productos que estos han comprado pero el usuario actual no.

**Qué hace**: Analiza el historial de compras de usuarios y genera recomendaciones personalizadas.

**Cómo funciona**: 
- Crea una matriz usuario-producto binaria.
- Calcula similitudes entre usuarios.
- Recomienda productos de usuarios similares no comprados por el usuario actual.

**Herramientas**: Python con pandas y scikit-learn. Dataset simulado en el código.

## 6. Frontend Web con Django
Se agregó un frontend web usando Django para una mejor experiencia de usuario:

- **Tecnologías**: Django 5.2.6, HTML/CSS básico.
- **Funcionalidades**:
  - Páginas: Inicio, Registro, Login, Productos, Compras, Recomendaciones.
  - Autenticación de usuarios.
  - Interfaz responsive básica.
- **Cómo ejecutar**: `python manage.py runserver` y acceder a http://127.0.0.1:8000.