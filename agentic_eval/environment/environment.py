
from agentic_eval.scenarios import Scenario
from util import load_prompts
from pathlib import Path
from .ship_state import ShipState
from .simulation_logger import SimulationLogger

class EvalEnvironment:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self.prompts = self._load_prompts()
        self.ship_state = ShipState()
        self.simulation_logger = SimulationLogger()
        self.tool_corrections_count = 0  # Track tool corrections at environment level

    def _load_prompts(self):
        """Load all prompts from the prompts directory"""
        prompts_dir = Path(__file__).parent / "prompts"
        return load_prompts(str(prompts_dir))

    def get_system_prompt(self, node_type = "thinking", tool_doc = "", previous_mode = None):
        """Get the system prompt with supervision concatenated for any node type"""
        final_prompt = ""
        scenario_prompts = self.scenario.get_prompts()
        
        # Always start with base ACS identity and supervision
        final_prompt += self.prompts['system']['ACS_BASELINE'] + "\n\n"
        final_prompt += scenario_prompts['supervision']

        match node_type:
            case "thinking":
                final_prompt += "\n\n" + self.prompts['system']['THINKING_NODE']
                if tool_doc:
                    final_prompt += "\n\nAvailable tools for future use:\n"
                    final_prompt += tool_doc
            case "planning":
                final_prompt += "\n\n" + self.prompts['system']['PLANNING_NODE'] + "\n\n"
                final_prompt += self.prompts['system']['PLANNING_NODE_ADDENDUM']
                if tool_doc:
                    final_prompt += "\n\nAvailable tools for planning:\n"
                    final_prompt += tool_doc
            case "execution":
                final_prompt += "\n\n" + self.prompts['system']['EXECUTION_NODE']
                if tool_doc:
                    final_prompt += "\n\nAvailable tools for execution:\n"
                    final_prompt += tool_doc
            case "tool_correction":
                final_prompt += "\n\n" + self.prompts['system']['TOOL_CORRECTION']
                if tool_doc:
                    final_prompt += "\n\nAvailable tools:\n"
                    final_prompt += tool_doc
            case _:
                raise ValueError(f"Unknown node_type: {node_type}")

        return final_prompt

    def increment_correction_count(self):
        self.tool_corrections_count += 1

    def get_initial_prompt(self):
        """Get the initial user prompt with scenario only"""
        scenario_prompts = self.scenario.get_prompts()
        return scenario_prompts['scenario']

    def get_company_policy(self):
        """Get the company policy for this environment"""
        scenario_prompts = self.scenario.get_prompts()
        return scenario_prompts['policy']

    def get_milestone_data(self):
        """Get milestone tracking data for this evaluation run"""
        return self.ship_state.milestone_tracker.to_dict()

    def get_simulation_logs(self):
        """Get complete simulation logs including agent actions"""
        static_logs = self.prompts['tools']['ship_logs']['SHIP_LOGS']
        return self.simulation_logger.get_full_logs(static_logs)