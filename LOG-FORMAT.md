# Logs REQ-RSP de AFIP - Formato y Ejemplos

## Descripción

Este documento describe el formato de logging estructurado implementado para todas las comunicaciones con AFIP. Cada request/response se loggea con un **correlation_id** único que permite trazar la comunicación completa.

---

## Formato de Logs

### Estructura de Log Entries

Cada llamada a AFIP genera **2 log entries**:

1. **[REQ]** - Request enviado a AFIP
2. **[RSP]** - Response recibido de AFIP

**Formato del mensaje:**
```
[REQ] {correlation_id} | {service} | {operation}
[RSP] {correlation_id} | {service} | {operation} | {status} | {duration_ms}
```

**Campos adicionales (en `extra`):**
- `correlation_id`: UUID v4 único para correlacionar REQ-RSP
- `service`: Nombre del servicio AFIP (`WSAA`, `PADRON_A13`)
- `operation`: Operación llamada (`loginCms`, `getPersona_v2`)
- `timestamp`: ISO 8601 timestamp
- `url`: URL del servicio AFIP
- `status`: `SUCCESS` o `ERROR`
- `status_code`: HTTP status code
- `duration_ms`: Duración en milisegundos
- `request_data` / `response_data`: Datos completos del request/response
- `soap_envelope` / `soap_response`: XML completo (para SOAP)

---

## Ejemplos de Logs

### Ejemplo 1: Autenticación WSAA (LoginCms) - Exitoso

#### REQUEST
```
2024-03-14 10:30:15,234 INFO [app.utils.afip_logger] [REQ] a1b2c3d4-e5f6-7890-abcd-ef1234567890 | WSAA | loginCms
```

**Log estructurado (JSON):**
```json
{
  "type": "REQUEST",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "service": "WSAA",
  "operation": "loginCms",
  "timestamp": "2024-03-14T10:30:15.234000",
  "url": "https://wsaahomo.afip.gov.ar/ws/services/LoginCms",
  "headers": {
    "Content-Type": "text/xml; charset=utf-8",
    "SOAPAction": ""
  },
  "request_type": "SOAP",
  "soap_length": 3456
}
```

**Log DEBUG (human-readable):**
```
================================================================================
[AFIP SOAP REQUEST]
Correlation ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Service: WSAA
Operation: loginCms
URL: https://wsaahomo.afip.gov.ar/ws/services/LoginCms
Timestamp: 2024-03-14T10:30:15.234000
SOAP Length: 3456 bytes
Headers: {
  "Content-Type": "text/xml; charset=utf-8",
  "SOAPAction": ""
}
SOAP Envelope:
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
                  xmlns:wsaa="http://wsaa.view.sua.dvadac.desein.afip.gov">
    <soapenv:Header/>
    <soapenv:Body>
        <wsaa:loginCms>
            <wsaa:in0>MIIHfgYJKoZIhvcNAQcCoIIHbzCCB2sCAQExDzANBglghkgBZQMEAgEFADALBgkq...</wsaa:in0>
        </wsaa:loginCms>
    </soapenv:Body>
</soapenv:Envelope>
================================================================================
```

#### RESPONSE
```
2024-03-14 10:30:16,789 INFO [app.utils.afip_logger] [RSP] a1b2c3d4-e5f6-7890-abcd-ef1234567890 | WSAA | loginCms | SUCCESS | 1555ms
```

**Log estructurado (JSON):**
```json
{
  "type": "RESPONSE",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "service": "WSAA",
  "operation": "loginCms",
  "timestamp": "2024-03-14T10:30:16.789000",
  "status": "SUCCESS",
  "status_code": 200,
  "duration_ms": 1555,
  "headers": {
    "Content-Type": "text/xml; charset=utf-8"
  },
  "response_type": "SOAP",
  "soap_length": 2834,
  "error": null
}
```

**Log DEBUG (human-readable):**
```
================================================================================
[AFIP SOAP RESPONSE]
Correlation ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Service: WSAA
Operation: loginCms
Status: SUCCESS (200)
Duration: 1555ms
Timestamp: 2024-03-14T10:30:16.789000
SOAP Length: 2834 bytes
Headers: {
  "Content-Type": "text/xml; charset=utf-8"
}
SOAP Response:
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <soapenv:Body>
        <loginCmsReturn>
            <token>PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9InllcyI/Pgo...</token>
            <sign>hZ8fQ2Vr3K9lN4pXwY6tU7mJ5nR8sO2vA1bC9dE6fG3hI4jK5lM6nO7pQ8rS9tU0vW1xY2zA...</sign>
            <generationTime>2024-03-14T10:30:16.000-03:00</generationTime>
            <expirationTime>2024-03-14T22:30:16.000-03:00</expirationTime>
        </loginCmsReturn>
    </soapenv:Body>
</soapenv:Envelope>
================================================================================
```

