"""
sap_connector.py
----------------
Módulo de integración con SAP PM via pyrfc.
Crea Notificaciones de Mantenimiento (NR - IW21) en SAP
a partir de una inspección guardada en Django.
"""

import os
import logging
from datetime import date

logger = logging.getLogger(__name__)


def _get_sap_params():
    """Lee los parámetros de conexión SAP desde las variables de entorno (.env)."""
    return {
        'ashost': os.environ.get('SAP_ASHOST', ''),
        'sysnr':  os.environ.get('SAP_SYSNR',  '00'),
        'client': os.environ.get('SAP_CLIENT', '100'),
        'user':   os.environ.get('SAP_USER',   ''),
        'passwd': os.environ.get('SAP_PASS',   ''),
        'lang':   os.environ.get('SAP_LANG',   'EN'),
    }


def _get_connection_class():
    """
    Obtiene la clase Connection de pyrfc.
    pyrfc requiere libsapnwrfc.so (SAP NetWeaver RFC SDK) en el sistema
    para que _cyrfc.so cargue correctamente.
    Si no está disponible retorna None.
    """
    try:
        # pyrfc expone Connection a través de su módulo interno _cyrfc
        from pyrfc._cyrfc import Connection  # noqa
        return Connection
    except ImportError:
        return None


def test_sap_connection():
    """
    Prueba rápida de conexión a SAP.
    Úsala desde la shell del venv para verificar antes de integrar:
        ./venv/bin/python -c "from inspeccion.sap_connector import test_sap_connection; print(test_sap_connection())"
    """
    Connection = _get_connection_class()
    if Connection is None:
        return {
            'status': 'error',
            'message': 'libsapnwrfc.so no encontrado. Instalar SAP NetWeaver RFC SDK en el servidor.'
        }
    try:
        conn = Connection(**_get_sap_params())
        result = conn.call('RFC_PING')
        conn.close()
        return {'status': 'ok', 'message': 'Conexión a SAP exitosa', 'result': str(result)}
    except Exception as e:
        logger.error(f"[SAP] Error de conexión: {e}")
        return {'status': 'error', 'message': str(e)}


def _build_long_text(inspeccion):
    """
    Construye el texto largo de la NR con el comentario de hallazgo
    y la lista de ítems técnicos con estado NOK o críticos.
    """
    lines = []

    if inspeccion.comentario_hallazgo:
        lines.append(inspeccion.comentario_hallazgo.strip())
        lines.append('')

    # Agregar ítems técnicos con NOK o críticos
    tecnicos_nok = inspeccion.revisiones.filter(
        estado__in=['NOK']
    ).values('descripcion', 'estado', 'comentario', 'es_critico')

    if tecnicos_nok:
        lines.append('--- Hallazgos ---')
        for t in tecnicos_nok:
            critico_tag = ' [CRITICO]' if t['es_critico'] else ''
            lines.append(f"- {t['descripcion']}: {t['estado']}{critico_tag}")
            if t['comentario']:
                lines.append(f"  Obs: {t['comentario']}")

    return '\n'.join(lines) if lines else f"Inspección #{inspeccion.id} - {inspeccion.fecha}"


def crear_notificacion_sap(inspeccion):
    """
    Crea una Notificación de Mantenimiento (tipo NR) en SAP PM
    usando BAPI_ALM_NOTIF_CREATE.

    Args:
        inspeccion: instancia del modelo Inspeccion (ya guardada en Django,
                    con sus InspeccionTecnico relacionados).

    Returns:
        dict con claves:
            - 'status': 'creada' | 'error' | 'pendiente'
            - 'nr_numero': número de notificación SAP (str) o ''
            - 'mensaje': descripción del resultado
    """
    # Si no hay código de equipo SAP, no tiene sentido crear la NR
    if not inspeccion.sap_equnr:
        logger.warning(f"[SAP] Inspección {inspeccion.id} sin sap_equnr - NR omitida")
        return {'status': 'pendiente', 'nr_numero': '', 'mensaje': 'Sin código de equipo SAP'}

    Connection = _get_connection_class()
    if Connection is None:
        msg = 'SAP NetWeaver RFC SDK (libsapnwrfc.so) no instalado en el servidor'
        logger.error(f"[SAP] {msg}")
        return {'status': 'pendiente', 'nr_numero': '', 'mensaje': msg}

    params = _get_sap_params()
    if not params['ashost'] or not params['user']:
        logger.error("[SAP] Credenciales SAP no configuradas en .env")
        return {'status': 'error', 'nr_numero': '', 'mensaje': 'Credenciales SAP no configuradas'}

    # Texto corto: máximo 40 caracteres
    equipo_nombre = inspeccion.equipo.nombre if inspeccion.equipo else 'EQUIPO'
    short_text = f"Insp. {equipo_nombre} {inspeccion.fecha}"[:40]

    # Texto largo
    long_text = _build_long_text(inspeccion)

    # Estructura de texto largo para BAPI (tabla NOTIF_TEXT)
    text_lines = []
    for i, line in enumerate(long_text.split('\n')[:60], start=1):  # máx 60 líneas
        text_lines.append({
            'TDOBJECT': 'QMEL',
            'TDID':     '0001',
            'TDLINE':   line[:132],  # máx 132 chars por línea
            'TDFORMAT': '*',
        })

    try:
        conn = Connection(**params)

        # Llamada principal al BAPI de creación de notificación
        result = conn.call(
            'BAPI_ALM_NOTIF_CREATE',
            NOTIF_TYPE   = 'NR',
            SHORT_TEXT   = short_text,
            NOTIF_DATE   = inspeccion.fecha,
            NOTIF_TIME   = inspeccion.hora_inicio,
            EQUIPMENT    = inspeccion.sap_equnr.strip()        if inspeccion.sap_equnr        else '',
            FUNCT_LOC    = inspeccion.sap_tplnr.strip()        if inspeccion.sap_tplnr        else '',
            WORK_CTR     = inspeccion.sap_puesto_trabajo.strip() if inspeccion.sap_puesto_trabajo else '',
            NOTIF_TEXT   = text_lines,
        )

        logger.debug(f"[SAP] BAPI_ALM_NOTIF_CREATE result: {result}")

        # Verificar mensajes de retorno del BAPI
        return_msgs = result.get('RETURN', [])
        nr_numero   = result.get('NOTIFNUMBER', '').strip()

        # Buscar errores en los mensajes
        errores = [m for m in return_msgs if m.get('TYPE') in ('E', 'A')]
        if errores:
            msg_error = '; '.join(m.get('MESSAGE', '') for m in errores)
            conn.close()
            logger.error(f"[SAP] Error BAPI para inspección {inspeccion.id}: {msg_error}")
            return {'status': 'error', 'nr_numero': '', 'mensaje': msg_error}

        # Confirmar la transacción SAP
        conn.call('BAPI_TRANSACTION_COMMIT', WAIT='X')
        conn.close()

        if nr_numero:
            logger.info(f"[SAP] NR {nr_numero} creada para inspección {inspeccion.id}")
            return {'status': 'creada', 'nr_numero': nr_numero, 'mensaje': f'NR {nr_numero} creada en SAP'}
        else:
            logger.warning(f"[SAP] BAPI sin número NR para inspección {inspeccion.id}")
            return {'status': 'error', 'nr_numero': '', 'mensaje': 'BAPI no retornó número de NR'}

    except Exception as e:
        logger.error(f"[SAP] Excepción al crear NR para inspección {inspeccion.id}: {e}")
        return {'status': 'error', 'nr_numero': '', 'mensaje': str(e)}
