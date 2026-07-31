import secrets

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class EquipoSinQRAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.headers.get('X-API-Token', '')
        expected = getattr(settings, 'EQUIPO_SIN_QR_API_TOKEN', '')
        if token and expected and secrets.compare_digest(token, expected):
            user, _ = User.objects.get_or_create(username='api_equipo_sin_qr')
            return (user, None)
        raise AuthenticationFailed('Token de API inválido o ausente')
