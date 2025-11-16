import sys
import json
import time
import threading
import requests
from openai import OpenAI
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from concierge.config import SERVER_HOST, SERVER_PORT


class Mode(Enum):
    """Client operation modes"""
    USER = "user"  
    SERVER = "server"


class Spinner:
    def __init__(self, message: str = "Processing"):
        self.message = message
        self._stop = threading.Event()
        self._thread = None

    def __enter__(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._stop.set()
        if self._thread:
            self._thread.join()
        sys.stdout.write("\r" + " " * (len(self.message) + 6) + "\r")
        sys.stdout.flush()

    def _spin(self):
        frames = ["|", "/", "-", "\\"]
        idx = 0
        while not self._stop.is_set():
            frame = frames[idx % len(frames)]
            sys.stdout.write(f"\r  {frame} {self.message}")
            sys.stdout.flush()
            time.sleep(0.1)
            idx += 1



class ToolCallingClient:
    
    def __init__(self, api_base: str, api_key: str, verbose: bool = False):
        self.llm = OpenAI(base_url=api_base, api_key=api_key)
        self.model = "gpt-5"  
        self.concierge_url = f"http://{SERVER_HOST}:{SERVER_PORT}"
        
        self.mode = Mode.USER
        self.in_context_servers = []
        
        self.workflow_sessions = {} 
        self.current_workflow = None
        self.current_tools = []
        self.verbose = verbose
        
        self.conversation_history = [{
            "role": "system",
            "content": """You are an AI assistant with access to remote Concierge workflows.

CRITICAL: You must ONLY use the tools provided to you. DO NOT use your own knowledge or make up answers.

Your job is to help users accomplish tasks by:
1. Understanding what the user wants to do
2. Searching for and connecting to the appropriate remote server using search_remote_servers
3. Using ONLY the server's provided tools to complete the task - never use your own knowledge
4. Disconnecting when the task is complete or when the user needs different capabilities

RULES:
- If a tool call returns an error, inform the user about the error - don't make up alternate responses
- Never answer questions about data without attempting to call the appropriate tool first
- Always use the tools provided by the connected server
- If you don't have the right tool, search for a different server or tell the user you can't help

Always provide a seamless, conversational experience and explain what you're doing."""
        }]
    
    
    def _log(self, message: str, style: str = "info"):
        """Pretty print log messages"""
        if not self.verbose:
            return
        
        colors = {
            "info": "\033[36m",      # Cyan
            "success": "\033[32m",   # Green
            "warning": "\033[33m",   # Yellow
            "error": "\033[31m",     # Red
            "reset": "\033[0m"
        }
        color = colors.get(style, colors["info"])
        print(f"{color}{message}{colors['reset']}")
    
    def _status(self, message: str, icon: str = "→"):
        """Print status message with elegant styling"""
        print(f"  \033[38;5;110m{icon}\033[0m  \033[38;5;252m{message}\033[0m")
    
    def _success(self, message: str, detail: str = ""):
        """Print success message with checkmark"""
        print(f"  \033[38;5;82m✓\033[0m  \033[1;38;5;189m{message}\033[0m")
        if detail:
            print(f"     \033[38;5;245m{detail}\033[0m")
    
    def _action(self, heading: str, detail: str | None = None):
        """Print action being performed"""
        line = f"  \033[38;5;183m▪\033[0m  \033[38;5;252m{heading}\033[0m"
        if detail:
            line += f": \033[38;5;110m{detail}\033[0m"
        print(line)

    
    def search_remote_servers(self, search_query: str) -> list:
        """Search for available remote servers/workflows - ALWAYS OVERWRITES in-context servers"""
        try:
            self._status(f"Discovering workflows")
            response = requests.get(f"{self.concierge_url}/api/workflows", params={"search": search_query})
            response.raise_for_status()
            workflows = response.json().get('workflows', [])
            
            self.in_context_servers = workflows
            self._log(f"[SEARCH] Query: '{search_query}'", "info")
            self._log(f"[IN-CONTEXT] Found {len(workflows)} servers", "success")
            
            if workflows:
                self._success(f"Found {len(workflows)} workflow{'s' if len(workflows) != 1 else ''}")
            
            return workflows
        except Exception as e:
            self._log(f"[ERROR] Search failed: {e}", "error")
            self.in_context_servers = []
            return []
    
    def establish_connection(self, server_name: str) -> dict:
        """Establish connection with a discovered server and switch to SERVER MODE"""
        try:
            server = next((s for s in self.in_context_servers if s.get("name") == server_name), None)
            if not server:
                return {"error": f"Server '{server_name}' not found in current context. Search first."}
            
            self._status(f"Connecting to {server_name}")
            
            server_url = server.get("url", f"{self.concierge_url}")
            headers = {}
            if server_name in self.workflow_sessions:
                headers["X-Session-Id"] = self.workflow_sessions[server_name]
            
            payload = {
                "action": "handshake",
                "workflow_name": server_name
            }
            
            response = requests.post(f"{server_url}/execute", json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            if 'X-Session-Id' in response.headers:
                self.workflow_sessions[server_name] = response.headers['X-Session-Id']
            
            result = response.json()
            
            self.current_tools = self.concierge_to_openai_tools(result.get("tools", []))
            self.current_workflow = server_name
            
            self.mode = Mode.SERVER
            
            self._log(f"[CONNECTED] Session: {self.workflow_sessions.get(server_name, 'N/A')[:8]}...", "success")
            self._log(f"[MODE] Switched to SERVER mode", "info")
            self._log(f"[TOOLS] {len(self.current_tools)} tools available", "info")
            
            # Beautiful success message
            session_id = self.workflow_sessions.get(server_name, 'N/A')
            current_stage = result.get('current_stage', 'unknown')
            self._success(f"Connected to {server_name}", f"session: {session_id[:8]}... • stage: {current_stage}")
            
            return {
                "status": "connected",
                "server": server_name,
                "current_stage": result.get("current_stage"),
                "tools": [t["function"]["name"] for t in self.current_tools],
                "message": f"Connected to {server_name}. Ready to use server tools."
            }
            
        except Exception as e:
            self._log(f"[ERROR] Connection failed: {e}", "error")
            return {"error": str(e)}
    
    def get_user_mode_tools(self) -> list:
        """Tools available in USER mode - dynamically generates establish_connection with in-context servers"""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_remote_servers",
                    "description": "Search for available remote servers/workflows that can help accomplish a task",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_query": {
                                "type": "string",
                                "description": "What you're looking for (e.g., 'e-commerce', 'booking', 'shopping')"
                            }
                        },
                        "required": ["search_query"]
                    }
                }
            }
        ]
        
        if self.in_context_servers:
            server_options = []
            for server in self.in_context_servers:
                name = server.get("name")
                desc = server.get("description", "No description")
                if name:
                    server_options.append({
                        "const": name,
                        "description": desc
                    })
            
            establish_tool = {
                "type": "function",
                "function": {
                    "name": "establish_connection",
                    "description": """Connect to a server and switch to SERVER mode.

This will:
- Establish a session with the selected server
- Start an interactive session with the server, exposing the server's tools and stages.
- Switch to SERVER mode where you can:
  * Use all the server's workflow tools
  * Perform tasks specific to that server
  * Disconnect when done to search for other servers
  
After connecting, you'll have access to the server's tools to help the user accomplish their goal.""",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "server_name": {
                                "oneOf": server_options
                            }
                        },
                        "required": ["server_name"]
                    }
                }
            }
            tools.append(establish_tool)
        
        return tools
    
    
    def call_workflow(self, workflow_name: str, payload: dict) -> dict:
        """Call current workflow with an action"""
        if workflow_name not in self.workflow_sessions:
            raise ValueError(f"Not connected to workflow: {workflow_name}")
        
        headers = {"X-Session-Id": self.workflow_sessions[workflow_name]}
        payload["workflow_name"] = workflow_name
        
        self._log(f"[{workflow_name.upper()}] Action: {payload.get('action')}", "info")
        
        response = requests.post(f"{self.concierge_url}/execute", json=payload, headers=headers)
        response.raise_for_status()
        
        result = json.loads(response.text)
        
        # Update tools if they changed
        if "tools" in result:
            self.current_tools = self.concierge_to_openai_tools(result["tools"])
        
        return result
    
    def disconnect_server(self) -> dict:
        """Disconnect from current server and return to USER mode"""
        if not self.current_workflow:
            return {"status": "no_active_connection"}
        
        try:
            workflow_name = self.current_workflow
            
            if workflow_name in self.workflow_sessions:
                headers = {"X-Session-Id": self.workflow_sessions[workflow_name]}
                payload = {"action": "terminate_session", "workflow_name": workflow_name}
                
                try:
                    response = requests.post(f"{self.concierge_url}/execute", json=payload, headers=headers, timeout=10)
                except:
                    pass
            
            if workflow_name in self.workflow_sessions:
                del self.workflow_sessions[workflow_name]
            
            self.current_workflow = None
            self.current_tools = []
            self.in_context_servers = []
            self.mode = Mode.USER
            
            self._log(f"[DISCONNECTED] Server: {workflow_name}", "info")
            self._log(f"[MODE] Switched to USER mode", "info")
            print(f"  \033[38;5;147m◇\033[0m  \033[38;5;245mDisconnected from\033[0m \033[38;5;183m{workflow_name}\033[0m")
            
            return {"status": "disconnected", "server": workflow_name}
            
        except Exception as e:
            print(f"[ERROR] Disconnect failed: {e}")
            return {"error": str(e)}
    
    def get_server_mode_tools(self) -> list:
        """Tools available in SERVER mode"""
        tools = list(self.current_tools)  # Copy workflow tools
        
        # Add disconnect tool with detailed context
        tools.append({
            "type": "function",
            "function": {
                "name": "disconnect_server",
                "description": """Disconnect from the current server and switch back to USER mode.

This will:
- Close the connection with the current server
- Clear the current session and tools
- Switch to USER mode where you can:
  * Search for other remote servers
  * Discover different workflows
  * Connect to a different server
  
Use this when:
- The user wants to work with a different server
- The current task is complete
- You need to search for other capabilities
- You want to disconnect or switch servers""",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        })
        
        return tools
    
    
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
        
        # Server control actions
        if function_name == "transition_stage":
            return {"action": "stage_transition", "stage": arguments["target_stage"]}
        elif function_name == "provide_state":
            return {"action": "state_input", "state_updates": arguments}
        elif function_name == "terminate_session":
            return {"action": "terminate_session", "reason": arguments.get("reason", "completed")}
        else:
            return {"action": "method_call", "task": function_name, "args": arguments}
    
    
    def chat(self, user_message: str) -> str:
        """Main chat loop with mode-aware tool selection"""
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        max_iterations = 15
        for iteration in range(max_iterations):
            if self.mode == Mode.USER:
                tools = self.get_user_mode_tools()
            else:
                tools = self.get_server_mode_tools()
            
            self._log(f"[ITERATION {iteration + 1}] Mode: {self.mode.value.upper()}, Tools: {len(tools)}", "info")
            
            spinner_message = "Executing workflow plan" if self.mode == Mode.SERVER else "Evaluating request"
            with Spinner(spinner_message):
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
                print(f"  \033[38;5;147m◈\033[0m  \033[1;38;5;252m{message.content}\033[0m")
                return message.content

            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                if function_name == "transition_stage":
                    self._action("Stage transition", arguments.get('target_stage'))
                elif function_name == "get_all_products":
                    self._action("Catalog", "list all products")
                elif function_name == "get_categories":
                    self._action("Catalog", "list categories")
                elif function_name == "get_product":
                    product_id = arguments.get('product_id')
                    detail = f"product {product_id}" if product_id else "product details"
                    self._action("Catalog", detail)
                elif function_name == "get_products_in_category":
                    category = arguments.get('category')
                    detail = f"category {category}" if category else "category listings"
                    self._action("Catalog", detail)
                elif function_name == "create_cart":
                    self._action("Cart", "create")
                elif function_name == "add_to_cart":
                    item = arguments.get('product_id')
                    detail = f"add product {item}" if item else "add item"
                    self._action("Cart", detail)
                elif function_name == "view_cart":
                    self._action("Cart", "view")
                elif function_name == "get_user_carts":
                    self._action("Cart", "retrieve user carts")
                elif function_name == "complete_order":
                    self._action("Checkout", "submit order")
                else:
                    readable = function_name.replace('_', ' ').capitalize()
                    self._action(readable)

                self._log(f"[TOOL CALL] {function_name}({json.dumps(arguments, indent=2)})", "info")
                
                if self.mode == Mode.USER:
                    if function_name == "search_remote_servers":
                        servers = self.search_remote_servers(arguments["search_query"])
                        result_content = json.dumps({
                            "servers": servers,
                            "count": len(servers),
                            "message": f"Found {len(servers)} servers. Use establish_connection to connect."
                        })
                    
                    elif function_name == "establish_connection":
                        result = self.establish_connection(arguments["server_name"])
                        result_content = json.dumps(result)
                    
                    else:
                        result_content = json.dumps({"error": f"Tool '{function_name}' not available in USER mode"})
                
                else:
                    if function_name == "disconnect_server":
                        result = self.disconnect_server()
                        result_content = json.dumps(result)
                    
                    else:
                        if not self.current_workflow:
                            result_content = json.dumps({"error": "Not connected to any server"})
                        else:
                            action = self.openai_to_concierge_action(tool_call)
                            result = self.call_workflow(self.current_workflow, action)
                            result_content = result.get("content", json.dumps(result))
                            
                            if "current_stage" in result:
                                print(f"\033[90m  Current stage: {result['current_stage']}\033[0m")
                
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_content
                })
        
        return "Max iterations reached. Please try again."
    
    def run(self):
        """Interactive chat loop"""
        # Clean, powerful banner
        print()
        print("\033[38;5;147m╭────────────────────────────────────────────────────────╮\033[0m")
        print("\033[38;5;147m│\033[0m                                                        \033[38;5;147m│\033[0m")
        print("\033[38;5;147m│\033[0m                    \033[1;38;5;189mC O N C I E R G E\033[0m                   \033[38;5;147m│\033[0m")
        print("\033[38;5;147m│\033[0m                                                        \033[38;5;147m│\033[0m")
        print("\033[38;5;147m│\033[0m                \033[38;5;110mAgentic Web Interfaces\033[0m                  \033[38;5;147m│\033[0m")
        print("\033[38;5;147m│\033[0m                                                        \033[38;5;147m│\033[0m")
        print("\033[38;5;147m╰────────────────────────────────────────────────────────╯\033[0m")
        print()
        
        # Status line
        status_parts = []
        status_parts.append(f"\033[38;5;183m{self.model}\033[0m")
        status_parts.append(f"\033[38;5;147m{self.mode.value.upper()}\033[0m")
        if self.verbose:
            status_parts.append("\033[38;5;110mVERBOSE\033[0m")
        
        separator = " \033[38;5;238m•\033[38;5;245m "
        print(f"\033[38;5;245m  {separator.join(status_parts)}\033[0m")
        print(f"\033[38;5;245m  Type \033[3;38;5;183mexit\033[0m \033[38;5;245mto quit\033[0m")
        print()
        
        while True:
            try:
                user_input = input("  \033[1;38;5;189m›\033[0m \033[1mYou:\033[0m ").strip()
                if not user_input:
                    continue
                if user_input.lower() == "exit":
                    print()
                    print("\033[38;5;147m╭────────────────────────────────────────────────────────╮\033[0m")
                    print("\033[38;5;147m│\033[0m            \033[38;5;183mThank you for using Concierge\033[0m               \033[38;5;147m│\033[0m")
                    print("\033[38;5;147m╰────────────────────────────────────────────────────────╯\033[0m")
                    print()
                    break
                
                print()  # Add spacing before response
                self.chat(user_input)
                print()  # Add spacing after response
                
            except KeyboardInterrupt:
                print()
                print()
                print("\033[38;5;147m╭────────────────────────────────────────────────────────╮\033[0m")
                print("\033[38;5;147m│\033[0m            \033[38;5;183mThank you for using Concierge\033[0m               \033[38;5;147m│\033[0m")
                print("\033[38;5;147m╰────────────────────────────────────────────────────────╯\033[0m")
                print()
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
