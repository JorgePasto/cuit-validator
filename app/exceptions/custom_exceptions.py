"""
Excepciones personalizadas para el microservicio.
"""


class AFIPBaseException(Exception):
    """Excepción base para errores relacionados con AFIP."""
    pass


class AFIPServiceException(AFIPBaseException):
    """Error al comunicarse con servicios de AFIP (WSAA o Padrón)."""
    pass


class CUITNotFoundException(AFIPBaseException):
    """CUIT no encontrado en el Padrón de AFIP."""
    pass


class AuthenticationException(AFIPBaseException):
    """Error de autenticación con WSAA."""
    pass


class SignatureException(AFIPBaseException):
    """Error al generar firma digital CMS/PKCS#7."""
    pass


class XMLParseException(AFIPBaseException):
    """Error al parsear o generar XML."""
    pass


class InvalidCUITException(AFIPBaseException):
    """CUIT con formato inválido."""
    pass


class CertificateException(AFIPBaseException):
    """Error al cargar o validar certificados."""
    pass
