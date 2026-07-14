"""OS-bound encryption for local Paper Flow secrets."""

from __future__ import annotations

import base64
import ctypes
import os
from pathlib import Path


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> tuple[_DataBlob, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data)
    value = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    return value, buffer


class SecretProtector:
    """Use Windows DPAPI or a per-installation Fernet key on other systems."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def protect(self, value: str) -> str:
        raw = str(value).encode("utf-8")
        if os.name == "nt":
            incoming, incoming_buffer = _blob(raw)
            entropy, entropy_buffer = _blob(b"PaperFlow/local-secret/v1")
            outgoing = _DataBlob()
            if not ctypes.windll.crypt32.CryptProtectData(
                ctypes.byref(incoming), "Paper Flow secret", ctypes.byref(entropy),
                None, None, 0, ctypes.byref(outgoing),
            ):
                raise ctypes.WinError()
            try:
                encrypted = ctypes.string_at(outgoing.pbData, outgoing.cbData)
            finally:
                ctypes.windll.kernel32.LocalFree(outgoing.pbData)
            # Keep buffers alive until CryptProtectData has returned.
            _ = incoming_buffer, entropy_buffer
            return "dpapi:" + base64.urlsafe_b64encode(encrypted).decode("ascii")
        from cryptography.fernet import Fernet

        key_path = self.data_dir / ".secret.key"
        if key_path.exists():
            key = key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            key_path.write_bytes(key)
            try:
                key_path.chmod(0o600)
            except OSError:
                pass
        return "fernet:" + Fernet(key).encrypt(raw).decode("ascii")

    def unprotect(self, value: str) -> str:
        encoded = str(value)
        if encoded.startswith("dpapi:"):
            encrypted = base64.urlsafe_b64decode(encoded.removeprefix("dpapi:"))
            incoming, incoming_buffer = _blob(encrypted)
            entropy, entropy_buffer = _blob(b"PaperFlow/local-secret/v1")
            outgoing = _DataBlob()
            if not ctypes.windll.crypt32.CryptUnprotectData(
                ctypes.byref(incoming), None, ctypes.byref(entropy),
                None, None, 0, ctypes.byref(outgoing),
            ):
                raise ctypes.WinError()
            try:
                raw = ctypes.string_at(outgoing.pbData, outgoing.cbData)
            finally:
                ctypes.windll.kernel32.LocalFree(outgoing.pbData)
            _ = incoming_buffer, entropy_buffer
            return raw.decode("utf-8")
        if encoded.startswith("fernet:"):
            from cryptography.fernet import Fernet

            key = (self.data_dir / ".secret.key").read_bytes()
            return Fernet(key).decrypt(encoded.removeprefix("fernet:").encode("ascii")).decode("utf-8")
        raise ValueError("Unsupported local secret format")
