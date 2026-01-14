# UAIP Quickstart

## Install

```bash
pip install uaip
```

## Define a Workflow

```python
# my_workflow.py
from uaip.core import workflow, stage, task, State

@stage(name="greet")
class GreetStage:
    @task()
    def say_hello(self, state: State, name: str) -> dict:
        return {"message": f"Hello, {name}!"}

@workflow(name="hello")
class HelloWorkflow:
    greet = GreetStage

if __name__ == "__main__":
    HelloWorkflow.run(port=8000)
```

## Run

```bash
python my_workflow.py
```

## Use

```bash
# Initialize session
curl -X POST http://localhost:8000/initialize \
  -H "Content-Type: application/json" \
  -d '{"workflow_name": "hello"}'

# Returns: {"session_id": "abc-123", "workflow": "hello", "initial_stage": "greet"}

# Execute task
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: abc-123" \
  -d '{"workflow_name": "hello", "action": "method_call", "task": "say_hello", "args": {"name": "World"}}'

# Returns: {"content": "Task 'say_hello' executed successfully.\n\nResult:\n{'message': 'Hello, World!'}", ...}
```

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Workflow** | Container for stages with defined transitions |
| **Stage** | Group of related tasks with prerequisites |
| **Task** | Single executable action |
| **State** | Shared context across tasks and stages |
| **Transitions** | Allowed paths between stages |
| **Prerequisites** | Required state before entering a stage |
| **Constructs** | Typed input/output schemas for tasks |

