from rest_framework import serializers
from .models import AsignacionInspeccion

class AsignacionInspeccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsignacionInspeccion
        fields = '__all__'
