"""
DX Cluster provider for amateur radio DX spots via telnet.
"""
import logging
import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Optional, Deque
from collections import deque
from providers.base import BaseSpotProvider, Spot

logger = logging.getLogger(__name__)

# DX Cluster spot format: DX de CALLSIGN: FREQ CALLSIGN [MODE] [COMMENT] [TIMESTAMP]
# Examples:
#   DX de W1ABC: 14023.5 N4OG FT8
#   DX de VU3YBH: 28075.1 AT4WWA World Wide Award ft8 0445Z
#   DX de N1FXP: 1840.0 AB8DD EL86XQ<>EN80 0446Z
# Note: Mode may be anywhere in the comment, or right after callsign
DX_SPOT_PATTERN = re.compile(
    r'DX de\s+([A-Z0-9/]+[A-Z0-9]):\s+(\d+\.?\d*)\s+([A-Z0-9/]+[A-Z0-9])\s+(.+?)(?:\s+(\d{4}Z))?\s*$',
    re.IGNORECASE
)

# Common mode patterns to extract from comment
MODE_PATTERNS = [
    r'\b(FT8|FT4|PSK31|PSK63|PSK125|CW|RTTY|SSB|AM|FM|SSTV|JT65|JT9|WSPR|APRS|FSK441|JTMS|ISCAT|MSK144|QRA64|T10|WSPR-15)\b',
    r'\b(LSB|USB)\b',  # Lower/Upper Sideband
]


