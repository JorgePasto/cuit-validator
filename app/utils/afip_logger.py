"""
Utilidad para logging estructurado de requests/responses AFIP.

Este módulo proporciona funciones para loggear todas las comunicaciones con AFIP
con un formato estructurado y trazabilidad mediante correlation_id.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Directorio para logs de XMLs literales
XML_LOGS_DIR = Path("logs/xml")
XML_LOGS_DIR.mkdir(parents=True, exist_ok=True)


class AFIPRequestLogger:
    """
    Logger estructurado para requests/responses de AFIP.
    
    Genera logs con formato:
    [REQ] {correlation_id} | {service} | {operation} | {timestamp}
    [RSP] {correlation_id} | {service} | {operation} | {status} | {duration_ms}
    """
    
    @staticmethod
    def generate_correlation_id() -> str:
        """
        Genera un ID de correlación único para trazabilidad.
        
        Returns:
            UUID v4 como string (ej: "a1b2c3d4-e5f6-...")
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def log_request(
        correlation_id: str,
        service: str,
        operation: str,
        request_data: Dict[str, Any],
        url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> datetime:
        """
        Loggea un request AFIP.
        
        Args:
            correlation_id: ID único para correlacionar REQ-RSP
            service: Nombre del servicio (ej: "WSAA", "PADRON_A13")
            operation: Operación llamada (ej: "LoginCms", "getPersona_v2")
            request_data: Datos del request (params, body, etc.)
            url: URL del servicio AFIP
            headers: Headers HTTP opcionales
            
        Returns:
            Timestamp de inicio (para calcular duración)
        """
        start_time = datetime.utcnow()
        
        # Log estructurado (JSON para agregadores de logs)
        log_entry = {
            "type": "REQUEST",
            "correlation_id": correlation_id,
            "service": service,
            "operation": operation,
            "timestamp": start_time.isoformat(),
            "url": url,
            "headers": headers or {},
            "request_data": request_data
        }
        
        logger.info(
            f"[REQ] {correlation_id} | {service} | {operation}",
            extra={"afip_request": log_entry}
        )
        
        # Log human-readable para debugging local
        logger.debug(
            f"\n{'='*80}\n"
            f"[AFIP REQUEST]\n"
            f"Correlation ID: {correlation_id}\n"
            f"Service: {service}\n"
            f"Operation: {operation}\n"
            f"URL: {url}\n"
            f"Timestamp: {start_time.isoformat()}\n"
            f"Headers: {json.dumps(headers or {}, indent=2)}\n"
            f"Request Data:\n{json.dumps(request_data, indent=2, ensure_ascii=False, default=str)}\n"
            f"{'='*80}"
        )
        
        return start_time
    
    @staticmethod
    def log_response(
        correlation_id: str,
        service: str,
        operation: str,
        start_time: datetime,
        status_code: int,
        response_data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        error: Optional[str] = None
    ):
        """
        Loggea un response AFIP.
        
        Args:
            correlation_id: ID único (mismo que en log_request)
            service: Nombre del servicio
            operation: Operación llamada
            start_time: Timestamp de inicio (retornado por log_request)
            status_code: HTTP status code
            response_data: Datos de la respuesta
            headers: Headers HTTP opcionales
            error: Mensaje de error si hubo falla
        """
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        status = "SUCCESS" if status_code == 200 and not error else "ERROR"
        
        # Log estructurado (JSON)
        log_entry = {
            "type": "RESPONSE",
            "correlation_id": correlation_id,
            "service": service,
            "operation": operation,
            "timestamp": end_time.isoformat(),
            "status": status,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "headers": headers or {},
            "response_data": response_data,
            "error": error
        }
        
        log_level = logging.INFO if status == "SUCCESS" else logging.ERROR
        
        logger.log(
            log_level,
            f"[RSP] {correlation_id} | {service} | {operation} | {status} | {duration_ms}ms",
            extra={"afip_response": log_entry}
        )
        
        # Log human-readable
        logger.debug(
            f"\n{'='*80}\n"
            f"[AFIP RESPONSE]\n"
            f"Correlation ID: {correlation_id}\n"
            f"Service: {service}\n"
            f"Operation: {operation}\n"
            f"Status: {status} ({status_code})\n"
            f"Duration: {duration_ms}ms\n"
            f"Timestamp: {end_time.isoformat()}\n"
            f"Headers: {json.dumps(headers or {}, indent=2)}\n"
            f"Response Data:\n{json.dumps(response_data, indent=2, ensure_ascii=False, default=str)}\n"
            f"{'='*80}"
        )
    
    @staticmethod
    def _write_xml_to_file(correlation_id: str, service: str, operation: str, direction: str, xml_content: str):
        """
        Escribe el XML literal a un archivo para debugging.
        
        Args:
            correlation_id: ID de correlación
            service: Servicio AFIP
            operation: Operación llamada
            direction: "REQUEST" o "RESPONSE"
            xml_content: Contenido XML completo
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{timestamp}_{correlation_id[:8]}_{service}_{operation}_{direction}.xml"
            filepath = XML_LOGS_DIR / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            logger.debug(f"XML {direction} guardado en: {filepath}")
        except Exception as e:
            logger.warning(f"No se pudo guardar XML {direction} en archivo: {str(e)}")
    
    @staticmethod
    def log_soap_request(
        correlation_id: str,
        service: str,
        operation: str,
        soap_envelope: str,
        url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> datetime:
        """
        Loggea un SOAP request AFIP (variante para XML).
        
        Args:
            correlation_id: ID único
            service: Nombre del servicio
            operation: Operación SOAP
            soap_envelope: SOAP envelope completo (XML)
            url: URL del servicio
            headers: Headers HTTP
            
        Returns:
            Timestamp de inicio
        """
        start_time = datetime.utcnow()
        
        # GUARDAR XML LITERAL EN ARCHIVO
        AFIPRequestLogger._write_xml_to_file(
            correlation_id=correlation_id,
            service=service,
            operation=operation,
            direction="REQUEST",
            xml_content=soap_envelope
        )
        
        # Truncar SOAP envelope si es muy largo (mantener primeros 2000 chars)
        soap_preview = soap_envelope[:2000] + "..." if len(soap_envelope) > 2000 else soap_envelope
        
        request_data = {
            "soap_envelope": soap_envelope,
            "soap_preview": soap_preview,
            "soap_length": len(soap_envelope)
        }
        
        log_entry = {
            "type": "REQUEST",
            "correlation_id": correlation_id,
            "service": service,
            "operation": operation,
            "timestamp": start_time.isoformat(),
            "url": url,
            "headers": headers or {},
            "request_type": "SOAP",
            "soap_length": len(soap_envelope)
        }
        
        logger.info(
            f"[REQ] {correlation_id} | {service} | {operation}",
            extra={"afip_request": log_entry}
        )
        
        # Log human-readable con XML formateado (siempre se muestra, no solo en DEBUG)
        logger.info(
            f"\n{'='*80}\n"
            f"[AFIP SOAP REQUEST - XML LITERAL]\n"
            f"Correlation ID: {correlation_id}\n"
            f"Service: {service}\n"
            f"Operation: {operation}\n"
            f"URL: {url}\n"
            f"Timestamp: {start_time.isoformat()}\n"
            f"SOAP Length: {len(soap_envelope)} bytes\n"
            f"Headers: {json.dumps(headers or {}, indent=2)}\n"
            f"{'='*80}\n"
            f"SOAP Envelope:\n{soap_envelope}\n"
            f"{'='*80}"
        )
        
        return start_time
    
    @staticmethod
    def log_soap_response(
        correlation_id: str,
        service: str,
        operation: str,
        start_time: datetime,
        status_code: int,
        soap_response: str,
        headers: Optional[Dict[str, str]] = None,
        error: Optional[str] = None
    ):
        """
        Loggea un SOAP response AFIP (variante para XML).
        
        Args:
            correlation_id: ID único
            service: Nombre del servicio
            operation: Operación SOAP
            start_time: Timestamp de inicio
            status_code: HTTP status code
            soap_response: SOAP response completo (XML)
            headers: Headers HTTP
            error: Mensaje de error si hubo
        """
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        status = "SUCCESS" if status_code == 200 and not error else "ERROR"
        
        # GUARDAR XML LITERAL EN ARCHIVO
        AFIPRequestLogger._write_xml_to_file(
            correlation_id=correlation_id,
            service=service,
            operation=operation,
            direction="RESPONSE",
            xml_content=soap_response
        )
        
        # Truncar response si es muy largo
        soap_preview = soap_response[:2000] + "..." if len(soap_response) > 2000 else soap_response
        
        log_entry = {
            "type": "RESPONSE",
            "correlation_id": correlation_id,
            "service": service,
            "operation": operation,
            "timestamp": end_time.isoformat(),
            "status": status,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "headers": headers or {},
            "response_type": "SOAP",
            "soap_length": len(soap_response),
            "error": error
        }
        
        log_level = logging.INFO if status == "SUCCESS" else logging.ERROR
        
        logger.log(
            log_level,
            f"[RSP] {correlation_id} | {service} | {operation} | {status} | {duration_ms}ms",
            extra={"afip_response": log_entry}
        )
        
        # Log human-readable con XML formateado (siempre se muestra, no solo en DEBUG)
        logger.log(
            log_level,
            f"\n{'='*80}\n"
            f"[AFIP SOAP RESPONSE - XML LITERAL]\n"
            f"Correlation ID: {correlation_id}\n"
            f"Service: {service}\n"
            f"Operation: {operation}\n"
            f"Status: {status} ({status_code})\n"
            f"Duration: {duration_ms}ms\n"
            f"Timestamp: {end_time.isoformat()}\n"
            f"SOAP Length: {len(soap_response)} bytes\n"
            f"Headers: {json.dumps(headers or {}, indent=2)}\n"
            f"{'='*80}\n"
            f"SOAP Response:\n{soap_response}\n"
            f"{'='*80}"
        )


# Instancia global para uso directo
afip_logger = AFIPRequestLogger()
