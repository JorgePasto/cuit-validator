"""
Modelos de respuesta (Response DTOs) para la API.
Enfocados en nombres y domicilios según requerimientos.
"""
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class DomicilioFiscal(BaseModel):
    """Domicilio fiscal del contribuyente."""
    
    direccion: str = Field(..., description="Dirección completa")
    localidad: Optional[str] = Field(None, description="Localidad")
    provincia: Optional[str] = Field(None, description="Provincia")
    codigo_postal: Optional[str] = Field(None, description="Código postal")
    
    class Config:
        json_schema_extra = {
            "example": {
                "direccion": "AV CORRIENTES 1234 PISO 5",
                "localidad": "CAPITAL FEDERAL",
                "provincia": "CIUDAD AUTONOMA BUENOS AIRES",
                "codigo_postal": "1043"
            }
        }


class PersonaResponse(BaseModel):
    """Respuesta de consulta de CUIT en Padrón A10."""
    
    cuit: str = Field(..., description="CUIT consultado")
    tipo_persona: Literal["FISICA", "JURIDICA"] = Field(..., description="Tipo de persona")
    
    # Para personas físicas
    apellido: Optional[str] = Field(None, description="Apellido (persona física)")
    nombre: Optional[str] = Field(None, description="Nombre (persona física)")
    
    # Para personas jurídicas
    razon_social: Optional[str] = Field(None, description="Razón social (persona jurídica)")
    
    # Domicilio fiscal
    domicilio_fiscal: DomicilioFiscal = Field(..., description="Domicilio fiscal registrado")
    
    # Metadatos
    estado_clave: str = Field(..., description="Estado de la clave fiscal (ACTIVO/INACTIVO)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "cuit": "20123456789",
                "tipo_persona": "FISICA",
                "apellido": "PEREZ",
                "nombre": "JUAN CARLOS",
                "razon_social": None,
                "domicilio_fiscal": {
                    "direccion": "AV CORRIENTES 1234 PISO 5",
                    "localidad": "CAPITAL FEDERAL",
                    "provincia": "CIUDAD AUTONOMA BUENOS AIRES",
                    "codigo_postal": "1043"
                },
                "estado_clave": "ACTIVO"
            }
        }


class ErrorResponse(BaseModel):
    """Respuesta de error estandarizada."""
    
    detail: str = Field(..., description="Descripción del error")
    error_code: Optional[str] = Field(None, description="Código de error interno")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp del error")
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "CUIT no encontrado en AFIP",
                "error_code": "CUIT_NOT_FOUND",
                "timestamp": "2024-03-14T10:30:00"
            }
        }


class HealthResponse(BaseModel):
    """Respuesta del health check."""
    
    status: Literal["ok", "error"] = Field(..., description="Estado del servicio")
    environment: str = Field(..., description="Ambiente (TEST/PROD)")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")