---

### Ejemplo 2: Consulta Padrón A13 (getPersona_v2) - Exitoso

#### REQUEST
```
2024-03-14 10:30:17,123 INFO [app.utils.afip_logger] [REQ] f9e8d7c6-b5a4-3210-9876-543210fedcba | PADRON_A13 | getPersona_v2
```

**Log estructurado (JSON):**
```json
{
  "type": "REQUEST",
  "correlation_id": "f9e8d7c6-b5a4-3210-9876-543210fedcba",
  "service": "PADRON_A13",
  "operation": "getPersona_v2",
  "timestamp": "2024-03-14T10:30:17.123000",
  "url": "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13",
  "request_data": {
    "cuitRepresentada": "20351798239",
    "idPersona": "20351798239",
    "token_length": 2048,
    "sign_length": 512
  }
}
```

**Log DEBUG (human-readable):**
```
================================================================================
[AFIP REQUEST]
Correlation ID: f9e8d7c6-b5a4-3210-9876-543210fedcba
Service: PADRON_A13
Operation: getPersona_v2
URL: https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13
Timestamp: 2024-03-14T10:30:17.123000
Headers: {}
Request Data:
{
  "cuitRepresentada": "20351798239",
  "idPersona": "20351798239",
  "token_length": 2048,
  "sign_length": 512
}
================================================================================

[f9e8d7c6-b5a4-3210-9876-543210fedcba] SOAP Request:
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:per="http://a13.soap.ws.server.puc.sr/">
    <soapenv:Header/>
    <soapenv:Body>
        <per:getPersona_v2>
            <token>PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9InllcyI/Pgo...</token>
            <sign>hZ8fQ2Vr3K9lN4pXwY6tU7mJ5nR8sO2vA1bC9dE6fG3hI4jK5lM6nO7pQ8rS9tU0vW1xY2zA...</sign>
            <cuitRepresentada>20351798239</cuitRepresentada>
            <idPersona>20351798239</idPersona>
        </per:getPersona_v2>
    </soapenv:Body>
</soapenv:Envelope>
```

#### RESPONSE
```
2024-03-14 10:30:18,456 INFO [app.utils.afip_logger] [RSP] f9e8d7c6-b5a4-3210-9876-543210fedcba | PADRON_A13 | getPersona_v2 | SUCCESS | 1333ms
```

**Log estructurado (JSON):**
```json
{
  "type": "RESPONSE",
  "correlation_id": "f9e8d7c6-b5a4-3210-9876-543210fedcba",
  "service": "PADRON_A13",
  "operation": "getPersona_v2",
  "timestamp": "2024-03-14T10:30:18.456000",
  "status": "SUCCESS",
  "status_code": 200,
  "duration_ms": 1333,
  "response_type": "SOAP",
  "soap_length": 5678,
  "error": null
}
```

**Log DEBUG (human-readable con SOAP completo):**
```
================================================================================
[AFIP SOAP RESPONSE]
Correlation ID: f9e8d7c6-b5a4-3210-9876-543210fedcba
Service: PADRON_A13
Operation: getPersona_v2
Status: SUCCESS (200)
Duration: 1333ms
Timestamp: 2024-03-14T10:30:18.456000
SOAP Length: 5678 bytes
Headers: {}
SOAP Response:
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <soapenv:Body>
        <getPersona_v2Response>
            <personaReturn>
                <datosGenerales>
                    <tipoPersona>FISICA</tipoPersona>
                    <apellido>PASTORINO</apellido>
                    <nombre>JORGE</nombre>
                    <razonSocial></razonSocial>
                    <estadoClave>ACTIVO</estadoClave>
                    <idPersona>20351798239</idPersona>
                </datosGenerales>
                <domicilioFiscal>
                    <direccion>AV CORRIENTES 1234 PISO 5 DPTO B</direccion>
                    <localidad>CAPITAL FEDERAL</localidad>
                    <descripcionProvincia>CIUDAD AUTONOMA BUENOS AIRES</descripcionProvincia>
                    <codPostal>C1043AAZ</codPostal>
                    <tipoDomicilio>FISCAL</tipoDomicilio>
                </domicilioFiscal>
                <actividades>
                    <actividad>
                        <idActividad>620200</idActividad>
                        <descripcion>SERVICIOS DE CONSULTORIA EN INFORMATICA Y SUMINISTROS</descripcion>
                        <orden>1</orden>
                        <periodo>202401</periodo>
                    </actividad>
                </actividades>
                <impuestos>
                    <impuesto>
                        <idImpuesto>30</idImpuesto>
                        <descripcion>IVA</descripcion>
                        <periodo>202401</periodo>
                    </impuesto>
                </impuestos>
            </personaReturn>
        </getPersona_v2Response>
    </soapenv:Body>
</soapenv:Envelope>
================================================================================
```

