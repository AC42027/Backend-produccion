from django.urls import path
from .views import AsignacionesView
from . import views

urlpatterns = [
    path('api/asignaciones/', AsignacionesView.as_view(), name='asignaciones_api'),
    path('api/guardar/', views.guardar_inspeccion_individual, name='guardar_inspeccion'),
    path('api/divisiones/', views.listar_divisiones, name='listar_divisiones'),
    path('api/areas/', views.listar_areas, name='listar_areas'),
    path('api/zonas/', views.listar_zonas, name='listar_zonas'),
    path('api/equipos/', views.listar_equipos, name='listar_equipos'),
    path('api/equipo/<int:equipo_id>/', views.obtener_equipo, name='obtener_equipo'),
    path('api/categorias/', views.listar_categorias, name='listar_categorias'),
    path('api/preguntas/<str:categoria_nombre>/', views.obtener_preguntas_por_categoria, name='preguntas_por_categoria'),

    # 🚀 Dashboard
    path('api/dashboard/inspecciones/', views.inspecciones_dashboard, name='dashboard_inspecciones'),
    path('api/inspecciones/<int:inspeccion_id>/cerrar/', views.cerrar_inspeccion_sap, name='cerrar_inspeccion_sap'),

    # 🔐 Autenticación LDAP
    path('api/login-ldap/', views.login_ldap, name='login_ldap'),
    path('api/logout/', views.logout_view, name='logout_view'),
]
