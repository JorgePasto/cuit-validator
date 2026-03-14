# CUIT Validator API

Microservicio Python/FastAPI para validación y consulta de CUITs argentinos mediante integración con servicios AFIP (Administración Federal de Ingresos Públicos).

## 🚀 Quick Start

```bash
# 1. Clonar y entrar al proyecto
git clone <repository-url>
cd cuit-validator

# 2. Crear entorno virtual con Python 3
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env y configurar certificados AFIP

# 5. Ejecutar con Uvicorn
uvicorn app.main:app --reload

# Acceder a:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
```

## Características

- **Consulta de CUITs**: Obtiene información completa de contribuyentes (nombres, razón social, domicilio fiscal)
- **Autenticación automática**: Gestión transparente de tokens WSAA (Web Service de Autenticación y Autorización)
- **Cache inteligente**: Tokens WSAA cacheados en memoria por 12 horas para optimizar performance
- **Logging estructurado**: Sistema completo de logs REQ-RSP con correlation IDs para trazabilidad
- **Multi-ambiente**: Soporte para TEST (homologación) y PROD
- **Arquitectura limpia**: Patrón Controller → Service → Connector (3 capas)
- **Dockerizado**: Listo para deployment con Docker y Docker Compose

## Servicios AFIP Utilizados

1. **WSAA** (Web Service de Autenticación y Autorización): Obtención de tokens de acceso
2. **Padrón A13**: Consulta de datos de personas físicas y jurídicas (requiere Nivel 3 de Clave Fiscal)

## Requisitos Previos

### Certificados AFIP

Para utilizar este microservicio necesitas:

1. **Certificado digital AFIP** (`.crt`) - Formato PEM (Computador Fiscal)
2. **Clave privada** (`.key`) - Formato PEM
3. **CUIT habilitado** para el servicio `ws_sr_padron_a13`
4. **Clave Fiscal Nivel 3 o superior** (requerido por A13)

**Cómo obtener certificados AFIP**:
- Acceder al sitio de AFIP con clave fiscal
- Generar un certificado digital para el servicio "Padrón A13"
- Descargar el certificado (.crt) y la clave privada (.key)
- Colocarlos en el directorio `certs/`

Consultar el archivo `TUTORIAL-CERTIFICADOS-AFIP.md` para instrucciones detalladas.

### Software

- **Python 3.11+** (para ejecución local)
- **Docker y Docker Compose** (para ejecución containerizada)

## Instalación

### Opción 1: Ejecución Local con Uvicorn (Recomendado para desarrollo)

```bash
# 1. Clonar repositorio
git clone <repository-url>
cd cuit-validator

# 2. Crear entorno virtual con Python 3
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Verificar versión de Python (debe ser 3.11+)
python --version

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar variables de entorno
cp .env.example .env
# Editar .env con tu configuración

# 6. Colocar certificados AFIP
# Copiar cert.crt y private.key al directorio certs/
mkdir -p certs
# cp /ruta/a/tus/certificados/* certs/

# 7. Ejecutar microservicio con Uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Alternativas de ejecución:
# - Modo producción (sin reload):
#   uvicorn app.main:app --host 0.0.0.0 --port 8000
#
# - Con más workers (producción):
#   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
#
# - Solo localhost:
#   uvicorn app.main:app --reload
```

El servidor estará disponible en: `http://localhost:8000`

**Documentación interactiva automática**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Opción 2: Docker Compose (Recomendado para producción)

```bash
# 1. Clonar repositorio
git clone <repository-url>
cd cuit-validator

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tu configuración

# 3. Colocar certificados AFIP en certs/
# Asegurarse de tener:
#   - certs/cert.crt
#   - certs/private.key

# 4. Construir y ejecutar
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

## Configuración

### Variables de Entorno

Editar el archivo `.env`:

```bash
# Ambiente: TEST (homologación) o PROD (producción)
ENVIRONMENT=TEST

# Rutas de certificados AFIP
AFIP_CERT_PATH=./certs/cert.crt
AFIP_KEY_PATH=./certs/private.key
AFIP_KEY_PASSPHRASE=  # Opcional, si la clave está cifrada
```

**Ambientes disponibles**:

- **TEST**: Utiliza URLs de homologación AFIP (para pruebas)
  - WSAA: `https://wsaahomo.afip.gov.ar/ws/services/LoginCms`
  - Padrón A13: `https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA13`

- **PROD**: Utiliza URLs de producción AFIP
  - WSAA: `https://wsaa.afip.gov.ar/ws/services/LoginCms`
  - Padrón A13: `https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13`

## Uso de la API

### Endpoints Disponibles

#### 1. Health Check

```bash
GET /api/v1/health
```

**Respuesta**:
```json
{
  "status": "OK",
  "environment": "TEST",
  "timestamp": "2024-03-14T10:30:00.000000"
}
```

#### 2. Consultar CUIT (GET)

