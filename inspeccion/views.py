import logging
import json
from datetime import datetime
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .ldap_auth import autenticar_usuario

from .models import (
    Division, Area, Zona, Equipo, Inspeccion, Categoria,
    InspeccionTecnico, PreguntaTecnica, UbicacionFisica, Owner,
    AsignacionInspeccion, EquipoPlanificacion
)
from .serializers import AsignacionInspeccionSerializer
from .sap_connector import crear_notificacion_sap, cerrar_notificacion_sap
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


@csrf_exempt
def login_ldap(request):
    # ✅ FIX CORS PREFLIGHT: Next.js siempre envía una petición 'OPTIONS' antes del POST
    # para verificar permisos. Si le devolvemos error aquí, Next.js cancela todo y da "Acceso denegado".
    if request.method == 'OPTIONS':
        return JsonResponse({'status': 'ok'})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')

            auth_result = autenticar_usuario(username, password)

            if auth_result.get('success'):
                user, created = User.objects.get_or_create(username=username)
                user.first_name = auth_result.get('first_name', '')
                user.last_name = auth_result.get('last_name', '')
                user.email = auth_result.get('email', '')
                user.save()
                login(request, user)

                is_admin = user.is_staff or user.is_superuser or user.username in ['ac18958', 'ac17157']
                full_name = f"{user.first_name} {user.last_name}".strip()
                return JsonResponse({
                    'status': 'ok',
                    'message': 'Login exitoso',
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': full_name,
                    'is_admin': is_admin,
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Credenciales inválidas'}, status=401)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Formato JSON inválido'}, status=400)

    # Si alguien intenta entrar con GET (como desde el navegador), respondemos en JSON
    return JsonResponse({'status': 'error', 'message': 'Método no permitido. Se requiere POST.'}, status=405)


@csrf_exempt
def logout_view(request):
    logout(request)
    return JsonResponse({'status': 'ok', 'message': 'Sesión cerrada'})


@csrf_exempt
def guardar_inspeccion_individual(request):
    # ✅ FIX CORS PREFLIGHT también aquí por si acaso
    if request.method == 'OPTIONS':
        return JsonResponse({'status': 'ok'})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.warning(f"[Guardar] Payload recibido: {data}")

            # ✅ CAPTURAR EL OWNER: Aquí recibimos el "ac17157" del frontend
            owner_ldap = data.get('owner', '')

            division = Division.objects.get(id=data['division'])
            area     = Area.objects.get(id=data['area'])
            zona     = Zona.objects.get(id=data['zona'])
            equipo   = Equipo.objects.get(id=data['equipo'])
            hora_inicio_parseada = parse_time(data['horaInicio'])

            # ──────────────────────────────────────────────────────────────────
            # 🛡️ GUARD ANTI-DUPLICADO con bloqueo de BD (select_for_update)
            #
            # Problema: si el usuario envía el formulario dos veces (doble clic,
            # error de red + retry, frontend lento), ambas peticiones llegan al
            # servidor y cada una crea una inspección + llama a SAP → dos avisos.
            # (Ejemplo: aviso 7000105188 se duplicó por este motivo)
            #
            # Solución: dentro de una transacción atómica, buscamos si ya existe
            # una inspección con la misma clave natural (equipo + fecha + owner +
            # hora_inicio). Si existe → devolvemos ese resultado sin crear nada.
            # select_for_update bloquea la fila para que dos requests simultáneos
            # no pasen el guard al mismo tiempo (condición de carrera).
            # ──────────────────────────────────────────────────────────────────
            with transaction.atomic():
                inspeccion_existente = (
                    Inspeccion.objects
                    .select_for_update()
                    .filter(
                        equipo=equipo,
                        fecha=data['fecha'],
                        owner=owner_ldap,
                        hora_inicio=hora_inicio_parseada,
                    )
                    .order_by('-id')
                    .first()
                )

                if inspeccion_existente is not None:
                    logger.warning(
                        f"[SAP Guard] Duplicado bloqueado: equipo={equipo.id} "
                        f"fecha={data['fecha']} owner={owner_ldap} "
                        f"hora={hora_inicio_parseada} → id existente={inspeccion_existente.id} "
                        f"SAP={inspeccion_existente.sap_nr_numero or 'sin aviso'}"
                    )
                    return JsonResponse({
                        'status': 'ok',
                        'message': 'Inspección ya registrada (evitando duplicado)',
                        'sap_nr': inspeccion_existente.sap_nr_numero or '',
                        'sap_status': inspeccion_existente.sap_nr_status or '',
                        'sap_mensaje': f'Aviso SAP ya existente: {inspeccion_existente.sap_nr_numero or "sin aviso"}',
                    })

                # ── Crear la inspección dentro de la misma transacción ────────
                inspeccion = Inspeccion.objects.create(
                    fecha=data['fecha'],
                    hora_inicio=hora_inicio_parseada,
                    hora_fin=parse_time(data['horaFin']),
                    division=division,
                    area=area,
                    zona=zona,
                    equipo=equipo,
                    observaciones=data.get('observaciones', ''),
                    sap_equnr=data.get('sap_equnr', ''),
                    sap_equnr_desc=data.get('sap_equnr_desc', ''),
                    sap_tplnr=data.get('sap_tplnr', ''),
                    sap_puesto_trabajo=data.get('sap_puesto_trabajo', ''),
                    comentario_hallazgo=data.get('comentario_hallazgo', ''),
                    owner=owner_ldap
                )
            # ── Fin bloque atómico ─────────────────────────────────────────────

            tecnicos_data    = data.get('tecnicos', {})
            comentarios_data = data.get('observacionesTecnicas', {})
            criticos_data    = data.get('criticos', {})

            for descripcion, estado in tecnicos_data.items():
                InspeccionTecnico.objects.create(
                    inspeccion=inspeccion,
                    descripcion=descripcion,
                    estado=estado,
                    comentario=comentarios_data.get(descripcion, ''),
                    es_critico=criticos_data.get(descripcion, False)
                )

            # --- Integración SAP PM: crear Notificación NR (IW21) ---
            # Solo crear aviso SAP si hay al menos un hallazgo NOK o un ítem
            # crítico, Y si todavía no tiene un número de aviso asignado.
            tiene_hallazgo = any(
                estado == 'NOK' for estado in tecnicos_data.values()
            ) or any(
                criticos_data.get(desc, False) for desc in tecnicos_data.keys()
            )

            if tiene_hallazgo and not inspeccion.sap_nr_numero:
                nr_result = crear_notificacion_sap(inspeccion)
                inspeccion.sap_nr_numero = nr_result.get('nr_numero', '')
                inspeccion.sap_nr_status = nr_result.get('status', 'error')
                inspeccion.save(update_fields=['sap_nr_numero', 'sap_nr_status'])
            else:
                nr_result = {}

            return JsonResponse({
                'status': 'ok',
                'message': 'Inspección guardada',
                'sap_nr': inspeccion.sap_nr_numero or '',
                'sap_status': inspeccion.sap_nr_status or '',
                'sap_mensaje': nr_result.get('mensaje', 'Sin hallazgos NOK/Críticos, no se creó aviso SAP.'),
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})


