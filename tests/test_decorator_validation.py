"""Tests for decorator validation - ensuring decorators are used correctly."""
import pytest
import warnings
from concierge import State, task, stage, workflow


def test_task_requires_self_parameter():
    """Test that @task raises error on functions without 'self' parameter"""
    
    with pytest.raises(TypeError, match="@task decorator can only be applied to instance methods"):
        @task()
        def standalone_function(state: State, x: int):
            """This should fail - not a method"""
            return {"result": x}


def test_task_on_staticmethod_fails():
    """Test that @task raises error on static methods"""
    
    with pytest.raises(TypeError, match="@task decorator cannot be applied to @staticmethod"):
        @stage()
        class BadStage:
            @task()
            @staticmethod
            def bad_task(state: State):
                """This should fail"""
                return {}


def test_task_on_classmethod_fails():
    """Test that @task raises error on class methods"""
    
    with pytest.raises(TypeError, match="@task decorator cannot be applied to @classmethod"):
        @stage()
        class BadStage:
            @task()
            @classmethod
            def bad_task(cls, state: State):
                """This should fail"""
                return {}


def test_task_directly_in_workflow_fails():
    """Test that @task decorator directly on workflow methods raises error"""
    
    with pytest.raises(TypeError, match="uses @task decorator directly on workflow class"):
        @stage()
        class GoodStage:
            @task()
            def good_task(self, state: State):
                """This is fine"""
                return {}
        
        @workflow(name="test")
        class BadWorkflow:
            """This should fail"""
            stage1 = GoodStage
            
            @task()  # This should be rejected
            def bad_task(self, state: State):
                """Tasks can't be directly in workflow"""
                return {}


def test_undecorated_stage_with_tasks_fails():
    """Test that class with @task methods but no @stage decorator raises error"""
    
    with pytest.raises(TypeError, match="has @task methods but is not decorated with @stage"):
        class UndecoratedClass:
            @task()
            def some_task(self, state: State):
                """This has a task but no @stage"""
                return {}
        
        @workflow(name="test")
        class BadWorkflow:
            """This should fail"""
            my_stage = UndecoratedClass  # Forgot @stage decorator!


def test_stage_with_no_tasks_warns():
    """Test that @stage with no tasks issues a warning"""
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        @stage()
        class EmptyStage:
            """This stage has no tasks"""
            pass
        
        assert len(w) == 1
        assert "has no @task methods defined" in str(w[0].message)
        assert w[0].category == UserWarning


def test_double_stage_decorator_fails():
    """Test that applying @stage twice raises error"""
    
    @stage(name="first")
    class MyStage:
        @task()
        def my_task(self, state: State):
            return {}
    
    # Try to apply @stage again
    with pytest.raises(TypeError, match="Cannot use @stage decorator on a Stage object that has already been decorated"):
        stage(name="second")(MyStage)


def test_valid_workflow_structure_succeeds():
    """Test that properly structured workflow/stage/task succeeds"""
    
    @stage(name="test_stage")
    class TestStage:
        """Valid stage"""
        
        @task()
        def task1(self, state: State, x: int):
            """First task"""
            return {"result": x * 2}
        
        @task()
        def task2(self, state: State, y: str):
            """Second task"""
            return {"result": y.upper()}
    
    @workflow(name="test_workflow")
    class TestWorkflow:
        """Valid workflow"""
        stage1 = TestStage
    
    # Should succeed without errors
    assert TestWorkflow._workflow.name == "test_workflow"
    assert "test_stage" in TestWorkflow._workflow.stages
    assert "task1" in TestWorkflow._workflow.stages["test_stage"].tasks
    assert "task2" in TestWorkflow._workflow.stages["test_stage"].tasks


def test_multiple_stages_in_workflow():
    """Test that multiple stages work correctly"""
    
    @stage(name="stage1")
    class Stage1:
        @task()
        def action1(self, state: State):
            return {"data": "stage1"}
    
    @stage(name="stage2")
    class Stage2:
        @task()
        def action2(self, state: State):
            return {"data": "stage2"}
    
    @workflow(name="multi_stage")
    class MultiStageWorkflow:
        s1 = Stage1
        s2 = Stage2
        
        transitions = {
            Stage1: [Stage2],
            Stage2: [Stage1]
        }
    
    wf = MultiStageWorkflow._workflow
    assert len(wf.stages) == 2
    assert "stage1" in wf.stages
    assert "stage2" in wf.stages


def test_error_messages_are_helpful():
    """Test that error messages provide helpful examples"""
    
    try:
        @task()
        def bad_func(x: int):
            return {"result": x}
    except TypeError as e:
        error_msg = str(e)
        assert "first parameter must be 'self'" in error_msg
        assert "@stage()" in error_msg  # Should show example
        assert "def bad_func(self, state, ...)" in error_msg
        assert "Example:" in error_msg
    else:
        pytest.fail("Expected TypeError to be raised")


def test_workflow_with_regular_class_attributes():
    """Test that workflows can have regular class attributes that aren't stages"""
    
    @stage()
    class MyStage:
        @task()
        def my_task(self, state: State):
            return {}
    
    @workflow(name="test")
    class MyWorkflow:
        """This should work fine"""
        stage1 = MyStage
        
        # Regular class attributes should be ignored
        some_config = {"key": "value"}
        some_number = 42
        
        transitions = {
            MyStage: []
        }
    
    # Should succeed
    assert MyWorkflow._workflow.name == "test"


def test_cannot_use_workflow_on_stage():
    """Test that @workflow decorator cannot be applied to a Stage object"""
    
    @stage(name="my_stage")
    class MyStage:
        @task()
        def my_task(self, state: State):
            return {}
    
    # MyStage is now a Stage object, not a class
    # Try to apply @workflow to it
    with pytest.raises(TypeError, match="Cannot use @workflow decorator on a Stage object"):
        workflow(name="bad_workflow")(MyStage)


def test_cannot_use_stage_on_workflow():
    """Test that @stage decorator cannot be applied to a Workflow object"""
    
    @stage(name="stage1")
    class Stage1:
        @task()
        def task1(self, state: State):
            return {}
    
    @workflow(name="my_workflow")
    class MyWorkflow:
        s1 = Stage1
    
    # MyWorkflow._workflow is a Workflow object
    # Try to apply @stage to it (this is a contrived example but tests the validation)
    with pytest.raises(TypeError, match="Cannot use @stage decorator on a Workflow object"):
        stage(name="bad_stage")(MyWorkflow._workflow)


def test_double_workflow_decorator_fails():
    """Test that applying @workflow twice raises error"""
    
    @stage()
    class MyStage:
        @task()
        def my_task(self, state: State):
            return {}
    
    @workflow(name="first")
    class MyWorkflow:
        stage1 = MyStage
    
    # Try to apply @workflow again
    with pytest.raises(TypeError, match="Cannot use @workflow decorator on a Workflow object that has already been decorated"):
        workflow(name="second")(MyWorkflow._workflow)


