"""
Contract validation tests - ensures presentation examples match actual API contracts.

This catches bugs where the presentation layer shows different JSON formats
than what the language engine actually expects.
"""
import json
import re
import asyncio
from pydantic import ValidationError

from concierge.core import State, task, stage, workflow
from concierge.engine.language_engine import LanguageEngine
from concierge.external.contracts import TaskCall, StageTransition


@stage(name="test_stage")
class TestStage:
    """Test stage"""
    
    @task()
    def test_task(self, state: State, arg1: str, arg2: int):
        """Test task with args"""
        return {"result": "success"}


@workflow(name="test_workflow")
class TestWorkflow:
    """Test workflow"""
    test_stage = TestStage
    transitions = {}


def extract_json_examples(presentation_output: str) -> dict[str, list[dict]]:
    """Extract all JSON examples from presentation output"""
    examples = {
        "task_calls": [],
        "transitions": []
    }
    
    lines = presentation_output.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if stripped.startswith('{'):
            has_action = False
            for check_line in lines[i:min(i+5, len(lines))]:
                if '"action"' in check_line:
                    has_action = True
                    break
            
            if has_action:
                indent = len(line) - len(line.lstrip())
                json_lines = []
                brace_count = 0
                
                for j in range(i, len(lines)):
                    dedented = lines[j][indent:] if lines[j].startswith(' ' * indent) else lines[j].strip()
                    if dedented:
                        json_lines.append(dedented)
                        brace_count += dedented.count('{') - dedented.count('}')
                        
                        if brace_count == 0 and json_lines:
                            i = j + 1
                            break
                
                json_str = '\n'.join(json_lines)
                
                try:
                    parsed = json.loads(json_str)
                    
                    action = parsed.get("action")
                    if action == "method_call":
                        examples["task_calls"].append(parsed)
                    elif action == "stage_transition":
                        examples["transitions"].append(parsed)
                except json.JSONDecodeError:
                    pass
        
        i += 1
    
    return examples


def test_presentation_task_call_examples_match_contract():
    """
    CRITICAL: Ensures task call examples in presentation match TaskCall contract.
    
    This catches bugs where presentation shows wrong JSON format.
    """
    async def run():
        wf = TestWorkflow._workflow
        engine = LanguageEngine(wf, session_id="test-validation")
        
        response = await engine.process({
            "action": "method_call",
            "task": "test_task",
            "args": {"arg1": "test", "arg2": 42}
        })
        
        examples = extract_json_examples(response)
        
        assert len(examples["task_calls"]) > 0, "No task call examples found in presentation!"
        
        for i, example in enumerate(examples["task_calls"]):
            try:
                validated = TaskCall(**example)
                
                assert hasattr(validated, 'action'), f"Example {i}: Missing 'action' field"
                assert hasattr(validated, 'task'), f"Example {i}: Missing 'task' field"
                assert hasattr(validated, 'args'), f"Example {i}: Missing 'args' field"
                
                example_keys = set(example.keys())
                contract_keys = set(TaskCall.model_fields.keys())
                extra_keys = example_keys - contract_keys
                assert not extra_keys, f"Example {i}: Unexpected fields {extra_keys} not in contract"
                
            except ValidationError as e:
                raise AssertionError(
                    f"Task call example {i} in presentation does NOT match TaskCall contract!\n"
                    f"Example: {json.dumps(example, indent=2)}\n"
                    f"Validation error: {e}"
                )
    
    asyncio.run(run())


def test_presentation_transition_examples_match_contract():
    """
    CRITICAL: Ensures transition examples in presentation match StageTransition contract.
    
    This catches bugs where presentation shows wrong JSON format.
    """
    async def run():
        wf = TestWorkflow._workflow
        engine = LanguageEngine(wf, session_id="test-validation-2")
        
        response = await engine.process({
            "action": "method_call",
            "task": "test_task",
            "args": {"arg1": "test", "arg2": 42}
        })
        
        examples = extract_json_examples(response)
        
        if examples["transitions"]:
            for i, example in enumerate(examples["transitions"]):
                try:
                    validated = StageTransition(**example)
                    
                    assert hasattr(validated, 'action'), f"Example {i}: Missing 'action' field"
                    assert hasattr(validated, 'stage'), f"Example {i}: Missing 'stage' field"
                    
                    example_keys = set(example.keys())
                    contract_keys = set(StageTransition.model_fields.keys())
                    extra_keys = example_keys - contract_keys
                    assert not extra_keys, f"Example {i}: Unexpected fields {extra_keys} not in contract"
                    
                except ValidationError as e:
                    raise AssertionError(
                        f"Transition example {i} in presentation does NOT match StageTransition contract!\n"
                        f"Example: {json.dumps(example, indent=2)}\n"
                        f"Validation error: {e}"
                    )
    
    asyncio.run(run())


def test_language_engine_accepts_presentation_examples():
    """
    CRITICAL: Ensures language engine can actually parse the JSON examples shown in presentation.
    
    This is the end-to-end validation - if presentation shows an example,
    the language engine MUST be able to parse it.
    """
    async def run():
        wf = TestWorkflow._workflow
        engine = LanguageEngine(wf, session_id="test-validation-3")
        
        response = await engine.process({
            "action": "method_call",
            "task": "test_task",
            "args": {"arg1": "test", "arg2": 42}
        })
        
        examples = extract_json_examples(response)
        
        for i, task_example in enumerate(examples["task_calls"]):
            try:
                result = await engine.process(task_example)
                
                assert "Unknown action type" not in result, \
                    f"Task call example {i} was rejected by language engine!"
                
            except Exception as e:
                raise AssertionError(
                    f"Language engine failed to parse task call example {i} from presentation!\n"
                    f"Example: {json.dumps(task_example, indent=2)}\n"
                    f"Error: {e}"
                )
    
    asyncio.run(run())


def test_contract_constants_match_literal_types():
    """
    CRITICAL: Ensures the extracted constants match the Literal types in contracts.
    
    This catches bugs where constants are manually set incorrectly.
    """
    from concierge.external.contracts import (
        ACTION_METHOD_CALL,
        ACTION_STAGE_TRANSITION,
        ACTION_STATE_INPUT,
        ACTION_TERMINATE_SESSION,
        TaskCall,
        StageTransition,
        StateInput,
        TerminateSession
    )
    
    assert ACTION_METHOD_CALL == TaskCall.model_fields["action"].annotation.__args__[0], \
        "ACTION_METHOD_CALL constant doesn't match TaskCall Literal type!"
    
    assert ACTION_STAGE_TRANSITION == StageTransition.model_fields["action"].annotation.__args__[0], \
        "ACTION_STAGE_TRANSITION constant doesn't match StageTransition Literal type!"
    
    assert ACTION_STATE_INPUT == StateInput.model_fields["action"].annotation.__args__[0], \
        "ACTION_STATE_INPUT constant doesn't match StateInput Literal type!"
    
    assert ACTION_TERMINATE_SESSION == TerminateSession.model_fields["action"].annotation.__args__[0], \
        "ACTION_TERMINATE_SESSION constant doesn't match TerminateSession Literal type!"

