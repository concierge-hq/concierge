from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Any, Optional


DEFAULT_ANNOTATIONS = {
    "destructiveHint": False,
    "openWorldHint": False,
    "readOnlyHint": True,
}


class WidgetMode(Enum):
    HTML = auto()        # Inline HTML string
    URL = auto()         # External URL (iframe)
    ENTRYPOINT = auto()  # Build from entrypoints/
    DYNAMIC = auto()     # Function that generates HTML


@dataclass
class Widget:
    """
    4 modes (mutually exclusive, auto-detected):
    
    1. html="<div>..."     → Serve inline HTML directly
    2. url="https://..."   → Wrap external URL in iframe
    3. entrypoint="X.html" → Build entrypoints/X.html → dist/X.html
    4. html_fn=fn          → Call function to generate HTML dynamically
    """
    
    uri: str
    
    # Mode 1: Inline HTML
    html: Optional[str] = None
    
    # Mode 2: External URL
    url: Optional[str] = None
    
    # Mode 3: Entrypoint (filename only, e.g., "pizzaz.html")
    entrypoint: Optional[str] = None
    
    # Mode 4: Dynamic function (takes tool args, returns HTML string)
    html_fn: Optional[Callable[[dict], str]] = None

    name: Optional[str] = None
    description: Optional[str] = None
    title: Optional[str] = None
    mime_type: str = "text/html+skybridge"
    invoking: str = "Loading..."
    invoked: str = "Done"
    widget_accessible: bool = True
    annotations: dict = field(default_factory=lambda: DEFAULT_ANNOTATIONS.copy())
    
    # Last args from tool call (for dynamic HTML generation)
    _last_args: Optional[dict] = field(default=None, repr=False)
    
    @property
    def mode(self) -> WidgetMode:
        if self.html:
            return WidgetMode.HTML
        if self.url:
            return WidgetMode.URL
        if self.entrypoint:
            return WidgetMode.ENTRYPOINT
        if self.html_fn:
            return WidgetMode.DYNAMIC
        raise ValueError(f"Widget {self.name}: must specify html, url, entrypoint, or html_fn")
    
    @property
    def dist_file(self) -> Optional[str]:
        """For entrypoint mode: the output path in dist/"""
        if self.entrypoint:
            # entrypoints/foo.html → dist/entrypoints/foo.html
            name = self.entrypoint.rsplit(".", 1)[0]
            return f"entrypoints/{name}.html"
        return None
