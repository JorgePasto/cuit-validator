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
from datetime import timezone
import subprocess
import shutil
import os
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
        # Usar attached signature (incluir contenido) ya que AFIP espera el contenido firmado
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
        # Fallback: intentar usar la utilidad openssl en PATH si cryptography no funciona
        openssl_path = shutil.which("openssl")
        if openssl_path:
            # Usar comando: openssl cms -sign -in /dev/stdin -signer cert.pem -inkey key.pem -outform DER -nodetach
            cmd = [openssl_path, "cms", "-sign", "-in", "/dev/stdin", "-signer", cert_path, "-inkey", private_key_path, "-outform", "DER", "-nodetach"]
            if passphrase:
                # openssl puede recibir passphrase vía environment var; evitamos exponerla en logs
                env = {**os.environ, "PASS": passphrase}
            else:
                env = None

            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            out, err = proc.communicate(input=data.encode('utf-8'))
            if proc.returncode != 0:
                raise SignatureException(f"OpenSSL cms failed: {err.decode('utf-8')}")
            return out

        # Si no hay openssl disponible, mantener intento con PyOpenSSL (legacy) pero lanzar excepción clara
        raise SignatureException("Legacy PKCS7 signing not available: requires openssl in PATH")

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
