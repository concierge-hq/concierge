"""Test Workflow - stage registration and transitions."""
import asyncio
from concierge.core import State, task, stage, workflow
from concierge.core.state_manager import get_state_manager

@stage(name="stage1")
class Stage1:
    @task()
    def action1(self, state: State) -> dict:
        return {"result": "stage1"}


@stage(name="stage2")
class Stage2:
    @task()
    def action2(self, state: State) -> dict:
        return {"result": "stage2"}


@workflow(name="test_workflow")
class TestWorkflow:
    s1 = Stage1
    s2 = Stage2
    
    transitions = {
        Stage1: [Stage2],
        Stage2: [Stage1]
    }


def test_workflow_stage_registration():
    wf = TestWorkflow._workflow
    assert len(wf.stages) == 2
    assert "stage1" in wf.stages
    assert "stage2" in wf.stages


def test_workflow_initial_stage():
    wf = TestWorkflow._workflow
    assert wf.initial_stage == "stage1"


def test_workflow_transitions():
    wf = TestWorkflow._workflow
    assert wf.stages["stage1"].transitions == ["stage2"]
    assert wf.stages["stage2"].transitions == ["stage1"]


def test_workflow_can_transition():
    wf = TestWorkflow._workflow
    assert wf.can_transition("stage1", "stage2")
    assert not wf.can_transition("stage1", "stage1")


def test_workflow_validate_transition():
    wf = TestWorkflow._workflow
    global_state = State()
    source_state = State()
    
    result = wf.validate_transition("stage1", "stage2", global_state, source_state)
    assert result["valid"]
    
    result = wf.validate_transition("stage1", "stage1", global_state, source_state)
    assert not result["valid"]


def test_workflow_call_task():
    
    wf = TestWorkflow._workflow
    wf.initialize()
    
    state_mgr = get_state_manager()
    state_mgr.create_session("test-wf-session", wf.name, wf.get_cursor().name)
    
    result = asyncio.run(wf.call_task("stage1", "action1", {}, "test-wf-session"))
    assert result["type"] == "task_result"
    assert result["result"] == {"result": "stage1"}

