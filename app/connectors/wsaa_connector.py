"""
Connector para AFIP WSAA (Web Service de Autenticación y Autorización).

Este módulo maneja la comunicación directa con el servicio WSAA de AFIP para
obtener tokens de autenticación necesarios para consumir otros servicios AFIP.
"""

import logging
from typing import Optional

import httpx
import html

from app.config.settings import Settings
from app.exceptions.custom_exceptions import (
    AFIPServiceException,
    AuthenticationException,
    CertificateException,
    SignatureException,
    XMLParseException
)
from app.models.afip_models import TokenData
from app.utils.afip_logger import afip_logger
from app.utils.crypto_utils import sign_and_encode
from app.utils.xml_utils import (
    build_login_ticket_request,
    build_wsaa_soap_envelope,
    extract_soap_fault,
    parse_login_cms_response
)

logger = logging.getLogger(__name__)


class WSAAConnector:
    """
    Connector para AFIP WSAA - maneja autenticación mediante LoginCms.

    Responsabilidades:
    - Generar LoginTicketRequest XML
    - Firmar con certificado/clave privada (CMS/PKCS#7)
    - Enviar SOAP request a WSAA
    - Parsear respuesta y extraer TokenData
    """

    def __init__(self):
        """Inicializa el connector con configuración desde Settings."""
        self.settings = Settings()
        self.wsaa_url = self.settings.wsaa_url
        self.cert_path = self.settings.AFIP_CERT_PATH
        self.key_path = self.settings.AFIP_KEY_PATH
        self.key_passphrase = self.settings.AFIP_KEY_PASSPHRASE
        self.service_name = "ws_sr_padron_a13"

        # Validar certificados al inicializar
        try:
            self.settings.validate_certificates()
        except Exception as e:
            logger.error(f"Certificate validation failed: {str(e)}")
            raise CertificateException(
                "Failed to validate AFIP certificates",
                details={"error": str(e)}
            )

    async def get_token(self, service_name: Optional[str] = None) -> TokenData:
        """
        Obtiene un nuevo token de AFIP WSAA.

        Flujo completo:
        1. Genera LoginTicketRequest XML
        2. Firma con certificado (CMS/PKCS#7 Base64)
        3. Construye SOAP envelope
        4. POST a WSAA LoginCms
        5. Parsea respuesta y retorna TokenData

        Returns:
            TokenData con token, sign y timestamps

        Raises:
            AuthenticationException: Error de autenticación (certificado inválido, etc.)
            SignatureException: Error al firmar el request
            XMLParseException: Error parseando la respuesta
            AFIPServiceException: Error de comunicación con AFIP
        """
        try:
            used_service = service_name if service_name else self.service_name
            logger.info(f"Requesting new WSAA token for service: {used_service}")

            # PASO 1: Generar LoginTicketRequest XML
            login_ticket_xml = build_login_ticket_request(service=used_service)
            logger.debug(f"Generated LoginTicketRequest: {login_ticket_xml}")

            # PASO 2: Firmar con CMS/PKCS#7 y codificar en Base64
            try:
                cms_signature_b64 = sign_and_encode(
                    xml_data=login_ticket_xml,
                    cert_path=self.cert_path,
                    key_path=self.key_path,
                    passphrase=self.key_passphrase
                )
                logger.debug(f"CMS signature generated: {len(cms_signature_b64)} bytes (Base64)")
            except (CertificateException, SignatureException) as e:
                logger.error(f"Signature failed: {str(e)}")
                raise

            # PASO 3: Construir SOAP envelope
            soap_request = build_wsaa_soap_envelope(cms_signature_b64)
            logger.debug("SOAP envelope constructed")

            # PASO 4: Enviar request a WSAA
            try:
                token_data = await self._send_login_cms_request(soap_request)
                logger.info(
                    f"Token obtained successfully. Expires at: {token_data.expiration_time}"
                )
                return token_data

            except httpx.HTTPError as e:
                logger.error(f"HTTP error calling WSAA: {str(e)}")
                raise AFIPServiceException(
                    f"Failed to call WSAA service: {str(e)}",
                    details={"url": self.wsaa_url, "error": str(e)}
                )

        except (AuthenticationException, SignatureException, XMLParseException, AFIPServiceException):
            # Re-raise custom exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_token: {str(e)}")
            raise AFIPServiceException(
                f"Unexpected error obtaining WSAA token: {str(e)}",
                details={"error": str(e)}
            )

    async def _send_login_cms_request(self, soap_request: str) -> TokenData:
        """
        Envía el SOAP request a WSAA y parsea la respuesta.

        Args:
            soap_request: SOAP envelope completo con la firma CMS

        Returns:
            TokenData parseado de la respuesta

        Raises:
            AuthenticationException: Error de autenticación
            XMLParseException: Error parseando respuesta
            AFIPServiceException: Error HTTP
        """
        # Generar correlation ID para trazabilidad
        correlation_id = afip_logger.generate_correlation_id()
        
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": ""  # WSAA no requiere SOAPAction específico
        }

        # LOG REQUEST
        start_time = afip_logger.log_soap_request(
            correlation_id=correlation_id,
            service="WSAA",
            operation="loginCms",
            soap_envelope=soap_request,
            url=self.wsaa_url,
            headers=headers
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.wsaa_url,
                    content=soap_request.encode('utf-8'),
                    headers=headers
                )
                logger.debug(f"WSAA response status: {response.status_code}")
                # LOG RESPONSE
                response_headers = dict(response.headers)
                afip_logger.log_soap_response(
                    correlation_id=correlation_id,
                    service="WSAA",
                    operation="loginCms",
                    start_time=start_time,
                    status_code=response.status_code,
                    soap_response=response.text,
                    headers=response_headers,
                    error=None if response.status_code == 200 else f"HTTP {response.status_code}"
                )

                # Validar status code
                if response.status_code != 200:
                    # Intentar extraer SOAP Fault
                    fault_message = extract_soap_fault(response.text)
                    if fault_message:
                        logger.error(f"SOAP Fault received: {fault_message}")
                        
                        # Detectar error de token ya existente (alreadyAuthenticated)
                        if "coe.alreadyAuthenticated" in fault_message or "ya posee un TA valido" in fault_message:
                            helpful_message = (
                                f"AFIP authentication failed: {fault_message}\n\n"
                                "CAUSA: AFIP ya emitió un token válido para este certificado y no permite solicitar uno nuevo.\n"
                                "SOLUCIÓN:\n"
                                "1. Esperar unos minutos para que el token existente en AFIP expire (o que el sistema lo detecte)\n"
                                "2. El token típicamente expira después de ~12 horas\n"
                                "3. Verificar que el sistema de caché local esté funcionando correctamente\n"
                                "4. Si el problema persiste, el certificado puede estar siendo usado por otro sistema/proceso"
                            )
                            raise AuthenticationException(
                                helpful_message,
                                details={
                                    "status_code": response.status_code,
                                    "fault": fault_message,
                                    "solution": "Wait for existing token to expire or check if certificate is being used elsewhere",
                                    "retry_recommended": True,
                                    "retry_wait_seconds": 300  # 5 minutos
                                }
                            )
                        
                        # Detectar error de certificado no autorizado
                        if "coe.notAuthorized" in fault_message or "Computador no autorizado" in fault_message:
                            helpful_message = (
                                f"AFIP authentication failed: {fault_message}\n\n"
                                "SOLUCIÓN: Tu certificado no está asociado al servicio 'ws_sr_padron_a13' en AFIP.\n"
                                "Debes seguir estos pasos:\n"
                                "1. Ir a https://auth.afip.gob.ar/contribuyente_/acceso.xhtml\n"
                                "2. Ingresar con Clave Fiscal (nivel 3 requerido)\n"
                                "3. Administrador de Relaciones de Clave Fiscal > Alta de Relación\n"
                                "4. Buscar 'ws_sr_padron_a13' y asociar tu certificado como Computador Fiscal\n"
                                "5. Consultar el TUTORIAL-CERTIFICADOS-AFIP.md para más detalles"
                            )
                            raise AuthenticationException(
                                helpful_message,
                                details={
                                    "status_code": response.status_code,
                                    "fault": fault_message,
                                    "solution": "Certificate not associated with ws_sr_padron_a13 service in AFIP portal"
                                }
                            )
                        
                        # Detectar error de expirationTime inválido
                        if "expirationTime.invalid" in fault_message:
                            helpful_message = (
                                f"AFIP authentication failed: {fault_message}\n\n"
                                "SOLUCIÓN: El timestamp de expiración es inválido.\n"
                                "Posibles causas:\n"
                                "1. Expiración configurada en más de 24 horas\n"
                                "2. Formato de timestamp incorrecto (debe incluir timezone)\n"
                                "3. Reloj del sistema desincronizado"
                            )
                            raise AuthenticationException(
                                helpful_message,
                                details={
                                    "status_code": response.status_code,
                                    "fault": fault_message,
                                    "solution": "Fix timestamp format or expiration time"
                                }
                            )
                        
                        # Error genérico de autenticación
                        raise AuthenticationException(
                            f"AFIP authentication failed: {fault_message}",
                            details={
                                "status_code": response.status_code,
                                "fault": fault_message
                            }
                        )

                    raise AFIPServiceException(
                        f"WSAA returned error status: {response.status_code}",
                        details={
                            "status_code": response.status_code,
                            "response": response.text[:500]
                        }
                    )

                # Parsear respuesta XML
                response_xml = response.text

                # Algunas respuestas vienen con el contenido de <loginCmsReturn>
                # como XML escapado (&lt; ... &gt;). Para evitar que el parser
                # reciba el texto 'dañado', unescapeamos aquí antes de parsear.
                response_unescape_xml = html.unescape(response_xml)
                logger.debug(f"Response XML received: {response_unescape_xml}")
                # Verificar si hay SOAP Fault en respuesta 200 (algunos servicios lo hacen)
                fault_message = extract_soap_fault(response_xml)
                if fault_message:
                    logger.error(f"SOAP Fault in 200 response: {fault_message}")
                    raise AuthenticationException(
                        f"AFIP authentication failed: {fault_message}",
                        details={"fault": fault_message}
                    )
                # Parsear LoginCmsResponse
                token_data = parse_login_cms_response(response_xml)

                return token_data

            except httpx.TimeoutException as e:
                logger.error(f"Timeout calling WSAA: {str(e)}")
                raise AFIPServiceException(
                    "Timeout connecting to AFIP WSAA service",
                    details={"timeout": 30.0, "url": self.wsaa_url}
                )
            except httpx.RequestError as e:
                logger.error(f"Request error calling WSAA: {str(e)}")
                raise AFIPServiceException(
                    f"Network error calling WSAA: {str(e)}",
                    details={"url": self.wsaa_url, "error": str(e)}
                )

    def get_service_name(self) -> str:
        """Retorna el nombre del servicio AFIP configurado."""
        return self.service_name


# Instancia global del connector (opcional, para uso directo)
_wsaa_connector: Optional[WSAAConnector] = None


def get_wsaa_connector() -> WSAAConnector:
    """
    Obtiene la instancia global del WSAAConnector (Singleton pattern).

    Returns:
        WSAAConnector instance
    """
    global _wsaa_connector
    if _wsaa_connector is None:
        _wsaa_connector = WSAAConnector()
    return _wsaa_connector