class DXClusterProvider(BaseSpotProvider):
    """Provider for DX Cluster telnet servers."""
    
    def __init__(self, host: str = "dxmaps.com", port: int = 7300, callsign: Optional[str] = None):
        """
        Initialize DX Cluster provider.
        
        Args:
            host: DX Cluster server hostname
            port: DX Cluster server port
            callsign: Optional callsign for login (some servers require)
        """
        super().__init__("dxcluster")
        self.host = host
        self.port = port
        self.callsign = callsign
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        self.connection_task: Optional[asyncio.Task] = None
        self.read_task: Optional[asyncio.Task] = None
        self.spot_buffer: Deque[Spot] = deque(maxlen=1000)  # Keep last 1000 spots
        self.reconnect_delay = 5  # Start with 5 seconds
        self.max_reconnect_delay = 300  # Max 5 minutes
        self._lock = asyncio.Lock()
        self._login_complete = False  # Flag to prevent sending commands after login
        
        # DX Cluster supports all modes
        self.supported_modes = [
            'SSB', 'CW', 'RTTY', 'PSK31', 'PSK63', 'PSK125', 'FT8', 'FT4',
            'JT65', 'JT9', 'WSPR', 'APRS', 'FSK441', 'JTMS', 'ISCAT',
            'MSK144', 'QRA64', 'T10', 'WSPR-15', 'AM', 'FM', 'SSTV'
        ]
    
    async def connect(self):
        """Establish telnet connection to DX Cluster server."""
        try:
            logger.info(f"Connecting to DX Cluster {self.host}:{self.port}")
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10.0
            )
            self.connected = True
            self.reconnect_delay = 5  # Reset delay on successful connection
            self._login_complete = False  # Reset login flag for new connection
            
            # DX Cluster servers send "login:" prompt and expect just the callsign
            if self.callsign:
                # Read until we see "login:" prompt
                login_prompt_found = False
                try:
                    for _ in range(20):  # Try reading up to 20 times (allow for slow servers)
                        chunk = await asyncio.wait_for(
                            self.reader.read(1024),
                            timeout=1.0
                        )
                        if not chunk:
                            break
                        
                        text = chunk.decode('utf-8', errors='ignore')
                        logger.debug(f"Initial server data: {text[:200]}")
                        
                        # Check if we see login prompt
                        if 'login:' in text.lower():
                            login_prompt_found = True
                            # Small delay to ensure prompt is ready
                            await asyncio.sleep(0.2)
                            break
                except asyncio.TimeoutError:
                    # If timeout, assume login prompt was sent and proceed
                    logger.debug("Timeout waiting for login prompt, sending callsign anyway")
                    login_prompt_found = True
                
                # Send callsign as login (just the callsign, nothing else)
                await self._send_command(self.callsign, login_only=True)
                logger.info(f"Sent callsign login: {self.callsign}")
                
                # Read and discard welcome message after login
                try:
                    response = await asyncio.wait_for(
                        self.reader.read(4096),
                        timeout=3.0
                    )
                    if response:
                        response_text = response.decode('utf-8', errors='ignore')
                        logger.debug(f"Server welcome message: {response_text[:200]}")
                except asyncio.TimeoutError:
                    pass
                
                # Mark login as complete - no more commands will be sent
                self._login_complete = True
                logger.info("Login complete - bot is now in read-only mode (no commands will be sent)")
            else:
                logger.warning("No callsign provided for DX Cluster login - connection may fail")
                self._login_complete = True  # Still mark as complete to prevent any commands
            
            logger.info(f"Connected to DX Cluster {self.host}:{self.port}")
            
            # Start reading spots in background
            if self.read_task is None or self.read_task.done():
                self.read_task = asyncio.create_task(self._read_spots())
            
            return True
        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to DX Cluster {self.host}:{self.port}")
            self.connected = False
            return False
        except ConnectionRefusedError:
            logger.error(f"Connection refused by DX Cluster {self.host}:{self.port} - server may be down or port incorrect")
            logger.info(f"Try testing with: telnet {self.host} {self.port}")
            self.connected = False
            return False
        except OSError as e:
            logger.error(f"Network error connecting to DX Cluster {self.host}:{self.port}: {e}")
            logger.info(f"Verify the server is accessible: telnet {self.host} {self.port}")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Failed to connect to DX Cluster {self.host}:{self.port}: {e}", exc_info=True)
            logger.info(f"Check if server is accessible: telnet {self.host} {self.port}")
            self.connected = False
            return False
    
    async def _send_command(self, command: str, login_only: bool = True):
        """
        Send a command to the DX Cluster server.
        
        Args:
            command: Command to send
            login_only: If True, only allow sending during login phase
        """
        if login_only and self._login_complete:
            logger.warning(f"Attempted to send command '{command}' after login - BLOCKED to prevent accidental spots")
            return
        
        if self.writer and not self.writer.is_closing():
            try:
                self.writer.write(f"{command}\r\n".encode('utf-8'))
                await self.writer.drain()
            except Exception as e:
                logger.warning(f"Failed to send command to DX Cluster: {e}")
    
    async def _read_spots(self):
        """Read spots from DX Cluster connection in background."""
        while self.connected:
            try:
                if self.reader is None:
                    break
                
                # Read line with timeout
                line_bytes = await asyncio.wait_for(
                    self.reader.readline(),
                    timeout=30.0
                )
                
                if not line_bytes:
                    logger.warning("DX Cluster connection closed by server")
                    self.connected = False
                    break
                
                line = line_bytes.decode('utf-8', errors='ignore').strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Skip command prompts (lines ending with > or $)
                if line.endswith('>') or line.endswith('$'):
                    continue
                
                # Skip login prompts and system messages
                skip_keywords = [
                    'login:', 'please enter', 'this is', 'running', 'capabilities:',
                    'nodes:', 'users', 'uptime:', 'de ', 'set/', 'enter your'
                ]
                if any(keyword in line.lower() for keyword in skip_keywords):
                    # But don't skip actual DX spots that contain "de" (they start with "DX de")
                    if not line.startswith('DX de'):
                        continue
                
                # Parse DX spots (format: "DX de CALLSIGN: FREQ CALLSIGN MODE COMMENT")
                if line.startswith('DX de'):
                    spot = self._parse_spot(line)
                    if spot:
                        async with self._lock:
                            self.spot_buffer.append(spot)
                            # Clean up old spots (older than 20 minutes) to prevent buffer bloat
                            # Keep at least 2-3 monitoring cycles worth of spots
                            cutoff_time = datetime.utcnow() - timedelta(minutes=20)
                            while self.spot_buffer and self.spot_buffer[0].timestamp < cutoff_time:
                                self.spot_buffer.popleft()
                            # Also enforce max size as safety limit
                            while len(self.spot_buffer) > 1000:
                                self.spot_buffer.popleft()
                
            except asyncio.TimeoutError:
                # Send keepalive (just Enter/newline) to maintain connection
                # This is safe - just a newline, won't create spots
                if self.writer and not self.writer.is_closing():
                    try:
                        # Send just a newline (Enter key) as keepalive
                        self.writer.write(b"\r\n")
                        await self.writer.drain()
                    except Exception as e:
                        logger.debug(f"Keepalive failed: {e}")
                continue
            except Exception as e:
                logger.error(f"Error reading from DX Cluster: {e}")
                self.connected = False
                break
        
        # Connection lost, schedule reconnection
        if self.connection_task is None or self.connection_task.done():
            self.connection_task = asyncio.create_task(self._reconnect_loop())
    
    async def _reconnect_loop(self):
        """Handle reconnection with exponential backoff."""
        while not self.connected:
            try:
                await asyncio.sleep(self.reconnect_delay)
                success = await self.connect()
                if not success:
                    # Exponential backoff
                    self.reconnect_delay = min(
                        self.reconnect_delay * 2,
                        self.max_reconnect_delay
                    )
                    logger.info(f"Will retry DX Cluster connection in {self.reconnect_delay} seconds")
            except Exception as e:
                logger.error(f"Error in DX Cluster reconnection loop: {e}")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(
                    self.reconnect_delay * 2,
                    self.max_reconnect_delay
                )
    
    def _parse_spot(self, line: str) -> Optional[Spot]:
        """
        Parse a DX Cluster spot line.
        
        Format: DX de CALLSIGN: FREQ CALLSIGN [MODE] [COMMENT] [TIMESTAMP]
        Mode may be anywhere in the comment or right after callsign.
        """
        try:
            match = DX_SPOT_PATTERN.match(line)
            if not match:
                return None
            
            spotter = match.group(1).strip().upper()
            frequency_str = match.group(2).strip()
            callsign = match.group(3).strip().upper()
            rest = match.group(4).strip() if match.group(4) else ""
            timestamp_str = match.group(5).strip() if match.group(5) else None
            
            # Try to extract mode from the rest of the line
            mode = None
            comment = rest
            
            # First, try to find a mode pattern in the comment
            for pattern in MODE_PATTERNS:
                mode_match = re.search(pattern, rest, re.IGNORECASE)
                if mode_match:
                    mode = mode_match.group(1).upper()
                    # Remove mode from comment
                    comment = re.sub(pattern, '', rest, flags=re.IGNORECASE).strip()
                    break
            
            # If no mode found, check if first word is a common mode
            if not mode:
                words = rest.split()
                if words:
                    first_word = words[0].upper()
                    # Check if first word is a known mode
                    known_modes = ['FT8', 'FT4', 'PSK31', 'CW', 'RTTY', 'SSB', 'LSB', 'USB', 'AM', 'FM']
                    if first_word in known_modes:
                        mode = first_word
                        comment = ' '.join(words[1:]).strip()
            
            # If still no mode, default to "SSB" for HF or "FM" for VHF/UHF
            if not mode:
                try:
                    freq = float(frequency_str)
                    if freq < 1000:
                        freq = freq * 1_000_000
                    elif freq < 100_000:
                        freq = freq * 1_000
                    
                    if freq >= 50_000_000:  # VHF/UHF
                        mode = "FM"
                    else:  # HF
                        mode = "SSB"
                except:
                    mode = "SSB"  # Default fallback
            
            # Basic validation
            if not callsign or len(callsign) < 2:
                logger.debug(f"Invalid callsign in DX spot: {callsign}")
                return None
            
            if not mode:
                logger.debug(f"Missing mode in DX spot")
                return None
            
            # Parse frequency (can be in kHz or MHz)
            try:
                frequency = float(frequency_str)
                # If frequency < 1000, assume MHz, convert to Hz
                if frequency < 1000:
                    frequency = frequency * 1_000_000
                # If frequency < 100000, assume kHz, convert to Hz
                elif frequency < 100_000:
                    frequency = frequency * 1_000
                # Otherwise assume already in Hz
                
                # Validate frequency range (amateur radio bands: 1.8 MHz to 148 MHz)
                if frequency < 1_800_000 or frequency > 148_000_000:
                    logger.debug(f"Frequency out of amateur radio range: {frequency} Hz")
                    # Still accept it, but log for debugging
            except ValueError:
                logger.warning(f"Invalid frequency in DX spot: {frequency_str}")
                return None
            
            # Create spot ID
            timestamp = datetime.utcnow()
            spot_id = f"{callsign}_{mode}_{frequency}_{int(timestamp.timestamp())}"
            
            # Build additional data
            additional_data = {}
            if comment:
                additional_data['comment'] = comment
            
            return Spot(
                callsign=callsign,
                mode=mode,
                frequency=frequency,
                timestamp=timestamp,
                spot_id=spot_id,
                source=self.source_name,
                spotter=spotter,
                additional_data=additional_data if additional_data else None
            )
        except Exception as e:
            logger.warning(f"Failed to parse DX spot line '{line}': {e}")
            return None
    
    async def test_connection(self) -> bool:
        """Test connection to DX Cluster server."""
        if not self.connected:
            return await self.connect()
        return self.connected
    
    async def fetch_recent_spots(self, since: Optional[datetime] = None) -> List[Spot]:
        """
        Fetch recent spots from DX Cluster buffer.
        
        Args:
            since: Only fetch spots after this timestamp. If None, fetch last 10 minutes.
            
        Returns:
            List of Spot objects
        """
        if since is None:
            since = datetime.utcnow() - timedelta(minutes=10)
        
        # Ensure connection is established
        if not self.connected:
            await self.connect()
        
        async with self._lock:
            # Filter spots by timestamp
            spots = [
                spot for spot in self.spot_buffer
                if spot.timestamp >= since
            ]
        
        logger.info(f"Fetched {len(spots)} spots from DX Cluster (since {since})")
        return spots
    
    def get_supported_modes(self) -> List[str]:
        """Get list of supported modes."""
        return self.supported_modes.copy()
    
    def get_recent_spots(self, count: int = 10) -> List[Spot]:
        """
        Get most recent spots from buffer (synchronous, for display commands).
        
        Args:
            count: Number of spots to return
            
        Returns:
            List of Spot objects
        """
        # Note: This is not async, so we access buffer directly
        # In practice, this should be safe since we're just reading
        spots = list(self.spot_buffer)[-count:]
        return spots[::-1]  # Reverse to get newest first
    
    async def close(self):
        """Close the DX Cluster connection."""
        self.connected = False
        
        if self.read_task and not self.read_task.done():
            self.read_task.cancel()
            try:
                await self.read_task
            except asyncio.CancelledError:
                pass
        
        if self.connection_task and not self.connection_task.done():
            self.connection_task.cancel()
            try:
                await self.connection_task
            except asyncio.CancelledError:
                pass
        
        if self.writer and not self.writer.is_closing():
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass
        
        self.reader = None
        self.writer = None
        logger.info("DX Cluster connection closed")
