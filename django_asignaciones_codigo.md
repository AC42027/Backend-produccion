# Código Backend para Django (Asignaciones Semanales ASRS)

## 1. Modelo de Datos (`models.py`)

```python
from django.db import models

class AsignacionInspeccion(models.Model):
    fecha = models.DateField(help_text="Fecha de inicio de la semana (Lunes)")
    asociado = models.CharField(max_length=150)
    equipo = models.CharField(max_length=150)
    zona = models.CharField(max_length=150, blank=True, null=True)
    asignado_por = models.CharField(max_length=100, default='Admin')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['asociado', 'zona', 'equipo']
        unique_together = ('fecha', 'asociado', 'equipo')

    def __str__(self):
        return f"{self.fecha} - {self.asociado} - {self.equipo}"
```

## 2. Serializador (`serializers.py`)

```python
from rest_framework import serializers
from .models import AsignacionInspeccion

class AsignacionInspeccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsignacionInspeccion
        fields = '__all__'
```

## 3. Vista de API (`views.py`)

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import AsignacionInspeccion
from .serializers import AsignacionInspeccionSerializer

class AsignacionesView(APIView):
    def get(self, request):
        fecha_filtro = request.query_params.get('fecha', None)
        if fecha_filtro:
            asignaciones = AsignacionInspeccion.objects.filter(fecha=fecha_filtro)
        else:
            asignaciones = AsignacionInspeccion.objects.all()
            
        serializer = AsignacionInspeccionSerializer(asignaciones, many=True)
        return Response(serializer.data)

    def post(self, request):
        fecha = request.data.get('fecha')
        asignaciones_data = request.data.get('asignaciones', [])
        
        if not fecha:
            return Response({"error": "Falta el campo 'fecha'"}, status=status.HTTP_400_BAD_REQUEST)

        # Eliminar previas de esa semana
        AsignacionInspeccion.objects.filter(fecha=fecha).delete()

        nuevas_asignaciones = []
        for item in asignaciones_data:
            nuevas_asignaciones.append(AsignacionInspeccion(
                fecha=fecha,
                asociado=item.get('asociado'),
                equipo=item.get('equipo'),
                zona=item.get('zona'),
                asignado_por=request.data.get('asignado_por', 'Admin')
            ))
        
        AsignacionInspeccion.objects.bulk_create(nuevas_asignaciones)
        return Response({"status": "ok", "mensaje": f"Se guardaron {len(nuevas_asignaciones)} asignaciones"}, status=status.HTTP_201_CREATED)
```

## 4. Rutas (`urls.py`)

```python
from django.urls import path
from .views import AsignacionesView

urlpatterns = [
    path('api/asignaciones/', AsignacionesView.as_view(), name='asignaciones_api'),
]
```
