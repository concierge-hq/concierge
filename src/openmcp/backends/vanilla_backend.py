from openmcp.backends.base_provider import BaseProvider


class VanillaBackend(BaseProvider):

    def initialize(self, config):
        self._tools = []

    def index_tools(self, tools):
        self._tools = list(tools)

    def serve_tools(self):
        return self._tools