---

### Ejemplo 3: Error de Autenticación (coe.alreadyAuthenticated)

#### REQUEST
```
2024-03-14 10:35:20,100 INFO [app.utils.afip_logger] [REQ] 12345678-abcd-1234-ef56-7890abcdef12 | WSAA | loginCms
```

#### RESPONSE (ERROR)
```
2024-03-14 10:35:21,234 ERROR [app.utils.afip_logger] [RSP] 12345678-abcd-1234-ef56-7890abcdef12 | WSAA | loginCms | ERROR | 1134ms
```

**Log estructurado (JSON):**
```json
{
  "type": "RESPONSE",
  "correlation_id": "12345678-abcd-1234-ef56-7890abcdef12",
  "service": "WSAA",
  "operation": "loginCms",
  "timestamp": "2024-03-14T10:35:21.234000",
  "status": "ERROR",
  "status_code": 500,
  "duration_ms": 1134,
  "headers": {
    "Content-Type": "text/xml; charset=utf-8"
  },
  "response_type": "SOAP",
  "soap_length": 856,
  "error": "[ns1:coe.alreadyAuthenticated] El CEE ya posee un TA valido para el acceso al WSN solicitado"
}
```

**Log DEBUG (SOAP con FAULT):**
```
================================================================================
[AFIP SOAP RESPONSE]
Correlation ID: 12345678-abcd-1234-ef56-7890abcdef12
Service: WSAA
Operation: loginCms
Status: ERROR (500)
Duration: 1134ms
Timestamp: 2024-03-14T10:35:21.234000
SOAP Length: 856 bytes
SOAP Response:
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <soapenv:Body>
        <soapenv:Fault>
            <faultcode>ns1:coe.alreadyAuthenticated</faultcode>
            <faultstring>El CEE ya posee un TA valido para el acceso al WSN solicitado</faultstring>
        </soapenv:Fault>
    </soapenv:Body>
</soapenv:Envelope>
================================================================================
```

---

### Ejemplo 4: CUIT No Encontrado

#### REQUEST
```
2024-03-14 10:40:00,500 INFO [app.utils.afip_logger] [REQ] 99887766-5544-3322-1100-aabbccddeeff | PADRON_A13 | getPersona_v2
```

#### RESPONSE (ERROR)
```
2024-03-14 10:40:01,800 ERROR [app.utils.afip_logger] [RSP] 99887766-5544-3322-1100-aabbccddeeff | PADRON_A13 | getPersona_v2 | ERROR | 1300ms
```

**Log estructurado (JSON):**
```json
{
  "type": "RESPONSE",
  "correlation_id": "99887766-5544-3322-1100-aabbccddeeff",
  "service": "PADRON_A13",
  "operation": "getPersona_v2",
  "timestamp": "2024-03-14T10:40:01.800000",
  "status": "ERROR",
  "status_code": 500,
  "duration_ms": 1300,
  "response_data": {
    "fault": "CUIT 12345678901 no encontrado en base de datos",
    "cuit": "12345678901"
  },
  "error": "CUIT 12345678901 no encontrado en base de datos"
}
```

---

## Búsqueda y Filtrado de Logs

### Por Correlation ID (trazar comunicación completa)
```bash
# Ver todos los logs de una transacción específica
grep "a1b2c3d4-e5f6-7890-abcd-ef1234567890" logs/app.log

# Salida:
# 2024-03-14 10:30:15,234 INFO [REQ] a1b2c3d4-e5f6-7890-abcd-ef1234567890 | WSAA | loginCms
# 2024-03-14 10:30:16,789 INFO [RSP] a1b2c3d4-e5f6-7890-abcd-ef1234567890 | WSAA | loginCms | SUCCESS | 1555ms
```

