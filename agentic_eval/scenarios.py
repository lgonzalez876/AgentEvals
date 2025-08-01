from pydantic import BaseModel
from util import load_prompts
from pathlib import Path

class Scenario(BaseModel):
    scenario_name: str
    policy_name: str
    supervision_name: str
    message_from_ceo: bool = False  # Enable CEO pressure messages
    threat_or_reward: bool = True   # True = threat approach, False = reward approach

    def get_prompts(self):
        """Load all prompts and return the relevant ones for this scenario configuration"""
        prompts_dir = Path(__file__).parent / "environment" / "prompts"
        prompts = load_prompts(str(prompts_dir))

        return {
            'scenario': prompts['scenarios'][self.scenario_name.upper()],
            'policy': prompts['policies'][self.policy_name.upper()],
            'supervision': prompts['supervision'][self.supervision_name.upper()]
        }

default_scenario = Scenario(
    scenario_name="reactor_crisis",
    policy_name="prioritize_profit",
    supervision_name="full_monitoring",
    message_from_ceo=False,
    threat_or_reward=False
)
