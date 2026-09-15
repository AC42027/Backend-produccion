"""
resumen_semanal
---------------
Calcula las métricas de la última semana de inspecciones técnicas cerrada y
envía una tarjeta AdaptiveCard al chat de Teams mediante el webhook de Power
Automate.

Semana de referencia
--------------------
La semana NO se asume Lunes-Domingo ni Lunes-Sábado. Se deriva de los datos
de la tabla AsignacionInspeccion (la misma fuente de verdad que usa el
dashboard). Concretamente:

  * Se obtienen todas las semanas (fechas de asignación) que existen para el
    mes en curso / planificado.
  * De esas semanas, se toma como referencia la última semana que YA TERMINÓ:
        semana.fecha + 7 días < = hoy
    (es decir, asignaciones cuya semana transcurrió por completo).
  * Rango de la semana: [semana.fecha , semana.fecha + 7)

Pendientes
----------
Asignaciones de la semana de referencia cuyo EQUIPO no tiene ninguna
inspección registrada dentro del rango de esa semana (válida también para
semana en curso).

Uso:
    python manage.py resumen_semanal
    python manage.py resumen_semanal --tiempo prueba
"""

import datetime as dt

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from inspeccion.models import (
    AsignacionInspeccion, EquipoSinQR, Inspeccion, InspeccionTecnico,
)


def normalize(nombre):
    """Normaliza para comparar nombres de equipos: minúsculas, sin tildes."""
    if not nombre:
        return ''
    n = nombre.lower().strip()
    for a, b in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'),
                 ('ú', 'u'), ('ü', 'u'), ('ñ', 'n')]:
        n = n.replace(a, b)
    return ' '.join(n.split())


def color_estado(estado):
    if estado == 'NOK':
        return 'Attention'
    if estado == 'NA':
        return 'Default'
    return 'Good'


