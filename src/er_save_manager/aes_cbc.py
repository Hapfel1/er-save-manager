"""
AES-CBC without padding for the BND4 save containers (DS2, DS3, DSR, NR, AC6).

Inputs must be a multiple of 16 bytes; padding is each container's own
format and stays with its caller.
"""

from Crypto.Cipher import AES


def decrypt(key: bytes, iv: bytes, data: bytes) -> bytes:
    return AES.new(key, AES.MODE_CBC, iv).decrypt(data)


def encrypt(key: bytes, iv: bytes, data: bytes) -> bytes:
    return AES.new(key, AES.MODE_CBC, iv).encrypt(data)
