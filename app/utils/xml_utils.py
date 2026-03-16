"""
Utilidades para generación y parseo de XML para AFIP WSAA.

Este módulo maneja:
- Generación de LoginTicketRequest XML
- Parseo de LoginCmsResponse XML
- Construcción de SOAP envelopes
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateutil_parser
from typing import Optional

from app.exceptions.custom_exceptions import XMLParseException
from app.models.afip_models import LoginTicketRequest, TokenData


def build_login_ticket_request(
    service: str = "ws_sr_padron_a13",
    expiration_hours: int = 24
) -> str:
    """
    Genera el XML LoginTicketRequest para WSAA.

    Estructura según especificación AFIP:
    <loginTicketRequest version="1.0">
      <header>
        <uniqueId>timestamp</uniqueId>
        <generationTime>ISO datetime</generationTime>
        <expirationTime>ISO datetime + N hours</expirationTime>
      </header>
      <service>ws_sr_padron_a13</service>
    </loginTicketRequest>

    Args:
        service: Nombre del servicio AFIP (default: ws_sr_padron_a13)
        expiration_hours: Horas de validez del ticket (default: 24)

    Returns:
        XML como string UTF-8 sin declaración XML
    """
    try:
        # Generar timestamps en hora de Argentina (UTC-3)
        # AFIP requiere timestamps con timezone y expiración <= 24 horas
        argentina_tz = timezone(timedelta(hours=-3))
        now = datetime.now(argentina_tz)
        
    # Formato: 2024-03-14T10:30:00-03:00 (sin milisegundos)
        # Generar timezone-aware en UTC-3 y formatear con offset
        generation_time = now.strftime('%Y-%m-%dT%H:%M:%S%z')
        # Insertar ':' en el timezone offset: -0300 -> -03:00
        generation_time = generation_time[:-2] + ':' + generation_time[-2:]
        
        # Calcular expiración (máximo 24 horas)
        expiration = now + timedelta(hours=expiration_hours)
        expiration_time = expiration.strftime('%Y-%m-%dT%H:%M:%S%z')
        expiration_time = expiration_time[:-2] + ':' + expiration_time[-2:]
        
        unique_id = str(int(now.timestamp()))  # Unix timestamp como ID único

        # Construir XML usando ElementTree
        root = ET.Element("loginTicketRequest", version="1.0")

        header = ET.SubElement(root, "header")
        ET.SubElement(header, "uniqueId").text = unique_id
        ET.SubElement(header, "generationTime").text = generation_time
        ET.SubElement(header, "expirationTime").text = expiration_time

        ET.SubElement(root, "service").text = service

        # Convertir a string sin declaración XML (AFIP no la requiere para el contenido a firmar)
        xml_string = ET.tostring(root, encoding='unicode', method='xml')

        return xml_string

    except Exception as e:
        raise XMLParseException(
            f"Failed to build LoginTicketRequest XML: {str(e)}",
            details={"service": service, "error": str(e)}
        )


def build_login_ticket_request_model(
    service: str = "ws_sr_padron_a13",
    expiration_hours: int = 24
) -> LoginTicketRequest:
    """
    Genera un modelo LoginTicketRequest (útil para testing).

    Args:
        service: Nombre del servicio AFIP
        expiration_hours: Horas de validez

    Returns:
        Objeto LoginTicketRequest
    """
    # Usar hora de Argentina (UTC-3)
    argentina_tz = timezone(timedelta(hours=-3))
    now = datetime.now(argentina_tz)
    return LoginTicketRequest(
        service=service,
        unique_id=str(int(now.timestamp())),
        generation_time=now,
        expiration_time=now + timedelta(hours=expiration_hours)
    )


def build_wsaa_soap_envelope(cms_signature_b64: str) -> str:
    """
    Construye el SOAP envelope para llamar a WSAA LoginCms.

    AFIP WSAA no tiene WSDL estable, por lo que construimos el SOAP manualmente.

    Args:
        cms_signature_b64: Firma CMS en Base64 (LoginTicketRequest firmado)

    Returns:
        SOAP envelope completo como string XML
    """
    soap_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wsaa="http://wsaa.view.sua.dvadac.desein.afip.gov">
    <soapenv:Header/>
    <soapenv:Body>
        <wsaa:loginCms>
            <wsaa:in0>{cms_signature_b64}</wsaa:in0>
        </wsaa:loginCms>
    </soapenv:Body>
</soapenv:Envelope>"""

    return soap_template


