"""
Connector para AFIP WSAA (Web Service de Autenticación y Autorización).

Este módulo maneja la comunicación directa con el servicio WSAA de AFIP para
obtener tokens de autenticación necesarios para consumir otros servicios AFIP.
"""

import logging
from typing import Optional

import httpx

from app.config.settings import Settings
from app.exceptions.custom_exceptions import (
    AFIPServiceException,
    AuthenticationException,
    CertificateException,
    SignatureException,
    XMLParseException
)
from app.models.afip_models import TokenData
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
        self.cert_path = self.settings.afip_cert_path
        self.key_path = self.settings.afip_key_path
        self.key_passphrase = self.settings.afip_key_passphrase
        self.service_name = "ws_sr_padron_a10"

        # Validar certificados al inicializar
        try:
            self.settings.validate_certificates()
        except Exception as e:
            logger.error(f"Certificate validation failed: {str(e)}")
            raise CertificateException(
                "Failed to validate AFIP certificates",
                details={"error": str(e)}
            )

    async def get_token(self) -> TokenData:
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
            logger.info(f"Requesting new WSAA token for service: {self.service_name}")

            # PASO 1: Generar LoginTicketRequest XML
            login_ticket_xml = build_login_ticket_request(service=self.service_name)
            logger.debug(f"Generated LoginTicketRequest: {login_ticket_xml[:200]}...")

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
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": ""  # WSAA no requiere SOAPAction específico
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.wsaa_url,
                    content=soap_request.encode('utf-8'),
                    headers=headers
                )

                logger.debug(f"WSAA response status: {response.status_code}")

                # Validar status code
                if response.status_code != 200:
                    # Intentar extraer SOAP Fault
                    fault_message = extract_soap_fault(response.text)
                    if fault_message:
                        logger.error(f"SOAP Fault received: {fault_message}")
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
                logger.debug(f"Response XML received: {len(response_xml)} bytes")

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
