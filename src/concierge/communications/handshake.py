"""Handshake communication - initial session setup."""
import json
from concierge.communications.base import Communications
from concierge.communications.messages import HANDSHAKE_MESSAGE


class HandshakeMessage(Communications):
    """Message for initial handshake and workflow selection"""
    
    def render(self, context: dict) -> str:
        """Render handshake message with workflow options"""
        workflows = context["workflows"]
        
        workflows_list = []
        for i, wf in enumerate(workflows, 1):
            stages = ', '.join(wf["stages"])
            workflows_list.append(
                f"{i}. {wf['id']}: {wf['description']}\n"
                f"   Stages: {stages}"
            )
        
        return HANDSHAKE_MESSAGE.format(
            app_name=context["app_name"],
            app_description=context["app_description"],
            workflow_count=len(workflows),
            workflows_list='\n'.join(workflows_list)
        )

