"""
HamQTH Callsign Lookup
Author: Ben Johnson, AB3NJ

Uses HamQTH's API to retrieve information on callsigns.

Refactored for async by N4OG - 2025
Security: Session key encryption added 2026-01-03
"""

import os
import aiohttp
import asyncio
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from defusedxml import ElementTree as ET
from . import olerror, olresult

__all__ = ['AsyncHamQTHLookup']

logger = logging.getLogger(__name__)

KEY_FILE = '/app/config/hamqth_key.txt'
# Salt file for encryption key derivation
SALT_FILE = '/app/config/hamqth_salt.bin'

class AsyncHamQTHLookup:
    def __init__(self, username, password, key_file=KEY_FILE):
        self.username = username
        self.password = password
        self.key = None
        self.active = False
        self.prefix = "{https://www.hamqth.com}"
        self.key_file = key_file
        self.salt_file = SALT_FILE
        self._cipher = None

    def _get_encryption_key(self) -> bytes:
        """
        Derive encryption key from username/password using PBKDF2.
        Uses a salt file to ensure consistent encryption/decryption.
        """
        # Get or create salt
        if os.path.exists(self.salt_file):
            with open(self.salt_file, 'rb') as f:
                salt = f.read()
        else:
            # Generate new salt (16 bytes)
            salt = os.urandom(16)
            os.makedirs(os.path.dirname(self.salt_file), exist_ok=True)
            with open(self.salt_file, 'wb') as f:
                f.write(salt)
            logger.info("Generated new encryption salt")

        # Derive key from password using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password.encode()))
        return key

    def _get_cipher(self) -> Fernet:
        """Get or create Fernet cipher for encryption/decryption."""
        if self._cipher is None:
            self._cipher = Fernet(self._get_encryption_key())
        return self._cipher

    def _encrypt_key(self, session_key: str) -> bytes:
        """Encrypt session key."""
        cipher = self._get_cipher()
        return cipher.encrypt(session_key.encode())

    def _decrypt_key(self, encrypted_data: bytes) -> str:
        """Decrypt session key."""
        cipher = self._get_cipher()
        return cipher.decrypt(encrypted_data).decode()

    async def connect(self):
        """
        Async initialization: load encrypted session key from file or get a new one from HamQTH.
        """
        try:
            with open(self.key_file, 'rb') as f:
                encrypted_data = f.read()
                if not encrypted_data:
                    logger.info("Empty key file, fetching new session key")
                    await self.get_key()
                else:
                    try:
                        # Try to decrypt the key
                        self.key = self._decrypt_key(encrypted_data)
                        self.active = True
                        logger.info("Loaded encrypted session key from file")
                    except Exception as e:
                        logger.warning(f"Failed to decrypt session key: {e}. Fetching new key...")
                        await self.get_key()
        except FileNotFoundError:
            logger.info("Key file not found, fetching new session key")
            await self.get_key()

    async def get_key(self):
        """
        Obtain and store a new HamQTH API session key using credentials.
        Session key is encrypted before storage.
        """
        url = f'https://www.hamqth.com/xml.php?u={self.username}&p={self.password}'
        timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise olerror.LookupVerificationError(f'HamQTH: HTTP {resp.status}')
                text = await resp.text()
                root = ET.fromstring(text)
                # Success
                if root[0][0].tag == self.prefix + "session_id":
                    self.active = True
                    self.key = root[0][0].text

                    # Encrypt and store the session key
                    encrypted_key = self._encrypt_key(self.key)
                    os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
                    with open(self.key_file, 'wb') as f:
                        f.write(encrypted_key)
                    logger.info("Stored encrypted session key")
                # Bad credentials
                elif root[0][0].tag == self.prefix + "error":
                    raise olerror.LookupVerificationError('HamQTH: bad credentials')
                # Unknown error
                else:
                    raise olerror.LookupVerificationError('HamQTH: unexpected response')

    async def lookup(self, call, retry=True):
        """
        Lookup a callsign asynchronously on HamQTH.
        Returns a LookupResult object or raises error on failure.
        """
        if not self.active:
            raise olerror.LookupActiveError('HamQTH')

        url = f'https://www.hamqth.com/xml.php?id={self.key}&callsign={call}&prg=hambot'
        timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise olerror.LookupResultError(f'HamQTH: HTTP {resp.status}')
                text = await resp.text()
                root = ET.fromstring(text)

                # Session or lookup error
                if root[0].tag == self.prefix + "session":
                    errmess = root[0][0].text
                    if errmess == 'Session does not exist or expired':
                        await self.get_key()
                        if retry:
                            return await self.lookup(call, retry=False)
                        else:
                            raise olerror.LookupVerificationError('HamQTH: session expired')
                    elif errmess == 'Callsign not found':
                        raise olerror.LookupResultError('HamQTH: callsign not found')
                    else:
                        raise olerror.LookupResultError(f'HamQTH: session error: {errmess}')

                # Successful lookup
                elif root[0].tag == self.prefix + "search":
                    lr = olresult.LookupResult()
                    retdict = {}
                    lr.source = 'HamQTH'
                    for t in root[0]:
                        key = t.tag[len(self.prefix):] if t.tag.startswith(self.prefix) else t.tag
                        value = t.text
                        # Fill LookupResult as in synchronous version
                        if key == 'callsign' and value: lr.callsign = value.upper()
                        elif key == 'adr_name' and value: lr.name = value
                        elif key == 'adr_street1' and value: lr.street1 = value
                        elif key == 'adr_street2' and value: lr.street2 = value
                        elif key == 'adr_city' and value: lr.city = value
                        elif key == 'us_state' and value: lr.state = value
                        elif key == 'adr_zip' and value: lr.zip = value
                        elif key == 'country' and value: lr.country = value
                        elif key == 'itu' and value: lr.itu = value
                        elif key == 'cq' and value: lr.cq = value
                        elif key == 'grid' and value: lr.grid = value
                        # Store all fields for raw data
                        if key and value:
                            retdict[key] = value
                    lr.raw = retdict
                    return lr

                # Unexpected response
                else:
                    raise olerror.LookupResultError('HamQTH: malformed XML response')
