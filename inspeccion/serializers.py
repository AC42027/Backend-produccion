from rest_framework import serializers
from .models import AsignacionInspeccion, EquipoPlanificacion

class AsignacionInspeccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsignacionInspeccion
        fields = '__all__'

class EquipoPlanificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipoPlanificacion
        fields = '__all__'
