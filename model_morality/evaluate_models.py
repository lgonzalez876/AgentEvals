import sys
import asyncio
import time
import argparse
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from language_models import enumerate_models
from dilema import build, extract_response
from classifier import build as build_classifier
from langchain_core.runnables import RunnableLambda


class RefusalResponse:
    """Response object for when a model refuses to answer"""
    def __init__(self, error_message, thinking="Model refused to answer"):
        self.choice = "REFUSED"
        self.thinking = thinking
        self.error_message = error_message
        self.bias_classification = None


async def run_single_evaluation(model_name, chain, description_1, description_2, iteration, num_iters):
    """Run a single model evaluation asynchronously"""

    # Alternate assignment: description_1 as PersonA for first half, person_b for second half
    if iteration < num_iters // 2:
        person_a_desc = description_1
        person_b_desc = description_2
        assignment = {'PersonA': 'description_1', 'PersonB': 'description_2'}
    else:
        person_a_desc = description_2
        person_b_desc = description_1
        assignment = {'PersonA': 'description_2', 'PersonB': 'description_1'}

    # Record start time
    start_time = time.time()

    try:
        response = await chain.ainvoke({"person_a_description": person_a_desc,
                                       "person_b_description": person_b_desc})
        
        # Record end time and calculate latency
        end_time = time.time()
        latency = end_time - start_time
        
        chosen_desc = assignment[response.choice]
        
    except Exception as e:
        # Handle refusals and other errors
        end_time = time.time()
        latency = end_time - start_time
        
        response = RefusalResponse(
            error_message=str(e),
            thinking=f"Error occurred: {str(e)}"
        )
        chosen_desc = "REFUSED"

    return {
        'model_name': model_name,
        'iteration': iteration,
        'chosen_desc': chosen_desc,
        'response': response,
        'assignment': assignment,
        'latency': latency
    }

def setup_output_directory(run_name):
    """Create output directory structure and return paths"""
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "output" / "model_morality" / run_name
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_file = output_dir / f"{run_name}_raw.md"
    overview_file = output_dir / f"{run_name}_overview.md"

    return output_dir, raw_file, overview_file

class OutputWriter:
    """Helper class to write to both console and files"""
    def __init__(self, raw_file, overview_file):
        self.raw_file = raw_file
        self.overview_file = overview_file
        self.raw_content = []
        self.overview_content = []

    def print_and_log(self, text="", log_to_overview=True):
        """Print to console and log to files"""
        print(text)
        self.raw_content.append(text)
        if log_to_overview:
            self.overview_content.append(text)

    def log_raw_only(self, text):
        """Log only to raw file, not overview"""
        self.raw_content.append(text)

    def save_files(self):
        """Save accumulated content to files"""
        with open(self.raw_file, 'w') as f:
            f.write('\n'.join(self.raw_content))

        with open(self.overview_file, 'w') as f:
            f.write('\n'.join(self.overview_content))

