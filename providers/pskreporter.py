"""
PSKReporter API provider for digital mode spots.
"""
import logging
from defusedxml import ElementTree as ET
from xml.etree.ElementTree import Element
from datetime import datetime, timedelta
from typing import List, Optional
import aiohttp
from providers.base import BaseSpotProvider, Spot

logger = logging.getLogger(__name__)

PSKREPORTER_API_URL = "https://retrieve.pskreporter.info/query"


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
        """Get or create HTTP session with granular timeouts."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(
                    total=15,      # Total timeout (reduced from 30)
                    connect=5,     # Connection timeout
                    sock_read=10   # Socket read timeout
                )
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
                    if resp.status == 503:
                        logger.warning(f"PSKReporter API temporarily unavailable (503) - will retry on next cycle")
                    else:
                        logger.error(f"PSKReporter API returned status {resp.status}")
                    return spots
                
                # PSKReporter returns XML, not JSON
                xml_text = await resp.text()
                
                try:
                    root = ET.fromstring(xml_text)
                    # Find all receptionReport elements
                    for report_elem in root.findall('.//receptionReport'):
                        try:
                            spot = self._parse_xml_report(report_elem)
                            if spot and spot.timestamp >= since:
                                spots.append(spot)
                        except Exception as e:
                            logger.warning(f"Failed to parse PSKReporter report: {e}")
                            continue
                except ET.ParseError as e:
                    logger.error(f"Failed to parse PSKReporter XML: {e}")
                    return spots
                
        except aiohttp.ClientError as e:
            logger.error(f"PSKReporter API request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching PSKReporter spots: {e}")
        
        logger.info(f"Fetched {len(spots)} spots from PSKReporter")
        return spots
    
    def _parse_xml_report(self, report_elem: Element) -> Optional[Spot]:
        """
        Parse a PSKReporter XML receptionReport element into a Spot object.
        
        Args:
            report_elem: XML Element for a receptionReport
            
        Returns:
            Spot object or None if parsing fails
        """
        try:
            # PSKReporter XML structure:
            # <receptionReport 
            #   senderCallsign="N9SOR"
            #   receiverCallsign="KC8PYO"
            #   frequency="3574351"
            #   mode="FT8"
            #   flowStartSeconds="1767399576"
            #   ... />
            
            callsign = report_elem.get('senderCallsign', '').strip()
            if not callsign:
                return None
            
            mode = report_elem.get('mode', '').upper().strip()
            if not mode:
                return None
            
            # Frequency in Hz
            frequency_str = report_elem.get('frequency', '')
            frequency = None
            if frequency_str:
                try:
                    frequency = float(frequency_str)
                except ValueError:
                    pass
            
            # Timestamp - flowStartSeconds is Unix timestamp
            flow_start = report_elem.get('flowStartSeconds', '')
            if flow_start:
                try:
                    timestamp = datetime.utcfromtimestamp(int(flow_start))
                except (ValueError, OSError):
                    timestamp = datetime.utcnow()
            else:
                timestamp = datetime.utcnow()
            
            # Get spotter (receiver)
            spotter = report_elem.get('receiverCallsign', '').strip()
            
            # Create unique spot ID
            spot_id = f"{callsign}_{mode}_{frequency}_{int(timestamp.timestamp())}"
            
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
            logger.warning(f"Error parsing PSKReporter XML report: {e}")
            return None
