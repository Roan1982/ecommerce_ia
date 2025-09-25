from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('registro/', views.registro, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('productos/', views.productos, name='productos'),
    path('comprar/<int:producto_id>/', views.comprar, name='comprar'),
    path('recomendaciones/', views.recomendaciones, name='recomendaciones'),
]