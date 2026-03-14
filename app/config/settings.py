"""
Configuración centralizada del microservicio.
Carga variables de entorno desde .env y proporciona acceso global a settings.
"""
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación con validación Pydantic."""
    
    # Ambiente
    ENVIRONMENT: Literal["TEST", "PROD"] = "TEST"
    
    # URLs AFIP WSAA (Autenticación)
    WSAA_URL_TEST: str = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"
    WSAA_URL_PROD: str = "https://wsaa.afip.gov.ar/ws/services/LoginCms"
    
    # URLs AFIP Padrón A13 (Consulta)
    PADRON_URL_TEST: str = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA13"
    PADRON_URL_PROD: str = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13"
    
    # Certificados AFIP
    AFIP_CERT_PATH: Path
    AFIP_KEY_PATH: Path
    AFIP_KEY_PASSPHRASE: str = ""
    AFIP_CUIT: str
    
    # Cache
    TOKEN_CACHE_TTL_HOURS: int = 12
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Server
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    @property
    def wsaa_url(self) -> str:
        """Retorna la URL de WSAA según el ambiente."""
        return self.WSAA_URL_TEST if self.ENVIRONMENT == "TEST" else self.WSAA_URL_PROD
    
    @property
    def padron_url(self) -> str:
        """Retorna la URL del Padrón A13 según el ambiente."""
        return self.PADRON_URL_TEST if self.ENVIRONMENT == "TEST" else self.PADRON_URL_PROD
    
    @property
    def token_cache_ttl_seconds(self) -> int:
        """Retorna el TTL del cache en segundos."""
        return self.TOKEN_CACHE_TTL_HOURS * 3600
    
    def validate_certificates(self) -> None:
        """Valida que los archivos de certificados existan."""
        if not self.AFIP_CERT_PATH.resolve().exists():
            raise FileNotFoundError(f"Certificado no encontrado: {self.AFIP_CERT_PATH}")
        if not self.AFIP_KEY_PATH.exists():
            raise FileNotFoundError(f"Clave privada no encontrada: {self.AFIP_KEY_PATH}")


# Singleton: instancia única de configuración
settings = Settings()
