"""
Modelos de request (Request DTOs) para la API.
"""
from pydantic import BaseModel, Field, field_validator


class CUITRequest(BaseModel):
    """Request para consulta de CUIT (uso futuro si se necesita POST)."""
    
    cuit: str = Field(..., min_length=11, max_length=11, description="CUIT a consultar")
    
    @field_validator('cuit')
    @classmethod
    def validate_cuit_format(cls, v: str) -> str:
        """Valida que el CUIT tenga formato numérico."""
        if not v.isdigit():
            raise ValueError('CUIT debe contener solo dígitos')
        if len(v) != 11:
            raise ValueError('CUIT debe tener exactamente 11 dígitos')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "cuit": "20123456789"
            }
        }
