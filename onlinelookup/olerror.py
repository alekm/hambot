"""
Online Lookup exceptions

The base class is OnlineLookupError

LookupVerificationError:
    raised when there is an issue verifying login credentials
    param api: Which API are you using?
"""

__all__ = [
    'OnlineLookupError',
    'LookupVerificationError',
    'LookupResultError',
    'LookupActiveError'
]

class OnlineLookupError(LookupError):
    """Base class for all online lookup errors."""

    def __init__(self, api, message=None):
        self.api = api
        self.message = message or f"Online lookup error for API: {api}"
        super().__init__(self.message)

    def __str__(self):
        return self.message

class LookupVerificationError(OnlineLookupError):
    """Raised when there's a problem verifying API login credentials."""
    def __init__(self, api, message=None):
        msg = message or f"Lookup verification failed for API: {api}"
        super().__init__(api, msg)

class LookupResultError(OnlineLookupError):
    """Raised when an API lookup returns no result or bad data."""
    def __init__(self, api, message=None):
        msg = message or f"No result or invalid data from API: {api}"
        super().__init__(api, msg)

class LookupActiveError(OnlineLookupError):
    """Raised when API session is not active/connected."""
    def __init__(self, api, message=None):
        msg = message or f"API session not active: {api}"
        super().__init__(api, msg)
