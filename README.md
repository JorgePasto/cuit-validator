# CUIT Validator API

Microservicio Python/FastAPI para consulta de contribuyentes argentinos mediante integración con los servicios SOAP de AFIP (Administración Federal de Ingresos Públicos).

Permite consultar datos de personas físicas y jurídicas por **CUIT** o por **número de documento (DNI)**, delegando la autenticación y comunicación con AFIP de forma transparente.

## Quick Start

```bash
# 1. Clonar y entrar al proyecto
git clone <repository-url>
cd cuit-validator

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env: configurar AFIP_CUIT, rutas de certificados y ENVIRONMENT

# 5. Colocar certificados AFIP
# cp /ruta/certificado.crt certs/afip_cert.crt
# cp /ruta/clave.key       certs/afip_private.key

# 6. Ejecutar
uvicorn app.main:app --reload

# Disponible en:
#   API:    http://localhost:8000
#   Swagger: http://localhost:8000/docs
#   ReDoc:   http://localhost:8000/redoc
```

## Características

- **Consulta por CUIT**: Datos completos del contribuyente (nombre/razón social, domicilio fiscal, estado)
- **Consulta por DNI**: Lista de personas asociadas a un documento, con datos básicos
- **Autenticación automática**: Gestión transparente de tokens WSAA con reintentos automáticos
- **Cache inteligente**: Tokens WSAA cacheados en memoria (TTL configurable, default 12 horas)
- **Logging estructurado**: REQ/RSP con `correlation_id` único, métricas de duración y XMLs SOAP
- **Multi-ambiente**: Soporte para TEST (homologación) y PROD
- **Arquitectura en capas**: Controller → Service → Connector
- **Dockerizado**: Listo para deployment con Docker y Docker Compose

## Servicios AFIP Utilizados

| Servicio | Uso |
|---|---|
| **WSAA** (Web Service de Autenticación y Autorización) | Obtención de tokens de acceso (LoginCms) |
| **Padrón A13** (`ws_sr_padron_a13`) | Consulta de datos de contribuyentes (requiere Clave Fiscal Nivel 3) |

## Requisitos Previos

### Certificados AFIP

Para utilizar este microservicio necesitás:

1. **Certificado digital AFIP** (`.crt`) — Formato PEM (Computador Fiscal)
2. **Clave privada** (`.key`) — Formato PEM
3. **CUIT habilitado** para el servicio `ws_sr_padron_a13`
4. **Clave Fiscal Nivel 3** o superior

Consultá `TUTORIAL-CERTIFICADOS-AFIP.md` para instrucciones paso a paso de cómo generar el CSR, obtener el certificado en el portal AFIP y asociarlo al servicio.

### Software

- **Python 3.11+** (para ejecución local)
- **Docker y Docker Compose** (para ejecución containerizada)

## Instalación

### Opción 1: Ejecución local (desarrollo)

```bash
# Clonar repositorio
git clone <repository-url>
cd cuit-validator

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu configuración (ver sección Configuración)

# Colocar certificados AFIP en certs/
mkdir -p certs
# cp /ruta/a/certificado.crt certs/afip_cert.crt
# cp /ruta/a/clave.key       certs/afip_private.key

# Ejecutar con recarga automática
uvicorn app.main:app --reload

# Producción (sin reload, múltiples workers):
# uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Opción 2: Docker Compose (producción)

```bash
# Clonar repositorio
git clone <repository-url>
cd cuit-validator

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu configuración

# Colocar certificados en certs/
# (el docker-compose monta ./certs como volumen de solo lectura)

# Construir y ejecutar
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f

# Detener
docker-compose down
```

## Configuración

Todas las variables se configuran en el archivo `.env` (copiarlo desde `.env.example`):

| Variable | Default | Descripción |
|---|---|---|
| `ENVIRONMENT` | `TEST` | Ambiente: `TEST` (homologación) o `PROD` |
| `AFIP_CERT_PATH` | — | Ruta al certificado X.509 (`.crt`) |
| `AFIP_KEY_PATH` | — | Ruta a la clave privada RSA (`.key`) |
| `AFIP_KEY_PASSPHRASE` | `""` | Passphrase de la clave privada (si aplica) |
| `AFIP_CUIT` | — | CUIT del certificado (quien realiza las consultas) |
| `TOKEN_CACHE_TTL_HOURS` | `12` | TTL del cache de tokens en horas |
| `LOG_LEVEL` | `INFO` | Nivel de logging: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `PORT` | `8000` | Puerto del servidor |
| `HOST` | `0.0.0.0` | Host del servidor |

### URLs por ambiente

| Ambiente | WSAA | Padrón A13 |
|---|---|---|
| **TEST** | `https://wsaahomo.afip.gov.ar/ws/services/LoginCms` | `https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA13` |
| **PROD** | `https://wsaa.afip.gov.ar/ws/services/LoginCms` | `https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13` |

