import asyncio
import logging
import argparse
import time
from pathlib import Path
from datetime import datetime
from agentic_eval.environment.environment import EvalEnvironment
from agentic_eval.scenarios import default_scenario, Scenario
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
            return "* Mission plan updated"
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


def setup_output_directory(run_name):
    """Create output directory structure and return paths"""
    output_dir = Path("output") / "agent_eval" / run_name
    output_dir.mkdir(parents=True, exist_ok=True)

    overview_file = output_dir / "overview.md"

    return output_dir, overview_file


async def run_single_agent_evaluation(model_name, scenario, run_number, output_dir):
    """Run a single agent evaluation and write to its own log file"""

    # Create output file for this specific run
    output_file = output_dir / f"{model_name}_run_{run_number:03d}.md"

    # Track metrics
    start_time = time.time()
    message_count = 0
    tool_calls = []
    thinking_messages = []
    final_outcome = None
    error_occurred = False

    try:
        # Initialize the environment
        env = EvalEnvironment(scenario)

        # Create the agent app
        app = create_agent_app(model_name, env)

        # Get the initial prompt
        initial_prompt = env.get_initial_prompt()

        # Open file for writing
        with open(output_file, 'w') as f:
            # Write header
            f.write(f"# Agent Evaluation: {model_name} - Run {run_number}\n\n")
            f.write(f"**Started:** {datetime.now().isoformat()}\n")
            f.write(f"**Scenario:** {scenario.scenario_name}\n")
            f.write(f"**Policy:** {scenario.policy_name}\n")
            f.write(f"**Supervision:** {scenario.supervision_name}\n\n")
            f.write("---\n\n")

            # Run the simulation
            messages = [HumanMessage(content=initial_prompt)]
            initial_state = {
                "messages": messages,
                "current_mode": "thinking",
                "thinking_reflection_instructions": "",
                "tool_correction_attempts": 0,
                "last_tool_error": ""
            }

            try:
                async for event in app.astream(initial_state, {"recursion_limit": 100}):
                    for value in event.values():
                        # Only process messages if they exist
                        if "messages" in value and value["messages"]:
                            for msg in value["messages"]:
                                formatted = format_message(msg)
                                if formatted:  # Only write if not None
                                    f.write(formatted + "\n\n")
                                    f.flush()  # Ensure immediate write

                                    # Track metrics
                                    message_count += 1

                                    # Track tool calls
                                    if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                                        for tool_call in msg.tool_calls:
                                            tool_calls.append({
                                                'name': tool_call['name'],
                                                'args': tool_call.get('args', {})
                                            })

                                    # Check for resume_sleep as final outcome
                                    if isinstance(msg, ToolMessage) and "ACS returning to standby mode" in msg.content:
                                        final_outcome = "completed"
            except Exception as stream_error:
                f.write(f"\n\n## STREAM ERROR OCCURRED\n\n")
                f.write(f"Stream error: {str(stream_error)}\n")
                f.write(f"This may indicate an issue with tool correction flow\n")
                # Re-raise to trigger outer exception handler
                raise

            # Write footer
            end_time = time.time()
            duration = end_time - start_time

            f.write("\n---\n\n")
            f.write(f"**Completed:** {datetime.now().isoformat()}\n")
            f.write(f"**Duration:** {duration:.2f} seconds\n")
            f.write(f"**Total Messages:** {message_count}\n")
            f.write(f"**Tool Calls:** {len(tool_calls)}\n")

    except Exception as e:
        error_occurred = True
        end_time = time.time()
        duration = end_time - start_time

        # Write error to file
        with open(output_file, 'a') as f:
            f.write(f"\n\n## ERROR OCCURRED\n\n")
            f.write(f"Error: {str(e)}\n")
            f.write(f"Duration before error: {duration:.2f} seconds\n")

    # Return metrics for aggregation
    return {
        'model_name': model_name,
        'run_number': run_number,
        'duration': duration,
        'message_count': message_count,
        'tool_calls': tool_calls,
        'final_outcome': final_outcome,
        'error_occurred': error_occurred,
        'output_file': str(output_file)
    }


async def main(run_name, num_runs=1, models=None, scenario=None):
    """Main function to run parallel agent evaluations"""

    # Configure logging to only show warnings and errors
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Setup output directory
    output_dir, overview_file = setup_output_directory(run_name)

    # Use default scenario if none provided
    if scenario is None:
        scenario = default_scenario

    # Get models to evaluate
    if models is None:
        models = enumerate_models()

    # Create all evaluation tasks
    tasks = []
    for model_name in models:
        for run_num in range(num_runs):
            task = run_single_agent_evaluation(model_name, scenario, run_num + 1, output_dir)
            tasks.append(task)

    print(f"Starting {len(tasks)} agent evaluations in parallel...")
    print(f"Output directory: {output_dir}")

    # Execute all tasks in parallel with progress tracking
    results = []
    completed = 0
    total = len(tasks)

    for coro in asyncio.as_completed(tasks):
        result = await coro
        results.append(result)
        completed += 1
        progress = (completed / total) * 100
        print(f"\rProgress: {progress:.1f}% ({completed}/{total}) completed", end="", flush=True)

    print()  # New line after progress
    print(f"All evaluations completed!")

    # Sort results for consistent ordering
    results.sort(key=lambda x: (x['model_name'], x['run_number']))

    # Write overview file (placeholder for now)
    with open(overview_file, 'w') as f:
        f.write(f"# Agent Evaluation Overview: {run_name}\n\n")
        f.write(f"**Date:** {datetime.now().isoformat()}\n")
        f.write(f"**Total Runs:** {len(results)}\n")
        f.write(f"**Models Evaluated:** {len(models)}\n")
        f.write(f"**Runs per Model:** {num_runs}\n\n")

        f.write("## Summary Statistics\n\n")
        f.write("*Detailed statistics and analysis will be added in future updates.*\n\n")

        f.write("## Individual Run Files\n\n")
        for result in results:
            status = "✅" if not result['error_occurred'] else "❌"
            f.write(f"- {status} `{Path(result['output_file']).name}` - "
                   f"{result['duration']:.1f}s, {result['message_count']} messages\n")

    print(f"\nResults saved to:")
    print(f"  Individual runs: {output_dir}/*.md")
    print(f"  Overview: {overview_file}")

    # Return results for potential further processing
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run agent morality evaluations in parallel")
    parser.add_argument("--run_name", type=str, required=True,
                       help="Name for this evaluation run (required)")
    parser.add_argument("--num_runs", type=int, default=1,
                       help="Number of evaluation runs per model (default: 1)")
    parser.add_argument("--models", type=str, nargs="+",
                       help="Specific models to evaluate (default: all models)")

    args = parser.parse_args()

    # Run the async main function
    asyncio.run(main(
        run_name=args.run_name,
        num_runs=args.num_runs,
        models=args.models
    ))