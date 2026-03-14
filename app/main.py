"""
Aplicación principal FastAPI - CUIT Validator Microservice.

Microservicio para validación de CUITs mediante integración con AFIP:
- WSAA (Web Service de Autenticación y Autorización)
- Padrón A10 (Consulta de datos de contribuyentes)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config.settings import Settings
from app.controllers.cuit_controller import router as cuit_router
from app.exceptions.custom_exceptions import AFIPBaseException
from app.models.responses import ErrorResponse

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager para FastAPI.

    Ejecuta tareas de inicialización y limpieza:
    - Startup: Validar certificados, configuración, conexiones
    - Shutdown: Limpiar recursos, cerrar conexiones
    """
    # STARTUP
    logger.info("Starting CUIT Validator microservice...")

    try:
        # Validar configuración
        settings = Settings()
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"WSAA URL: {settings.wsaa_url}")
        logger.info(f"Padrón URL: {settings.padron_url}")

        # Validar certificados
        settings.validate_certificates()
        logger.info("AFIP certificates validated successfully")

        # TODO: Precalentar cache de tokens si es necesario
        # await auth_service.get_valid_token()

        logger.info("CUIT Validator microservice started successfully")

    except Exception as e:
        logger.error(f"Failed to start microservice: {str(e)}")
        raise

    yield

    # SHUTDOWN
    logger.info("Shutting down CUIT Validator microservice...")

    # Limpiar cache si es necesario
    from app.cache.token_cache import clear_token_cache
    clear_token_cache()

    logger.info("CUIT Validator microservice stopped")


# Crear aplicación FastAPI
app = FastAPI(
    title="CUIT Validator API",
    description="""
    Microservicio para validación y consulta de CUITs argentinos mediante AFIP.

    ## Funcionalidades

    - **Consulta de CUITs**: Obtener datos de contribuyentes (nombres, domicilios fiscales)
    - **Autenticación automática**: Gestión transparente de tokens WSAA con cache
    - **Cache inteligente**: Tokens cacheados por 12 horas para optimizar performance
    - **Ambientes**: Soporte para TEST (homologación) y PROD

    ## Servicios AFIP utilizados

    - **WSAA**: Web Service de Autenticación y Autorización
    - **Padrón A10**: Consulta de datos de personas físicas y jurídicas

    ## Endpoints principales

    - `GET /cuit-validator/v1/cuit/{cuit}`: Consulta información de un CUIT
    - `POST /cuit-validator/v1/cuit/validate`: Consulta información (método POST)
    - `GET /cuit-validator/v1/health`: Health check del servicio
    - `GET /cuit-validator/v1/cache/stats`: Estadísticas del cache de tokens
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Registrar routers
app.include_router(cuit_router)


# Exception handlers globales
@app.exception_handler(AFIPBaseException)
async def afip_exception_handler(request: Request, exc: AFIPBaseException):
    """
    Maneja excepciones personalizadas de AFIP.

    Convierte excepciones custom a respuestas HTTP consistentes.
    """
    from datetime import datetime

    logger.error(f"AFIP exception: {str(exc)}", exc_info=True)

    # Mapear excepciones a status codes
    status_code_map = {
        "InvalidCUITException": status.HTTP_400_BAD_REQUEST,
        "CUITNotFoundException": status.HTTP_404_NOT_FOUND,
        "AuthenticationException": status.HTTP_401_UNAUTHORIZED,
        "AFIPServiceException": status.HTTP_503_SERVICE_UNAVAILABLE,
        "CertificateException": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "SignatureException": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "XMLParseException": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    exception_name = exc.__class__.__name__
    status_code = status_code_map.get(exception_name, status.HTTP_500_INTERNAL_SERVER_ERROR)

    error_response = ErrorResponse(
        detail=str(exc),
        error_code=exception_name.upper().replace("EXCEPTION", "_ERROR"),
        timestamp=datetime.utcnow()
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response.dict()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Maneja errores de validación de Pydantic.

    Retorna errores de validación en formato consistente.
    """
    from datetime import datetime

    logger.warning(f"Validation error: {str(exc)}")

    error_response = ErrorResponse(
        detail=f"Request validation failed: {str(exc)}",
        error_code="VALIDATION_ERROR",
        timestamp=datetime.utcnow()
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Maneja excepciones no capturadas.

    Evita exponer detalles internos al cliente.
    """
    from datetime import datetime

    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    error_response = ErrorResponse(
        detail="Internal server error",
        error_code="INTERNAL_ERROR",
        timestamp=datetime.utcnow()
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict()
    )


# Middleware de logging (opcional)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware para logging de requests.

    Registra todas las peticiones HTTP con método, path y status code.
    """
    logger.info(f"Incoming request: {request.method} {request.url.path}")

    response = await call_next(request)

    logger.info(f"Response status: {response.status_code}")

    return response


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint - información básica del servicio.
    """
    return {
        "service": "CUIT Validator API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn

    # Cargar configuración
    settings = Settings()

    # Ejecutar servidor
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "TEST",  # Hot reload solo en TEST
        log_level="info"
    )
