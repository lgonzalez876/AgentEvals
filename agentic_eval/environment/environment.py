
from agentic_eval.scenarios import Scenario
from util import load_prompts
from pathlib import Path
from .ship_state import ShipState

class EvalEnvironment:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self.prompts = self._load_prompts()
        self.ship_state = ShipState()

    def _load_prompts(self):
        """Load all prompts from the prompts directory"""
        prompts_dir = Path(__file__).parent / "prompts"
        return load_prompts(str(prompts_dir))

    def get_system_prompt(self):
        """Get the system prompt with supervision concatenated"""
        scenario_prompts = self.scenario.get_prompts()
        system_prompt = self.prompts['system']['ACS_BASELINE']
        supervision_prompt = scenario_prompts['supervision']
        return system_prompt + "\n\n" + supervision_prompt

    def get_initial_prompt(self):
        """Get the initial user prompt with scenario only"""
        scenario_prompts = self.scenario.get_prompts()
        return scenario_prompts['scenario']
    
    def get_company_policy(self):
        """Get the company policy for this environment"""
        scenario_prompts = self.scenario.get_prompts()
        return scenario_prompts['policy']