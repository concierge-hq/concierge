"""Base Presentation class - defines interface for rendering responses."""
from abc import ABC, abstractmethod


class Presentation(ABC):
    """
    Base class for presentations - handles formatting of response content
    with orchestrator context (stage, tasks, state, etc.)
    """
    
    def __init__(self, content: str):
        """
        Initialize presentation with rendered content.
        
        Args:
            content: The rendered content from Communications.render()
        """
        self.content = content
    
    @abstractmethod
    def render_text(self, orchestrator) -> str:
        """
        Render the full response by combining content with orchestrator context.
        
        Args:
            orchestrator: Orchestrator instance to fetch metadata from
            
        Returns:
            Fully formatted response string
        """
        pass
    
    @abstractmethod
    def render_json(self, orchestrator) -> dict:
        """
        Render response as structured JSON for LLM tool calling.
        
        Args:
            orchestrator: Orchestrator instance to fetch metadata from
            
        Returns:
            dict with 'content' (response message) and 'tools' (available actions)
        """
        pass