def parse_time(hora_str):
    formatos = ['%H:%M:%S', '%I:%M:%S %p', '%H:%M']
    for fmt in formatos:
        try:
            return datetime.strptime(hora_str, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Hora inválida: {hora_str}")


def listar_divisiones(request):
    return JsonResponse(list(Division.objects.values('id', 'nombre')), safe=False)


def listar_areas(request):
    return JsonResponse(list(Area.objects.values('id', 'nombre')), safe=False)


def listar_zonas(request):
    return JsonResponse(list(Zona.objects.values('id', 'nombre')), safe=False)


def listar_categorias(request):
    return JsonResponse(list(Categoria.objects.values('id', 'nombre')), safe=False)


def listar_equipos(request):
    equipos = Equipo.objects.select_related(
        'ubicacion', 'categoria', 'zona', 'area', 'division', 'owner'
    ).all()
    data = [
        {
            'id': e.id,
            'nombre': e.nombre,
            'ubicacion': e.ubicacion.descripcion if e.ubicacion else '',
            'categoria': e.categoria.nombre if e.categoria else '',
            'categoria_id': e.categoria.id if e.categoria else None,
            'zona': e.zona.nombre if e.zona else '',
            'zona_id': e.zona.id if e.zona else None,
            'area': e.area.nombre if e.area else '',
            'area_id': e.area.id if e.area else None,
            'division': e.division.nombre if e.division else '',
            'division_id': e.division.id if e.division else None,
            'owner': e.owner.nombre if e.owner else ''
        }
        for e in equipos
    ]
    return JsonResponse(data, safe=False)


def obtener_equipo(request, equipo_id):
    equipo = get_object_or_404(
        Equipo.objects.select_related(
            'ubicacion', 'categoria', 'zona', 'area', 'division', 'owner'
        ),
        id=equipo_id
    )
    return JsonResponse({
        'id': equipo.id,
        'nombre': equipo.nombre,
        'ubicacion': equipo.ubicacion.descripcion if equipo.ubicacion else '',
        'categoria': equipo.categoria.nombre if equipo.categoria else '',
        'zona': equipo.zona.nombre if equipo.zona else '',
        'area': equipo.area.nombre if equipo.area else '',
        'division': equipo.division.nombre if equipo.division else '',
        'owner': equipo.owner.nombre if equipo.owner else ''
    })


def obtener_preguntas_por_categoria(request, categoria_nombre):
    preguntas = PreguntaTecnica.objects.filter(categoria__nombre=categoria_nombre)
    data = list(preguntas.values('id', 'descripcion'))
    return JsonResponse(data, safe=False)


def inspecciones_dashboard(request):
    inspecciones = Inspeccion.objects.select_related('division', 'area', 'zona', 'equipo').all()
    data = []

    for ins in inspecciones:
        tecnicos = InspeccionTecnico.objects.filter(inspeccion=ins).values('descripcion', 'estado', 'comentario', 'es_critico')
        
        # Obtener nombre completo del owner si está registrado en los usuarios de Django (LDAP)
        owner_str = ins.owner if hasattr(ins, 'owner') and ins.owner else ''
        if owner_str:
            user_obj = User.objects.filter(username=owner_str).first()
            if user_obj and (user_obj.first_name or user_obj.last_name):
                owner_str = f"{owner_str} ({user_obj.first_name} {user_obj.last_name})".strip()

        data.append({
            'id': ins.id,
            'fecha': ins.fecha.strftime('%Y-%m-%d'),
            'horaInicio': ins.hora_inicio.strftime('%H:%M'),
            'horaFin': ins.hora_fin.strftime('%H:%M'),
            'division': ins.division.nombre,
            'area': ins.area.nombre,
            'zona': ins.zona.nombre,
            'equipo': ins.equipo.nombre,
            'owner': owner_str,
            'observaciones': ins.observaciones,
            'tecnicos': list(tecnicos),
            # Campos SAP PM
            'sap_nr_numero': ins.sap_nr_numero or '',
            'sap_nr_status': ins.sap_nr_status or '',
            'sap_equnr': ins.sap_equnr or '',
            'sap_tplnr': ins.sap_tplnr or '',
            'sap_puesto_trabajo': ins.sap_puesto_trabajo or '',
        })

    return JsonResponse(data, safe=False)


class AsignacionesView(APIView):
    def get(self, request):
        mes = request.query_params.get('mes', None)
        fecha = request.query_params.get('fecha', None)

        if mes:
            try:
                año, mes_num = mes.split('-')
                asignaciones = AsignacionInspeccion.objects.filter(
                    fecha__year=año, fecha__month=mes_num
                )
            except (ValueError, IndexError):
                return Response({"error": "Formato de mes inválido. Use YYYY-MM"}, status=status.HTTP_400_BAD_REQUEST)
        elif fecha:
            asignaciones = AsignacionInspeccion.objects.filter(fecha=fecha)
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


@csrf_exempt
def eliminar_asignacion(request, asignacion_id):
    if request.method == 'OPTIONS':
        return JsonResponse({'status': 'ok'})
    if request.method == 'DELETE':
        try:
            asignacion = get_object_or_404(AsignacionInspeccion, id=asignacion_id)
            asignacion.delete()
            return JsonResponse({'status': 'ok', 'message': 'Asignación eliminada'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)


@csrf_exempt
def cerrar_inspeccion_sap(request, inspeccion_id):
    """
    Endpoint para solicitar el cierre de una notificación de SAP.
    """
    if request.method == 'OPTIONS':
        return JsonResponse({'status': 'ok'})

    if request.method == 'POST':
        inspeccion = get_object_or_404(Inspeccion, id=inspeccion_id)
        if not inspeccion.sap_nr_numero:
            return JsonResponse({'status': 'error', 'message': 'Esta inspección no tiene un aviso de SAP asociado.'}, status=400)

        res = cerrar_notificacion_sap(inspeccion)
        if res.get('status') == 'ok':
            inspeccion.sap_nr_status = 'cerrada'
            inspeccion.save(update_fields=['sap_nr_status'])
            return JsonResponse({'status': 'ok', 'message': res.get('mensaje')})
        else:
            return JsonResponse({'status': 'error', 'message': res.get('mensaje')}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido. Se requiere POST.'}, status=405)


class EquipoPlanificacionView(APIView):
    def get(self, request):
        equipo, _ = EquipoPlanificacion.objects.get_or_create(pk=1)
        return Response({'nombres': equipo.lista_nombres})

    def put(self, request):
        equipo, _ = EquipoPlanificacion.objects.get_or_create(pk=1)
        nombres = request.data.get('nombres', [])
        if not isinstance(nombres, list):
            return Response({'error': 'nombres debe ser una lista'}, status=status.HTTP_400_BAD_REQUEST)
        equipo.lista_nombres = nombres
        equipo.save()
        return Response({'nombres': equipo.lista_nombres})
