import sys
import json
import requests
from openai import OpenAI


class ToolCallingClient:
    
    def __init__(self, api_base: str, api_key: str):
        self.llm = OpenAI(base_url=api_base, api_key=api_key)
        self.model = "gpt-5"  
        self.concierge_url = "http://localhost:8082"
        
        self.workflow_sessions = {} 
        self.current_workflow = None
        self.current_tools = []
        
        self.conversation_history = [{
            "role": "system",
            "content": """You are an AI assistant with access to multiple workflows via Concierge.

You can choose to discover several workflows at your disposal, you need to abstract the workflow from the user. You can navigate the workflow and do anything but user must get a whiteglove experience where you ask the user anything that is needed etc.:
1. First, discover available workflows that match their intent
2. Connect to the appropriate workflow
3. Use the provided tools to complete the task
4. You can switch workflows if needed

Start by understanding what the user wants to do."""
        }]
    
    def discover_workflows(self, user_intent: str) -> list:
        """Get available workflows from Concierge API"""
        try:
            response = requests.get(f"{self.concierge_url}/api/workflows")
            response.raise_for_status()
            workflows = response.json()
            
            print(f"\n[DISCOVERED WORKFLOWS] {len(workflows.get('workflows', []))} available")
            return workflows.get('workflows', [])
        except Exception as e:
            print(f"[ERROR] Failed to discover workflows: {e}")
            return []
    
    def connect_to_workflow(self, workflow_name: str) -> dict:
        """Initialize session with a specific workflow"""
        headers = {}
        if workflow_name in self.workflow_sessions:
            headers["X-Session-Id"] = self.workflow_sessions[workflow_name]
        
        payload = {
            "action": "handshake",
            "workflow_name": workflow_name
        }
        
        print(f"\n[CONNECTING] Workflow: {workflow_name}")
        
        response = requests.post(f"{self.concierge_url}/execute", json=payload, headers=headers)
        response.raise_for_status()
        
        self.workflow_sessions[workflow_name] = response.headers['X-Session-Id']
        self.current_workflow = workflow_name
        
        result = json.loads(response.text)
        self.current_tools = self.concierge_to_openai_tools(result["tools"])
        
        print(f"[CONNECTED] Session: {self.workflow_sessions[workflow_name][:8]}...")
        return result
    
    def call_workflow(self, workflow_name: str, payload: dict) -> dict:
        """Call current workflow with an action"""
        if workflow_name not in self.workflow_sessions:
            raise ValueError(f"Not connected to workflow: {workflow_name}")
        
        headers = {"X-Session-Id": self.workflow_sessions[workflow_name]}
        payload["workflow_name"] = workflow_name
        
        print(f"\n[{workflow_name.upper()}] Action: {payload.get('action')}")
        
        response = requests.post(f"{self.concierge_url}/execute", json=payload, headers=headers)
        response.raise_for_status()
        
        result = json.loads(response.text)
        self.current_tools = self.concierge_to_openai_tools(result["tools"])
        
        return result
    
    def concierge_to_openai_tools(self, concierge_tools: list) -> list:
        """Convert Concierge tools to OpenAI format"""
        openai_tools = []
        for tool in concierge_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            })
        return openai_tools
    
    def openai_to_concierge_action(self, tool_call) -> dict:
        """Convert OpenAI tool_call to Concierge contract"""
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        if function_name == "discover_workflows":
            return {"_internal": "discover", "intent": arguments.get("intent", "")}
        elif function_name == "connect_workflow":
            return {"_internal": "connect", "workflow": arguments["workflow_name"]}
        elif function_name == "transition_stage":
            return {"action": "stage_transition", "stage": arguments["target_stage"]}
        elif function_name == "provide_state":
            return {"action": "state_input", "state_updates": arguments}
        elif function_name == "terminate_session":
            return {"action": "terminate_session", "reason": arguments.get("reason", "completed")}
        else:
            return {"action": "method_call", "task": function_name, "args": arguments}
    
    def get_workflow_discovery_tools(self) -> list:
        """Tools for workflow discovery phase"""
        return [{
            "type": "function",
            "function": {
                "name": "discover_workflows",
                "description": "Discover available workflows based on user intent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "description": "User's intent or what they want to do"
                        }
                    },
                    "required": ["intent"]
                }
            }
        }, {
            "type": "function",
            "function": {
                "name": "connect_workflow",
                "description": "Connect to a specific workflow to start using it",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "workflow_name": {
                            "type": "string",
                            "description": "Name of the workflow to connect to"
                        }
                    },
                    "required": ["workflow_name"]
                }
            }
        }]
    
    def chat(self, user_message: str) -> str:
        """Main chat loop with dynamic workflow discovery"""
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        max_iterations = 15
        for iteration in range(max_iterations):
            if not self.current_workflow:
                tools = self.get_workflow_discovery_tools()
            else:
                tools = self.current_tools + self.get_workflow_discovery_tools()
            
            print(f"\n[ITERATION {iteration + 1}] Tools: {len(tools)}, Workflow: {self.current_workflow or 'None'}")
            
            response = self.llm.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                tools=tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            assistant_message = {"role": "assistant", "content": message.content}
            if message.tool_calls:
                assistant_message["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            self.conversation_history.append(assistant_message)
            
            if not message.tool_calls:
                print(f"\n[ASSISTANT] {message.content}")
                return message.content
            
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                print(f"\n[TOOL CALL] {function_name}({json.dumps(arguments, indent=2)})")
                
                if function_name == "discover_workflows":
                    workflows = self.discover_workflows(arguments.get("intent", ""))
                    result_content = json.dumps({
                        "workflows": workflows,
                        "message": f"Found {len(workflows)} workflows. Choose one to connect."
                    })
                
                elif function_name == "connect_workflow":
                    workflow_name = arguments["workflow_name"]
                    result = self.connect_to_workflow(workflow_name)
                    result_content = result["content"]
                
                else:
                    if not self.current_workflow:
                        result_content = "Error: Not connected to any workflow. Use connect_workflow first."
                    else:
                        action = self.openai_to_concierge_action(tool_call)
                        result = self.call_workflow(self.current_workflow, action)
                        result_content = result["content"]
                
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_content
                })
        
        return "Max iterations reached. Please try again."
    
    def run(self):
        """Interactive chat loop"""
        print(f"Concierge Tool Calling Client | Model: {self.model}")
        print("Type 'exit' to quit\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() == "exit":
                    break
                
                response = self.chat(user_input)
                print(f"\nAssistant: {response}\n")
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"\nError: {e}\n")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python client_tool_calling.py <api_base> <api_key>")
        sys.exit(1)
    
    api_base = sys.argv[1]
    api_key = sys.argv[2]
    
    client = ToolCallingClient(api_base, api_key)
    client.run()
