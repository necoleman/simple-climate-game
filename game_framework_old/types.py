"""Contains types for the framework
"""
from typing import Any, Optional

from dataclasses import dataclass

@dataclass
class Event:
    """Basic class for an event. Contains an event_type and, optionally, data
    """
    event_type: str
    data: Optional[Any] = None