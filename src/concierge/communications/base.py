from abc import ABC, abstractmethod
from typing import Type

from concierge.presentations import Presentation


class Communications(ABC):
    """Base class for all message communications"""

    presentation_type: Type[Presentation] = None

    @abstractmethod
    def render(self, context: dict) -> str:
        """Render message with context data"""
        pass
