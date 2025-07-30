class LookupResult:
    """
    Container for online callsign lookup data.
    All fields default to empty string, False, or empty dict as appropriate.
    """

    def __init__(self):
        # Basic info
        self.callsign: str = ''
        self.prevcall: str = ''
        self.opclass: str = ''
        self.name: str = ''

        # Location information
        self.country: str = ''
        self.grid: str = ''
        self.itu: str = ''
        self.cq: str = ''
        self.zip: str = ''
        self.state: str = ''
        self.city: str = ''

        # Club info
        self.club: bool = False
        self.trusteename: str = ''
        self.trusteecall: str = ''

        # Other address info
        self.street1: str = ''
        self.street2: str = ''

        # ULS/FCC/etc.
        self.frn: str = ''
        self.uls: str = ''

        # Parsed raw data from API
        self.raw: dict = {}

        # Source indicator (e.g., "HamQTH", "Callook", etc.)
        self.source: str = ''
