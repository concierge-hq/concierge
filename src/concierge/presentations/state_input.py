"""State Input Presentation - used when state information is required"""
from concierge.presentations.base import Presentation


class StateInputPresentation(Presentation):
    """
    Used exclusively when state input is required.
    Only shows the provide_state tool with dynamic schema for required fields.
    """
    
    def render_text(self, orchestrator) -> str:
        return self.content
    
    def render_json(self, orchestrator) -> dict:
        """
        Render JSON with only the provide_state tool.
        Schema is dynamically generated from required fields.
        """
        required_fields = getattr(orchestrator, 'required_state_fields', [])
        
        properties = {}
        for field in required_fields:
            properties[field] = {
                "type": "string",
                "description": f"Value for {field}"
            }
        
        return {
            "content": self.content,
            "tools": [{
                "name": "provide_state",
                "description": "Provide required the following state information to continue with the workflow",
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required_fields
                }
            }]
        }

