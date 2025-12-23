from dataclasses import dataclass, field


DEFAULT_ANNOTATIONS = {
    "destructiveHint": False,
    "openWorldHint": False,
    "readOnlyHint": True,
}


@dataclass
class Widget:

    uri: str
    html: str | None = None
    html_file: str | None = None

    name: str | None = None
    description: str | None = None

    title: str | None = None
    mime_type: str = "text/html+skybridge"
    invoking: str = "Loading..."
    invoked: str = "Done"
    widget_accessible: bool = True
    annotations: dict = field(default_factory=lambda: DEFAULT_ANNOTATIONS.copy())

