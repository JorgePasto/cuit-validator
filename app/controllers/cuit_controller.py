"""
Controlador REST API para consultas de CUIT.

Define los endpoints FastAPI para el microservicio de validación de CUITs.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.cache.token_cache import (
    get_token_cache_stats,
    clear_token_cache,
    invalidate_cached_token
)
from app.exceptions.custom_exceptions import (
    AFIPBaseException,
    AFIPServiceException,
    AuthenticationException,
    CUITNotFoundException,
    InvalidCUITException
)
from app.models.requests import CUITRequest
from app.models.responses import ErrorResponse, HealthResponse, PersonaResponse, PersonaSummaryResponse
from app.services.cuit_service import CUITService, get_cuit_service
from app.services.dni_service import DNIService, get_dni_service

logger = logging.getLogger(__name__)

# Router de FastAPI
router = APIRouter(prefix="/cuit-validator/v1", tags=["cuit"])


def get_service() -> CUITService:
    """Dependency injection para CUITService."""
    return get_cuit_service()


def get_dni_service_dep() -> DNIService:
    """Dependency injection para DNIService."""
    return get_dni_service()


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
        status="ok",
        environment=settings.ENVIRONMENT,
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
    service: CUITService = Depends(get_service)
) -> PersonaResponse:
    """
    Consulta información de un CUIT en AFIP Padrón A13.

    Retorna datos del contribuyente:
    - Tipo de persona (física/jurídica)
    - Nombre y apellido (persona física) o razón social (jurídica)
    - Domicilio fiscal completo
    - Estado de la clave (ACTIVO/INACTIVO)

    **Ejemplo de CUIT válido**: `20-12345678-9` o `20123456789`
    """
    try:
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
            ).model_dump(mode='json')
        )

    except CUITNotFoundException as e:
        logger.info(f"CUIT not found: {cuit}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                detail=str(e),
                error_code="CUIT_NOT_FOUND",
                timestamp=datetime.utcnow()
            ).model_dump(mode='json')
        )

    except AuthenticationException as e:
        logger.error(f"Authentication failed for CUIT {cuit}: {str(e)}")
        
        # Incluir el mensaje completo con instrucciones de solución
        error_message = str(e)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                detail=error_message,
                error_code="AUTHENTICATION_FAILED",
                timestamp=datetime.utcnow()
            ).model_dump(mode='json')
        )

    except AFIPServiceException as e:
        logger.error(f"AFIP service error for CUIT {cuit}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                detail="AFIP service is temporarily unavailable",
                error_code="SERVICE_UNAVAILABLE",
                timestamp=datetime.utcnow()
            ).model_dump(mode='json')
        )

    except AFIPBaseException as e:
        logger.error(f"AFIP error for CUIT {cuit}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                detail=str(e),
                error_code="AFIP_ERROR",
                timestamp=datetime.utcnow()
            ).model_dump(mode='json')
        )

    except Exception as e:
        logger.error(f"Unexpected error for CUIT {cuit}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                detail="Internal server error",
                error_code="INTERNAL_ERROR",
                timestamp=datetime.utcnow()
            ).model_dump(mode='json')
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
    service: CUITService = Depends(get_service)
) -> PersonaResponse:
    """
    Consulta información de un CUIT en AFIP Padrón A13 (método POST).

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
    "/dni/{dni}",
    response_model=list[PersonaSummaryResponse],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Personas encontradas para el DNI"},
        401: {"model": ErrorResponse, "description": "Error de autenticación con AFIP"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"},
        503: {"model": ErrorResponse, "description": "Servicio AFIP no disponible"},
    },
)
async def get_personas_by_dni(
    dni: str = Path(..., description="Número de DNI a consultar", example="30123456"),
    service: DNIService = Depends(get_dni_service_dep),
) -> list[PersonaSummaryResponse]:
    """
    Consulta las personas asociadas a un número de DNI en AFIP Padrón A13.

    Retorna una lista de personas con datos básicos:
    - CUIT
    - Tipo de persona (física/jurídica)
    - Nombre y apellido (persona física) o razón social (jurídica)
    - Estado de la clave (ACTIVO/INACTIVO)

    **Ejemplo**: `/dni/30123456`
    """
    try:
        logger.info(f"Received request for DNI: {dni}")
        personas = await service.get_personas_by_dni(dni)
        return personas

    except AuthenticationException as e:
        logger.error(f"Authentication failed for DNI {dni}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                detail=str(e),
                error_code="AUTHENTICATION_FAILED",
                timestamp=datetime.utcnow(),
            ).model_dump(mode="json"),
        )

    except AFIPServiceException as e:
        logger.error(f"AFIP service error for DNI {dni}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                detail="AFIP service is temporarily unavailable",
                error_code="SERVICE_UNAVAILABLE",
                timestamp=datetime.utcnow(),
            ).model_dump(mode="json"),
        )

    except Exception as e:
        logger.error(f"Unexpected error for DNI {dni}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                detail="Internal server error",
                error_code="INTERNAL_ERROR",
                timestamp=datetime.utcnow(),
            ).model_dump(mode="json"),
        )


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
            ).model_dump(mode='json')
        )


