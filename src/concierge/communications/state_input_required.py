"""
State Input Required Message - prompts user for missing state fields.
"""
from concierge.communications.base import Communications
from concierge.core.results import StateInputRequiredResult
from concierge.external.contracts import ACTION_STATE_INPUT


class StateInputRequiredMessage(Communications):
    """Message requesting user to provide missing state fields"""
    
    def render(self, result: StateInputRequiredResult) -> str:
        """Render only the state input request, without stage context"""
        lines = [
            result.message,
            "",
            "Please provide the values in the following format:",
            f'{{"action": "{ACTION_STATE_INPUT}", "state_updates": {{',
        ]
        
        field_examples = []
        for field_name in result.required_fields:
            example = f'  "{field_name}": "value"'
            field_examples.append(example)
        
        lines.append(',\n'.join(field_examples))
        lines.extend([
            "}}"
        ])
        
        return "\n".join(lines)

