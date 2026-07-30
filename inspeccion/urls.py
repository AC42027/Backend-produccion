from django.urls import path
from .views import AsignacionesView, EquipoPlanificacionView, EquipoSinQRList.as_view(), EquipoSinQRCreate.as_view()
from . import views

urlpatterns = [
    path('api/asignaciones/', AsignacionesView.as_view(), name='asignaciones_api'),
    path('api/asignaciones/<int:asignacion_id>/eliminar/', views.eliminar_asignacion, name='eliminar_asignacion'),
    path('api/guardar/', views.guardar_inspeccion_individual, name='guardar_inspeccion'),
    path('api/divisiones/', views.listar_divisiones, name='listar_divisiones'),
    path('api/areas/', views.listar_areas, name='listar_areas'),
    path('api/zonas/', views.listar_zonas, name='listar_zonas'),
    path('api/equipos/', views.listar_equipos, name='listar_equipos'),
    path('api/equipo/<int:equipo_id>/', views.obtener_equipo, name='obtener_equipo'),
    path('api/categorias/', views.listar_categorias, name='listar_categorias'),
    path('api/preguntas/<str:categoria_nombre>/', views.obtener_preguntas_por_categoria, name='preguntas_por_categoria'),
    path('api/dashboard/inspecciones/', views.inspecciones_dashboard, name='dashboard_inspecciones'),
    path('api/inspecciones/<int:inspeccion_id>/cerrar/', views.cerrar_inspeccion_sap, name='cerrar_inspeccion_sap'),
    path('api/login-ldap/', views.login_ldap, name='login_ldap'),
    path('api/logout/', views.logout_view, name='logout_view'),
    path('api/equipo/', EquipoPlanificacionView.as_view(), name='equipo_api'),
    # Nuevos endpoints para "Equipos sin QR"
    path('api/equipos-sin-qr/', EquipoSinQRList.as_view(), name='equipos_sin_qr_list'),
    path('api/equipos-sin-qr/<int:pk>/', EquipoSinQRDelete.as_view(), name='equipo_sin_qr_delete'),
]
