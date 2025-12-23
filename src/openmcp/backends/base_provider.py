from abc import ABC, abstractmethod


class BaseProvider(ABC):

    @abstractmethod
    def initialize(self, config):
        """Initialize provider with config."""
        pass

    @abstractmethod
    def index_tools(self, tools):
        """Index original tools."""
        pass

    @abstractmethod
    def serve_tools(self):
        """Return tool functions to expose on the MCP server."""
        pass

