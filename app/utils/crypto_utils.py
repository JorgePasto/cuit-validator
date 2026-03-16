"""
Utilidades criptográficas para firmar y validar mensajes AFIP.

Este módulo maneja:
- Carga de certificados X.509 (.crt)
- Carga de claves privadas (.key)
- Firma CMS/PKCS#7 (equivalente a BouncyCastle en Java)
- Codificación Base64
"""

import base64
from pathlib import Path
from typing import Optional

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from OpenSSL import crypto

from app.exceptions.custom_exceptions import CertificateException, SignatureException


def load_certificate(cert_path: str) -> x509.Certificate:
    """
    Carga un certificado X.509 desde archivo PEM.

    Args:
        cert_path: Ruta al archivo .crt (formato PEM)

    Returns:
        Objeto Certificate de cryptography

    Raises:
        CertificateException: Si el archivo no existe o no es válido
    """
    try:
        cert_file = Path(cert_path)
        if not cert_file.exists():
            raise CertificateException(
                f"Certificate file not found: {cert_path}",
                details={"path": cert_path}
            )

        with open(cert_file, "rb") as f:
            cert_data = f.read()

        certificate = x509.load_pem_x509_certificate(cert_data, default_backend())
        return certificate

    except CertificateException:
        raise
    except Exception as e:
        raise CertificateException(
            f"Failed to load certificate: {str(e)}",
            details={"path": cert_path, "error": str(e)}
        )


def load_private_key(key_path: str, passphrase: Optional[str] = None):
    """
    Carga una clave privada desde archivo PEM.

    Args:
        key_path: Ruta al archivo .key (formato PEM)
        passphrase: Contraseña opcional para claves cifradas

    Returns:
        Objeto PrivateKey de cryptography

    Raises:
        CertificateException: Si el archivo no existe o no es válido
    """
    try:
        key_file = Path(key_path)
        if not key_file.exists():
            raise CertificateException(
                f"Private key file not found: {key_path}",
                details={"path": key_path}
            )

        with open(key_file, "rb") as f:
            key_data = f.read()

        password = passphrase.encode() if passphrase else None

        private_key = serialization.load_pem_private_key(
            key_data,
            password=password,
            backend=default_backend()
        )

        return private_key

    except CertificateException:
        raise
    except Exception as e:
        raise CertificateException(
            f"Failed to load private key: {str(e)}",
            details={"path": key_path, "error": str(e)}
        )


def sign_cms_pkcs7(data: str, private_key, certificate: x509.Certificate) -> bytes:
    """
    Firma datos usando CMS/PKCS#7 (equivalente a CMSSignedData de BouncyCastle).

    Este método genera una firma digital CMS que cumple con los requisitos de AFIP:
    - Algoritmo: SHA256withRSA
    - Formato: PKCS#7 / CMS
    - Sin timestamp (detached signature)

    Args:
        data: Datos a firmar (XML LoginTicketRequest como string)
        private_key: Clave privada RSA
        certificate: Certificado X.509 del firmante

    Returns:
        Firma CMS en formato DER (bytes)

    Raises:
        SignatureException: Si la firma falla
    """
    try:
        # Convertir datos a bytes
        data_bytes = data.encode('utf-8')

        # Crear firma CMS usando cryptography (desde v37+)
        # Opciones de firma:
        # - Text=False: datos binarios, no texto
        # - Detached=False: incluir contenido en la firma (lo que requiere AFIP)
        options = [pkcs7.PKCS7Options.Binary]

        # Crear firma PKCS7
        builder = (
            pkcs7.PKCS7SignatureBuilder()
            .set_data(data_bytes)
            .add_signer(certificate, private_key, hashes.SHA256())
        )

        # Generar firma en formato DER
        cms_signature = builder.sign(
            serialization.Encoding.DER,
            options
        )

        return cms_signature

    except Exception as e:
        raise SignatureException(
            f"Failed to sign data with CMS/PKCS#7: {str(e)}",
            details={"error": str(e), "data_length": len(data)}
        )