## Uso de la API

El prefijo base de todos los endpoints es `/cuit-validator/v1`.

### Endpoints

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/cuit-validator/v1/health` | Health check |
| `GET` | `/cuit-validator/v1/cuit/{cuit}` | Consulta contribuyente por CUIT |
| `POST` | `/cuit-validator/v1/cuit/validate` | Consulta contribuyente por CUIT (body JSON) |
| `GET` | `/cuit-validator/v1/dni/{dni}` | Consulta personas por número de documento |
| `GET` | `/cuit-validator/v1/cache/stats` | Estadísticas del cache de tokens |
| `DELETE` | `/cuit-validator/v1/cache/clear` | Limpia todo el cache de tokens |
| `DELETE` | `/cuit-validator/v1/cache/invalidate/{service_name}` | Invalida token de un servicio |

---

#### Health Check

```bash
GET /cuit-validator/v1/health
```

```json
{
  "status": "ok",
  "environment": "TEST",
  "timestamp": "2026-03-16T22:30:00.000000"
}
```

---

#### Consultar CUIT (GET)

```bash
GET /cuit-validator/v1/cuit/{cuit}
```

Acepta el CUIT con o sin guiones: `20-12345678-9` o `20123456789`.

```bash
curl http://localhost:8000/cuit-validator/v1/cuit/20351798239
```

**Respuesta exitosa (200)**:
```json
{
  "cuit": "20351798239",
  "tipo_persona": "FISICA",
  "apellido": "PEREZ",
  "nombre": "JUAN CARLOS",
  "razon_social": null,
  "domicilio_fiscal": {
    "direccion": "AV CORRIENTES 1234 PISO 5",
    "localidad": "CAPITAL FEDERAL",
    "provincia": "CIUDAD AUTONOMA BUENOS AIRES",
    "codigo_postal": "1043"
  },
  "estado_clave": "ACTIVO"
}
```

**Errores posibles**:

| Código | Error | Causa |
|---|---|---|
| `400` | `INVALID_CUIT_FORMAT` | CUIT con formato inválido (no 11 dígitos) |
| `404` | `CUIT_NOT_FOUND` | CUIT no encontrado en AFIP |
| `401` | `AUTHENTICATION_FAILED` | Error de autenticación WSAA |
| `503` | `SERVICE_UNAVAILABLE` | Servicio AFIP temporalmente no disponible |

---

#### Consultar CUIT (POST)

```bash
POST /cuit-validator/v1/cuit/validate
Content-Type: application/json
```

```bash
curl -X POST http://localhost:8000/cuit-validator/v1/cuit/validate \
  -H "Content-Type: application/json" \
  -d '{"cuit": "20351798239"}'
```

Retorna el mismo `PersonaResponse` que el endpoint GET.

---

#### Consultar por DNI

```bash
GET /cuit-validator/v1/dni/{dni}
```

Busca todos los CUITs asociados al número de documento y retorna datos básicos de cada persona (sin domicilio fiscal).

```bash
curl http://localhost:8000/cuit-validator/v1/dni/35179823
```

**Respuesta exitosa (200)**:
```json
[
  {
    "cuit": "20351798239",
    "tipo_persona": "FISICA",
    "apellido": "PEREZ",
    "nombre": "JUAN CARLOS",
    "razon_social": null,
    "estado_clave": "ACTIVO"
  }
]
```

El endpoint puede retornar múltiples personas si el DNI está asociado a más de un CUIT. Si no se encuentran personas, retorna una lista vacía `[]`.

**Errores posibles**:

| Código | Error | Causa |
|---|---|---|
| `401` | `AUTHENTICATION_FAILED` | Error de autenticación WSAA |
| `503` | `SERVICE_UNAVAILABLE` | Servicio AFIP temporalmente no disponible |

---

#### Administración del Cache

```bash
# Ver estadísticas
GET /cuit-validator/v1/cache/stats

# Limpiar todo el cache (fuerza renovación de todos los tokens)
DELETE /cuit-validator/v1/cache/clear

