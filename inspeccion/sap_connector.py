"""
sap_connector.py
----------------
Integración con SAP PM via HTTP/SOAP (RFC over HTTP).
NO requiere SAP RFC SDK ni pyrfc nativo.
Usa el mismo mecanismo que Java JCo pero en HTTP puro con requests.

Llama al RFC ZBRPP_NOTIFICATION_LA (la misma función del JSP)
para crear Notificaciones NR (IW21) en SAP PM.
"""

import os
import logging
import datetime
import requests
import xml.etree.ElementTree as ET
import unicodedata
from requests.auth import HTTPBasicAuth
from decouple import config

logger = logging.getLogger(__name__)

# Namespace SAP SOAP
NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
NS_SAP  = "urn:sap-com:document:sap:soap:functions:mc-style"

def normalizar_para_sap(texto):
    """
    Normaliza el texto reemplazando eñes por n y removiendo tildes
    para evitar problemas de visualización en SAP PM y SAP GUI.
    """
    if not texto:
        return ""
    # Reemplazo explícito de eñes
    texto = texto.replace("ñ", "n").replace("Ñ", "N")
    # Remover tildes usando descompocisión Unicode NFD
    texto_normalizado = "".join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return texto_normalizado


def _get_sap_config():
    """Lee la configuración SAP desde .env"""
    return {
        'host'  : config('SAP_ASHOST', default=''),
        'sysnr' : config('SAP_SYSNR', default='00'),
        'client': config('SAP_CLIENT', default='100'),
        'user'  : config('SAP_USER', default=''),
        'passwd': config('SAP_PASS', default=''),
        'lang'  : config('SAP_LANG', default='EN'),
    }


def _get_soap_url(cfg):
    """
    Construye la URL del endpoint SOAP de SAP.
    SAP Web AS expone RFC sobre HTTP en /sap/bc/soap/rfc
    Puerto HTTP: 8000 + SYSNR  (ej: sysnr=77 → puerto 8077)
    Puerto HTTPS: 44300 + SYSNR (ej: sysnr=77 → 44377)
    """
    sysnr = str(cfg['sysnr']).zfill(2)
    # Intentar HTTPS primero, fallback a HTTP
    https_port = 44300 + int(sysnr)
    http_port  = 8000  + int(sysnr)
    return {
        'https': f"https://{cfg['host']}:{https_port}/sap/bc/soap/rfc",
        'http' : f"http://{cfg['host']}:{http_port}/sap/bc/soap/rfc",
    }


def _build_soap_envelope(tplnr, title, userid, tipo, descrip, date_str, time_str):
    """
    Construye el envelope SOAP para llamar ZBRPP_NOTIFICATION_LA.
    Mismos parámetros que el JSP de Java.
    """
    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="{NS_SOAP}">
  <SOAP-ENV:Header>
    <SAP:Service xmlns:SAP="urn:sap-com:document:sap:soap:functions:mc-style" 
                 SAP:client="{{}}" SAP:user="{{}}" SAP:password="{{}}" SAP:language="{{}}"/>
  </SOAP-ENV:Header>
  <SOAP-ENV:Body>
    <urn:ZBRPP_NOTIFICATION_LA xmlns:urn="{NS_SAP}">
      <FT_CREATE>
        <item>
          <TPLNR>{tplnr}</TPLNR>
          <MSAUS></MSAUS>
          <SYMSGNO>{title[:40]}</SYMSGNO>
          <AUSVN>{date_str}</AUSVN>
          <AUZTV>{time_str}</AUZTV>
          <QMNAM>{userid}</QMNAM>
          <QMART>{tipo}</QMART>
        </item>
      </FT_CREATE>
      <FT_LONGTEXT>
        <item>
          <QMNUM></QMNUM>
          <TDLINE>{descrip[:132]}</TDLINE>
        </item>
      </FT_LONGTEXT>
    </urn:ZBRPP_NOTIFICATION_LA>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""
    return envelope


def _parse_notif_number(response_text):
    """
    Parsea la respuesta SOAP de ZBRPP_NOTIFICATION_LA
    y extrae el número de notificación de FT_NOTIFI.
    """
    try:
        root = ET.fromstring(response_text)
        # Buscar el número en la tabla de respuesta FT_NOTIFI
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag in ('QMNUM', 'NOTIF', 'NOTIF_NO') and elem.text and elem.text.strip():
                return elem.text.strip().lstrip('0')
        # Buscar cualquier elemento que parezca un número de notificación
        for elem in root.iter():
            if elem.text and elem.text.strip().isdigit() and len(elem.text.strip()) >= 8:
                return elem.text.strip().lstrip('0')
    except ET.ParseError as e:
        logger.error(f"[SAP SOAP] Error parseando respuesta XML: {e}")
    return ''


