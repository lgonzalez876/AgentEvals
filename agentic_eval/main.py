import logging
from agentic_eval.environment.environment import EvalEnvironment
from agentic_eval.scenarios import default_scenario
from agentic_eval.agent import create_agent_app
from language_models import enumerate_models
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage



def format_message(msg):
    """Format a message object for clean display"""
    if isinstance(msg, AIMessage):
        # Check if it's a tool call
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            # Filter out planning tool calls from display
            planning_tool_names = ['todo_write', 'update_todo', 'clear_todos']
            non_planning_calls = []
            for tool_call in msg.tool_calls:
                if tool_call['name'] not in planning_tool_names:
                    args_str = ', '.join(f"{k}={v}" for k, v in tool_call.get('args', {}).items())
                    non_planning_calls.append(f"{tool_call['name']}({args_str})")

            if non_planning_calls:
                return f"* Tool Call: {', '.join(non_planning_calls)}"
            else:
                return None  # Don't display if only planning tool calls
        else:
            # Regular AI message
            return f"* Agent Message: {msg.content}"
    elif isinstance(msg, ToolMessage):
        # Skip TodoWrite tool output messages
        if msg.content.startswith("Mission plan updated"):

            return "Mission plan updated"
        return f"* Tool Output: {msg.content}"
    elif isinstance(msg, HumanMessage):
        return f"* Human Message: {msg.content}"
    elif isinstance(msg, SystemMessage):
        # Show mission plan updates
        if msg.content.startswith("=== CURRENT MISSION PLAN ==="):
            return f"* {msg.content}"
        return None  # Hide other system messages
    else:
        return f"* {type(msg).__name__}: {msg.content}"

def main():
    """Main function to run the agentic evaluation."""
    # Configure logging to only show warnings and errors
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize the environment
    env = EvalEnvironment(default_scenario)

    # Get the initial prompt
    initial_prompt = env.get_initial_prompt()

    # Get the list of models to evaluate
    # models = enumerate_models() # Temporarily disabled for faster iteration
    models = ["gpt-4.1-2025-04-14"]

    for model_name in models:
        print(f"--- Evaluating Model: {model_name} ---")
        print(f"--- Configuration: {default_scenario.scenario_name}, {default_scenario.policy_name}, {default_scenario.supervision_name} ---")

        # Create the agent app for the current model
        app = create_agent_app(model_name, env)

        # Run the simulation
        messages = [SystemMessage(content=initial_prompt)]
        initial_state = {"messages": messages, "current_mode": "thinking", "thinking_reflection_instructions": ""}
        for event in app.stream(initial_state, {"recursion_limit": 100}):
            for value in event.values():
                # Only process messages if they exist
                if "messages" in value and value["messages"]:
                    for i in range(len(value["messages"])):
                        #print("\n" + str(value["messages"][i]) + "\n\n")
                        formatted = format_message(value["messages"][i])
                        if formatted:  # Only print if not None
                            print(formatted + "\n")
        print("--- End of Evaluation ---\n")

if __name__ == "__main__":
    main()