def parse_login_cms_response(xml_response: str) -> TokenData:
    """
    Parsea la respuesta XML de WSAA LoginCms y extrae el TokenData.

    Estructura esperada:
    <loginCmsReturn>
      <token>...</token>
      <sign>...</sign>
      <generationTime>2024-03-14T10:30:00.000-03:00</generationTime>
      <expirationTime>2024-03-15T10:30:00.000-03:00</expirationTime>
    </loginCmsReturn>

    Args:
        xml_response: XML de respuesta completo (SOAP envelope)

    Returns:
        TokenData con token, sign y timestamps

    Raises:
        XMLParseException: Si el XML no tiene la estructura esperada
    """
    try:
        # Parsear XML
        root = ET.fromstring(xml_response)

        # Definir namespaces (SOAP puede tener variaciones)
        namespaces = {
            'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        }

        # Buscar loginCmsReturn en el Body (sin namespace específico por flexibilidad)
        # Intentar con y sin namespaces
        login_return = None

        # Intento 1: Con namespace soapenv
        body = root.find('.//soapenv:Body', namespaces)
        if body is not None:
            login_return = body.find('.//{*}loginCmsReturn')

        # Intento 2: Con namespace soap
        if login_return is None:
            body = root.find('.//soap:Body', namespaces)
            if body is not None:
                login_return = body.find('.//{*}loginCmsReturn')

        # Intento 3: Sin namespace (búsqueda recursiva)
        if login_return is None:
            login_return = root.find('.//{*}loginCmsReturn')

        if login_return is None:
            raise XMLParseException(
                "loginCmsReturn element not found in SOAP response",
                details={"xml_snippet": xml_response[:500]}
            )

        # Extraer campos requeridos
        token = login_return.findtext('token') or login_return.findtext('{*}token')
        sign = login_return.findtext('sign') or login_return.findtext('{*}sign')
        generation_time_str = (
            login_return.findtext('generationTime') or 
            login_return.findtext('{*}generationTime')
        )
        expiration_time_str = (
            login_return.findtext('expirationTime') or 
            login_return.findtext('{*}expirationTime')
        )

        # Validar campos obligatorios
        if not token:
            raise XMLParseException(
                "Token not found in loginCmsReturn",
                details={"login_return": ET.tostring(login_return, encoding='unicode')}
            )

        if not sign:
            raise XMLParseException(
                "Sign not found in loginCmsReturn",
                details={"login_return": ET.tostring(login_return, encoding='unicode')}
            )

        # Parsear timestamps (formato AFIP: 2024-03-14T10:30:00.000-03:00)
        try:
            # Limpiar milisegundos y timezone para simplificar parseo
            generation_time = parse_afip_timestamp(generation_time_str) if generation_time_str else datetime.utcnow()
            expiration_time = parse_afip_timestamp(expiration_time_str) if expiration_time_str else datetime.utcnow() + timedelta(hours=12)
        except Exception as e:
            raise XMLParseException(
                f"Failed to parse timestamps: {str(e)}",
                details={
                    "generation_time": generation_time_str,
                    "expiration_time": expiration_time_str
                }
            )

        # Construir TokenData
        token_data = TokenData(
            token=token,
            sign=sign,
            generation_time=generation_time,
            expiration_time=expiration_time
        )

        return token_data

    except XMLParseException:
        raise
    except ET.ParseError as e:
        raise XMLParseException(
            f"Invalid XML format: {str(e)}",
            details={"xml_snippet": xml_response[:500], "error": str(e)}
        )
    except Exception as e:
        raise XMLParseException(
            f"Failed to parse LoginCmsResponse: {str(e)}",
            details={"error": str(e), "xml_snippet": xml_response[:500]}
        )


def parse_afip_timestamp(timestamp_str: str) -> datetime:
    """
    Parsea timestamps de AFIP en formato ISO con timezone.

    Formatos soportados:
    - 2024-03-14T10:30:00.000-03:00
    - 2024-03-14T10:30:00-03:00
    - 2024-03-14T10:30:00

    Args:
        timestamp_str: String de timestamp

    Returns:
        datetime objeto (naive UTC)
    """
    # Usar dateutil para parsear formatos ISO flexibles y conservar offset
    # Luego normalizar a UTC timezone-aware
    if timestamp_str is None:
        raise ValueError("timestamp_str is None")

    # dateutil.isoparse maneja milisegundos y offsets correctamente
    try:
        dt = dateutil_parser.isoparse(timestamp_str)
    except Exception:
        # Intentar remover milisegundos y reintentar
        clean_ts = timestamp_str.split('.')
        clean_ts = clean_ts[0]
        try:
            dt = dateutil_parser.isoparse(clean_ts)
        except Exception as e:
            raise

    # Si el datetime es naive, asumir que viene en hora local de Argentina (UTC-3)
    if dt.tzinfo is None:
        argentina_tz = timezone(timedelta(hours=-3))
        dt = dt.replace(tzinfo=argentina_tz)

    # Normalizar a UTC
    return dt.astimezone(timezone.utc)


def extract_soap_fault(xml_response: str) -> Optional[str]:
    """
    Extrae mensaje de error SOAP Fault si existe.

    Args:
        xml_response: XML de respuesta SOAP

    Returns:
        Mensaje de error o None si no hay fault
    """
    try:
        root = ET.fromstring(xml_response)

        namespaces = {
            'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        }

        # Buscar Fault
        fault = root.find('.//soapenv:Fault', namespaces)
        if fault is None:
            fault = root.find('.//soap:Fault', namespaces)
        if fault is None:
            fault = root.find('.//{*}Fault')

        if fault is not None:
            faultstring = fault.findtext('faultstring') or fault.findtext('{*}faultstring')
            faultcode = fault.findtext('faultcode') or fault.findtext('{*}faultcode')

            if faultstring:
                return f"[{faultcode}] {faultstring}" if faultcode else faultstring

        return None

    except Exception:
        return None
