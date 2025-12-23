"""Test Orchestrator - runtime execution."""
import asyncio
from concierge.core import State, task, stage, workflow
from concierge.engine import Orchestrator
from concierge.core.actions import MethodCallAction, StageTransitionAction
from concierge.core.results import TaskResult, TransitionResult, ErrorResult


@stage(name="start")
class StartStage:
    @task()
    def init(self, state: State, value: int) -> dict:
        state.set("value", value)
        return {"result": value}


@stage(name="end")
class EndStage:
    @task()
    def finalize(self, state: State) -> dict:
        return {"result": "done"}


@workflow(name="test_flow")
class TestFlow:
    start = StartStage
    end = EndStage
    
    transitions = {
        StartStage: [EndStage]
    }


def test_orchestrator_task_call():
    wf = TestFlow._workflow
    orch = Orchestrator(wf, session_id="test-task-call")
    
    action = MethodCallAction(task_name="init", args={"value": 42})
    result = asyncio.run(orch.execute_method_call(action))
    
    assert isinstance(result, TaskResult)
    assert result.task_name == "init"
    assert result.result["result"] == 42


def test_orchestrator_transition():
    wf = TestFlow._workflow
    orch = Orchestrator(wf, session_id="test-transition")
    
    action = StageTransitionAction(target_stage="end")
    result = asyncio.run(orch.execute_stage_transition(action))
    
    assert isinstance(result, TransitionResult)
    assert result.from_stage == "start"
    assert result.to_stage == "end"
    assert orch.get_current_stage().name == "end"


def test_orchestrator_invalid_transition():
    wf = TestFlow._workflow
    orch = Orchestrator(wf, session_id="test-invalid-transition")
    
    action = StageTransitionAction(target_stage="start")
    result = asyncio.run(orch.execute_stage_transition(action))
    
    assert isinstance(result, ErrorResult)
    assert "Cannot transition" in result.message


def test_orchestrator_session_info():
    wf = TestFlow._workflow
    orch = Orchestrator(wf, session_id="test-orch-info")
    
    info = asyncio.run(orch.get_session_info())
    assert info["session_id"] == "test-orch-info"
    assert info["workflow"] == "test_flow"
    assert info["current_stage"] == "start"

