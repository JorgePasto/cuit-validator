"""
Servicio de consulta de CUITs en AFIP Padrón A10.

Este módulo maneja la lógica de negocio para consultar información de contribuyentes.
Coordina la autenticación WSAA y las consultas al Padrón.
"""

import logging
from typing import Optional

from app.connectors.padron_connector import PadronConnector, get_padron_connector
from app.exceptions.custom_exceptions import (
    AFIPServiceException,
    AuthenticationException,
    CUITNotFoundException,
    InvalidCUITException
)
from app.models.responses import PersonaResponse
from app.services.auth_service import AuthService, get_auth_service

logger = logging.getLogger(__name__)


class CUITService:
    """
    Servicio de consulta de CUITs con autenticación automática.

    Responsabilidades:
    - Validar formato de CUIT
    - Obtener token WSAA válido
    - Consultar datos en Padrón A10
    - Manejar reintentos en caso de token expirado
    """

    def __init__(
        self,
        auth_service: Optional[AuthService] = None,
        padron_connector: Optional[PadronConnector] = None
    ):
        """
        Inicializa el servicio de consulta de CUITs.

        Args:
            auth_service: Servicio de autenticación (opcional, usa singleton si no se provee)
            padron_connector: Connector de Padrón (opcional, usa singleton si no se provee)
        """
        self.auth_service = auth_service or get_auth_service()
        self.padron_connector = padron_connector or get_padron_connector()
        # Nombre del servicio WSAA utilizado para consultar el Padrón A13
        self.service_name = "ws_sr_padron_a13"

    async def get_persona_by_cuit(self, cuit: str) -> PersonaResponse:
        """
        Obtiene información de una persona/contribuyente por CUIT.

        Flujo:
        1. Valida formato de CUIT
        2. Obtiene token WSAA válido (con cache)
        3. Consulta Padrón A10
        4. Si falla por token expirado, reintenta con token nuevo

        Args:
            cuit: CUIT a consultar (11 dígitos, con o sin guiones)

        Returns:
            PersonaResponse con datos del contribuyente

        Raises:
            InvalidCUITException: CUIT con formato inválido
            CUITNotFoundException: CUIT no encontrado en AFIP
            AuthenticationException: Error de autenticación
            AFIPServiceException: Error de comunicación con AFIP
        """
        try:
            # PASO 1: Validar formato de CUIT
            self._validate_cuit_format(cuit)

            # PASO 2: Obtener token válido
            logger.info(f"Getting valid WSAA token for CUIT query: {cuit}")
            token_data = await self.auth_service.get_valid_token(service_name=self.service_name)

            # PASO 3: Consultar Padrón A10
            try:
                logger.info(f"Querying CUIT {cuit} in Padrón A10")
                persona_response = await self.padron_connector.get_persona_by_cuit(
                    cuit=cuit,
                    token_data=token_data
                )

                logger.info(f"Successfully retrieved data for CUIT {cuit}")
                return persona_response

            except AuthenticationException as e:
                # Token puede haber expirado en el cache pero aún estar allí
                # Reintentar con token fresco
                logger.warning(
                    f"Authentication failed for CUIT {cuit}, retrying with fresh token: {str(e)}"
                )

                # Obtener token nuevo (force refresh)
                token_data = await self.auth_service.refresh_token(service_name=self.service_name)

                # Reintentar consulta
                logger.info(f"Retrying CUIT {cuit} query with fresh token")
                persona_response = await self.padron_connector.get_persona_by_cuit(
                    cuit=cuit,
                    token_data=token_data
                )

                logger.info(f"Successfully retrieved data for CUIT {cuit} after retry")
                return persona_response

        except (InvalidCUITException, CUITNotFoundException, AuthenticationException, AFIPServiceException):
            # Re-raise custom exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error querying CUIT {cuit}: {str(e)}")
            raise AFIPServiceException(
                f"Unexpected error querying CUIT: {str(e)}",
                details={"cuit": cuit, "error": str(e)}
            )

    def _validate_cuit_format(self, cuit: str) -> None:
        """
        Valida el formato del CUIT.

        Reglas:
        - Debe tener 11 dígitos (con o sin guiones)
        - Solo números (ignorando guiones)
        - Formato: XX-XXXXXXXX-X o XXXXXXXXXXX

        Args:
            cuit: CUIT a validar

        Raises:
            InvalidCUITException: Si el formato es inválido
        """
        # Limpiar CUIT (remover guiones y espacios)
        clean_cuit = cuit.replace("-", "").replace(" ", "").strip()

        # Validar longitud
        if len(clean_cuit) != 11:
            raise InvalidCUITException(
                f"CUIT must have exactly 11 digits, got {len(clean_cuit)}",
                details={"cuit": cuit, "clean_cuit": clean_cuit}
            )

        # Validar que solo contenga dígitos
        if not clean_cuit.isdigit():
            raise InvalidCUITException(
                "CUIT must contain only numeric digits",
                details={"cuit": cuit, "clean_cuit": clean_cuit}
            )

        # Opcional: Validar dígito verificador (algoritmo módulo 11)
        # Por ahora solo validamos formato básico
        # TODO: Implementar validación de dígito verificador si se requiere

        logger.debug(f"CUIT format validated: {clean_cuit}")

    async def validate_cuit_exists(self, cuit: str) -> bool:
        """
        Valida si un CUIT existe en AFIP (retorna True/False en lugar de exception).

        Args:
            cuit: CUIT a validar

        Returns:
            True si existe, False si no existe o hay error
        """
        try:
            await self.get_persona_by_cuit(cuit)
            return True
        except CUITNotFoundException:
            return False
        except Exception as e:
            logger.error(f"Error validating CUIT {cuit}: {str(e)}")
            return False


# Instancia global del servicio (opcional, para uso directo)
_cuit_service: Optional[CUITService] = None


def get_cuit_service() -> CUITService:
    """
    Obtiene la instancia global del CUITService (Singleton pattern).

    Returns:
        CUITService instance
    """
    global _cuit_service
    if _cuit_service is None:
        _cuit_service = CUITService()
    return _cuit_service
