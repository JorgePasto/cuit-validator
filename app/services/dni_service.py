"""
Servicio de consulta de personas por número de documento (DNI) en AFIP Padrón A13.

Orquesta la búsqueda de CUITs asociados a un DNI y la recolección de datos
básicos de cada persona, sin incluir información de domicilio.
"""

import logging
from typing import Optional

from app.connectors.padron_connector import PadronConnector, get_padron_connector
from app.exceptions.custom_exceptions import (
    AFIPServiceException,
    AuthenticationException,
)
from app.models.responses import PersonaSummaryResponse
from app.services.auth_service import AuthService, get_auth_service

logger = logging.getLogger(__name__)


class DNIService:
    """
    Servicio de consulta de personas por DNI.

    Responsabilidades:
    - Obtener token WSAA válido
    - Consultar la lista de CUITs asociados al DNI
    - Obtener datos básicos de cada persona (sin domicilio)
    - Manejar reintentos en caso de token expirado
    """

    def __init__(
        self,
        auth_service: Optional[AuthService] = None,
        padron_connector: Optional[PadronConnector] = None,
    ):
        """
        Inicializa el servicio de consulta por DNI.

        Args:
            auth_service: Servicio de autenticación (usa singleton si no se provee)
            padron_connector: Connector de Padrón (usa singleton si no se provee)
        """
        self.auth_service = auth_service or get_auth_service()
        self.padron_connector = padron_connector or get_padron_connector()
        self.service_name = "ws_sr_padron_a13"

    async def get_personas_by_dni(self, dni: str) -> list[PersonaSummaryResponse]:
        """
        Obtiene la lista de personas asociadas a un número de DNI.

        Flujo:
        1. Obtiene token WSAA válido (con cache)
        2. Consulta la lista de idPersona (CUITs) asociados al DNI
        3. Por cada idPersona, consulta los datos básicos (sin domicilio)
        4. Si falla por token expirado, reintenta con token nuevo

        Args:
            dni: Número de DNI a consultar

        Returns:
            Lista de PersonaSummaryResponse con datos básicos de cada persona

        Raises:
            AuthenticationException: Error de autenticación con AFIP
            AFIPServiceException: Error de comunicación con AFIP
        """
        try:
            clean_dni = dni.strip()
            logger.info(f"Getting personas for DNI: {clean_dni}")

            token_data = await self.auth_service.get_valid_token(service_name=self.service_name)

            try:
                personas = await self._fetch_personas(clean_dni, token_data)
            except AuthenticationException as e:
                logger.warning(
                    f"Authentication failed for DNI {clean_dni}, retrying with fresh token: {str(e)}"
                )
                token_data = await self.auth_service.refresh_token(service_name=self.service_name)
                personas = await self._fetch_personas(clean_dni, token_data)

            logger.info(f"Successfully retrieved {len(personas)} personas for DNI {clean_dni}")
            return personas

        except (AuthenticationException, AFIPServiceException):
            raise
        except Exception as e:
            logger.error(f"Unexpected error querying DNI {dni}: {str(e)}")
            raise AFIPServiceException(
                f"Unexpected error querying by DNI: {str(e)}",
                details={"dni": dni, "error": str(e)},
            )

    async def _fetch_personas(self, dni: str, token_data) -> list[PersonaSummaryResponse]:
        """
        Ejecuta la consulta al Padrón y orquesta la recolección de datos.

        Args:
            dni: DNI ya limpio
            token_data: Token WSAA válido

        Returns:
            Lista de PersonaSummaryResponse
        """
        # 1. Obtener lista de idPersona (CUITs) asociados al DNI
        id_personas = await self.padron_connector.get_id_persona_list_by_documento(
            documento=dni,
            token_data=token_data,
        )

        if not id_personas:
            logger.info(f"No personas found for DNI {dni}")
            return []

        # 2. Por cada idPersona, obtener datos básicos
        personas: list[PersonaSummaryResponse] = []
        for id_persona in id_personas:
            cuit_str = str(id_persona)
            try:
                logger.info(f"Fetching persona data for CUIT {cuit_str} (DNI {dni})")
                full_response = await self.padron_connector.get_persona_by_cuit(
                    cuit=cuit_str,
                    token_data=token_data,
                )
                personas.append(
                    PersonaSummaryResponse(
                        cuit=full_response.cuit,
                        tipo_persona=full_response.tipo_persona,
                        apellido=full_response.apellido,
                        nombre=full_response.nombre,
                        razon_social=full_response.razon_social,
                        estado_clave=full_response.estado_clave,
                    )
                )
            except Exception as e:
                # Loggear el error pero continuar con el resto de personas
                logger.warning(
                    f"Could not retrieve data for CUIT {cuit_str} (DNI {dni}): {str(e)}"
                )

        return personas


# Instancia global del servicio (Singleton)
_dni_service: Optional[DNIService] = None


def get_dni_service() -> DNIService:
    """
    Obtiene la instancia global del DNIService (Singleton pattern).

    Returns:
        DNIService instance
    """
    global _dni_service
    if _dni_service is None:
        _dni_service = DNIService()
    return _dni_service
