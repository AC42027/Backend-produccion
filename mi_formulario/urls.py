from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('inspeccion.urls')),
]

# Esto sirve archivos estáticos incluso con DEBUG = False
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
