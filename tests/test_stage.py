"""Test Stage - task discovery and local state."""
import asyncio
from concierge.core import State, task, stage


@stage(name="test_stage")
class TestStage:
    """Test stage"""
    
    @task()
    def task1(self, state: State, x: int) -> dict:
        """First task"""
        return {"result": x}
    
    @task()
    def task2(self, state: State, y: str) -> dict:
        """Second task"""
        state.set("key", y)
        return {"result": y}


def test_stage_task_discovery():
    assert len(TestStage.tasks) == 2
    assert "task1" in TestStage.tasks
    assert "task2" in TestStage.tasks


def test_stage_local_state():
    """Test that tasks can modify state"""
    from concierge.core.state import State
    
    state = State()
    
    asyncio.run(TestStage.tasks["task2"].execute(state, y="test"))
    
    # Verify state was updated
    assert state.get("key") == "test"


def test_stage_instance_binding():
    task_obj = TestStage.tasks["task1"]
    
    # Verify func is bound to instance (not unbound)
    assert hasattr(task_obj.func, '__self__')

