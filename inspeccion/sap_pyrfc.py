"""
sap_pyrfc.py
------------
Integración directa con SAP PM via pyRFC (SAP NW RFC SDK).

El backend abre una conexión RFC directa a SAP usando las credenciales LDAP
del usuario como user/pass SAP.

Misma lógica de consulta que saptest/consultar_notificacion.jsp:
    1. QMEL  -> OBJNR del aviso (QMNUM, 12 dígitos).
    2. JEST  -> STAT activos para ese OBJNR (INACT = '').

Estado: si JEST contiene 'MEAB' el aviso está cerrado; en caso contrario,
se reporta abierto. Auth: user/pass LDAP del request.
"""

import os
import ctypes
import logging
import threading
from decouple import config

logger = logging.getLogger(__name__)

# pyRFC NO es thread-safe: un lock global serializa las llamadas dentro del
# proceso.
_rfc_lock = threading.Lock()

AVISO_TARGETS_SOPORTADOS = ['L1P']


class SapRfcError(Exception):
    pass


def _sdk_home():
    """
    Resuelve el directorio del SAP NW RFC SDK intentando: variable del .env,
    variable de entorno, y rutas habituales en el servidor.
    """
    from_env = config('SAPNWRFC_HOME', default='') or os.environ.get('SAPNWRFC_HOME', '')
    if from_env:
        return from_env
    for path in (
        '/home/ac42027/nwrfcsdk',
        '/usr/local/sap/nwrfcsdk',
        '/opt/sap/nwrfcsdk',
    ):
        if os.path.isfile(os.path.join(path, 'lib', 'libsapnwrfc.so')):
            return path
    return '/usr/local/sap/nwrfcsdk'


def _precargar_sdk():
    """
    Carga las librerías compartidas del SDK SAP NW RFC con RTLD_GLOBAL
    ANTES de importar pyrfc. Evita depender de LD_LIBRARY_PATH heredado.
    """
    sdk_home = _sdk_home()
    lib_dir = os.path.join(sdk_home, 'lib')
    if not os.path.isdir(lib_dir):
        raise SapRfcError(
            f"No se encontró el SDK SAP NW RFC en {lib_dir}. "
            f"Defina SAPNWRFC_HOME en el .env."
        )
    for lib in ('libsapnwrfc.so', 'libsapucum.so'):
        path = os.path.join(lib_dir, lib)
        if os.path.exists(path):
            try:
                ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
            except OSError as e:
                logger.warning(f"[SAP pyrfc] No se pudo precargar {path}: {e}")
    # En caso de que solo existan con otro prefijo (ej. libsapnwrfc.so.75)
    for name in os.listdir(lib_dir):
        if name.startswith('libsapnwrfc') and name.endswith('.so') and \
                not any(name.endswith(sfx) for sfx in ('.so.75', '.so.74')):
            try:
                ctypes.CDLL(os.path.join(lib_dir, name), mode=ctypes.RTLD_GLOBAL)
            except OSError:
                pass


# Intentar importar pyrfc al cargar el módulo (falla soft si no está instalado).
_pyrfc = None
try:
    _precargar_sdk()
    import pyrfc as _pyrfc
except ImportError as e:
    logger.error(f"[SAP pyrfc] No se pudo importar pyrfc: {e}")


