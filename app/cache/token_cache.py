"""
Cache en memoria para tokens WSAA con TTL (Time To Live).

Este módulo implementa un cache simple usando cachetools.TTLCache para almacenar
tokens AFIP WSAA que son válidos por ~12 horas.

No utiliza Redis para mantener la simplicidad del microservicio.
"""

from datetime import datetime
from typing import Optional

from cachetools import TTLCache

from app.models.afip_models import TokenData


class TokenCache:
    """
    Cache en memoria para tokens WSAA con gestión automática de TTL.

    Características:
    - TTL por defecto: 12 horas (43200 segundos)
    - Capacidad máxima: 100 tokens (suficiente para múltiples servicios)
    - Thread-safe mediante cachetools
    - Singleton pattern para uso global
    """

    _instance: Optional['TokenCache'] = None
    _cache: TTLCache

    def __new__(cls):
        """Implementa Singleton para uso global."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # TTL de 12 horas = 43200 segundos
            # Capacidad de 100 tokens (más que suficiente)
            cls._instance._cache = TTLCache(maxsize=100, ttl=43200)
        return cls._instance

    def get_token(self, service: str) -> Optional[TokenData]:
        """
        Obtiene el token cacheado para un servicio específico.

        Args:
            service: Nombre del servicio AFIP (ej: ws_sr_padron_a13)

        Returns:
            TokenData si existe y es válido, None si no existe o expiró
        """
        token_data = self._cache.get(service)

        # Validar que el token no haya expirado manualmente
        # (TTLCache ya maneja esto, pero agregamos validación adicional por seguridad)
        if token_data and self._is_token_valid(token_data):
            return token_data

        # Si expiró, eliminarlo del cache
        if token_data:
            self.invalidate_token(service)

        return None

    def set_token(self, service: str, token_data: TokenData) -> None:
        """
        Almacena un token en el cache.

        Args:
            service: Nombre del servicio AFIP
            token_data: Datos del token (token, sign, timestamps)
        """
        self._cache[service] = token_data

    def invalidate_token(self, service: str) -> None:
        """
        Invalida (elimina) un token del cache.

        Args:
            service: Nombre del servicio AFIP
        """
        if service in self._cache:
            del self._cache[service]

    def clear_all(self) -> None:
        """
        Limpia todos los tokens del cache.
        Útil para testing o reinicio del servicio.
        """
        self._cache.clear()

    def get_cache_stats(self) -> dict:
        """
        Obtiene estadísticas del cache (útil para debugging/monitoring).

        Returns:
            Dict con información del cache:
            - size: cantidad de tokens almacenados
            - maxsize: capacidad máxima
            - ttl: TTL en segundos
        """
        return {
            "size": len(self._cache),
            "maxsize": self._cache.maxsize,
            "ttl_seconds": self._cache.ttl,
            "services": list(self._cache.keys())
        }

    def _is_token_valid(self, token_data: TokenData) -> bool:
        """
        Valida si un token aún es válido según su expiration_time.

        Args:
            token_data: Datos del token

        Returns:
            True si el token es válido, False si expiró
        """
        now = datetime.utcnow()

        # Agregar margen de seguridad de 5 minutos antes de la expiración
        # para evitar race conditions
        safety_margin_seconds = 300

        # Comparar con expiration_time menos el margen
        expiration_with_margin = token_data.expiration_time
        if (expiration_with_margin - now).total_seconds() > safety_margin_seconds:
            return True

        return False


# Instancia global del cache (Singleton)
token_cache = TokenCache()


# Funciones de conveniencia para uso directo
def get_cached_token(service: str) -> Optional[TokenData]:
    """
    Obtiene un token del cache global.

    Args:
        service: Nombre del servicio AFIP

    Returns:
        TokenData o None
    """
    return token_cache.get_token(service)


def cache_token(service: str, token_data: TokenData) -> None:
    """
    Almacena un token en el cache global.

    Args:
        service: Nombre del servicio AFIP
        token_data: Datos del token
    """
    token_cache.set_token(service, token_data)


def invalidate_cached_token(service: str) -> None:
    """
    Invalida un token del cache global.

    Args:
        service: Nombre del servicio AFIP
    """
    token_cache.invalidate_token(service)


def clear_token_cache() -> None:
    """Limpia todo el cache global."""
    token_cache.clear_all()


def get_token_cache_stats() -> dict:
    """Obtiene estadísticas del cache global."""
    return token_cache.get_cache_stats()
