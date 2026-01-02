"""
PSKReporter API provider for digital mode spots.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
import aiohttp
from providers.base import BaseSpotProvider, Spot

logger = logging.getLogger(__name__)

PSKREPORTER_API_URL = "https://api.pskreporter.info/pskreporter/query"


class PSKReporterProvider(BaseSpotProvider):
    """Provider for PSKReporter API (digital modes only)."""
    
    def __init__(self):
        super().__init__("pskreporter")
        self.session: Optional[aiohttp.ClientSession] = None
        self.supported_modes = [
            'FT8', 'FT4', 'PSK31', 'PSK63', 'PSK125', 'CW', 'RTTY',
            'JT65', 'JT9', 'WSPR', 'APRS', 'FSK441', 'JTMS', 'ISCAT',
            'MSK144', 'QRA64', 'T10', 'WSPR-15'
        ]
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def get_supported_modes(self) -> List[str]:
        """Get list of supported digital modes."""
        return self.supported_modes.copy()
    
    async def test_connection(self) -> bool:
        """Test connection to PSKReporter API."""
        try:
            session = await self._get_session()
            # Try a simple query with very recent time window
            params = {
                'mode': 'FT8',
                'timerange': '300'  # Last 5 minutes
            }
            async with session.get(PSKREPORTER_API_URL, params=params) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"PSKReporter connection test failed: {e}")
            return False
    
    async def fetch_recent_spots(self, since: Optional[datetime] = None) -> List[Spot]:
        """
        Fetch recent spots from PSKReporter.
        
        Args:
            since: Only fetch spots after this timestamp. If None, fetch last 10 minutes.
            
        Returns:
            List of Spot objects
        """
        if since is None:
            since = datetime.utcnow() - timedelta(minutes=10)
        
        # Calculate timerange in seconds
        now = datetime.utcnow()
        timerange_seconds = int((now - since).total_seconds())
        
        # PSKReporter API parameters
        params = {
            'timerange': str(timerange_seconds),
            'limit': '1000'  # Maximum spots per query
        }
        
        spots = []
        session = await self._get_session()
        
        try:
            async with session.get(PSKREPORTER_API_URL, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"PSKReporter API returned status {resp.status}")
                    return spots
                
                data = await resp.json()
                
                # PSKReporter returns data in a specific format
                # The structure may vary, so we need to handle it carefully
                if 'r' in data:  # 'r' typically contains receiver reports
                    for report in data['r']:
                        try:
                            spot = self._parse_report(report, data.get('s', []))
                            if spot and spot.timestamp >= since:
                                spots.append(spot)
                        except Exception as e:
                            logger.warning(f"Failed to parse PSKReporter report: {e}")
                            continue
                
        except aiohttp.ClientError as e:
            logger.error(f"PSKReporter API request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching PSKReporter spots: {e}")
        
        logger.info(f"Fetched {len(spots)} spots from PSKReporter")
        return spots
    
    def _parse_report(self, report: dict, senders: List[dict]) -> Optional[Spot]:
        """
        Parse a PSKReporter report into a Spot object.
        
        Args:
            report: Receiver report dictionary
            senders: List of sender information dictionaries
            
        Returns:
            Spot object or None if parsing fails
        """
        try:
            # PSKReporter report structure:
            # - 'rCallsign': receiver callsign
            # - 'sCallsign': sender callsign (index into senders array)
            # - 'mode': mode name
            # - 'frequency': frequency in Hz
            # - 'time': timestamp (Unix timestamp)
            
            sender_idx = report.get('sCallsign')
            if sender_idx is not None and 0 <= sender_idx < len(senders):
                callsign = senders[sender_idx].get('callsign', '')
            else:
                callsign = report.get('sCallsign', '')  # Sometimes direct
            
            if not callsign:
                return None
            
            mode = report.get('mode', '').upper()
            if not mode:
                return None
            
            frequency = report.get('frequency')
            if frequency:
                frequency = float(frequency)
            
            # Timestamp - PSKReporter uses Unix timestamp
            time_val = report.get('time')
            if time_val:
                timestamp = datetime.utcfromtimestamp(time_val)
            else:
                timestamp = datetime.utcnow()
            
            # Create unique spot ID
            spot_id = f"{callsign}_{mode}_{frequency}_{int(timestamp.timestamp())}"
            
            # Get spotter (receiver)
            spotter = report.get('rCallsign', '')
            
            return Spot(
                callsign=callsign.upper(),
                mode=mode,
                frequency=frequency,
                timestamp=timestamp,
                spot_id=spot_id,
                source=self.source_name,
                spotter=spotter.upper() if spotter else None
            )
            
        except Exception as e:
            logger.warning(f"Error parsing PSKReporter report: {e}")
            return None