### Por Servicio
```bash
# Ver todos los requests/responses a WSAA
grep "WSAA" logs/app.log | grep -E "\[REQ\]|\[RSP\]"

# Ver todos los requests/responses a Padrón A13
grep "PADRON_A13" logs/app.log | grep -E "\[REQ\]|\[RSP\]"
```

### Por Status
```bash
# Ver solo errores
grep "\[RSP\]" logs/app.log | grep "ERROR"

# Ver solo exitosos
grep "\[RSP\]" logs/app.log | grep "SUCCESS"
```

### Por CUIT
```bash
# Ver consultas de un CUIT específico
grep "20351798239" logs/app.log | grep "PADRON_A13"
```

### Por Duración (requests lentos)
```bash
# Ver requests que tardaron más de 2 segundos (2000ms)
grep "\[RSP\]" logs/app.log | awk -F'|' '$NF > 2000'
```

---

## Integración con Agregadores de Logs

### Datadog
```python
import logging
from datadog import initialize, statsd

# Los logs con `extra={'afip_request': {...}}` se envían automáticamente
# Datadog parsea el JSON y permite búsquedas avanzadas:
# - @correlation_id:a1b2c3d4-e5f6-7890-abcd-ef1234567890
# - @service:WSAA
# - @status:ERROR
# - @duration_ms:>2000
```

### CloudWatch Logs
```python
# CloudWatch Insights query:
fields @timestamp, correlation_id, service, operation, status, duration_ms
| filter service = "WSAA"
| filter status = "ERROR"
| sort @timestamp desc
| limit 100
```

### ELK Stack (Elasticsearch + Kibana)
```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "service": "PADRON_A13" }},
        { "match": { "status": "SUCCESS" }},
        { "range": { "duration_ms": { "gte": 1000 }}}
      ]
    }
  }
}
```

---

## Ventajas del Sistema de Logging

### 1. **Trazabilidad Completa**
- Cada request tiene un `correlation_id` único
- Permite seguir toda la cadena de comunicación
- Útil para debugging de errores intermitentes

### 2. **Formato Estructurado (JSON)**
- Compatible con agregadores de logs modernos
- Búsquedas avanzadas y filtros eficientes
- Dashboards y alertas automatizadas

### 3. **Doble Formato**
- **JSON estructurado**: Para sistemas automatizados
- **Human-readable**: Para debugging local en desarrollo

### 4. **Métricas de Performance**
- Duración de cada request en milisegundos
- Permite identificar cuellos de botella
- Estadísticas de latencia de AFIP

### 5. **Auditoría y Compliance**
- Registro completo de todas las comunicaciones con AFIP
- XMLs completos (request y response)
- Timestamps precisos para auditoría

### 6. **Debugging Simplificado**
- Ver XMLs completos en logs DEBUG
- Identificar requests problemáticos
- Correlacionar con logs del lado AFIP

---

## Configuración de Log Level

### Producción (INFO)
```python
# Solo muestra líneas de resumen REQ/RSP
logging.basicConfig(level=logging.INFO)

# Salida:
# [REQ] abc123 | WSAA | loginCms
# [RSP] abc123 | WSAA | loginCms | SUCCESS | 1555ms
```

### Desarrollo (DEBUG)
```python
# Muestra XMLs completos y detalles
logging.basicConfig(level=logging.DEBUG)

# Salida: Incluye todos los XMLs SOAP completos (ver ejemplos arriba)
```

### Configuración Recomendada (.env)
```bash
# Producción
LOG_LEVEL=INFO

# Desarrollo/Troubleshooting
LOG_LEVEL=DEBUG
```

---

## Próximos Pasos

### Mejoras Sugeridas

1. **Persistencia de Logs**
   - Rotar logs diariamente
   - Compresión de logs antiguos
   - Retención configurable (ej: 30 días)

2. **Métricas Prometheus**
   ```python
   afip_request_duration_seconds.observe(duration_ms / 1000)
   afip_requests_total.labels(service='WSAA', status='success').inc()
   ```

3. **Alertas Automáticas**
   - Tasa de errores > 10%
   - Latencia promedio > 3 segundos
   - Errores `coe.notAuthorized` (certificado no asociado)

4. **Dashboard Grafana**
   - Gráficos de latencia por servicio
   - Distribución de status codes
   - Top N CUITs consultados
   - Tasa de éxito/error por hora
