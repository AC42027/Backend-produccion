import socket
from django.http import HttpResponseForbidden
from django.conf import settings

class RestringirIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip_cliente = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')

        # ✅ 0. Verificar si la ruta está exenta de restricción de IP
        rutas_exentas = getattr(settings, 'EXEMPT_IP_RESTRICTION_PATHS', [])
        if request.path in rutas_exentas:
            return self.get_response(request)

        if not ip_cliente:
            return HttpResponseForbidden("Acceso denegado: No se pudo identificar la IP.")

        # ✅ 1. Verificar IPs y Subredes fijas
        # Leemos la lista de settings, si no existe usamos un fallback vacío
        prefijos_permitidos = getattr(settings, 'ALLOWED_IP_PREFIXES', [])
        for prefijo in prefijos_permitidos:
            if ip_cliente.startswith(prefijo):
                return self.get_response(request)

        # ✅ 2. Verificar Equipos Dinámicos (Hostnames)
        hostnames_permitidos = getattr(settings, 'ALLOWED_DYNAMIC_HOSTNAMES', [])
        for hostname in hostnames_permitidos:
            try:
                # Consulta al DNS de la empresa qué IP tiene este equipo ahora mismo
                ip_resuelta = socket.gethostbyname(hostname)
                if ip_cliente == ip_resuelta:
                    return self.get_response(request)
            except socket.gaierror:
                # Si el DNS no encuentra ese equipo (ej. está apagado), ignora el error y prueba el siguiente
                continue 

        # ❌ 3. Si terminó de revisar ambas listas y no hubo coincidencia, se bloquea
        return HttpResponseForbidden("Acceso denegado: Dispositivo no autorizado.")