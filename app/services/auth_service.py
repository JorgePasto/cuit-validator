"""
Servicio de autenticación para AFIP WSAA.

Este módulo maneja la lógica de negocio para obtener y cachear tokens WSAA.
Actúa como intermediario entre los conectores y los controladores.
"""

import logging
from typing import Optional

from app.cache.token_cache import cache_token, get_cached_token
from app.connectors.wsaa_connector import WSAAConnector, get_wsaa_connector
from app.exceptions.custom_exceptions import AuthenticationException
from app.models.afip_models import TokenData

logger = logging.getLogger(__name__)


class AuthService:
    """
    Servicio de autenticación WSAA con gestión de cache.

    Responsabilidades:
    - Obtener tokens WSAA con cache automático
    - Validar tokens existentes
    - Renovar tokens expirados
    - Gestionar el ciclo de vida del token
    """

    def __init__(self, wsaa_connector: Optional[WSAAConnector] = None):
        """
        Inicializa el servicio de autenticación.

        Args:
            wsaa_connector: Connector WSAA (opcional, usa singleton si no se provee)
        """
        self.wsaa_connector = wsaa_connector or get_wsaa_connector()

    async def get_valid_token(self, force_refresh: bool = False, service_name: Optional[str] = None) -> TokenData:
        """
        Obtiene un token válido de WSAA (usa cache si está disponible).

        Flujo:
        1. Verifica si hay token en cache
        2. Si existe y es válido, lo retorna
        3. Si no existe o expiró, solicita uno nuevo a WSAA
        4. Cachea el nuevo token
        5. Retorna el token

        Args:
            force_refresh: Si True, fuerza renovación aunque exista token válido en cache

        Returns:
            TokenData válido

        Raises:
            AuthenticationException: Error obteniendo token de AFIP
        """
        try:
            # Si no se fuerza refresh, intentar obtener del cache
            if not force_refresh:
                cached_token = get_cached_token(service_name)
                if cached_token is not None:
                    logger.info(f"Using cached token for service: {service_name}")
                    logger.debug(f"Token expires at: {cached_token.expiration_time}")
                    return cached_token

            # Si no hay cache o se forzó refresh, obtener nuevo token
            logger.info(f"Requesting new token from WSAA for service: {service_name}")
            new_token = await self.wsaa_connector.get_token(service_name=service_name)

            # Cachear el nuevo token
            cache_token(service_name, new_token)
            logger.info(f"New token cached. Expires at: {new_token.expiration_time}")

            return new_token

        except AuthenticationException:
            # Re-raise authentication errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_valid_token: {str(e)}")
            raise AuthenticationException(
                f"Failed to obtain valid WSAA token: {str(e)}",
                details={"service": service_name, "error": str(e)}
            )

    async def refresh_token(self, service_name: Optional[str] = None) -> TokenData:
        """
        Fuerza la renovación del token (ignora cache).

        Returns:
            TokenData nuevo

        Raises:
            AuthenticationException: Error obteniendo token
        """
        logger.info(f"Force refreshing token for service: {service_name}")
        return await self.get_valid_token(force_refresh=True, service_name=service_name)

    def get_cached_token_info(self, service_name: Optional[str] = None) -> Optional[dict]:
        """
        Obtiene información del token cacheado (sin renovar).

        Returns:
            Dict con información del token o None si no existe en cache
        """
        used_service = service_name if service_name else self.wsaa_connector.get_service_name()

        cached_token = get_cached_token(used_service)

        if cached_token is None:
            return None

        return {
            "service": used_service,
            "generation_time": cached_token.generation_time.isoformat(),
            "expiration_time": cached_token.expiration_time.isoformat(),
            "token_length": len(cached_token.token),
            "sign_length": len(cached_token.sign)
        }


# Instancia global del servicio (opcional, para uso directo)
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """
    Obtiene la instancia global del AuthService (Singleton pattern).

    Returns:
        AuthService instance
    """
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
