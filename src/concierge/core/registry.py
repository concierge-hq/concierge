"""Workflow Registry - Central discovery for all workflows"""
from typing import Dict, List
from datetime import datetime
from dataclasses import dataclass

from concierge.core.workflow import Workflow


@dataclass
class WorkflowMetadata:
    """Workflow metadata"""
    name: str
    description: str
    stages: List[str]
    source_type: str = "code"
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class WorkflowRegistry:
    """Registry for all workflows"""
    
    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}
        self._metadata: Dict[str, WorkflowMetadata] = {}
    
    def register(self, workflow: Workflow):
        """Register a workflow"""
        self._workflows[workflow.name] = workflow
        self._metadata[workflow.name] = WorkflowMetadata(
            name=workflow.name,
            description=workflow.description,
            stages=list(workflow.stages.keys())
        )
    
    def get_workflow(self, name: str) -> Workflow:
        """Get workflow by name"""
        return self._workflows[name]
    
    def has_workflow(self, name: str) -> bool:
        """Check if workflow exists"""
        return name in self._workflows
    
    def list_workflows(self) -> List[WorkflowMetadata]:
        """List all workflows"""
        return list(self._metadata.values())


_registry = WorkflowRegistry()


def get_registry() -> WorkflowRegistry:
    """Get global registry"""
    return _registry


def register_workflow(workflow_class):
    """Register a workflow class"""
    _registry.register(workflow_class._workflow)

