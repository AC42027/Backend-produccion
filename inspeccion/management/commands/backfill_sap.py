"""
backfill_sap
------------
Puebla los campos SAP (sap_equnr, sap_tplnr y descripciones) de los Equipos.

Fase 1 (--json PATH): importa el mapeo ya validado django_to_sap_map.json
        (claves = id de Django, valores con sap_tplnr/sap_equnr y descripciones).
Fase 2: auto-match contra la API de activos SAP para los equipos que queden
        sin datos. La primera consulta con resultados decide; el resto se lista
        para revisión manual en el admin.

Uso:
    python manage.py backfill_sap --json ../ruta/django_to_sap_map.json
    python manage.py backfill_sap --dry-run
    python manage.py backfill_sap --skip-json
"""

import json

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from inspeccion.models import Equipo
from inspeccion import sap_assets


class Command(BaseCommand):
    help = 'Puebla campos SAP de los equipos (JSON validado + auto-match API activos)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--json', dest='json_path', default=None,
            help='Ruta al archivo django_to_sap_map.json a importar'
        )
        parser.add_argument(
            '--skip-json', action='store_true',
            help='Omite la fase 1 (importación del JSON)'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='No escribe en la base de datos, solo reporta'
        )

    def handle(self, *args, **options):
        json_path = options.get('json_path')
        skip_json = options.get('skip_json')
        dry_run = options.get('dry_run')

        actualizados = 0
        ambiguos = []

        # ── Fase 1: importar JSON validado ──────────────────────────────
        if not skip_json:
            if not json_path:
                raise CommandError(
                    'Fase 1: indique --json <ruta/django_to_sap_map.json> '
                    'o use --skip-json para saltar esta fase.'
                )
            actualizados += self._importar_json(json_path, dry_run)

        # ── Fase 2: auto-match de equipos sin datos SAP ─────────────────
        # Solo equipos sin NINGUN dato SAP: si el JSON ya asigno un TPLNR,
        # el auto-match no debe pisarlo (ej. maquinas completas tipo Plummer/
        # Crane cuyo mapa no define EQUNR).
        restantes = Equipo.objects.filter(
            Q(sap_equnr__isnull=True) | Q(sap_equnr=''),
            Q(sap_tplnr__isnull=True) | Q(sap_tplnr='')
        )
        total_restantes = restantes.count()
        if total_restantes:
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'Fase 2: auto-match para {total_restantes} equipo(s) sin datos SAP'
            ))
            for eq in restantes:
                match = sap_assets.auto_match(eq.nombre)
                if match is None:
                    ambiguos.append(eq.nombre)
                    self.stdout.write(f'  [?] {eq.nombre}: sin coincidencia -> revisar en admin')
                    continue
                if not dry_run:
                    eq.sap_equnr = match['equnr']
                    eq.sap_equnr_desc = match['equnr_desc']
                    eq.sap_tplnr = match['tplnr']
                    eq.sap_tplnr_desc = match['tplnr_desc']
                    eq.save(update_fields=[
                        'sap_equnr', 'sap_equnr_desc', 'sap_tplnr', 'sap_tplnr_desc'
                    ])
                actualizados += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  [+] {eq.nombre} -> EQUNR {match['equnr']} | TPLNR {match['tplnr']}"
                ))

        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY-RUN: no se escribió nada en la BD.'))
        self.stdout.write(self.style.SUCCESS(f'Total equipos actualizados: {actualizados}'))
        if ambiguos:
            self.stdout.write(self.style.NOTICE(
                f'Equipos sin asignar ({len(ambiguos)}): ' + ', '.join(ambiguos)
            ))
            self.stdout.write('Asígnelos manualmente desde el admin (buscador "Buscar en SAP").')

    # ── helpers ──────────────────────────────────────────────────────────

    def _importar_json(self, json_path, dry_run):
        self.stdout.write(self.style.MIGRATE_HEADING(f'Fase 1: importando {json_path}'))
        try:
            with open(json_path, 'r', encoding='utf-8') as fh:
                mapa = json.load(fh)
        except (OSError, ValueError) as e:
            raise CommandError(f'No se pudo leer el JSON: {e}')

        count = 0
        omitidos = []
        for key, entry in mapa.items():
            try:
                eq = Equipo.objects.get(id=int(key))
            except (Equipo.DoesNotExist, ValueError):
                omitidos.append(key)
                continue
            if not dry_run:
                eq.sap_tplnr = entry.get('sap_tplnr') or ''
                eq.sap_tplnr_desc = entry.get('sap_tplnr_desc') or ''
                eq.sap_equnr = entry.get('sap_equnr') or ''
                eq.sap_equnr_desc = entry.get('sap_equnr_desc') or ''
                eq.save(update_fields=[
                    'sap_tplnr', 'sap_tplnr_desc', 'sap_equnr', 'sap_equnr_desc'
                ])
            count += 1
            self.stdout.write(
                f"  [=] {eq.nombre} -> TPLNR {entry.get('sap_tplnr')} | EQUNR {entry.get('sap_equnr')}"
            )
        if omitidos:
            self.stdout.write(self.style.WARNING(
                f'IDs del JSON sin equipo en la BD: {", ".join(omitidos)}'
            ))
        return count