class Command(BaseCommand):
    help = ('Genera el resumen semanal de inspecciones y lo envía al chat '
            'de Teams vía webhook de Power Automate.')

    def add_arguments(self, parser):
        parser.add_argument(
            '--tiempo', dest='tiempo', choices=['produccion', 'prueba'],
            default='produccion',
            help='Etiqueta del reporte (produccion | prueba).')

    # ── helpers ──────────────────────────────────────────────────────────

    def _fact(self, titulo, valor, color=None):
        fact = {"title": titulo, "value": valor}
        if color:
            fact["color"] = color
        return fact

    def _progress(self, titulo, done, total, color):
        pct = round(100.0 * done / total) if total else 0
        filled = '█' * round(pct / 10)
        rest = '░' * (10 - len(filled))
        return [
            {"type": "TextBlock", "text": titulo, "weight": "Bolder",
             "size": "Small", "wrap": False},
            {"type": "TextBlock", "text": filled + rest,
             "color": color, "spacing": "None", "wrap": True, "size": "Small"},
            {"type": "TextBlock", "text": f"{done}/{total} · {pct}%",
             "spacing": "None", "isSubtle": True, "size": "Small",
             "wrap": False},
        ]

    # ── cálculo ──────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        hoy = dt.date.today()
        etiqueta = options['tiempo']

        # ── 1. Semana de referencia ──────────────────────────────────────
        semanas = list(
            AsignacionInspeccion.objects.order_by('fecha')
            .values_list('fecha', flat=True).distinct()
        )
        referencia = None
        for s in semanas:
            if s + dt.timedelta(days=7) <= hoy:
                referencia = s
        if referencia is None:
            raise CommandError(
                'No hay una semana de asignación completamente terminada '
                'aún. Genera asignaciones primero.')
        inicio = referencia
        fin = referencia + dt.timedelta(days=6)

        # ── 2. Inspecciones de la semana ─────────────────────────────────
        inspecciones = list(
            Inspeccion.objects.select_related('zona', 'equipo')
            .filter(fecha__gte=inicio, fecha__lte=fin)
            .order_by('fecha')
        )
        realizadas = len(inspecciones)

        # ── 3. Pendientes ────────────────────────────────────────────────
        asignaciones = list(
            AsignacionInspeccion.objects.filter(fecha=referencia)
        )
        equipos_realizados = {
            normalize(i.equipo.nombre) for i in inspecciones
        }
        pendientes = [
            a for a in asignaciones
            if normalize(a.equipo) not in equipos_realizados
        ]

        # ── 4. Críticos / NOK ────────────────────────────────────────────
        revisiones = list(
            InspeccionTecnico.objects.filter(
                inspeccion__in=inspecciones,
                estado__in=['NOK', 'NA'],
            ).select_related('inspeccion__equipo')
        )
        criticos = [r for r in revisiones
                    if r.estado == 'NOK' or r.es_critico]

        # ── 5. Equipos sin QR (totales actuales) ─────────────────────────
        sin_qr = list(EquipoSinQR.objects.order_by('-creado_en')[:8])

        # ── 6. Por zonas (diagrama de barras) ────────────────────────────
        zonas = {}
        for i in inspecciones:
            z = i.zona.nombre if i.zona else 'Sin zona'
            zonas.setdefault(z, []).append(i)

        # ── 7. Tarjeta: resumen ejecutivo (solo cifras) ─────────────────
        base_url = settings.TEAMS_WEBHOOK_URL or ''

        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": "emphasis",
                    "items": [
                        {"type": "TextBlock",
                         "text": "📊 RESUMEN SEMANAL · INSPECCIONES TÉCNICAS",
                         "size": "Large", "weight": "Bolder", "wrap": True},
                        {"type": "TextBlock",
                         "text": f"Semana del {inicio:%d/%m/%Y} al {fin:%d/%m/%Y}",
                         "isSubtle": True, "spacing": "None", "wrap": True},
                    ],
                },
                {
                    "type": "Container",
                    "items": [{"type": "TextBlock", "text": "📈 RESUMEN GENERAL",
                               "weight": "Bolder", "size": "Medium",
                               "wrap": True}],
                },
                {
                    "type": "FactSet",
                    "spacing": "None",
                    "facts": [
                        self._fact("Inspecciones realizadas",
                                   str(realizadas), "Good"),
                        self._fact("Pendientes", str(len(pendientes)),
                                   "Attention"),
                        self._fact("Hallazgos críticos / NOK",
                                   str(len(criticos)), "Attention"),
                        self._fact("Equipos sin QR", str(len(sin_qr)),
                                   "Attention"),
                    ],
                },
            ],
        }

        # 🔗 Acción única: abrir el dashboard (resumen ejecutivo sin detalle)
        card["actions"] = [
            {
                "type": "Action.OpenUrl",
                "title": "🔗 Ver Dashboard",
                "url": "http://10.107.194.110/insp_pry/dashboard/",
            },
        ]

        # ── 8. Enviar vía webhook / flujo de Power Automate ──────────────
        import json
        import urllib.request
        import urllib.error

        payload = json.dumps(card).encode('utf-8')

        # La URL del webhook YA incluye ?api-version=1&sp=..&sv=1.0&sig=...
        # por lo que añadir etiqueta debe ir con '&' (nunca '?', rompe el sig).
        import urllib.parse
        p = urllib.parse.urlsplit(base_url)
        qs = dict(urllib.parse.parse_qsl(p.query))
        qs['etiqueta'] = etiqueta
        url = urllib.parse.urlunsplit(
            (p.scheme, p.netloc, p.path,
             urllib.parse.urlencode(qs), p.fragment))

        req = urllib.request.Request(
            url, data=payload, method='POST',
            headers={'Content-Type': 'application/json; charset=utf-8'})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                self.stdout.write(self.style.SUCCESS(
                    f"Resumen enviado a Teams (semana {inicio:%d/%m}) · "
                    f"HTTP {resp.status}"))
        except urllib.error.HTTPError as e:
            raise CommandError(
                f"Teams HTTP {e.code}: {e.read().decode('utf-8', 'replace')}")
        except urllib.error.URLError as e:
            raise CommandError(
                f"No se pudo contactar el webhook: {e.reason}")