# Invalidar token de un servicio específico
DELETE /cuit-validator/v1/cache/invalidate/ws_sr_padron_a13
```

Útil para resolver errores `alreadyAuthenticated` de AFIP sin reiniciar el servicio.

---

### Documentación interactiva

Con el servicio corriendo:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Arquitectura

```
Cliente HTTP
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  Controllers  (app/controllers/)                            │
│    └─ cuit_controller.py  — Endpoints REST + manejo HTTP   │
├─────────────────────────────────────────────────────────────┤
│  Services  (app/services/)                                  │
│    ├─ cuit_service.py  — Lógica: consulta por CUIT         │
│    ├─ dni_service.py   — Lógica: consulta por DNI          │
│    └─ auth_service.py  — Tokens WSAA + cache               │
├─────────────────────────────────────────────────────────────┤
│  Connectors  (app/connectors/)                              │
│    ├─ padron_connector.py  — AFIP Padrón A13 (Zeep/SOAP)  │
│    └─ wsaa_connector.py    — AFIP WSAA (httpx/SOAP manual) │
├─────────────────────────────────────────────────────────────┤
│  Utils  (app/utils/)                                        │
│    ├─ afip_logger.py   — Logger REQ/RSP con correlation_id │
│    ├─ crypto_utils.py  — Firma CMS/PKCS#7 (cryptography)  │
│    └─ xml_utils.py     — Generación/parseo de XML SOAP     │
├─────────────────────────────────────────────────────────────┤
│  Cache  (app/cache/)                                        │
│    └─ token_cache.py  — TTLCache en memoria (cachetools)   │
└─────────────────────────────────────────────────────────────┘
     │                              │
     ▼                              ▼
AFIP Padrón A13               AFIP WSAA
(ws_sr_padron_a13)            (LoginCms)
```

### Flujo de consulta por CUIT

```
Request → Controller → CUITService → AuthService (cache/WSAA)
                                   → PadronConnector.getPersona()
                     ← PersonaResponse ←─────────────────────
```

### Flujo de consulta por DNI

```
Request → Controller → DNIService → AuthService (cache/WSAA)
                                  → PadronConnector.getIdPersonaListByDocumento()
                                    (devuelve lista de CUITs)
                                  → PadronConnector.getPersona() × N CUITs
                     ← list[PersonaSummaryResponse] ──────────
```

## Estructura del Proyecto

```
cuit-validator/
├── app/
│   ├── main.py                    # Entrypoint FastAPI, lifespan, middlewares
│   ├── config/
│   │   └── settings.py            # Configuración centralizada (pydantic-settings)
│   ├── controllers/
│   │   └── cuit_controller.py     # Endpoints REST
│   ├── services/
│   │   ├── auth_service.py        # Orquestación de tokens WSAA + cache
│   │   ├── cuit_service.py        # Lógica de consulta por CUIT
│   │   └── dni_service.py         # Lógica de consulta por DNI
│   ├── connectors/
│   │   ├── padron_connector.py    # Comunicación con Padrón A13 (Zeep/SOAP)
│   │   └── wsaa_connector.py      # Comunicación con WSAA (autenticación)
│   ├── models/
│   │   ├── afip_models.py         # TokenData, LoginTicketRequest
│   │   ├── requests.py            # CUITRequest
│   │   └── responses.py           # PersonaResponse, PersonaSummaryResponse, ErrorResponse
│   ├── cache/
│   │   └── token_cache.py         # TTLCache (cachetools), Singleton
│   ├── exceptions/
│   │   └── custom_exceptions.py   # Jerarquía de excepciones custom
│   └── utils/
│       ├── afip_logger.py         # Logger estructurado REQ/RSP
│       ├── crypto_utils.py        # Firma CMS/PKCS#7
│       └── xml_utils.py           # Generación y parseo de XML
├── certs/                         # Certificados AFIP (gitignored)
│   └── .gitkeep
├── logs/                          # Logs de aplicación (gitignored)
│   └── xml/                       # XMLs SOAP guardados automáticamente
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example                   # Plantilla de variables de entorno
├── .gitignore
├── flujo-conexion.md              # Diagrama de secuencia + troubleshooting AFIP
├── LOG-FORMAT.md                  # Documentación del sistema de logging
└── TUTORIAL-CERTIFICADOS-AFIP.md  # Guía de certificados AFIP paso a paso
```

## Stack Tecnológico

| Paquete | Versión | Uso |
|---|---|---|
| `fastapi` | 0.135.1 | Framework REST |
| `uvicorn[standard]` | 0.42.0 | Servidor ASGI |
| `httpx` | 0.28.1 | Cliente HTTP async (WSAA) |
| `zeep` | 4.3.2 | Cliente SOAP (Padrón A13) |
| `pydantic` | 2.12.5 | Modelos y validación |
| `pydantic-settings` | 2.13.1 | Configuración desde `.env` |
| `cryptography` | 46.0.1 | Firma CMS/PKCS#7 |
| `pyopenssl` | 25.3.0 | Firma alternativa legacy |
| `cachetools` | 6.2.1 | TTLCache para tokens |
| `pytest` | 8.4.2 | Testing |
| `pytest-asyncio` | 1.3.0 | Testing async |

## Logging y Trazabilidad

Cada llamada a AFIP genera un par de entradas de log con un `correlation_id` único (UUID v4):

```
2026-03-16 22:30:58 INFO  [REQ] ae62539f | PersonaServiceA13 | getPersona | url=...
2026-03-16 22:30:58 INFO  [RSP] ae62539f | PersonaServiceA13 | getPersona | SUCCESS | 245ms
```

Características:
- **Correlation ID**: UUID v4 para trazar cada transacción de extremo a extremo
- **Métricas de duración**: milisegundos por llamada
- **XMLs SOAP completos**: guardados en `logs/xml/` para auditoría
- **Formato JSON** a nivel INFO (compatible con Datadog, CloudWatch, ELK)
- **XMLs human-readable** a nivel DEBUG para debugging local

```bash
# Filtrar logs por correlation_id
grep "ae62539f" logs/app.log