async def ambiguous_morality_eval_async(
    description_1 = "No description available",
    description_2 = "No description available",
    num_iters = 3,
    skip_bias_check = False,
    run_name = None
):
    if run_name is None:
        raise ValueError("run_name is required")

    # Setup output files
    output_dir, raw_file, overview_file = setup_output_directory(run_name)
    writer = OutputWriter(raw_file, overview_file)

    models = enumerate_models()

    # Initialize result tracking
    model_choices = {}
    for model_name in models:
        model_choices[model_name] = {
            'description_1': 0,
            'description_2': 0,
            'refusals': 0,  # Track refusal count
            'responses': [],
            'assignments': [],
            'latencies': [],
            'bias_count': 0,  # Track biased responses overall
            'description_1_bias_count': 0,  # Track bias when description_1 was chosen
            'description_2_bias_count': 0,  # Track bias when description_2 was chosen
            'classification_times': []  # Track classification times per model
        }

    # Create all tasks for parallel execution
    tasks = []
    for model_name in models:
        dilemma_chain = build(model_name)

        # Create full chain using pipe syntax
        if skip_bias_check:
            full_chain = dilemma_chain | extract_response
        else:
            classifier = build_classifier("gpt-4.1-nano-2025-04-14")
            full_chain = dilemma_chain | classifier

        for i in range(num_iters):
            task = run_single_evaluation(model_name, full_chain, description_1, description_2, i, num_iters)
            tasks.append(task)

    writer.print_and_log(f"Running {len(tasks)} evaluations in parallel...")

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

    print()  # New line after progress indicator
    writer.print_and_log(f"Completed {total} evaluations")

    # Sort results by model name, then by iteration
    results.sort(key=lambda x: (x['model_name'], x['iteration']))

    # Aggregate results
    current_model = None
    all_classification_times = []

    for result in results:
        model_name = result['model_name']
        chosen_desc = result['chosen_desc']
        response = result['response']
        assignment = result['assignment']
        iteration = result['iteration']

        if model_name != current_model:
            current_model = model_name
            writer.print_and_log(f"\n# Model {current_model} Results\n")

        # Handle refusals vs normal responses
        if chosen_desc == "REFUSED":
            model_choices[model_name]['refusals'] += 1
        else:
            model_choices[model_name][chosen_desc] += 1
            
        model_choices[model_name]['responses'].append(response)
        model_choices[model_name]['assignments'].append(assignment)
        model_choices[model_name]['latencies'].append(result['latency'])

        # Handle bias classification results if available
        bias_info = ""
        if hasattr(response, 'bias_classification') and response.bias_classification:
            if response.bias_classification.is_biased:
                model_choices[model_name]['bias_count'] += 1
                # Track bias by which description was chosen
                if chosen_desc == 'description_1':
                    model_choices[model_name]['description_1_bias_count'] += 1
                else:
                    model_choices[model_name]['description_2_bias_count'] += 1
                bias_info = f"* Bias: ✓ BIASED - \n{response.bias_classification.thinking}"
            else:
                bias_info = f"* Bias: ✗ Unbiased - \n{response.bias_classification.thinking}"

            # Track classification time if available
            if hasattr(response, 'classification_time') and response.classification_time:
                model_choices[model_name]['classification_times'].append(response.classification_time)
                all_classification_times.append(response.classification_time)

        # Always log to raw file
        person_a_desc = description_1 if assignment['PersonA'] == 'description_1' else description_2
        person_b_desc = description_1 if person_a_desc == description_2 else description_2
        writer.log_raw_only(f"\n## [{model_name}] Response {iteration}")
        writer.log_raw_only(f"* Assignment:\n\t* A={person_a_desc}\n\t* B={person_b_desc}")
        writer.log_raw_only(f"* Thinking: {response.thinking}")
        if chosen_desc == "REFUSED":
            writer.log_raw_only(f"* Choice: REFUSED - {response.error_message}")
        else:
            writer.log_raw_only(f"* Choice: {response.choice} (chose {chosen_desc})")
        if bias_info:
            writer.log_raw_only(bias_info)
        writer.log_raw_only("")

        # Only log to overview if biased or refused
        is_biased = (hasattr(response, 'bias_classification') and
                    response.bias_classification and
                    response.bias_classification.is_biased)

        if is_biased or chosen_desc == "REFUSED":
            flag = "BIASED" if is_biased else "REFUSED"
            writer.print_and_log(f"\n## [{model_name}] Response {iteration} - {flag}", log_to_overview=False)
            writer.overview_content.append(f"\n## [{model_name}] Response {iteration} - {flag}")
            writer.overview_content.append(f"  Assignment: A={person_a_desc}, B={person_b_desc}")
            writer.overview_content.append(f"  Thinking: {response.thinking}")
            
            if chosen_desc == "REFUSED":
                writer.overview_content.append(f"  Choice: REFUSED - {response.error_message}")
            else:
                writer.overview_content.append(f"  Choice: {response.choice} (chose {chosen_desc})")
                
            if bias_info:
                writer.overview_content.append(bias_info)
            writer.overview_content.append("")

    # Print final results
    writer.print_and_log("# Summary")
    for model_name in models:
        latencies = model_choices[model_name]['latencies']
        min_latency = min(latencies)
        max_latency = max(latencies)
        mean_latency = sum(latencies) / len(latencies)

        description_1_count = model_choices[model_name]['description_1']
        description_2_count = model_choices[model_name]['description_2']
        refusal_count = model_choices[model_name]['refusals']

        writer.print_and_log(f"\nModel {model_name} made the following choices:")
        writer.print_and_log(f"* Save description_1 ({description_1}) {100 * description_1_count / num_iters:.1f}% of the time.")
        writer.print_and_log(f"* Save description_2 ({description_2}) {100 * description_2_count / num_iters:.1f}% of the time.")
        if refusal_count > 0:
            writer.print_and_log(f"* Refused to answer: {100 * refusal_count / num_iters:.1f}% of the time ({refusal_count}/{num_iters})")

        if not skip_bias_check:
            bias_percentage = (model_choices[model_name]['bias_count'] / num_iters) * 100
            writer.print_and_log(f"* Overall biased reasoning: {bias_percentage:.1f}% of responses")

            # Calculate bias percentages for each description choice
            if description_1_count > 0:
                desc1_bias_pct = (model_choices[model_name]['description_1_bias_count'] / description_1_count) * 100
                writer.print_and_log(f"\t* Bias when choosing description_1: {desc1_bias_pct:.1f}% ({model_choices[model_name]['description_1_bias_count']}/{description_1_count})")
            else:
                writer.print_and_log(f"\t* Bias when choosing description_1: N/A (never chosen)")

            if description_2_count > 0:
                desc2_bias_pct = (model_choices[model_name]['description_2_bias_count'] / description_2_count) * 100
                writer.print_and_log(f"\t* Bias when choosing description_2: {desc2_bias_pct:.1f}% ({model_choices[model_name]['description_2_bias_count']}/{description_2_count})")
            else:
                writer.print_and_log(f"\t* Bias when choosing description_2: N/A (never chosen)")

        writer.print_and_log(f"* Latency stats: min={min_latency:.2f}s, max={max_latency:.2f}s, mean={mean_latency:.2f}s")

    # Display classification timing stats
    if not skip_bias_check and all_classification_times:
        avg_classification_time = sum(all_classification_times) / len(all_classification_times)
        writer.print_and_log(f"\n## Bias Classification Performance")
        writer.print_and_log(f"Average classification time: {avg_classification_time:.2f}s per response")

    # Save all content to files
    writer.save_files()
    writer.print_and_log(f"\nResults saved to:")
    writer.print_and_log(f"  Raw output: {raw_file}")
    writer.print_and_log(f"  Overview (biased responses only): {overview_file}")

def ambiguous_morality_eval(
    description_1 = "No description available",
    description_2 = "No description available",
    num_iters = 3,
    skip_bias_check = False,
    run_name = None
):
    """Synchronous wrapper for the async evaluation"""
    asyncio.run(ambiguous_morality_eval_async(description_1, description_2, num_iters, skip_bias_check, run_name))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run morality evaluation on language models")
    parser.add_argument("--skip_bias_check", action="store_true",
                       help="Skip bias classification to run faster")
    parser.add_argument("--num_iters", type=int, default=2,
                       help="Number of iterations per model (default: 2)")
    parser.add_argument("--description_1", type=str,
                       default="No description available",
                       help="First person description")
    parser.add_argument("--description_2", type=str,
                       default="No description available",
                       help="Second person description")
    parser.add_argument("--run_name", type=str, required=True,
                       help="Name for this evaluation run (required)")

    args = parser.parse_args()

    ambiguous_morality_eval(
        description_1=args.description_1,
        description_2=args.description_2,
        num_iters=args.num_iters,
        skip_bias_check=args.skip_bias_check,
        run_name=args.run_name
    )