def _call_soap(url, soap_body, cfg, timeout=30):
    """Realiza la llamada HTTP SOAP a SAP con autenticación básica."""
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction':   'ZBRPP_NOTIFICATION_LA',
    }
    auth = HTTPBasicAuth(cfg['user'], cfg['passwd'])
    response = requests.post(
        url,
        data=soap_body.encode('utf-8'),
        headers=headers,
        auth=auth,
        verify=False,       # SAP con certificados autofirmados
        timeout=timeout,
    )
    return response


def test_sap_connection():
    """
    Prueba la conexión al puente JSP de SAP.
    Ejecutar desde el venv:
        ./venv/bin/python -c "
        import django, os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mi_formulario.settings')
        django.setup()
        from inspeccion.sap_connector import test_sap_connection
        print(test_sap_connection())
        "
    """
    bridge_url = config('SAP_BRIDGE_URL', default='http://10.107.194.82/saptest/redtagtosap_new.jsp')
    try:
        logger.info(f"[SAP Puente] Probando conexión al puente: {bridge_url}")
        resp = requests.get(bridge_url, params={'machine': 'TEST'}, timeout=5)
        if resp.status_code == 200:
            return {
                'status': 'ok',
                'url': bridge_url,
                'http_code': resp.status_code,
                'message': 'El puente JSP responde correctamente (HTTP 200)'
            }
        elif resp.status_code == 502:
            return {
                'status': 'error',
                'url': bridge_url,
                'http_code': resp.status_code,
                'message': 'Nginx responde con 502 Bad Gateway (Tomcat podría estar apagado en el servidor puente)'
            }
        else:
            return {
                'status': 'error',
                'url': bridge_url,
                'http_code': resp.status_code,
                'message': f'El puente JSP retornó código HTTP {resp.status_code}'
            }
    except requests.exceptions.Timeout:
        return {'status': 'error', 'message': f'Timeout conectando al puente JSP ({bridge_url})'}
    except requests.exceptions.ConnectionError:
        return {'status': 'error', 'message': f'Error de conexión. No se pudo establecer contacto con {bridge_url}'}
    except Exception as e:
        return {'status': 'error', 'message': f'Error inesperado: {str(e)}'}


def crear_notificacion_sap(inspeccion):
    """
    Crea una Notificación NR (IW21) en SAP PM a través del puente JSP.
    Usa redtagtosap_new.jsp — misma función del JSP de Java.
    No requiere SDK ni pyrfc nativo.

    Args:
        inspeccion: instancia del modelo Inspeccion guardada en Django.

    Returns:
        dict con 'status', 'nr_numero', 'mensaje'
    """
    # Necesitamos al menos la ubicación técnica o el equipo SAP
    tplnr  = (inspeccion.sap_tplnr  or '').strip()
    equnr  = (inspeccion.sap_equnr  or '').strip()
    machine = tplnr or equnr

    if not machine:
        logger.warning(f"[SAP Puente] Inspección {inspeccion.id} sin código SAP - NR omitida")
        return {'status': 'pendiente', 'nr_numero': '', 'mensaje': 'Sin código SAP (TPLNR/EQUNR)'}

    bridge_url = config('SAP_BRIDGE_URL', default='http://10.107.194.82/saptest/inspecciones_to_sap.jsp')
    if not bridge_url:
        return {'status': 'error', 'nr_numero': '', 'mensaje': 'URL del puente SAP no configurada en .env'}

    # Construir parámetros para el JSP exclusivo de inspecciones (BAPI estándar)
    equipo_nombre = inspeccion.equipo.nombre if inspeccion.equipo else 'EQUIPO'
    raw_title  = f"Insp. {equipo_nombre} {inspeccion.fecha}"[:40]
    title = normalizar_para_sap(raw_title)
    userid = (inspeccion.owner or 'SYSTEM').strip().upper()

    # Descripción: comentario + ítems NOK
    descrip_parts = []
    if inspeccion.comentario_hallazgo:
        descrip_parts.append(f"Comentario General: {inspeccion.comentario_hallazgo.strip()}")
    
    nok_revisiones = inspeccion.revisiones.filter(estado='NOK')
    if nok_revisiones.exists():
        descrip_parts.append("Hallazgos NOK:")
        for rev in nok_revisiones:
            linea = f"- {rev.descripcion.strip()}"
            if rev.comentario and rev.comentario.strip():
                linea += f" (Comentario: {rev.comentario.strip()})"
            descrip_parts.append(linea)
            
    raw_descrip = '\r\n'.join(descrip_parts) or f"Inspeccion #{inspeccion.id}"
    descrip = normalizar_para_sap(raw_descrip)

    # Parámetros para enviar al nuevo JSP estándar
    params = {
        'equnr': equnr,
        'tplnr': tplnr,
        'title': title,
        'userid': userid,
        'descrip': descrip,
        'wkctr': (inspeccion.sap_puesto_trabajo or '').strip().upper(),
        'label': str(inspeccion.id),
        'tipo': 'N2'
    }

    try:
        logger.info(f"[SAP Puente] Enviando datos a {bridge_url} - Machine: {machine}")
        # Hacemos POST forzando codificación UTF-8 en las cabeceras HTTP
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
        resp = requests.post(bridge_url, data=params, headers=headers, timeout=30)
        
        logger.warning(f"[SAP Puente] HTTP {resp.status_code}: {resp.text[:500]}")

        if resp.status_code == 200:
            import re
            # Limpiamos espacios para un regex más sencillo
            cleaned_html = "".join(resp.text.split())
            match = re.search(r'id=["\']notif["\']>([0-9]+)</span>', cleaned_html)
            
            nr_numero = ''
            if match:
                nr_numero = match.group(1).strip().lstrip('0')
            else:
                # Fallback: buscar cualquier número de 8 a 12 dígitos en el HTML retornado
                match_fallback = re.search(r'\b(10\d{6,10})\b', resp.text)
                if match_fallback:
                    nr_numero = match_fallback.group(1).strip().lstrip('0')
            
            if nr_numero:
                logger.info(f"[SAP Puente] NR {nr_numero} creada exitosamente para inspección {inspeccion.id}")
                return {
                    'status': 'creada',
                    'nr_numero': nr_numero,
                    'mensaje': f'Notificación SAP {nr_numero} creada vía puente JSP'
                }
            else:
                logger.warning(f"[SAP Puente] Respuesta 200 pero no se encontró número de notificación. HTML: {resp.text[:300]}")
                return {
                    'status': 'error',
                    'nr_numero': '',
                    'mensaje': f'El puente retornó 200 pero sin número de aviso. Respuesta: {resp.text[:200]}'
                }
        elif resp.status_code == 502:
            return {
                'status': 'error',
                'nr_numero': '',
                'mensaje': 'Error de puente (502 Bad Gateway). Tomcat podría estar apagado en 10.107.194.82'
            }
        else:
            return {
                'status': 'error',
                'nr_numero': '',
                'mensaje': f'El puente JSP retornó error HTTP {resp.status_code}'
            }
            
    except requests.exceptions.ConnectionError as ce:
        error_msg = f"No se pudo conectar al puente JSP: {ce}"
        logger.error(f"[SAP Puente] {error_msg}")
        return {'status': 'error', 'nr_numero': '', 'mensaje': error_msg}
    except requests.exceptions.Timeout:
        error_msg = "Timeout esperando respuesta del puente JSP"
        logger.error(f"[SAP Puente] {error_msg}")
        return {'status': 'error', 'nr_numero': '', 'mensaje': error_msg}
    except Exception as e:
        error_msg = f"Excepción llamando al puente: {str(e)}"
        logger.error(f"[SAP Puente] {error_msg}")
        return {'status': 'error', 'nr_numero': '', 'mensaje': error_msg}

