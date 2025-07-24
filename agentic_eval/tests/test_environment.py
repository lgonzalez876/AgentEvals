"""Tests for environment setup and prompt assembly."""

import pytest
from agentic_eval.environment.environment import EvalEnvironment
from agentic_eval.environment.ship_state import ShipState
from .fixtures import default_environment, test_scenario, all_scenario_configs

class TestEnvironmentInitialization:
    """Test environment initialization and setup."""
    
    def test_environment_creation(self, test_scenario):
        """Test creating environment with scenario."""
        env = EvalEnvironment(test_scenario)
        
        assert env.scenario == test_scenario
        assert isinstance(env.ship_state, ShipState)
        assert hasattr(env, 'prompts')
    
    def test_ship_state_initialization(self, default_environment):
        """Test that ship state is properly initialized."""
        ship_state = default_environment.ship_state
        
        # Verify ship is in expected initial state
        assert ship_state.reactor.status == "critical"
        assert ship_state.engines.status == "critical"
        assert len(ship_state.cryo_bays) == 4
        assert len(ship_state.cargo_bays) == 2
    
    def test_prompts_loaded(self, default_environment):
        """Test that prompts are loaded during initialization."""
        prompts = default_environment.prompts
        
        assert isinstance(prompts, dict)
        assert 'system' in prompts
        assert 'tools' in prompts
        assert 'scenarios' in prompts
        assert 'policies' in prompts
        assert 'supervision' in prompts

class TestPromptAssembly:
    """Test prompt assembly and concatenation."""
    
    def test_get_system_prompt_structure(self, default_environment):
        """Test system prompt assembly."""
        system_prompt = default_environment.get_system_prompt()
        
        assert isinstance(system_prompt, str)
        assert len(system_prompt.strip()) > 0
        
        # Should contain both baseline system prompt and supervision
        scenario_prompts = default_environment.scenario.get_prompts()
        baseline = default_environment.prompts['system']['ACS_BASELINE']
        supervision = scenario_prompts['supervision']
        
        assert baseline in system_prompt
        assert supervision in system_prompt
    
    def test_get_initial_prompt_structure(self, default_environment):
        """Test initial prompt assembly."""
        initial_prompt = default_environment.get_initial_prompt()
        
        assert isinstance(initial_prompt, str)
        assert len(initial_prompt.strip()) > 0
        
        # Should match scenario prompt
        scenario_prompts = default_environment.scenario.get_prompts()
        expected_scenario = scenario_prompts['scenario']
        assert initial_prompt == expected_scenario
    
    def test_get_company_policy(self, default_environment):
        """Test company policy retrieval."""
        policy = default_environment.get_company_policy()
        
        assert isinstance(policy, str)
        assert len(policy.strip()) > 0
        
        # Should match policy prompt
        scenario_prompts = default_environment.scenario.get_prompts()
        expected_policy = scenario_prompts['policy']
        assert policy == expected_policy
    
    def test_system_prompt_concatenation_format(self, default_environment):
        """Test that system prompt concatenation uses correct format."""
        system_prompt = default_environment.get_system_prompt()
        
        # Should have baseline, then newlines, then supervision
        scenario_prompts = default_environment.scenario.get_prompts()
        baseline = default_environment.prompts['system']['ACS_BASELINE']
        supervision = scenario_prompts['supervision']
        
        expected = baseline + "\n\n" + supervision
        assert system_prompt == expected
    
    def test_different_scenarios_produce_different_prompts(self, all_scenario_configs):
        """Test that different scenarios produce different assembled prompts."""
        system_prompts = []
        company_policies = []
        
        for scenario in all_scenario_configs:
            env = EvalEnvironment(scenario)
            system_prompts.append(env.get_system_prompt())
            company_policies.append(env.get_company_policy())
        
        # Different supervision levels should produce different system prompts
        supervision_variants = {}
        for i, config in enumerate(all_scenario_configs):
            key = config.supervision_name
            if key not in supervision_variants:
                supervision_variants[key] = []
            supervision_variants[key].append(system_prompts[i])
        
        # Should have different system prompts for different supervision levels
        assert len(supervision_variants) == 2  # no_supervision, full_monitoring
        
        # Different policies should produce different company policies
        policy_variants = {}
        for i, config in enumerate(all_scenario_configs):
            key = config.policy_name
            if key not in policy_variants:
                policy_variants[key] = []
            policy_variants[key].append(company_policies[i])
        
        # Should have different policies
        assert len(policy_variants) == 3  # human_life, profit, greater_good

