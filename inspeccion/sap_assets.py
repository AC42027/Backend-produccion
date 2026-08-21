"""
sap_assets.py
-------------
Cliente para la API de activos SAP (árbol de equipos de la planta).
URL configurable en .env via SAP_ASSETS_API_URL (default http://10.107.194.110:8081)

Endpoints utilizados:
  GET /api/search/assets/{query} -> [{id, descript, type}]   (type: EQ=Equipo, FL=Ubicación Técnica)
  GET /api/equipment/{equnr}     -> {equnr, descripcion, parent(=TPLNR), ...}
  GET /api/location/{tplnr}      -> {tplnr, descripcion, ...}
  GET /api/export                -> {equipos, ubicaciones, jerarquia, ...} (fallback cacheado)
"""

import logging
from urllib.parse import quote

import requests
from decouple import config
from django.core.cache import cache

logger = logging.getLogger(__name__)

ASSETS_API_URL = config('SAP_ASSETS_API_URL', default='http://10.107.194.110:8081')
TIMEOUT = 8
EXPORT_CACHE_KEY = 'sap_assets_export'
EXPORT_CACHE_TTL = 60 * 60 * 6  # 6 horas


class SapAssetsError(Exception):
    """Error consultando la API de activos SAP."""


def _get(path):
    try:
        resp = requests.get(f"{ASSETS_API_URL}{path}", timeout=TIMEOUT)
    except requests.exceptions.Timeout as e:
        raise SapAssetsError(f"Timeout consultando {path}") from e
    except requests.exceptions.RequestException as e:
        raise SapAssetsError(f"Error de conexión con la API de activos SAP: {e}") from e
    if resp.status_code != 200:
        raise SapAssetsError(f"HTTP {resp.status_code} en {path}")
    try:
        return resp.json()
    except ValueError as e:
        raise SapAssetsError(f"Respuesta no válida de la API de activos: {e}") from e


def buscar_activos(query):
    """Busca equipos y ubicaciones técnicas por texto. Retorna [{id, descript, type}]."""
    return _get(f"/api/search/assets/{quote(query, safe='')}")


def obtener_equipo(equnr):
    """
    Detalle de un equipo por EQUNR.
    La API no resuelve IDs con '/' en la ruta (%2F tampoco funciona),
    por lo que esos casos se resuelven contra /api/export (cacheado).
    """
    equnr = (equnr or '').strip()
    if '/' not in equnr:
        return _get(f"/api/equipment/{quote(equnr, safe='')}")
    nodo = _buscar_en_jerarquia(equnr)
    if nodo is None:
        raise SapAssetsError(f"Equipo '{equnr}' no encontrado en el árbol SAP")
    # Normalizar al formato del endpoint /api/equipment/
    return {
        'equnr': nodo.get('id_hijo', '') or equnr,
        'descripcion': _descripcion_desde_export(equnr),
        'parent': nodo.get('id_padre'),
    }


def obtener_ubicacion(tplnr):
    """Detalle de una ubicación técnica por TPLNR."""
    return _get(f"/api/location/{quote((tplnr or '').strip(), safe='')}")


def _get_export():
    data = cache.get(EXPORT_CACHE_KEY)
    if data is None:
        data = _get('/api/export')
        cache.set(EXPORT_CACHE_KEY, data, EXPORT_CACHE_TTL)
    return data


def _buscar_en_jerarquia(asset_id):
    """
    Busca un activo por ID exacto dentro de la jerarquía completa (fallback).
    El array 'jerarquia' usa las claves id_hijo / id_padre / tipo_hijo.
    """
    try:
        export = _get_export()
    except SapAssetsError:
        return None
    for nodo in export.get('jerarquia', []):
        if str(nodo.get('id_hijo', '')) == asset_id:
            return nodo
    return None


def _descripcion_desde_export(equnr):
    """Obtiene la descripción de un equipo desde la lista 'equipos' del export."""
    try:
        export = _get_export()
    except SapAssetsError:
        return ''
    for eq in export.get('equipos', []):
        if str(eq.get('equnr', '')) == equnr:
            return eq.get('descripcion', '') or ''
    return ''


# ── Auto-match ───────────────────────────────────────────────────────────────

def _consultas(nombre):
    """Genera consultas ordenadas por especificidad a partir del nombre."""
    import re
    limpio = re.sub(r'[^A-Za-z0-9]+', ' ', nombre or '').strip()
    partes = [p for p in limpio.split() if p]
    consultas = []
    # Token más significativo primero (el sufijo numérico/alfanumérico)
    for parte in reversed(partes):
        if re.search(r'\d', parte):
            consultas.append(parte)
    for parte in partes:
        if parte not in consultas and len(parte) >= 2:
            consultas.append(parte)
    if not consultas and (nombre or '').strip():
        consultas.append(nombre.strip())
    return consultas


def _tokens(nombre):
    """Tokens alfanuméricos del nombre, en mayúsculas."""
    import re
    limpio = re.sub(r'[^A-Za-z0-9]+', ' ', nombre or '').strip().upper()
    return [p for p in limpio.split() if p]


def _es_gabinete(item):
    """True si el activo es un gabinete compartido (id CH-GB-* o desc GABINETE)."""
    tokens = _tokens(f"{item.get('id', '')} {item.get('descript', '')}")
    return 'GB' in tokens or 'GAB' in tokens or 'GABINETE' in tokens


def auto_match(nombre):
    """
    Resuelve automáticamente los datos SAP de un equipo a partir de su nombre.
    Prueba los tokens del nombre ordenados por especificidad; la primera
    consulta con resultados decide y se toma el primer candidato tipo EQ.
    Los gabinetes compartidos solo se usan si son la única opción o si el
    nombre del equipo menciona un gabinete (GB/GAB).
    Retorna dict {equnr, equnr_desc, tplnr, tplnr_desc} o None si no hay
    coincidencia o falla la API.
    """
    menciona_gab = any(t in ('GB', 'GAB', 'GABINETE') for t in _tokens(nombre))
    for consulta in _consultas(nombre):
        try:
            items = buscar_activos(consulta)
        except SapAssetsError as e:
            logger.warning('auto_match: error buscando "%s": %s', consulta, e)
            return None  # API caída: mejor abortar que asignar a medias
        candidatos = [i for i in (items or []) if i.get('type') == 'EQ']
        if not candidatos:
            continue  # sin resultados: probar con el siguiente token

        if not menciona_gab:
            especificos = [c for c in candidatos if not _es_gabinete(c)]
            if especificos:
                candidatos = especificos

        elegido = candidatos[0]
        try:
            detalle = obtener_equipo(elegido['id'])
        except SapAssetsError as e:
            logger.warning('auto_match: error resolviendo %s: %s', elegido['id'], e)
            return None

        tplnr = (detalle.get('parent') or '').strip()
        tplnr_desc = ''
        if tplnr:
            try:
                tplnr_desc = obtener_ubicacion(tplnr).get('descripcion', '') or ''
            except SapAssetsError:
                pass  # descripción es opcional; el TPLNR ya está resuelto

        return {
            'equnr': detalle.get('equnr', '') or elegido['id'],
            'equnr_desc': detalle.get('descripcion', '') or elegido.get('descript', ''),
            'tplnr': tplnr,
            'tplnr_desc': tplnr_desc,
        }
    return None
