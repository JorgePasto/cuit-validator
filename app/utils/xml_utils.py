"""
Utilidades para generación y parseo de XML para AFIP WSAA.

Este módulo maneja:
- Generación de LoginTicketRequest XML
- Parseo de LoginCmsResponse XML
- Construcción de SOAP envelopes
"""

from asyncio.log import logger
import html
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
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


import html
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

def parse_login_cms_response(xml_response: str) -> TokenData:
    """
    Parsea la respuesta XML de WSAA LoginCms y extrae el TokenData.

    Soporta dos formatos:
    1. loginCmsReturn con nodos hijos directos
    2. loginCmsReturn conteniendo un XML interno escapado como texto

    Args:
        xml_response: XML de respuesta completo (SOAP envelope)

    Returns:
        TokenData con token, sign y timestamps

    Raises:
        XMLParseException: Si el XML no tiene la estructura esperada
    """
    try:
        root = ET.fromstring(xml_response)

        namespaces = {
            "soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
            "soap": "http://schemas.xmlsoap.org/soap/envelope/",
            "wsaa": "http://wsaa.view.sua.dvadac.desein.afip.gov",
        }

        login_return = None

        body = root.find(".//soapenv:Body", namespaces)
        if body is not None:
            login_return = body.find(".//{*}loginCmsReturn")

        if login_return is None:
            body = root.find(".//soap:Body", namespaces)
            if body is not None:
                login_return = body.find(".//{*}loginCmsReturn")

        if login_return is None:
            login_return = root.find(".//{*}loginCmsReturn")

        if login_return is None:
            raise XMLParseException(
                "loginCmsReturn element not found in SOAP response",
                details={"xml_snippet": xml_response[:500]}
            )

        # ------------------------------------------------------------------
        # Caso A: AFIP responde con hijos directos dentro de loginCmsReturn
        # ------------------------------------------------------------------
        token = login_return.findtext("token") or login_return.findtext("{*}token")
        sign = login_return.findtext("sign") or login_return.findtext("{*}sign")
        generation_time_str = (
            login_return.findtext("generationTime")
            or login_return.findtext("{*}generationTime")
        )
        expiration_time_str = (
            login_return.findtext("expirationTime")
            or login_return.findtext("{*}expirationTime")
        )

        # ------------------------------------------------------------------
        # Caso B: AFIP responde con XML escapado dentro de loginCmsReturn.text
        # ------------------------------------------------------------------
        if not token or not sign:
            inner_xml_raw = (login_return.text or "").strip()

            if inner_xml_raw:
                logger.debug(
                    "loginCmsReturn contains inner XML text, attempting nested parse"
                )

                # Normalmente ElementTree ya devuelve el texto desescapado,
                # pero html.unescape acá no rompe porque se aplica SOLO al
                # fragmento interno, nunca al SOAP completo.
                inner_xml = html.unescape(inner_xml_raw).strip()

                try:
                    inner_root = ET.fromstring(inner_xml)
                except ET.ParseError as inner_exc:
                    raise XMLParseException(
                        f"Failed to parse inner loginCmsReturn XML: {str(inner_exc)}",
                        details={
                            "inner_xml_snippet": inner_xml[:500],
                            "login_return": ET.tostring(login_return, encoding="unicode"),
                        }
                    )

                token = inner_root.findtext(".//token") or inner_root.findtext(".//{*}token")
                sign = inner_root.findtext(".//sign") or inner_root.findtext(".//{*}sign")
                generation_time_str = (
                    inner_root.findtext(".//generationTime")
                    or inner_root.findtext(".//{*}generationTime")
                )
                expiration_time_str = (
                    inner_root.findtext(".//expirationTime")
                    or inner_root.findtext(".//{*}expirationTime")
                )

        logger.debug(
            "Parsed loginCmsReturn: token=%s, sign=%s, generationTime=%s, expirationTime=%s",
            "found" if token else "missing",
            "found" if sign else "missing",
            generation_time_str,
            expiration_time_str,
        )

        if not token:
            raise XMLParseException(
                "Token not found in loginCmsReturn",
                details={"login_return": ET.tostring(login_return, encoding="unicode")}
            )

        if not sign:
            raise XMLParseException(
                "Sign not found in loginCmsReturn",
                details={"login_return": ET.tostring(login_return, encoding="unicode")}
            )

        try:
            generation_time = (
                parse_afip_timestamp(generation_time_str)
                if generation_time_str
                else datetime.utcnow()
            )
            expiration_time = (
                parse_afip_timestamp(expiration_time_str)
                if expiration_time_str
                else datetime.utcnow() + timedelta(hours=12)
            )
        except Exception as e:
            raise XMLParseException(
                f"Failed to parse timestamps: {str(e)}",
                details={
                    "generation_time": generation_time_str,
                    "expiration_time": expiration_time_str,
                }
            )

        return TokenData(
            token=token,
            sign=sign,
            generation_time=generation_time,
            expiration_time=expiration_time,
        )
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
    # Remover milisegundos si existen
    clean_ts = timestamp_str.split('.')[0]

    # Remover timezone si existe (convertir a UTC es complejo, asumimos UTC)
    if '+' in clean_ts or clean_ts.count('-') > 2:
        # Formato: 2024-03-14T10:30:00-03:00
        clean_ts = clean_ts.rsplit('-', 1)[0] if clean_ts.count('-') > 2 else clean_ts.rsplit('+', 1)[0]

    # Parsear como datetime naive
    try:
        dt = datetime.fromisoformat(clean_ts)
        return dt
    except ValueError:
        # Fallback: intentar formato básico
        dt = datetime.strptime(clean_ts, "%Y-%m-%dT%H:%M:%S")
        return dt


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
