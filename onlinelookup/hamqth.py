"""
HamQTH Callsign Lookup
Author: Ben Johnson, AB3NJ

Uses HamQTH's API to retrieve information on callsigns.

Refactored for async by N4OG - 2025
"""

import os
import aiohttp
import asyncio
import xml.etree.ElementTree as ET
from . import olerror, olresult

__all__ = ['AsyncHamQTHLookup']

KEY_FILE = '/app/config/hamqth_key.txt'

class AsyncHamQTHLookup:
    def __init__(self, username, password, key_file=KEY_FILE):
        self.username = username
        self.password = password
        self.key = None
        self.active = False
        self.prefix = "{https://www.hamqth.com}"
        self.key_file = key_file

    async def connect(self):
        """
        Async initialization: load session key from file or get a new one from HamQTH.
        """
        try:
            with open(self.key_file, 'r') as f:
                lines = f.readlines()
                if len(lines) != 1:
                    await self.get_key()
                else:
                    self.key = lines[0].strip()
                    self.active = True
        except FileNotFoundError:
            await self.get_key()

    async def get_key(self):
        """
        Obtain and store a new HamQTH API session key using credentials.
        """
        url = f'https://www.hamqth.com/xml.php?u={self.username}&p={self.password}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise olerror.LookupVerificationError(f'HamQTH: HTTP {resp.status}')
                text = await resp.text()
                root = ET.fromstring(text)
                # Success
                if root[0][0].tag == self.prefix + "session_id":
                    self.active = True
                    self.key = root[0][0].text
                    with open(self.key_file, 'w') as f:
                        f.write(self.key)
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
        async with aiohttp.ClientSession() as session:
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