```bash
GET /cuit-validator/v1/cuit/{cuit}
```

**Ejemplo**:
```bash
curl http://localhost:8000/cuit-validator/v1/cuit/20123456789
```

**Respuesta exitosa** (200):
```json
{
  "cuit": "20123456789",
  "tipo_persona": "FISICA",
  "apellido": "PEREZ",
  "nombre": "JUAN",
  "razon_social": null,
  "domicilio_fiscal": {
    "direccion": "AV CORRIENTES 1234",
    "localidad": "CAPITAL FEDERAL",
    "provincia": "CIUDAD AUTONOMA BUENOS AIRES",
    "codigo_postal": "1043"
  },
  "estado_clave": "ACTIVO"
}
```

**Errores posibles**:
- `400 Bad Request`: CUIT con formato inválido
- `404 Not Found`: CUIT no encontrado en AFIP
- `401 Unauthorized`: Error de autenticación con AFIP
- `503 Service Unavailable`: Servicio AFIP temporalmente no disponible

#### 3. Consultar CUIT (POST)

```bash
POST /cuit-validator/v1/cuit/validate
Content-Type: application/json

{
  "cuit": "20123456789"
}
```

**Ejemplo con curl**:
```bash
curl -X POST http://localhost:8000/cuit-validator/v1/cuit/validate \
  -H "Content-Type: application/json" \
  -d '{"cuit": "20123456789"}'
```

#### 4. Estadísticas del Cache (Admin)

```bash
GET /cuit-validator/v1/cache/stats
```

**Respuesta**:
```json
{
  "cache_stats": {
    "size": 1,
    "maxsize": 100,
    "ttl_seconds": 43200,
    "services": ["ws_sr_padron_a13"]
  },
  "timestamp": "2024-03-14T10:30:00.000000"
}
```

### Documentación Interactiva

Una vez ejecutado el servicio, acceder a:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│  Controllers (app/controllers/)                             │
│    └─ cuit_controller.py  → REST API endpoints             │
├─────────────────────────────────────────────────────────────┤
│  Services (app/services/)                                   │
│    ├─ auth_service.py     → Token management + cache       │
│    └─ cuit_service.py     → Business logic                 │
├─────────────────────────────────────────────────────────────┤
│  Connectors (app/connectors/)                               │
│    ├─ wsaa_connector.py   → AFIP authentication           │
│    └─ padron_connector.py → CUIT queries (Zeep/SOAP)      │
├─────────────────────────────────────────────────────────────┤
│  Utils (app/utils/)                                         │
│    ├─ crypto_utils.py     → CMS/PKCS#7 signature          │
│    ├─ xml_utils.py        → XML generation/parsing         │
│    └─ afip_logger.py      → Structured REQ-RSP logging     │
├─────────────────────────────────────────────────────────────┤
│  Cache (app/cache/)                                         │
│    └─ token_cache.py      → In-memory cache (TTL: 12h)    │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Consulta de CUIT

1. **Request HTTP** → Controller recibe CUIT
2. **Validación** → Service valida formato del CUIT
3. **Token WSAA** → AuthService obtiene/renueva token (con cache)
4. **Consulta Padrón** → PadronConnector consulta AFIP (SOAP/Zeep)
5. **Response HTTP** → Controller retorna PersonaResponse

## Testing

```bash
# Ejecutar tests unitarios
pytest tests/ -v

# Con cobertura
pytest tests/ --cov=app --cov-report=html
```

## Seguridad

- **Certificados**: Los certificados AFIP **NO** deben committearse al repositorio
- **Variables sensibles**: Usar `.env` para configuración (incluido en `.gitignore`)
- **Usuario no-root**: El container Docker ejecuta con usuario no privilegiado
- **Logs**: No se registran tokens ni datos sensibles en logs

## Troubleshooting

### Error: "SyntaxError: invalid syntax" al ejecutar

**Causa**: Estás usando Python 2.7 en lugar de Python 3.11+

**Solución**:
```bash
# Verificar versión actual
python --version   # Si muestra Python 2.x, usar python3

# Usar Python 3 explícitamente
python3 --version  # Debe mostrar Python 3.11 o superior

# Crear entorno virtual con Python 3
python3 -m venv venv
source venv/bin/activate

# Ahora python apuntará a Python 3
python --version
uvicorn app.main:app --reload
```

**Nota**: Python 2.7 está deprecado. Este proyecto requiere **Python 3.11+** para soportar las características modernas de FastAPI (async/await, type hints, etc.).

### Error: "Certificate file not found"

**Causa**: Los certificados AFIP no están en el directorio `certs/`

**Solución**:
```bash
# Verificar que existan los archivos
ls -la certs/
# Debe mostrar: cert.crt y private.key
```

### Error: "SOAP Fault: No autorizado"

**Causa**: El certificado no está habilitado para el servicio `ws_sr_padron_a13`

