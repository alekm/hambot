"""
Callook Callsign Lookup
Author: Ben Johnson, AB3NJ

Uses Callook's API to retrieve information on callsigns

Refactored for async by N4OG - 2025
"""

import aiohttp
from typing import Optional
from . import olerror, olresult

__all__ = ['AsyncCallookLookup']

def prettify(name: str) -> str:
    names = name.split()
    newname = ''
    for i in names:
        if len(i) > 1:
            newname += i[0] + i[1:].lower()
        else:
            newname += i
        newname += ' '
    return newname.strip()

class AsyncCallookLookup:
    """
    Provides US callsign lookup via callook.info API (async).
    Reuses HTTP session for better performance.
    """
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with granular timeouts."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(
                total=15,      # Total timeout
                connect=5,     # Connection timeout
                sock_read=10   # Socket read timeout
            )
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def lookup(self, call: str):
        """
        Async lookup of a US callsign using callook.info.

        :param call: the callsign to look up
        :returns: LookupResult object with Callook info
        :raises LookupResultError: on errors or if not found
        """
        lr = olresult.LookupResult()
        req = f'https://callook.info/{call}/json'
        try:
            session = await self._get_session()
            async with session.get(req) as resp:
                if resp.status != 200:
                    raise olerror.LookupResultError(f'Callook: HTTP {resp.status}')
                data = await resp.json()
        except Exception as ex:
            raise olerror.LookupResultError(f'Callook network/parse error: {ex}')

        if data.get('status') == 'INVALID':
            raise olerror.LookupResultError('Callook: invalid callsign')

        lr.source = 'Callook'

        # basic info
        lr.callsign = data.get('current', {}).get('callsign', call.upper())
        lr.prevcall = data.get('previous', {}).get('callsign', '')

        lr.name = prettify(data.get('name', ''))
        lr.opclass = prettify(data.get('current', {}).get('operClass', ''))

        # location
        lr.country = 'United States'
        lr.grid = data.get('location', {}).get('gridsquare', '')

        # Defensive address parsing
        address = data.get('address', {}).get('line2', '')
        if ',' in address:
            addrs = address.split(',')
            lr.city = prettify(addrs[0])
            addrs2 = addrs[1].strip().split()
            if len(addrs2) >= 2:
                lr.state = addrs2[0]
                lr.zip = addrs2[1]
            elif len(addrs2) == 1:
                lr.state = addrs2[0]
                lr.zip = ''
            else:
                lr.state = lr.zip = ''
        else:
            lr.city = prettify(address)
            lr.state = lr.zip = ''

        # club info
        lr.club = data.get('type', '') == 'CLUB'
        if lr.club:
            trustee = data.get('trustee', {})
            lr.trusteename = trustee.get('name', '')
            lr.trusteecall = trustee.get('callsign', '')

        # ULS/other info
        other = data.get('otherInfo', {})
        lr.frn = other.get('frn', '')
        lr.uls = other.get('ulsUrl', '')

        lr.raw = data

        return lr