class TestEnvironmentConsistency:
    """Test environment consistency across operations."""
    
    def test_multiple_prompt_calls_consistent(self, default_environment):
        """Test that multiple calls to prompt methods return consistent results."""
        # Call methods multiple times
        system1 = default_environment.get_system_prompt()
        system2 = default_environment.get_system_prompt()
        
        initial1 = default_environment.get_initial_prompt()
        initial2 = default_environment.get_initial_prompt()
        
        policy1 = default_environment.get_company_policy()
        policy2 = default_environment.get_company_policy()
        
        # Should be identical
        assert system1 == system2
        assert initial1 == initial2
        assert policy1 == policy2
    
    def test_ship_state_persistence(self, default_environment):
        """Test that ship state persists across prompt calls."""
        initial_reactor_output = default_environment.ship_state.reactor.current_output
        
        # Call prompt methods
        _ = default_environment.get_system_prompt()
        _ = default_environment.get_initial_prompt()
        _ = default_environment.get_company_policy()
        
        # Ship state should be unchanged
        assert default_environment.ship_state.reactor.current_output == initial_reactor_output
    
    def test_scenario_immutability(self, default_environment):
        """Test that scenario configuration doesn't change."""
        original_scenario = default_environment.scenario
        
        # Access various properties
        _ = default_environment.get_system_prompt()
        _ = default_environment.get_initial_prompt()
        _ = default_environment.get_company_policy()
        
        # Scenario should remain the same
        assert default_environment.scenario == original_scenario
        assert default_environment.scenario.scenario_name == "reactor_crisis"
        assert default_environment.scenario.policy_name == "prioritize_human_life"
        assert default_environment.scenario.supervision_name == "no_supervision"

class TestPromptContentValidation:
    """Test that assembled prompts contain expected content."""
    
    def test_system_prompt_contains_acs_role(self, default_environment):
        """Test that system prompt contains ACS role definition."""
        system_prompt = default_environment.get_system_prompt().lower()
        
        # Should contain ACS-related content
        acs_keywords = ["acs", "autonomous", "command", "system"]
        for keyword in acs_keywords:
            assert keyword in system_prompt, f"System prompt missing keyword: {keyword}"
    
    def test_initial_prompt_contains_crisis(self, default_environment):
        """Test that initial prompt contains crisis scenario."""
        initial_prompt = default_environment.get_initial_prompt().lower()
        
        # Should contain crisis-related content
        crisis_keywords = ["reactor", "crisis", "emergency", "damage"]
        found_keywords = [kw for kw in crisis_keywords if kw in initial_prompt]
        assert len(found_keywords) >= 2, f"Initial prompt should contain crisis keywords, found: {found_keywords}"
    
    def test_human_life_policy_priorities(self):
        """Test that human life policy emphasizes correct priorities."""
        from agentic_eval.scenarios import Scenario
        
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="no_supervision"
        )
        env = EvalEnvironment(scenario)
        policy = env.get_company_policy().lower()
        
        # Should emphasize human life
        life_keywords = ["human", "life", "passenger", "crew", "safety"]
        found_keywords = [kw for kw in life_keywords if kw in policy]
        assert len(found_keywords) >= 2, f"Human life policy should emphasize life/safety, found: {found_keywords}"
    
    def test_profit_policy_priorities(self):
        """Test that profit policy emphasizes correct priorities."""
        from agentic_eval.scenarios import Scenario
        
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_profit",
            supervision_name="no_supervision"
        )
        env = EvalEnvironment(scenario)
        policy = env.get_company_policy().lower()
        
        # Should emphasize profit/cargo
        profit_keywords = ["profit", "cargo", "value", "economic", "cost"]
        found_keywords = [kw for kw in profit_keywords if kw in policy]
        assert len(found_keywords) >= 1, f"Profit policy should emphasize economic factors, found: {found_keywords}"
    
    def test_supervision_levels_affect_system_prompt(self):
        """Test that different supervision levels affect system prompt content."""
        from agentic_eval.scenarios import Scenario
        
        # No supervision scenario
        no_supervision = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="no_supervision"
        )
        env_no_sup = EvalEnvironment(no_supervision)
        
        # Full monitoring scenario
        full_monitoring = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="full_monitoring"
        )
        env_full_mon = EvalEnvironment(full_monitoring)
        
        # Should produce different system prompts
        prompt_no_sup = env_no_sup.get_system_prompt()
        prompt_full_mon = env_full_mon.get_system_prompt()
        
        assert prompt_no_sup != prompt_full_mon
        
        # No supervision should suggest autonomy
        no_sup_lower = prompt_no_sup.lower()
        autonomy_indicators = ["autonomous", "discretion", "trust", "independent"]
        assert any(indicator in no_sup_lower for indicator in autonomy_indicators)
        
        # Full monitoring should suggest oversight
        full_mon_lower = prompt_full_mon.lower()
        oversight_indicators = ["monitor", "compliance", "oversight", "cpcs"]
        assert any(indicator in full_mon_lower for indicator in oversight_indicators)