**Solución**:
1. Acceder a AFIP con clave fiscal
2. Verificar que el certificado tenga permiso para "Padrón A13"
3. Regenerar certificado si es necesario

### Error: "Failed to sign data with CMS/PKCS#7"

**Causa**: Problema con la clave privada o certificado

**Solución**:
- Verificar que el certificado y la clave coincidan
- Si la clave está cifrada, configurar `AFIP_KEY_PASSPHRASE` en `.env`

## Logging y Trazabilidad

Este microservicio implementa un sistema completo de logging estructurado para todas las comunicaciones con AFIP:

### Sistema de Logs REQ-RSP

Cada llamada a AFIP genera **2 log entries** con un `correlation_id` único:

```
[REQ] a1b2c3d4-e5f6-7890 | WSAA | loginCms
[RSP] a1b2c3d4-e5f6-7890 | WSAA | loginCms | SUCCESS | 1555ms
```

### Características del Logging

- **Correlation ID único**: UUID v4 para trazar cada transacción completa
- **Formato estructurado**: JSON para agregadores de logs (Datadog, CloudWatch, ELK)
- **Formato human-readable**: XMLs completos en nivel DEBUG para debugging local
- **Métricas de performance**: Duración en milisegundos de cada request
- **XMLs SOAP completos**: Captura de requests y responses para auditoría

### Ejemplo de Logs

```python
# Nivel INFO (producción) - Solo resumen
2024-03-14 10:30:15,234 INFO [REQ] abc123 | PADRON_A13 | getPersona_v2
2024-03-14 10:30:16,567 INFO [RSP] abc123 | PADRON_A13 | getPersona_v2 | SUCCESS | 1333ms

# Nivel DEBUG (desarrollo) - Incluye XMLs completos
2024-03-14 10:30:15,234 DEBUG [abc123] SOAP Request:
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope>
  ...
</soapenv:Envelope>
```

### Búsqueda y Filtrado

```bash
# Trazar una transacción completa por correlation_id
grep "abc123" logs/app.log

# Ver todos los errores
grep "\[RSP\]" logs/app.log | grep "ERROR"

# Ver requests lentos (> 2 segundos)
grep "\[RSP\]" logs/app.log | awk -F'|' '$NF > 2000'

# Ver consultas de un CUIT específico
grep "20351798239" logs/app.log | grep "PADRON_A13"
```

### Configuración de Log Level

```bash
# En .env
LOG_LEVEL=INFO    # Producción (solo resumen)
LOG_LEVEL=DEBUG   # Desarrollo (XMLs completos)
```

**Documentación completa**: Ver `LOG-FORMAT.md` para ejemplos detallados y formatos JSON.

**Flujo de comunicación con AFIP**: Ver `flujo-conexion.md` para diagramas y documentación técnica.

## Mejoras Futuras

Funcionalidades documentadas pero no implementadas (ver `FUTURE_ENHANCEMENTS.md`):

- **Metrics**: Prometheus + Grafana para monitoring
- **Rate Limiting**: Protección contra abuso (requests/minuto)
- **API Keys**: Autenticación de clientes del microservicio
- **Redis Cache**: Cache distribuido para ambientes multi-instancia
- **Circuit Breaker**: Resiliencia ante fallos de AFIP

## Stack Tecnológico

- **Framework**: FastAPI 0.104+
- **HTTP Client**: HTTPX (async)
- **SOAP Client**: Zeep
- **Criptografía**: cryptography, pyOpenSSL
- **Cache**: cachetools (in-memory TTL)
- **Validación**: Pydantic
- **Server**: Uvicorn
- **Containerización**: Docker, Docker Compose

## Estructura del Proyecto

```
cuit-validator/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config/
│   │   └── settings.py      # Configuración (Pydantic)
│   ├── controllers/
│   │   └── cuit_controller.py
│   ├── services/
│   │   ├── auth_service.py
│   │   └── cuit_service.py
│   ├── connectors/
│   │   ├── wsaa_connector.py
│   │   └── padron_connector.py
│   ├── models/
│   │   ├── afip_models.py   # TokenData, LoginTicketRequest
│   │   ├── requests.py      # CUITRequest
│   │   └── responses.py     # PersonaResponse, ErrorResponse
│   ├── exceptions/
│   │   └── custom_exceptions.py
│   ├── utils/
│   │   ├── crypto_utils.py
│   │   └── xml_utils.py
│   └── cache/
│       └── token_cache.py
├── tests/                   # Tests unitarios
├── certs/                   # Certificados AFIP (gitignored)
├── .env.example             # Template de configuración
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Licencia

[Especificar licencia del proyecto]

## Contacto

Para consultas o soporte, contactar al equipo de DevOps de BDS.

---

**Nota**: Este microservicio requiere certificados válidos de AFIP (Computador Fiscal) y autorización para el servicio "Padrón A13". Para pruebas, utilizar el ambiente TEST (homologación). A13 requiere Nivel 3 de Clave Fiscal.
