Consideraciones: 
1. Acceso a Proyectos de Referencia: Los proyectos de referencia (people-arca-connector y token-arca-admin) están en Java y fuera de mi directorio accesible. ¿Preferirías:
   - Otorgarme acceso para leer esos directorios? Si, te autorizo a leer los proyectos
   - Copiar archivos/patrones relevantes a este directorio para que los revise? Patrones reelevantes y soluciones de integración con ARCA
   - ¿O procedo con una arquitectura estándar Python/FastAPI basada en los requerimientos? Debes proceeder con una arquitecura estandar Python/FastAPI
2. Certificados/Credenciales AFIP: La autenticación WSAA de AFIP requiere:
   - Un certificado (.crt)
   - Una clave privada (.key)
   - CUIT de la organización
   ¿Ya cuentas con estas credenciales, o debo documentar cómo generarlas? Documenta como generarlas en un archivo AUTH_ARCA.md
3. Configuración de Entornos: Mencionaste entornos TEST y PROD. ¿Debería:
   - Usar el ambiente de homologación (testing) de AFIP inicialmente? SI
   - Configurar ambos entornos desde el inicio? SI
4. Estrategia de Cache de Tokens: Para el cache de tokens con vencimiento, ¿qué enfoque prefieres:
   - Cache en memoria con TTL (simple, pierde cache al reiniciar)
5. Diseño del Endpoint API: Para el endpoint de validación de CUIT, ¿debería:
   - Aceptar solo el número de CUIT y retornar datos de validación? SI
   - Incluir parámetros o filtros adicionales? NO 
   - ¿Qué formato de respuesta prefieres (respuesta completa de AFIP o datos filtrados)? JSON
6. Manejo de Errores: ¿Cómo debería manejar el servicio:
   - CUITs inválidos? SI 
   - Indisponibilidad del servicio AFIP? SI
   - Fallos de autenticación? NO
Déjame saber tus preferencias y crearé un plan de implementación completo.


❓ PREGUNTAS ANTES DE COMENZAR LA IMPLEMENTACIÓN
1. ¿Te parece bien este plan y orden de implementación?
R:  SI esta correcto
2. ¿Quieres que agregue alguna funcionalidad adicional? Por ejemplo:
   - Métricas/monitoring (Prometheus)
   - Rate limiting
   - API Key authentication
 R: Inicialmente no pero prepara una documentación para hacerlo luego
3. ¿Prefieres que use alguna libCrería específica para SOAP? (como zeep) o mantengo la construcción manual con lxml como en los proyectos Java?
R: Si en python hay una libreria que creas conveniente, usemosla.
4. ¿Deseas que el cache sea:
   - En memoria (más simple, recomendado inicial)
   - Redis (más robusto, requiere infraestructura adicional)
R: por el tipo de requerimiento prefiero que sea en memoria.
5. ¿Qué datos específicos del Padrón A13 te interesan en la respuesta? (nombre, domicilio, actividades, impuestos, etc.)
R: Nombres y domicilios