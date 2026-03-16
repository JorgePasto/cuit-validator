"""
Connector para AFIP Padrón A13 - Consulta de datos de contribuyentes.

Este módulo maneja la comunicación con el Web Service sr-padron A13 de AFIP
para obtener información de contribuyentes (nombres y domicilios fiscales).
"""

import logging
from typing import Optional

from zeep import Client
from zeep.exceptions import Fault as ZeepFault, TransportError, XMLParseError
from zeep.transports import Transport
from zeep.plugins import HistoryPlugin

from app.config.settings import Settings
from app.exceptions.custom_exceptions import (
    AFIPServiceException,
    CUITNotFoundException,
    XMLParseException
)
from app.models.afip_models import TokenData
from app.models.responses import DomicilioFiscal, PersonaResponse
from app.utils.afip_logger import afip_logger

logger = logging.getLogger(__name__)


class PadronConnector:
    """
    Connector para AFIP Padrón A13 - consulta datos de contribuyentes.

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
        
        # Plugin para capturar requests/responses SOAP
        self.history = HistoryPlugin()

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
                logger.info(f"Initializing Zeep client for Padrón A13: {self.wsdl_url}")
                self._client = Client(
                    wsdl=self.wsdl_url, 
                    transport=self.transport,
                    plugins=[self.history]  # Agregar plugin para capturar SOAP
                )
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

            logger.info(f"Querying Padrón A13 for CUIT: {clean_cuit}")

            # Obtener cliente Zeep
            client = self._get_client()

            # Preparar parámetros del request según WSDL (getPersona)
            # En el WSDL cuitRepresentada e idPersona son tipo long, enviarlos como int
            request_params = {
                "token": token_data.token,
                "sign": token_data.sign,
                "cuitRepresentada": int(clean_cuit),  # CUIT del certificado (quien consulta)
                "idPersona": int(clean_cuit)           # CUIT a consultar (para autoconsulta, ambos son iguales)
            }

            logger.debug(f"Request params: {request_params}")

            # Generar correlation ID para trazabilidad
            correlation_id = afip_logger.generate_correlation_id()
            
            # LOG REQUEST
            from datetime import datetime
            start_time = afip_logger.log_request(
                correlation_id=correlation_id,
                service="PersonaServiceA13",
                operation="getPersona",
                request_data={
                    "cuitRepresentada": clean_cuit,
                    "idPersona": clean_cuit,
                    "token_length": len(token_data.token),
                    "sign_length": len(token_data.sign)
                },
                url=self.padron_url
            )

            # Llamar al servicio SOAP
            try:
                # Método del WSDL A13: getPersona
                response = client.service.getPersona(**request_params)

                logger.debug(f"Response received for CUIT {clean_cuit}")
                
                # LOG RESPONSE (exitoso)
                # Capturar SOAP request/response usando HistoryPlugin
                soap_request = None
                soap_response = None
                if self.history.last_sent:
                    soap_request = self.history.last_sent.get("envelope")
                if self.history.last_received:
                    soap_response = self.history.last_received.get("envelope")
                
                # Loggear SOAP completo si está disponible
                if soap_request:
                    from lxml import etree
                    soap_request_str = etree.tostring(soap_request, encoding='unicode', pretty_print=True)
                    logger.debug(f"[{correlation_id}] SOAP Request:\n{soap_request_str}")
                    
                if soap_response:
                    from lxml import etree
                    soap_response_str = etree.tostring(soap_response, encoding='unicode', pretty_print=True)
                    logger.debug(f"[{correlation_id}] SOAP Response:\n{soap_response_str}")
                    
                    afip_logger.log_soap_response(
                        correlation_id=correlation_id,
                        service="PersonaServiceA13",
                        operation="getPersona",
                        start_time=start_time,
                        status_code=200,
                        soap_response=soap_response_str,
                        error=None
                    )
                else:
                    # Fallback si no hay history
                    afip_logger.log_response(
                        correlation_id=correlation_id,
                        service="PersonaServiceA13",
                        operation="getPersona",
                        start_time=start_time,
                        status_code=200,
                        response_data={"status": "success", "cuit": clean_cuit},
                        error=None
                    )

                # Parsear respuesta a PersonaResponse
                persona_response = self._parse_persona_response(clean_cuit, response)

                return persona_response

            except ZeepFault as e:
                # SOAP Fault - puede indicar CUIT no encontrado
                fault_message = str(e)
                logger.warning(f"SOAP Fault for CUIT {clean_cuit}: {fault_message}")
                
                # LOG ERROR RESPONSE
                afip_logger.log_response(
                    correlation_id=correlation_id,
                    service="PersonaServiceA13",
                    operation="getPersona",
                    start_time=start_time,
                    status_code=500,
                    response_data={"fault": fault_message, "cuit": clean_cuit},
                    error=fault_message
                )

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
                
                # LOG ERROR RESPONSE
                afip_logger.log_response(
                    correlation_id=correlation_id,
                    service="PersonaServiceA13",
                    operation="getPersona",
                    start_time=start_time,
                    status_code=502,
                    response_data={"error": str(e), "cuit": clean_cuit},
                    error=f"Transport error: {str(e)}"
                )
                
                raise AFIPServiceException(
                    f"Network error calling AFIP Padrón: {str(e)}",
                    details={"cuit": clean_cuit, "error": str(e)}
                )

            except XMLParseError as e:
                logger.error(f"XML parse error for CUIT {clean_cuit}: {str(e)}")
                
                # LOG ERROR RESPONSE
                afip_logger.log_response(
                    correlation_id=correlation_id,
                    service="PersonaServiceA13",
                    operation="getPersona",
                    start_time=start_time,
                    status_code=500,
                    response_data={"error": str(e), "cuit": clean_cuit},
                    error=f"XML parse error: {str(e)}"
                )
                
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
        Parsea la respuesta del servicio Padrón A13 a PersonaResponse.

        La estructura de respuesta de A13 incluye datos adicionales vs A10:
        - datosGenerales: nombre, apellido, razon social, tipo persona
        - domicilioFiscal: dirección, localidad, provincia, código postal
        - actividades: lista de actividades económicas (NO se expone en API)
        - impuestos: lista de impuestos inscriptos (NO se expone en API)
        - categoriaMonotributo: categoría si corresponde (NO se expone en API)

        NOTA: Esta función mantiene el contrato del API sin cambios. Los campos adicionales
        de A13 se loggean completamente (ver _log_full_a13_response) pero no se exponen
        en PersonaResponse para mantener backward compatibility con consumers.

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

            # Loggear el response completo de A13 para debugging/auditoría
            self._log_full_a13_response(cuit, response)

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

    def _log_full_a13_response(self, cuit: str, response) -> None:
        """
        Loggea el response completo de A13 para debugging y auditoría.

        A13 devuelve información adicional vs A10 (actividades, impuestos, monotributo, etc.)
        que no se expone en el API para mantener el contrato. Este método registra
        toda la respuesta para propósitos de debugging y auditoría futura.

        Args:
            cuit: CUIT consultado
            response: Response object completo de Zeep (objeto con estructura compleja)

        Returns:
            None (solo loggea, no retorna valor)

        Notas:
            - Usa serialize_object de zeep.helpers para convertir response a dict
            - Loggea a nivel INFO con estructura JSON en campo extra
            - Loggea a nivel DEBUG con formato pretty-print para lectura humana
            - Errores de serialización/logging NO interrumpen el flujo (se capturan)
        """
        try:
            import json
            from zeep.helpers import serialize_object
            
            # Convertir response de Zeep a dict serializable
            response_dict = serialize_object(response)
            
            # Log estructurado a nivel INFO (para agregadores de logs)
            logger.info(
                f"A13 Full Response for CUIT {cuit}",
                extra={
                    "cuit": cuit,
                    "service": "ws_sr_padron_a13",
                    "response_data": response_dict
                }
            )
            
            # Log pretty-print a nivel DEBUG (para debugging local)
            logger.debug(
                f"A13 Response Detail for CUIT {cuit}:\n"
                f"{json.dumps(response_dict, indent=2, ensure_ascii=False, default=str)}"
            )
            
        except Exception as e:
            # No interrumpir el flujo principal si falla el logging
            logger.warning(
                f"Could not log full A13 response for CUIT {cuit}: {str(e)}",
                exc_info=True
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