@router.delete(
    "/cache/clear",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["admin"]
)
async def clear_cache():
    """
    Limpia TODO el cache de tokens WSAA.
    
    **⚠️ ADVERTENCIA**: Esta operación elimina todos los tokens cacheados.
    El próximo request solicitará nuevos tokens a AFIP.
    
    **Casos de uso**:
    - Resolver error "alreadyAuthenticated" de AFIP
    - Forzar renovación de todos los tokens
    - Debugging/troubleshooting
    
    Returns:
        Mensaje de confirmación con estadísticas previas
    """
    try:
        # Obtener estadísticas antes de limpiar
        stats_before = get_token_cache_stats()
        
        # Limpiar cache
        clear_token_cache()
        logger.info("Token cache cleared manually via admin endpoint")
        
        return {
            "status": "ok",
            "message": "Token cache cleared successfully",
            "tokens_removed": stats_before.get("size", 0),
            "services_cleared": stats_before.get("services", []),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                detail="Failed to clear cache",
                error_code="CACHE_CLEAR_ERROR",
                timestamp=datetime.utcnow()
            ).model_dump(mode='json')
        )


@router.delete(
    "/cache/invalidate/{service_name}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["admin"]
)
async def invalidate_token(
    service_name: str = Path(
        ...,
        description="Nombre del servicio AFIP (ej: ws_sr_padron_a13)",
        example="ws_sr_padron_a13"
    )
):
    """
    Invalida el token cacheado para un servicio específico.
    
    **Casos de uso**:
    - Resolver error "alreadyAuthenticated" para un servicio específico
    - Forzar renovación de token para un servicio
    - Invalidar token sin afectar otros servicios
    
    Args:
        service_name: Nombre del servicio AFIP (ej: ws_sr_padron_a13)
    
    Returns:
        Mensaje de confirmación
    """
    try:
        # Verificar si el token existe
        stats = get_token_cache_stats()
        services = stats.get("services", [])
        
        if service_name not in services:
            logger.warning(f"Attempted to invalidate non-existent token: {service_name}")
            return {
                "status": "ok",
                "message": f"No token found for service '{service_name}' (already cleared or never cached)",
                "service": service_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Invalidar token específico
        invalidate_cached_token(service_name)
        logger.info(f"Token invalidated for service: {service_name}")
        
        return {
            "status": "ok",
            "message": f"Token for service '{service_name}' invalidated successfully",
            "service": service_name,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error invalidating token for {service_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                detail=f"Failed to invalidate token for service '{service_name}'",
                error_code="TOKEN_INVALIDATION_ERROR",
                timestamp=datetime.utcnow()
            ).model_dump(mode='json')
        )
