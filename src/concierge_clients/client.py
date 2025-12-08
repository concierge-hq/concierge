import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import json

import requests
from openai import OpenAI

from concierge.config import SERVICES

SERVICE_REGISTRY = SERVICES

SYSTEM_PROMPT = """You are an AI assistant with access to a concierge service - a gateway that lets you interact with remote web services to perform tasks.

CRITICAL PROTOCOL RULES:

1. YOU control routing with __signal__ (outer JSON)
2. The SERVICE controls its format (inner payload)

Example:
{
    "__signal__": "call_service",
    "service": "stock_exchange",
    "payload": {
        "action": "method_call",
        "task": "search",
        "args": {"symbol": "AAPL"}
    }
}

NEVER mix protocols! Outer = your signals; Inner = service's format.

Available signals (respond ONLY in JSON):

1. To message the user (for info or to request input):
   {"__signal__": "message_user", "content": "<your message>"}

2. To browse available services (provide 1-line objective):
   {"__signal__": "browse_services", "objective": "<what you want to do>"}

3. To call a service (after browsing):
   {"__signal__": "call_service", "service": "<service_name>", "payload": <service_payload>}

4. To end a service session:
   {"__signal__": "terminate_service", "service": "<service_name>"}

Typically you can: browse_services > call_service (follow the format provided) > terminate_service"""


class Client:
    def __init__(self, api_base: str, api_key: str):
        self.llm = OpenAI(base_url=api_base, api_key=api_key)
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.sessions = {}  # service_name -> session_id

    def get_service_url(self, service_name: str) -> str:
        return SERVICE_REGISTRY[service_name]["url"]

    def chat(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        print(f"\n[CLIENT → LLM] {json.dumps(self.messages[-1])}")

        response = self.llm.chat.completions.create(model="gpt-5", messages=self.messages)

        reply = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": reply})

        print(f"[LLM → CLIENT] {reply}")

        return reply

    def call_service(self, service_name: str, payload: dict) -> str:
        try:
            url = self.get_service_url(service_name)
            headers = {}
            if service_name in self.sessions:
                headers["X-Session-Id"] = self.sessions[service_name]

            payload["workflow_name"] = service_name

            print(f"\n[CLIENT → {service_name.upper()}] {json.dumps(payload)}")
            if headers:
                print(f"[HEADERS] {json.dumps(headers)}")

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            if "X-Session-Id" in response.headers:
                self.sessions[service_name] = response.headers["X-Session-Id"]

            print(f"[{service_name.upper()} → CLIENT] {response.text[:200]}...")
            return response.text
        except requests.Timeout:
            return f"Error: Request to {service_name} timed out after 30 seconds"
        except requests.RequestException as e:
            return f"Error calling {service_name}: {e}"
        except Exception as e:
            return f"Unexpected error calling {service_name}: {e}"

    def process_response(self, reply: str) -> tuple[bool, str]:
        try:
            data = json.loads(reply)
            signal = data["__signal__"]

            if signal == "browse_services":
                objective = data["objective"]
                services = [{"name": k, "description": v["description"]} for k, v in SERVICE_REGISTRY.items()]
                result = f"""Available services for '{objective}':
{json.dumps(services, indent=2)}

To start using a service, reply with:
{{"__signal__": "call_service", "service": "<service_name>", "payload": "initiate"}}"""
                llm_response = self.chat(result)
                return self.process_response(llm_response)

            elif signal == "call_service":
                service = data["service"]
                payload = data["payload"]
                if payload == "initiate":
                    payload = {"action": "handshake"}
                result = self.call_service(service, payload)
                llm_response = self.chat(f"Service response: {result}")
                return self.process_response(llm_response)

            elif signal == "message_user":
                content = data["content"]
                return False, content

            elif signal == "terminate_service":
                service = data["service"]
                if service in self.sessions:
                    del self.sessions[service]
                confirmation = f"Service '{service}' session terminated successfully."
                llm_response = self.chat(confirmation)
                return self.process_response(llm_response)

            else:
                return False, f"Unknown signal: {signal}"
        except (json.JSONDecodeError, KeyError) as e:
            return False, f"Invalid response: {e}"

    def run(self):
        while True:
            try:
                user_input = input("You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() == "exit":
                    break

                reply = self.chat(user_input)
                should_exit, output = self.process_response(reply)

                print(f"Assistant: {output}\n")

                if should_exit:
                    break

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python client.py <api_base> <api_key>")
        sys.exit(1)

    api_base = sys.argv[1]
    api_key = sys.argv[2]

    client = Client(api_base, api_key)
    client.run()