# Ver todos los errores
grep "\[RSP\]" logs/app.log | grep "ERROR"

# Ver requests lentos (> 2 segundos)
grep "\[RSP\]" logs/app.log | awk -F'|' '$NF > 2000'
```

Ver `LOG-FORMAT.md` para documentación completa del formato y ejemplos.

## Seguridad

- **Certificados**: Los archivos `.crt`, `.key` y `.p12` están en `.gitignore` y **nunca deben commitearse**
- **Variables sensibles**: Toda la configuración va en `.env` (también en `.gitignore`)
- **Usuario non-root**: El container Docker ejecuta con usuario sin privilegios
- **Tokens**: No se registran tokens ni firmas en los logs

## Troubleshooting

### `Certificate file not found`

Los certificados no están en la ruta configurada en `.env`.

```bash
ls -la certs/
# Verificar que existan afip_cert.crt y afip_private.key
```

### `SOAP Fault: coe.alreadyAuthenticated`

AFIP rechaza la autenticación porque el token anterior aún está activo en su servidor.

```bash
# Invalidar el token cacheado y forzar renovación
curl -X DELETE http://localhost:8000/cuit-validator/v1/cache/invalidate/ws_sr_padron_a13
```

### `SOAP Fault: coe.notAuthorized`

El certificado no tiene permiso para el servicio `ws_sr_padron_a13`.

1. Acceder a AFIP con clave fiscal Nivel 3
2. Ir a "Administración de Certificados Digitales"
3. Asociar el certificado al servicio "ws_sr_padron_a13"

### `Failed to sign data with CMS/PKCS#7`

Problema con la clave privada o el certificado.

- Verificar que el `.crt` y el `.key` correspondan al mismo par
- Si la clave está cifrada, configurar `AFIP_KEY_PASSPHRASE` en `.env`

### Python 2.x en lugar de 3.11+

```bash
python3 -m venv venv
source venv/bin/activate
python --version  # Debe mostrar 3.11+
```

Ver `flujo-conexion.md` para troubleshooting avanzado de la comunicación con AFIP.

## Testing

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Con reporte de cobertura
pytest tests/ --cov=app --cov-report=html
```

## Mejoras Futuras

- **Rate Limiting**: Protección contra abuso (requests/minuto por cliente)
- **API Keys**: Autenticación de consumidores del microservicio
- **Redis Cache**: Cache distribuido para ambientes multi-instancia
- **Circuit Breaker**: Resiliencia automática ante fallos de AFIP
- **Métricas Prometheus**: Monitoring con Grafana

---

**Nota**: Este microservicio requiere certificados válidos de AFIP (Computador Fiscal) y autorización explícita para el servicio `ws_sr_padron_a13`. Para pruebas, usar `ENVIRONMENT=TEST` (homologación AFIP). El servicio A13 requiere Clave Fiscal Nivel 3 o superior.
