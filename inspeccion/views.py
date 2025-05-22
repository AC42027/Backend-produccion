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
    InspeccionTecnico, PreguntaTecnica, UbicacionFisica, Owner
)

import json
from datetime import datetime

@csrf_exempt
def login_ldap(request):
    if request.method == 'POST':
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
            return JsonResponse({
                'status': 'ok',
                'message': 'Login exitoso',
                'first_name': user.first_name,
                'last_name': user.last_name,
            })
        else:
            return JsonResponse({'status': 'error', 'message': 'Credenciales inválidas'})

@csrf_exempt
def logout_view(request):
    logout(request)
    return JsonResponse({'status': 'ok', 'message': 'Sesión cerrada'})

@csrf_exempt
def guardar_inspeccion_individual(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            division = Division.objects.get(id=data['division'])
            area = Area.objects.get(id=data['area'])
            zona = Zona.objects.get(id=data['zona'])
            equipo = Equipo.objects.get(id=data['equipo'])

            hora_inicio = parse_time(data['horaInicio'])
            hora_fin = parse_time(data['horaFin'])

            inspeccion = Inspeccion.objects.create(
                fecha=data['fecha'],
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                division=division,
                area=area,
                zona=zona,
                equipo=equipo,
                observaciones=data.get('observaciones', '')
            )

            for descripcion, estado in data.get('tecnicos', {}).items():
                InspeccionTecnico.objects.create(
                    inspeccion=inspeccion,
                    descripcion=descripcion,
                    estado=estado
                )

            return JsonResponse({'status': 'ok', 'message': 'Inspección guardada'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

def parse_time(hora_str):
    formatos = ['%H:%M:%S', '%I:%M:%S %p']
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
    inspecciones = Inspeccion.objects.select_related('division', 'area', 'zona', 'equipo__owner').all()
    data = []

    for ins in inspecciones:
        tecnicos = InspeccionTecnico.objects.filter(inspeccion=ins).values('descripcion', 'estado')
        data.append({
            'id': ins.id,
            'fecha': ins.fecha.strftime('%Y-%m-%d'),
            'horaInicio': ins.hora_inicio.strftime('%H:%M'),
            'horaFin': ins.hora_fin.strftime('%H:%M'),
            'division': ins.division.nombre,
            'area': ins.area.nombre,
            'zona': ins.zona.nombre,
            'equipo': ins.equipo.nombre,
            'owner': ins.equipo.owner.nombre if ins.equipo.owner else '',
            'observaciones': ins.observaciones,
            'tecnicos': list(tecnicos),
        })

    return JsonResponse(data, safe=False)