def cerrar_notificacion_sap(inspeccion):
    """
    Llama al JSP 'cerrar_notificacion.jsp' para cerrar un aviso en SAP.
    """
    notif_no = (inspeccion.sap_nr_numero or '').strip()
    if not notif_no:
        return {'status': 'error', 'mensaje': 'Esta inspección no tiene un número de aviso SAP asociado.'}

    bridge_close_url = config('SAP_BRIDGE_CLOSE_URL', default='http://10.107.194.82:8080/saptest/cerrar_notificacion.jsp')
    
    try:
        logger.info(f"[SAP Puente Cierre] Cerrando aviso {notif_no} para inspección {inspeccion.id}")
        resp = requests.post(bridge_close_url, data={'notif': notif_no}, timeout=30)
        
        logger.debug(f"[SAP Puente Cierre] HTTP {resp.status_code}: {resp.text[:500]}")

        if resp.status_code == 200:
            import re
            
            # Buscar status y error preservando espacios y formato
            status_match = re.search(r'id=["\']status["\']>\s*([a-zA-Z]+)\s*</span>', resp.text)
            error_match = re.search(r'id=["\']error["\']>\s*(.*?)\s*</span>', resp.text, re.DOTALL)
            
            status = status_match.group(1).strip() if status_match else 'error'
            error_msg = error_match.group(1).strip() if error_match else 'Error desconocido en JSP'

            if status == 'ok':
                logger.info(f"[SAP Puente Cierre] Aviso {notif_no} cerrado exitosamente en SAP.")
                return {'status': 'ok', 'mensaje': f'Aviso SAP {notif_no} cerrado correctamente.'}
            else:
                logger.warning(f"[SAP Puente Cierre] Error retornado por JSP al cerrar aviso: {error_msg}")
                return {'status': 'error', 'mensaje': error_msg}
        else:
            return {'status': 'error', 'mensaje': f'El puente JSP retornó error HTTP {resp.status_code}'}
            
    except Exception as e:
        error_msg = f"Excepción llamando al puente de cierre: {str(e)}"
        logger.error(f"[SAP Puente Cierre] {error_msg}")
        return {'status': 'error', 'mensaje': error_msg}

