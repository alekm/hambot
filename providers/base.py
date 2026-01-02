"""
Abstract base class for spot data providers.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Spot:
    """Represents a single spot from a data source."""
    callsign: str
    mode: str
    frequency: Optional[float]  # Frequency in Hz
    timestamp: datetime
    spot_id: str  # Unique identifier for this spot from the source
    source: str  # Source name (e.g., 'pskreporter')
    spotter: Optional[str] = None  # Callsign of the spotter
    additional_data: Optional[dict] = None  # Provider-specific additional data


class BaseSpotProvider(ABC):
    """Abstract base class for spot data providers."""
    
    def __init__(self, source_name: str):
        """
        Initialize the provider.
        
        Args:
            source_name: Name of this data source (e.g., 'pskreporter')
        """
        self.source_name = source_name
        self.last_check: Optional[datetime] = None
    
    @abstractmethod
    async def fetch_recent_spots(self, since: Optional[datetime] = None) -> List[Spot]:
        """
        Fetch recent spots from the data source.
        
        Args:
            since: Only fetch spots after this timestamp. If None, fetch recent spots.
            
        Returns:
            List of Spot objects
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test if the provider can connect to its data source.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    def get_supported_modes(self) -> List[str]:
        """
        Get list of modes supported by this provider.
        
        Returns:
            List of mode names
        """
        return []
