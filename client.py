import asyncio
import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("Error: GOOGLE_API_KEY not found in .env file.")
    sys.exit(1)

# Path to the Python executable and server script
# We rely on the relative path to server.py in the current directory
SERVER_SCRIPT = os.path.join(os.getcwd(), "server.py")
PYTHON_EXE = sys.executable # Will use the python running this script

async def run_chat_loop():
    # Define server parameters
    server_params = StdioServerParameters(
        command=PYTHON_EXE,
        args=[SERVER_SCRIPT],
        env=None # Inherit env
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize connection
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print(f"Connected to MCP Server. Found {len(tools.tools)} tools.")
            
            # Initialize Gemini Client
            client = genai.Client(api_key=API_KEY)
            
            # Adapt MCP tools to Gemini format
            # straightforward mapping as google-genai supports function calling
            # We need to manually construct the tool definitions for Gemini
            # Or use a helper if available. For this POC, we'll map them manually or use the client's expectation.
            # Actually, google-genai might not natively consume MCP tool objects directly yet.
            # We need to construct `types.Tool` from `tools.tools`.
            
            # Construct tool definitions for Gemini
            function_declarations = []
            for tool in tools.tools:
                function_declarations.append(
                    types.FunctionDeclaration(
                        name=tool.name,
                        description=tool.description,
                        parameters=tool.inputSchema
                    )
                )
            
            gemini_tools = [types.Tool(function_declarations=function_declarations)]

            # System Instruction
            sys_instruct = """You are a Forensics Analyst for a Social Media Platform.
            Your job is to detect and investigate suspicious "bot attacks" on videos.
            
            Process:
            1. When given a Video ID, use `get_video_stats` to verify it exists and see total likes.
            2. To check for bots, you often need to look at specific hourly spikes. 
               The user might tell you a specific time, or you might need to ask. 
            3. Use `analyze_hourly_spike(video_id, target_hour)` to see if an hour has > 2x the likes of its neighbors.
            4. If a spike is detected, use `fetch_suspicious_users(video_id, target_hour)` to inspect the users.
            5. Report the findings:
               - Is there a spike?
               - What percentage of users in that spike look like bots (Fresh or Sleeper)?
               - Give a final verdict: "Attack Detected" or "Organic Activity".
               
            Target Hour Format is 'YYYY-MM-DD HH'. (e.g. 2025-12-05 14)
            """

            chat = client.chats.create(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruct,
                    tools=gemini_tools,
                    temperature=0
                )
            )

            print("Try: 'Investigate video 20 for suspicious activity yesterday at 14:00'")

            def send_message_with_retry(chat, content):
                """Sends a message with retry logic for 429 Resource Exhausted errors."""
                import time
                max_retries = 5
                base_delay = 10
                
                for attempt in range(max_retries):
                    try:
                        return chat.send_message(content)
                    except Exception as e:
                        if "429" in str(e):
                            wait_time = base_delay * (attempt + 1)
                            print(f"\n[Rate Limit] Hit 429 Quota Limit. Waiting {wait_time}s before retry ({attempt+1}/{max_retries})...")
                            time.sleep(wait_time)
                        else:
                            raise e
                raise Exception("Max retries exceeded for 429 error.")

            while True:
                user_input = input("\nUser: ")
                if user_input.lower() in ["exit", "quit"]:
                    break
                
                # Send message to Gemini
                try:
                    response = send_message_with_retry(chat, user_input)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    print(f"Error sending message: {e}")
                    continue
                
                # Handle tool calls loop
                while True:
                     # Check if there are function calls
                    try:
                        part = response.candidates[0].content.parts[0]
                    except IndexError:
                        print("No content in response.")
                        break
                        
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        tool_name = fc.name
                        tool_args = fc.args
                        
                        print(f"  [Agent calls tool: {tool_name}]")
                        
                        # Execute tool via MCP
                        try:
                            # MCP call_tool expects dictionary args
                            result = await session.call_tool(tool_name, arguments=tool_args)
                            
                            # Result is a CallToolResult, usually has content list (TextContent or ImageContent)
                            # We extract text
                            tool_output = ""
                            if result.content:
                                for content in result.content:
                                    if hasattr(content, "text"):
                                        tool_output += content.text
                                    else:
                                        tool_output += str(content)
                            else:
                                tool_output = "No output."
                                
                        except Exception as e:
                            tool_output = f"Error executing tool: {e}"
                        
                        # Send result back to Gemini
                        print("  [Rate Limit] Pausing 2s to respect free tier quotas...")
                        import time
                        time.sleep(2) 
                        
                        response = send_message_with_retry(
                            chat,
                            types.Part.from_function_response(
                                name=tool_name,
                                response={"result": tool_output}
                            )
                        )
                    else:
                        # No more function calls, print the text response
                        print(f"Agent: {response.text}")
                        break

if __name__ == "__main__":
    # Ensure checking/installing deps is done or we run in venv
    try:
        asyncio.run(run_chat_loop())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception:
        import traceback
        with open("crash.log", "w") as f:
            traceback.print_exc(file=f)
        traceback.print_exc()