def _conexion(username, password, target='L1P'):
    """
    Abre una conexión RFC a SAP usando las credenciales LDAP del usuario.
    """
    if _pyrfc is None:
        raise SapRfcError(
            "pyRFC no está instalado. Ejecute: ./venv/bin/pip install pyrfc==3.3.1"
        )
    target = (target or 'L1P').strip().upper()
    if target not in AVISO_TARGETS_SOPORTADOS:
        raise SapRfcError(
            f"Target SAP '{target}' no soportado. Soportados: {AVISO_TARGETS_SOPORTADOS}"
        )

    # Config específica del target (SAP_L1P_*) sobreescribe
    # a las claves genéricas del backend (SAP_ASHOST/SAP_SYSNR/...).
    def _cfg(key, gen_key, default=''):
        return config(
            f'SAP_{target}_{key}',
            default=config(gen_key, default=default),
        )

    ashost = _cfg('HOST', 'SAP_ASHOST')
    sysnr = _cfg('SYSNR', 'SAP_SYSNR', '00')
    client = _cfg('CLIENT', 'SAP_CLIENT', '100')
    lang = _cfg('LANG', 'SAP_LANG', 'EN')

    if not ashost:
        raise SapRfcError(
            f"Falta configurar el host SAP para el target '{target}'. "
            f"Defina SAP_{target}_HOST (o SAP_ASHOST) en el .env del backend."
        )

    conn = _pyrfc.Connection(
        ashost=ashost,
        sysnr=sysnr,
        client=client,
        user=(username or '').strip().upper(),
        passwd=password or '',
        lang=lang,
    )
    return conn


def _rutina_read_table(conn, query_table, fields, options):
    """
    Ejecuta RFC_READ_TABLE y devuelve las filas de DATA (lista de WA).
    """
    result = conn.call(
        'RFC_READ_TABLE',
        QUERY_TABLE=query_table,
        FIELDS=[{'FIELDNAME': f} for f in fields],
        OPTIONS=[{'TEXT': o} for o in options],
        DELIMITER='|',
    )
    filas = []
    for row in result.get('DATA') or []:
        filas.append((row.get('WA') or '').strip())
    return filas


def consultar_status_avisos_directo(numeros, username, password, target='L1P'):
    """
    Consulta el estado de uno o varios avisos directamente en SAP vía pyRFC.

    Devuelve dict {aviso: {'status','order','description','equipment'}}.
      - status: 'Cerrado' (MEAB en JEST) | 'Abierto' | '' si no se encuentra.
      - order: número de orden asociada (QMEL.AUFNR).
      - description: texto corto del aviso (QMEL.QMTXT).
    """
    if not numeros:
        return {}

    avisos = [str(n).strip() for n in numeros if str(n).strip()]
    if not avisos:
        return {}

    resultado = {}
    conn = None
    with _rfc_lock:
        try:
            conn = _conexion(username, password, target)
            logger.info(
                f"[SAP pyrfc] Conectado directo a SAP ({target}) - consultando {len(avisos)} avisos"
            )
            for aviso in avisos:
                qmnum = aviso.zfill(12)
                try:
                    qmel_rows = _rutina_read_table(
                        conn,
                        'QMEL',
                        ['OBJNR', 'QMTXT', 'AUFNR'],
                        [f"QMNUM = '{qmnum}'"],
                    )
                    if not qmel_rows:
                        logger.debug(f"[SAP pyrfc] Aviso {aviso} no encontrado en QMEL")
                        resultado[aviso] = {
                            'status': '', 'order': '', 'description': '', 'equipment': '',
                        }
                        continue

                    wa = qmel_rows[0]
                    parts = wa.split('|')
                    objnr = parts[0].strip() if len(parts) > 0 else ''
                    desc  = parts[1].strip() if len(parts) > 1 else ''
                    aufnr = parts[2].strip() if len(parts) > 2 else ''

                    status = 'Abierto'
                    if objnr:
                        jest_rows = _rutina_read_table(
                            conn,
                            'JEST',
                            ['STAT'],
                            [f"OBJNR = '{objnr}' AND INACT = ''"],
                        )
                        stats = [r for r in jest_rows if r]
                        if 'MEAB' in stats:
                            status = 'Cerrado'

                    resultado[aviso] = {
                        'status': status,
                        'order': aufnr,
                        'description': desc,
                        'equipment': '',
                    }
                except Exception as e:
                    logger.warning(f"[SAP pyrfc] Error consultando aviso {aviso}: {e}")
                    resultado[aviso] = {
                        'status': '', 'order': '', 'description': '', 'equipment': '',
                    }
        except SapRfcError:
            raise
        except Exception as e:
            logger.exception("[SAP pyrfc] Error abriendo conexión directa a SAP")
            raise SapRfcError(f"Error conectando a SAP ({target}): {e}") from e
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
    return resultado