from rest_framework import serializers
from .models import AsignacionInspeccion, EquipoPlanificacion, EquipoSinQR

class AsignacionInspeccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsignacionInspeccion
        fields = '__all__'

class EquipoPlanificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipoPlanificacion
        fields = '__all__'

class EquipoSinQRSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipoSinQR
        fields = '__all__'
