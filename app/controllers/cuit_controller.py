"""
Controlador REST API para consultas de CUIT.

Define los endpoints FastAPI para el microservicio de validación de CUITs.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query, status

from app.cache.token_cache import get_token_cache_stats
from app.exceptions.custom_exceptions import (
    AFIPBaseException,
    AFIPServiceException,
    AuthenticationException,
    CUITNotFoundException,
    InvalidCUITException
)
from app.models.requests import CUITRequest
from app.models.responses import ErrorResponse, HealthResponse, PersonaResponse
from app.services.cuit_service import CUITService, get_cuit_service

logger = logging.getLogger(__name__)

# Router de FastAPI
router = APIRouter(prefix="/cuit-validator/v1", tags=["cuit"])


def get_service() -> CUITService:
    """Dependency injection para CUITService."""
    return get_cuit_service()


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint.

    Verifica que el servicio esté activo y responda correctamente.

    Returns:
        HealthResponse con status OK y timestamp
    """
    from app.config.settings import Settings

    settings = Settings()

    return HealthResponse(
        status="OK",
        environment=settings.environment,
        timestamp=datetime.utcnow()
    )


@router.get(
    "/cuit/{cuit}",
    response_model=PersonaResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "CUIT encontrado exitosamente"},
        400: {"model": ErrorResponse, "description": "CUIT con formato inválido"},
        404: {"model": ErrorResponse, "description": "CUIT no encontrado en AFIP"},
        401: {"model": ErrorResponse, "description": "Error de autenticación con AFIP"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"},
        503: {"model": ErrorResponse, "description": "Servicio AFIP no disponible"}
    }
)
async def get_cuit(
    cuit: str = Path(..., description="CUIT a consultar (11 dígitos, con o sin guiones)", example="20123456789"),
    service: CUITService = None
) -> PersonaResponse:
    """
    Consulta información de un CUIT en AFIP Padrón A10.

    Retorna datos del contribuyente:
    - Tipo de persona (física/jurídica)
    - Nombre y apellido (persona física) o razón social (jurídica)
    - Domicilio fiscal completo
    - Estado de la clave (ACTIVO/INACTIVO)

    **Ejemplo de CUIT válido**: `20-12345678-9` o `20123456789`
    """
    try:
        # Obtener servicio (dependency injection manual si no se inyectó)
        if service is None:
            service = get_service()

        logger.info(f"Received request for CUIT: {cuit}")

        # Consultar CUIT
        persona_response = await service.get_persona_by_cuit(cuit)

        return persona_response

    except InvalidCUITException as e:
        logger.warning(f"Invalid CUIT format: {cuit} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                detail=str(e),
                error_code="INVALID_CUIT_FORMAT",
                timestamp=datetime.utcnow()
            ).dict()
        )

    except CUITNotFoundException as e:
        logger.info(f"CUIT not found: {cuit}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                detail=str(e),
                error_code="CUIT_NOT_FOUND",
                timestamp=datetime.utcnow()
            ).dict()
        )

    except AuthenticationException as e:
        logger.error(f"Authentication failed for CUIT {cuit}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                detail="Failed to authenticate with AFIP",
                error_code="AUTHENTICATION_FAILED",
                timestamp=datetime.utcnow()
            ).dict()
        )

    except AFIPServiceException as e:
        logger.error(f"AFIP service error for CUIT {cuit}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                detail="AFIP service is temporarily unavailable",
                error_code="SERVICE_UNAVAILABLE",
                timestamp=datetime.utcnow()
            ).dict()
        )

    except AFIPBaseException as e:
        logger.error(f"AFIP error for CUIT {cuit}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                detail=str(e),
                error_code="AFIP_ERROR",
                timestamp=datetime.utcnow()
            ).dict()
        )

    except Exception as e:
        logger.error(f"Unexpected error for CUIT {cuit}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                detail="Internal server error",
                error_code="INTERNAL_ERROR",
                timestamp=datetime.utcnow()
            ).dict()
        )


@router.post(
    "/cuit/validate",
    response_model=PersonaResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "CUIT encontrado exitosamente"},
        400: {"model": ErrorResponse, "description": "CUIT con formato inválido"},
        404: {"model": ErrorResponse, "description": "CUIT no encontrado en AFIP"},
        401: {"model": ErrorResponse, "description": "Error de autenticación con AFIP"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"},
        503: {"model": ErrorResponse, "description": "Servicio AFIP no disponible"}
    }
)
async def validate_cuit_post(
    request: CUITRequest,
    service: CUITService = None
) -> PersonaResponse:
    """
    Consulta información de un CUIT en AFIP Padrón A10 (método POST).

    Versión POST del endpoint de consulta, acepta JSON body con el CUIT.

    **Request body**:
    ```json
    {
        "cuit": "20123456789"
    }
    ```
    """
    # Reutilizar la lógica del endpoint GET
    return await get_cuit(cuit=request.cuit, service=service)


@router.get(
    "/cache/stats",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["admin"]
)
async def get_cache_stats():
    """
    Obtiene estadísticas del cache de tokens WSAA.

    **Útil para**:
    - Debugging
    - Monitoring
    - Verificar estado del cache

    Returns:
        Estadísticas del cache (tamaño, TTL, servicios cacheados)
    """
    try:
        stats = get_token_cache_stats()
        return {
            "cache_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                detail="Failed to retrieve cache stats",
                error_code="CACHE_ERROR",
                timestamp=datetime.utcnow()
            ).dict()
        )
