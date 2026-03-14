"""
Connector para AFIP Padrón A10 - Consulta de datos de contribuyentes.

Este módulo maneja la comunicación con el Web Service sr-padron A10 de AFIP
para obtener información de contribuyentes (nombres y domicilios fiscales).
"""

import logging
from typing import Optional

from zeep import Client
from zeep.exceptions import Fault as ZeepFault, TransportError, XMLParseError
from zeep.transports import Transport

from app.config.settings import Settings
from app.exceptions.custom_exceptions import (
    AFIPServiceException,
    CUITNotFoundException,
    XMLParseException
)
from app.models.afip_models import TokenData
from app.models.responses import DomicilioFiscal, PersonaResponse

logger = logging.getLogger(__name__)


class PadronConnector:
    """
    Connector para AFIP Padrón A10 - consulta datos de contribuyentes.

    Utiliza Zeep (cliente SOAP Python) para consumir el WSDL del servicio.

    Responsabilidades:
    - Consultar datos de personas por CUIT
    - Parsear respuesta XML del servicio
    - Transformar a modelos internos (PersonaResponse)
    """

    def __init__(self):
        """Inicializa el connector con configuración desde Settings."""
        self.settings = Settings()
        self.padron_url = self.settings.padron_url
        self.wsdl_url = f"{self.padron_url}?wsdl"

        # Configurar transporte con timeout
        self.transport = Transport(timeout=30)

        # Cliente Zeep (lazy initialization)
        self._client: Optional[Client] = None

    def _get_client(self) -> Client:
        """
        Obtiene el cliente Zeep (lazy initialization).

        Returns:
            Cliente Zeep configurado

        Raises:
            AFIPServiceException: Error creando el cliente
        """
        if self._client is None:
            try:
                logger.info(f"Initializing Zeep client for Padrón A10: {self.wsdl_url}")
                self._client = Client(wsdl=self.wsdl_url, transport=self.transport)
                logger.debug("Zeep client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Zeep client: {str(e)}")
                raise AFIPServiceException(
                    f"Failed to initialize AFIP Padrón client: {str(e)}",
                    details={"wsdl_url": self.wsdl_url, "error": str(e)}
                )

        return self._client

    async def get_persona_by_cuit(
        self,
        cuit: str,
        token_data: TokenData
    ) -> PersonaResponse:
        """
        Consulta datos de una persona/contribuyente por CUIT.

        Args:
            cuit: CUIT a consultar (11 dígitos, con o sin guiones)
            token_data: Token de autenticación WSAA

        Returns:
            PersonaResponse con datos del contribuyente

        Raises:
            CUITNotFoundException: CUIT no encontrado en AFIP
            AFIPServiceException: Error de comunicación con AFIP
            XMLParseException: Error parseando respuesta
        """
        try:
            # Limpiar CUIT (remover guiones si existen)
            clean_cuit = cuit.replace("-", "").strip()

            logger.info(f"Querying Padrón A10 for CUIT: {clean_cuit}")

            # Obtener cliente Zeep
            client = self._get_client()

            # Preparar parámetros del request
            # Basado en el WSDL de Padrón A10, el método es getPersona
            request_params = {
                "token": token_data.token,
                "sign": token_data.sign,
                "cuitRepresentada": clean_cuit  # CUIT a consultar
            }

            logger.debug(f"Request params: {request_params}")

            # Llamar al servicio SOAP
            try:
                # Método del WSDL: getPersona o similar (ajustar según WSDL real)
                # Nota: Verificar nombre exacto del método en WSDL
                response = client.service.getPersona(**request_params)

                logger.debug(f"Response received for CUIT {clean_cuit}")

                # Parsear respuesta a PersonaResponse
                persona_response = self._parse_persona_response(clean_cuit, response)

                return persona_response

            except ZeepFault as e:
                # SOAP Fault - puede indicar CUIT no encontrado
                fault_message = str(e)
                logger.warning(f"SOAP Fault for CUIT {clean_cuit}: {fault_message}")

                # Verificar si es un error de "no encontrado"
                if any(keyword in fault_message.lower() for keyword in ["no encontrado", "not found", "inexistente"]):
                    raise CUITNotFoundException(
                        f"CUIT {clean_cuit} not found in AFIP",
                        details={"cuit": clean_cuit, "fault": fault_message}
                    )

                raise AFIPServiceException(
                    f"AFIP service error: {fault_message}",
                    details={"cuit": clean_cuit, "fault": fault_message}
                )

            except TransportError as e:
                logger.error(f"Transport error querying CUIT {clean_cuit}: {str(e)}")
                raise AFIPServiceException(
                    f"Network error calling AFIP Padrón: {str(e)}",
                    details={"cuit": clean_cuit, "error": str(e)}
                )

            except XMLParseError as e:
                logger.error(f"XML parse error for CUIT {clean_cuit}: {str(e)}")
                raise XMLParseException(
                    f"Failed to parse AFIP response: {str(e)}",
                    details={"cuit": clean_cuit, "error": str(e)}
                )

        except (CUITNotFoundException, AFIPServiceException, XMLParseException):
            raise
        except Exception as e:
            logger.error(f"Unexpected error querying CUIT {cuit}: {str(e)}")
            raise AFIPServiceException(
                f"Unexpected error querying CUIT: {str(e)}",
                details={"cuit": cuit, "error": str(e)}
            )

    def _parse_persona_response(self, cuit: str, response: dict) -> PersonaResponse:
        """
        Parsea la respuesta del servicio Padrón A10 a PersonaResponse.

        La estructura de respuesta puede variar, pero generalmente incluye:
        - datosGenerales: nombre, apellido, razon social, tipo persona
        - domicilioFiscal: dirección, localidad, provincia, código postal

        Args:
            cuit: CUIT consultado
            response: Respuesta del servicio (dict de Zeep)

        Returns:
            PersonaResponse

        Raises:
            XMLParseException: Si la respuesta no tiene el formato esperado
        """
        try:
            logger.debug(f"Parsing response for CUIT {cuit}")

            # Estructura esperada (ajustar según WSDL real):
            # response.persona.datosGenerales
            # response.persona.domicilioFiscal

            # Verificar que response tenga datos
            if response is None:
                raise XMLParseException(
                    f"Empty response from AFIP for CUIT {cuit}",
                    details={"cuit": cuit}
                )

            # Extraer datos generales
            datos_generales = getattr(response, "datosGenerales", None)
            if datos_generales is None:
                raise XMLParseException(
                    "datosGenerales not found in AFIP response",
                    details={"cuit": cuit, "response": str(response)[:500]}
                )

            # Campos de persona
            tipo_persona = getattr(datos_generales, "tipoPersona", None)
            apellido = getattr(datos_generales, "apellido", None)
            nombre = getattr(datos_generales, "nombre", None)
            razon_social = getattr(datos_generales, "razonSocial", None)

            # Estado de la clave (activo/inactivo)
            estado_clave = getattr(datos_generales, "estadoClave", "ACTIVO")

            # Extraer domicilio fiscal
            domicilio_fiscal_data = getattr(response, "domicilioFiscal", None)
            domicilio_fiscal = None

            if domicilio_fiscal_data is not None:
                domicilio_fiscal = DomicilioFiscal(
                    direccion=getattr(domicilio_fiscal_data, "direccion", None),
                    localidad=getattr(domicilio_fiscal_data, "localidad", None),
                    provincia=getattr(domicilio_fiscal_data, "descripcionProvincia", None),
                    codigo_postal=getattr(domicilio_fiscal_data, "codPostal", None)
                )

            # Construir PersonaResponse
            persona_response = PersonaResponse(
                cuit=cuit,
                tipo_persona=tipo_persona,
                apellido=apellido,
                nombre=nombre,
                razon_social=razon_social,
                domicilio_fiscal=domicilio_fiscal,
                estado_clave=estado_clave
            )

            logger.info(f"Successfully parsed response for CUIT {cuit}")

            return persona_response

        except XMLParseException:
            raise
        except Exception as e:
            logger.error(f"Error parsing response for CUIT {cuit}: {str(e)}")
            raise XMLParseException(
                f"Failed to parse persona response: {str(e)}",
                details={"cuit": cuit, "error": str(e), "response": str(response)[:500]}
            )


# Instancia global del connector (opcional, para uso directo)
_padron_connector: Optional[PadronConnector] = None


def get_padron_connector() -> PadronConnector:
    """
    Obtiene la instancia global del PadronConnector (Singleton pattern).

    Returns:
        PadronConnector instance
    """
    global _padron_connector
    if _padron_connector is None:
        _padron_connector = PadronConnector()
    return _padron_connector
