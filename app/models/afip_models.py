"""
Modelos de datos internos para AFIP.
"""
from datetime import datetime
from pydantic import BaseModel, Field


class TokenData(BaseModel):
    """Datos del token de autenticación WSAA."""
    
    token: str = Field(..., description="Token de acceso")
    sign: str = Field(..., description="Firma del token")
    generation_time: datetime = Field(..., description="Fecha/hora de generación")
    expiration_time: datetime = Field(..., description="Fecha/hora de expiración")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4...",
                "sign": "ZjE4YzRjMzY5ZDU0ZDMyZTQwNzE5ZTk3MWQ1YzI4ZjI=",
                "generation_time": "2024-03-14T10:00:00",
                "expiration_time": "2024-03-14T22:00:00"
            }
        }


class LoginTicketRequest(BaseModel):
    """Request para WSAA LoginCms."""
    
    service: str = Field(..., description="Nombre del servicio AFIP")
    unique_id: int = Field(..., description="ID único del request (timestamp)")
    generation_time: str = Field(..., description="Fecha/hora de generación (ISO)")
    expiration_time: str = Field(..., description="Fecha/hora de expiración (ISO)")
