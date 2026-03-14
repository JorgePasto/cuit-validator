# Tutorial: Obtener Certificado Digital AFIP para Padrón A13

Este tutorial te guiará paso a paso para obtener y configurar el certificado digital AFIP necesario para utilizar el servicio **ws_sr_padron_a13**.

---

## Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Ambientes Disponibles](#ambientes-disponibles)
3. [Paso 1: Generar Certificado y Clave Privada](#paso-1-generar-certificado-y-clave-privada)
4. [Paso 2: Crear CSR (Certificate Signing Request)](#paso-2-crear-csr-certificate-signing-request)
5. [Paso 3: Subir CSR a AFIP](#paso-3-subir-csr-a-afip)
6. [Paso 4: Asociar Certificado al Servicio ws_sr_padron_a13](#paso-4-asociar-certificado-al-servicio-ws_sr_padron_a13)
7. [Paso 5: Descargar Certificado de AFIP](#paso-5-descargar-certificado-de-afip)
8. [Paso 6: Configurar el Microservicio](#paso-6-configurar-el-microservicio)
9. [Verificación y Testing](#verificación-y-testing)
10. [Troubleshooting](#troubleshooting)

---

## Requisitos Previos

### Software Necesario

- **OpenSSL** instalado (viene preinstalado en Linux/macOS, en Windows descargar de [https://slproweb.com/products/Win32OpenSSL.html](https://slproweb.com/products/Win32OpenSSL.html))
- **Navegador web** compatible (Chrome, Firefox, Edge)
- **Clave Fiscal AFIP** nivel 2 o superior (A13 requiere menor nivel que A10)

### Accesos Requeridos

- CUIT habilitado para operar con AFIP
- Usuario y clave fiscal de AFIP
- Permiso de Administrador del sistema (para asociar certificados)

### URLs AFIP

**Homologación (TEST)**:
- Portal AFIP: `https://auth.afip.gob.ar/contribuyente_/homologacion.xhtml`
- WSAA: `https://wsaahomo.afip.gov.ar/ws/services/LoginCms`
- Padrón A13: `https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA13`

**Producción (PROD)**:
- Portal AFIP: `https://auth.afip.gob.ar/contribuyente_/`
- WSAA: `https://wsaa.afip.gov.ar/ws/services/LoginCms`
- Padrón A13: `https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13`

---

## Ambientes Disponibles

AFIP ofrece dos ambientes para trabajar con sus servicios:

### 1. Homologación (TEST)
- **Propósito**: Desarrollo y pruebas
- **Certificados**: Certificados de prueba (auto-firmados o de homologación)
- **Datos**: Datos ficticios o de prueba
- **Restricciones**: Sin límites de consultas, sin costo

### 2. Producción (PROD)
- **Propósito**: Operación real
- **Certificados**: Certificados oficiales de AFIP
- **Datos**: Datos reales de contribuyentes
- **Restricciones**: Sujeto a términos y condiciones de AFIP

**Recomendación**: Comenzar siempre en **Homologación** para validar la integración antes de pasar a producción.

---

## Paso 1: Generar Certificado y Clave Privada

### Opción A: Con OpenSSL (Recomendado)

1. **Generar clave privada RSA de 2048 bits**:

```bash
openssl genrsa -out afip_private.key 2048
```

**Salida esperada**:
```
Generating RSA private key, 2048 bit long modulus
.....+++
.............+++
e is 65537 (0x10001)
```

2. **Generar Certificate Signing Request (CSR)**:

```bash
openssl req -new -key afip_private.key -out afip.csr \
  -subj "/C=AR/O=PIPO-DEV/CN=20351798239/serialNumber=20351798239 20351798239"
```

**Reemplazar**:
- `MI_ORGANIZACION`: Nombre de tu empresa u organización
- `MI_CUIT`: Tu CUIT (11 dígitos, sin guiones)

**Ejemplo**:
```bash
openssl req -new -key afip_private.key -out afip.csr \
  -subj "/C=AR/O=Acme Corp/CN=20123456789/serialNumber=CUIT 20123456789"
```

3. **Verificar el CSR generado**:

```bash
openssl req -text -noout -verify -in afip.csr
```

### Opción B: Con Clave Privada Cifrada (Más Seguro)

Si deseas proteger la clave privada con contraseña:

```bash
# Generar clave privada cifrada con AES-256
openssl genrsa -aes256 -out afip_private.key 2048

# Te pedirá una contraseña (guardarla de forma segura)
Enter pass phrase for afip_private.key: ********
Verifying - Enter pass phrase for afip_private.key: ********
```

**Configuración en el microservicio**:
```bash
# En .env
AFIP_KEY_PASSPHRASE=tu_contraseña_aqui
```

---

## Paso 2: Crear CSR (Certificate Signing Request)

El CSR ya fue generado en el paso anterior. Ahora debes visualizarlo:

```bash
cat afip.csr
```

**Salida esperada**:
```
-----BEGIN CERTIFICATE REQUEST-----
MIIC5jCCAc4CAQAwgZsxCzAJBgNVBAYTAkFSMRQwEgYDVQQKDAtBY21lIENvcnAx
...
(muchas líneas de texto en Base64)
...
-----END CERTIFICATE REQUEST-----
```

**Copiar todo el contenido del CSR** (incluyendo las líneas BEGIN/END).

---

## Paso 3: Subir CSR a AFIP

### Para Homologación (TEST)

1. **Acceder al Portal de Homologación**:
   - URL: `https://auth.afip.gob.ar/contribuyente_/homologacion.xhtml`
   - Ingresar con CUIT y Clave Fiscal

2. **Navegar a "Administrador de Relaciones de Clave Fiscal"**:
   - Menú: **Administración** → **Relaciones de Clave Fiscal**

3. **Crear Nueva Relación**:
   - Click en **"Nueva Relación"** o **"Adherir Servicio"**
   - Buscar servicio: **"ws_sr_padron_a13"** o **"Padrón A13"**
   - Seleccionar el servicio

4. **Cargar Certificado Digital**:
   - Seleccionar: **"Generar Certificado Digital"** o **"Subir CSR"**
   - Pegar el contenido del archivo `afip.csr`
   - Click en **"Generar Certificado"**

5. **Descargar Certificado**:
   - AFIP mostrará el certificado generado
   - Click en **"Descargar Certificado"**
   - Guardar como `afip_cert.crt`

### Para Producción (PROD)

El proceso es similar, pero con mayor validación:

1. **Acceder al Portal de Producción**:
   - URL: `https://auth.afip.gob.ar/contribuyente_/`
   - Ingresar con CUIT y Clave Fiscal

2. **Validación de Identidad**:
   - AFIP puede solicitar validación adicional (DNI, documentos, etc.)
   - Seguir las instrucciones del portal

3. **Proceso de Asociación**:
   - Similar al ambiente de homologación
   - Mayor tiempo de aprobación (puede demorar 24-48 hs)

---

## Paso 4: Asociar Certificado al Servicio ws_sr_padron_a13

### Verificar Servicios Habilitados

1. **Ingresar a "Administrador de Relaciones"**:
   - Verificar que aparezca **"ws_sr_padron_a13"** en la lista de servicios

2. **Asociar Certificado**:
   - Si el servicio no está asociado, hacer click en **"Asociar Certificado"**
   - Seleccionar el certificado recién generado
   - Confirmar la asociación

3. **Verificar Estado**:
   - El servicio debe aparecer como **"Activo"** o **"Vigente"**
   - Anotar la fecha de vencimiento del certificado

### Servicios AFIP Relacionados

Además de `ws_sr_padron_a13`, podrías necesitar habilitar:

- `ws_sr_padron_a4`: Padrón A4 (simplificado)
- `ws_sr_padron_a5`: Padrón A5 (datos adicionales)
- `ws_sr_padron_a13`: Padrón A13 (constancia de inscripción)

Para este microservicio, **solo necesitas ws_sr_padron_a13**.

---

## Paso 5: Descargar Certificado de AFIP

Si no descargaste el certificado en el Paso 3:

1. **Acceder a "Administrador de Certificados Digitales"**:
   - Menú: **Administración** → **Certificados Digitales**

2. **Buscar Certificado**:
   - Filtrar por servicio: **"ws_sr_padron_a13"**
   - Verificar estado: **"Vigente"**

3. **Descargar Certificado**:
   - Click en el certificado
   - Botón **"Descargar Certificado"**
   - Guardar como `afip_cert.crt`

### Verificar el Certificado Descargado

```bash
# Verificar formato del certificado
openssl x509 -in afip_cert.crt -text -noout

# Verificar que el certificado corresponde a la clave privada
openssl x509 -noout -modulus -in afip_cert.crt | openssl md5
openssl rsa -noout -modulus -in afip_private.key | openssl md5

# Los hashes MD5 deben coincidir
```

---

## Paso 6: Configurar el Microservicio

### Estructura de Archivos

```
cuit-validator/
├── certs/
│   ├── afip_cert.crt       ← Certificado descargado de AFIP
│   └── afip_private.key    ← Clave privada generada en Paso 1
├── .env                     ← Configuración
└── ...
```

### Configuración del Archivo .env

1. **Copiar el template**:

```bash
cp .env.example .env
```

2. **Editar `.env`**:

```bash
# Ambiente: TEST o PROD
ENVIRONMENT=TEST

# Rutas a los certificados
AFIP_CERT_PATH=./certs/afip_cert.crt
AFIP_KEY_PATH=./certs/afip_private.key

# Contraseña de la clave privada (solo si está cifrada)
AFIP_KEY_PASSPHRASE=

# Logging
LOG_LEVEL=INFO
```

### Permisos de Archivos (Importante para Seguridad)

```bash
# Proteger la clave privada
chmod 600 certs/afip_private.key

# Certificado puede ser lectura pública
chmod 644 certs/afip_cert.crt

# Verificar permisos
ls -la certs/
```

**Salida esperada**:
```
-rw-r--r-- 1 user group 1234 Mar 14 10:00 afip_cert.crt
-rw------- 1 user group 1679 Mar 14 10:00 afip_private.key
```

---

## Verificación y Testing

### 1. Verificar Configuración del Microservicio

```bash
# Ejecutar el microservicio
python -m app.main

# O con Docker
docker-compose up
```

**Salida esperada**:
```
INFO:     Starting CUIT Validator microservice...
INFO:     Environment: TEST
INFO:     WSAA URL: https://wsaahomo.afip.gov.ar/ws/services/LoginCms
INFO:     Padrón URL: https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA13
INFO:     AFIP certificates validated successfully
INFO:     CUIT Validator microservice started successfully
```

### 2. Test de Health Check

```bash
curl http://localhost:8000/api/v1/health
```

**Respuesta esperada**:
```json
{
  "status": "OK",
  "environment": "TEST",
  "timestamp": "2024-03-14T10:30:00.000000"
}
```

### 3. Test de Autenticación WSAA (Interno)

El microservicio automáticamente intentará obtener un token WSAA al arrancar. Verifica los logs:

```
INFO:     Requesting new WSAA token for service: ws_sr_padron_a13
DEBUG:    Generated LoginTicketRequest: <loginTicketRequest version="1.0">...
DEBUG:    CMS signature generated: 2048 bytes (Base64)
DEBUG:    SOAP envelope constructed
DEBUG:    WSAA response status: 200
INFO:     Token obtained successfully. Expires at: 2024-03-14T22:30:00
```

### 4. Test de Consulta de CUIT

**En Homologación** (CUITs de prueba):

```bash
# CUIT de prueba (reemplazar con un CUIT válido de homologación)
curl http://localhost:8000/api/v1/cuit/20123456789
```

**En Producción** (CUITs reales):

```bash
# Consultar un CUIT real (verificar que esté habilitado)
curl http://localhost:8000/api/v1/cuit/20123456789
```

**Respuesta esperada (200 OK)**:
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

### 5. Verificar Cache de Tokens

```bash
curl http://localhost:8000/api/v1/cache/stats
```

**Respuesta esperada**:
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

---

## Troubleshooting

### Error: "Certificate file not found"

**Problema**: Los archivos de certificado no están en la ruta correcta.

**Solución**:
```bash
# Verificar que los archivos existan
ls -la certs/

# Verificar rutas en .env
cat .env | grep AFIP_CERT
cat .env | grep AFIP_KEY

# Copiar archivos si es necesario
cp /ruta/origen/afip_cert.crt certs/
cp /ruta/origen/afip_private.key certs/
```

### Error: "Failed to load private key"

**Problema**: La clave privada está cifrada pero no se proporcionó la contraseña.

**Solución**:
```bash
# Agregar contraseña en .env
echo "AFIP_KEY_PASSPHRASE=tu_contraseña" >> .env

# O remover el cifrado de la clave (menos seguro)
openssl rsa -in certs/afip_private.key -out certs/afip_private_unencrypted.key
mv certs/afip_private_unencrypted.key certs/afip_private.key
```

### Error: "SOAP Fault: No autorizado" o "Token inválido"

**Problema**: El certificado no está asociado correctamente al servicio `ws_sr_padron_a13`.

**Solución**:
1. Acceder al portal de AFIP
2. Verificar en **"Administrador de Relaciones"** que el servicio esté asociado
3. Re-asociar el certificado si es necesario
4. Esperar 5-10 minutos para que los cambios se propaguen

### Error: "Certificate and private key do not match"

**Problema**: El certificado y la clave privada no corresponden.

**Solución**:
```bash
# Verificar que los hashes coincidan
openssl x509 -noout -modulus -in certs/afip_cert.crt | openssl md5
openssl rsa -noout -modulus -in certs/afip_private.key | openssl md5

# Si no coinciden, regenerar CSR y solicitar nuevo certificado
```

### Error: "Failed to sign data with CMS/PKCS#7"

**Problema**: Error al generar la firma digital CMS.

**Solución**:
1. Verificar que OpenSSL esté instalado correctamente
2. Verificar que la librería `cryptography` de Python esté actualizada:
   ```bash
   pip install --upgrade cryptography pyOpenSSL
   ```
3. Verificar permisos de lectura en los archivos

### Error: "CUIT not found in AFIP"

**Problema**: El CUIT consultado no existe o no está habilitado en AFIP.

**Solución**:
- **En Homologación**: Usar CUITs de prueba válidos
- **En Producción**: Verificar que el CUIT esté registrado en AFIP
- Verificar formato del CUIT (11 dígitos, sin guiones)

### Error: "Timeout connecting to AFIP"

**Problema**: No hay conectividad con los servidores de AFIP.

**Solución**:
1. Verificar conectividad de red:
   ```bash
   ping wsaahomo.afip.gov.ar
   ping awshomo.afip.gov.ar
   ```
2. Verificar que no haya firewall bloqueando el puerto 443 (HTTPS)
3. Verificar configuración de proxy si aplica

---

## Renovación de Certificados

Los certificados AFIP tienen **vencimiento** (típicamente 1 año). Para renovar:

### Opción 1: Generar Nuevo Certificado

1. Generar nuevo CSR (Paso 1-2)
2. Subir a AFIP (Paso 3)
3. Re-asociar al servicio (Paso 4)
4. Descargar nuevo certificado (Paso 5)
5. Actualizar archivos en `certs/`

### Opción 2: Renovar Certificado Existente

1. Acceder al portal de AFIP
2. **Administración** → **Certificados Digitales**
3. Seleccionar certificado a renovar
4. Click en **"Renovar Certificado"**
5. Descargar certificado renovado

**Recomendación**: Renovar **30 días antes** del vencimiento para evitar interrupciones.

---

## Referencias Oficiales

### Documentación AFIP

- **Especificación Técnica WSAA**: [https://www.afip.gob.ar/ws/WSAA/Especificacion_Tecnica_WSAA_1.2.2.pdf](https://www.afip.gob.ar/ws/WSAA/Especificacion_Tecnica_WSAA_1.2.2.pdf)
- **Manual de Desarrollo WSAA**: [https://www.afip.gob.ar/ws/WSAA/WSAAmanualDev.pdf](https://www.afip.gob.ar/ws/WSAA/WSAAmanualDev.pdf)
- **Obtención de Certificados (PROD)**: [https://www.afip.gob.ar/ws/WSAA/wsaa_obtener_certificado_produccion.pdf](https://www.afip.gob.ar/ws/WSAA/wsaa_obtener_certificado_produccion.pdf)
- **Asociación de Certificados (PROD)**: [https://www.afip.gob.ar/ws/WSAA/wsaa_asociar_certificado_a_wsn_produccion.pdf](https://www.afip.gob.ar/ws/WSAA/wsaa_asociar_certificado_a_wsn_produccion.pdf)

### Sitios Útiles

- **Portal AFIP**: [https://www.afip.gob.ar](https://www.afip.gob.ar)
- **Servicios Web AFIP**: [https://www.afip.gob.ar/ws/](https://www.afip.gob.ar/ws/)
- **OpenSSL Documentation**: [https://www.openssl.org/docs/](https://www.openssl.org/docs/)

---

## Checklist Final

Antes de desplegar en producción, verificar:

- [ ] Certificado generado y descargado de AFIP
- [ ] Certificado asociado al servicio `ws_sr_padron_a13`
- [ ] Clave privada con permisos correctos (`600`)
- [ ] Archivo `.env` configurado correctamente
- [ ] Certificados ubicados en `certs/`
- [ ] Health check funcionando (`/api/v1/health`)
- [ ] Autenticación WSAA exitosa (verificar logs)
- [ ] Consulta de CUIT de prueba exitosa
- [ ] Cache de tokens funcionando (`/api/v1/cache/stats`)
- [ ] Fecha de vencimiento del certificado anotada
- [ ] Plan de renovación de certificado definido

---

## Soporte

Para dudas o problemas:

1. **Consultar logs del microservicio**: `docker-compose logs -f`
2. **Revisar documentación oficial de AFIP**: Enlaces arriba
3. **Contactar soporte AFIP**: 0800-999-2347 (Argentina)
4. **Consultar con el equipo de DevOps de BDS**

---

**Última actualización**: Marzo 2024  
**Versión del documento**: 1.0
