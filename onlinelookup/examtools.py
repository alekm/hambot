"""
ExamTools US Callsign Lookup (async)
Author: [YourNameHere]

Uses exam.tools API to retrieve information on US callsigns.
"""

import aiohttp
from . import olerror, olresult

__all__ = ['AsyncExamToolsLookup']

class AsyncExamToolsLookup:
    """
    Looks up US callsign info using the exam.tools API asynchronously.
    """
    async def lookup(self, call):
        """
        Async lookup for a US callsign using exam.tools.

        :param call: the callsign to look up
        :returns: LookupResult object populated with info from exam.tools
        :raises LookupResultError: if there's no result or a network/parse issue
        """
        lr = olresult.LookupResult()
        url = f'https://exam.tools/api/uls/individual/{call}'

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise olerror.LookupResultError(f'ExamTools: HTTP {resp.status}')
                    data = await resp.json()
        except Exception as ex:
            raise olerror.LookupResultError(f'ExamTools network/parse error: {ex}')

        if data.get('type') == 'NotFound':
            raise olerror.LookupResultError('ExamTools: callsign not found')

        # Source marker
        lr.source = 'exam.tools'

        # Core info
        lr.callsign = data.get('callsign', call.upper())
        first_name = data.get('first_name', '')
        middle_initial = data.get('middle_initial', '')
        last_name = data.get('last_name', '')

        # Name formatting
        name = first_name
        if middle_initial:
            name += f' {middle_initial}'
        if last_name:
            name += f' {last_name}'
        lr.name = name.strip()

        lr.opclass = data.get('license_class', '')

        # Location
        lr.country = 'United States'
        lr.city = data.get('city', '')
        lr.state = data.get('state', '')
        lr.zip = data.get('zip', '')

        # Club info—exam.tools currently doesn't support this
        # lr.club = False

        # Additional ULS info
        lr.frn = data.get('frn', '')

        # Store all raw data for future use
        lr.raw = data

        return lr
