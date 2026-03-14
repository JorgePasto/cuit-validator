# CUIT Validator API

Microservicio Python/FastAPI para validación y consulta de CUITs argentinos mediante integración con servicios AFIP (Administración Federal de Ingresos Públicos).

## Características

- **Consulta de CUITs**: Obtiene información completa de contribuyentes (nombres, razón social, domicilio fiscal)
- **Autenticación automática**: Gestión transparente de tokens WSAA (Web Service de Autenticación y Autorización)
- **Cache inteligente**: Tokens WSAA cacheados en memoria por 12 horas para optimizar performance
- **Multi-ambiente**: Soporte para TEST (homologación) y PROD
- **Arquitectura limpia**: Patrón Controller → Service → Connector (3 capas)
- **Dockerizado**: Listo para deployment con Docker y Docker Compose

## Servicios AFIP Utilizados

1. **WSAA** (Web Service de Autenticación y Autorización): Obtención de tokens de acceso
2. **Padrón A10**: Consulta de datos de personas físicas y jurídicas

## Requisitos Previos

### Certificados AFIP

Para utilizar este microservicio necesitas:

1. **Certificado digital AFIP** (`.crt`) - Formato PEM
2. **Clave privada** (`.key`) - Formato PEM
3. **CUIT habilitado** para el servicio `ws_sr_padron_a10`

**Cómo obtener certificados AFIP**:
- Acceder al sitio de AFIP con clave fiscal
- Generar un certificado digital para el servicio "Padrón A10"
- Descargar el certificado (.crt) y la clave privada (.key)
- Colocarlos en el directorio `certs/`

### Software

- **Python 3.11+** (para ejecución local)
- **Docker y Docker Compose** (para ejecución containerizada)

## Instalación

### Opción 1: Ejecución Local (Python)

```bash
# 1. Clonar repositorio
git clone <repository-url>
cd cuit-validator

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tu configuración

# 5. Colocar certificados AFIP
# Copiar cert.crt y private.key al directorio certs/

# 6. Ejecutar microservicio
python -m app.main
```

El servidor estará disponible en: `http://localhost:8000`

### Opción 2: Docker Compose (Recomendado)

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
  - Padrón A10: `https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA10`

- **PROD**: Utiliza URLs de producción AFIP
  - WSAA: `https://wsaa.afip.gov.ar/ws/services/LoginCms`
  - Padrón A10: `https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA10`

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
GET /api/v1/cuit/{cuit}
```

**Ejemplo**:
```bash
curl http://localhost:8000/api/v1/cuit/20123456789
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
POST /api/v1/cuit/validate
Content-Type: application/json

{
  "cuit": "20123456789"
}
```

**Ejemplo con curl**:
```bash
curl -X POST http://localhost:8000/api/v1/cuit/validate \
  -H "Content-Type: application/json" \
  -d '{"cuit": "20123456789"}'
```

#### 4. Estadísticas del Cache (Admin)

```bash
GET /api/v1/cache/stats
```

**Respuesta**:
```json
{
  "cache_stats": {
    "size": 1,
    "maxsize": 100,
    "ttl_seconds": 43200,
    "services": ["ws_sr_padron_a10"]
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
│    └─ xml_utils.py        → XML generation/parsing         │
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

### Error: "Certificate file not found"

**Causa**: Los certificados AFIP no están en el directorio `certs/`

**Solución**:
```bash
# Verificar que existan los archivos
ls -la certs/
# Debe mostrar: cert.crt y private.key
```

### Error: "SOAP Fault: No autorizado"

**Causa**: El certificado no está habilitado para el servicio `ws_sr_padron_a10`

**Solución**:
1. Acceder a AFIP con clave fiscal
2. Verificar que el certificado tenga permiso para "Padrón A10"
3. Regenerar certificado si es necesario

### Error: "Failed to sign data with CMS/PKCS#7"

**Causa**: Problema con la clave privada o certificado

**Solución**:
- Verificar que el certificado y la clave coincidan
- Si la clave está cifrada, configurar `AFIP_KEY_PASSPHRASE` en `.env`

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

**Nota**: Este microservicio requiere certificados válidos de AFIP y autorización para el servicio "Padrón A10". Para pruebas, utilizar el ambiente TEST (homologación).
