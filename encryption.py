import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
import base64

def generate_symmetric_key() -> bytes:
    """Generates a Fernet symmetric key."""
    return Fernet.generate_key()

def encrypt_symmetric_key(symmetric_key: bytes, public_key_pem: str) -> str:
    """Encrypts the symmetric key using the user's RSA public key."""
    public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
    encrypted_key = public_key.encrypt(
        symmetric_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(encrypted_key).decode('utf-8')

def decrypt_symmetric_key(encrypted_symmetric_key_b64: str, private_key_pem: str) -> bytes:
    """Decrypts the symmetric key using the user's RSA private key."""
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode('utf-8'),
        password=None,
    )
    encrypted_key = base64.b64decode(encrypted_symmetric_key_b64)
    symmetric_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return symmetric_key

def encrypt_file(file_data: bytes, symmetric_key: bytes) -> bytes:
    """Encrypts file data using the symmetric key."""
    f = Fernet(symmetric_key)
    return f.encrypt(file_data)

def decrypt_file(encrypted_file_data: bytes, symmetric_key: bytes) -> bytes:
    """Decrypts file data using the symmetric key."""
    f = Fernet(symmetric_key)
    return f.decrypt(encrypted_file_data)