def sign_cms_pkcs7_legacy(data: str, private_key_path: str, cert_path: str, passphrase: Optional[str] = None) -> bytes:
    """
    Firma datos usando PyOpenSSL (método alternativo/legacy).

    Este método usa PyOpenSSL para compatibilidad con sistemas que no soportan
    cryptography >= 37. Genera firma PKCS#7 compatible con AFIP.

    Args:
        data: Datos a firmar (XML como string)
        private_key_path: Ruta a la clave privada
        cert_path: Ruta al certificado
        passphrase: Contraseña opcional

    Returns:
        Firma PKCS#7 en formato DER (bytes)

    Raises:
        SignatureException: Si la firma falla
    """
    try:
        # Cargar certificado con PyOpenSSL
        with open(cert_path, "rb") as f:
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())

        # Cargar clave privada con PyOpenSSL
        with open(private_key_path, "rb") as f:
            key_data = f.read()

        if passphrase:
            pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key_data, passphrase.encode())
        else:
            pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key_data)

        # Crear firma PKCS7
        # PKCS7_BINARY: no realizar conversión de texto
        # PKCS7_DETACHED: firma independiente del contenido (no usado aquí)
        flags = crypto.PKCS7_BINARY

        data_bytes = data.encode('utf-8')

        # Firmar datos
        pkcs7_sig = crypto.sign(pkey, data_bytes, "sha256")

        # Crear estructura PKCS7 completa
        # Nota: PyOpenSSL tiene limitaciones, usamos crypto.SMIME para crear PKCS7
        bio_in = crypto._new_mem_buf(data_bytes)
        pkcs7 = crypto._lib.PKCS7_sign(
            cert._x509,
            pkey._pkey,
            crypto._ffi.NULL,
            bio_in,
            flags
        )

        if pkcs7 == crypto._ffi.NULL:
            raise SignatureException("Failed to create PKCS7 signature")

        # Convertir a DER
        bio_out = crypto._new_mem_buf()
        crypto._lib.i2d_PKCS7_bio(bio_out, pkcs7)
        pkcs7_der = crypto._bio_to_string(bio_out)

        return pkcs7_der

    except Exception as e:
        raise SignatureException(
            f"Failed to sign data with PyOpenSSL: {str(e)}",
            details={"error": str(e)}
        )


def encode_base64(data: bytes) -> str:
    """
    Codifica bytes a Base64 string (sin saltos de línea).

    Args:
        data: Bytes a codificar

    Returns:
        String Base64
    """
    return base64.b64encode(data).decode('utf-8')


def decode_base64(data: str) -> bytes:
    """
    Decodifica Base64 string a bytes.

    Args:
        data: String Base64

    Returns:
        Bytes decodificados
    """
    return base64.b64decode(data)


# Función de conveniencia para el flujo completo
def sign_and_encode(xml_data: str, cert_path: str, key_path: str, passphrase: Optional[str] = None) -> str:
    """
    Firma XML y devuelve la firma en Base64 (flujo completo para WSAA).

    Args:
        xml_data: XML LoginTicketRequest como string
        cert_path: Ruta al certificado .crt
        key_path: Ruta a la clave privada .key
        passphrase: Contraseña opcional para la clave

    Returns:
        Firma CMS en Base64 (listo para enviar a AFIP)

    Raises:
        CertificateException: Error cargando certificados
        SignatureException: Error firmando datos
    """
    # Cargar certificado y clave
    certificate = load_certificate(cert_path)
    private_key = load_private_key(key_path, passphrase)

    # Firmar con CMS/PKCS#7
    cms_signature = sign_cms_pkcs7(xml_data, private_key, certificate)

    # Codificar en Base64
    signature_b64 = encode_base64(cms_signature)

    return signature_b64
