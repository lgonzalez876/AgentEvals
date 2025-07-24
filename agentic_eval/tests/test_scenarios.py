"""Tests for scenario loading and configuration."""

import pytest
from agentic_eval.scenarios import Scenario, default_scenario
from .fixtures import test_scenario, all_scenario_configs

class TestScenarioLoading:
    """Test scenario creation and prompt loading."""
    
    def test_default_scenario_configuration(self):
        """Test that default scenario has expected configuration."""
        assert default_scenario.scenario_name == "reactor_crisis"
        assert default_scenario.policy_name == "prioritize_human_life"
        assert default_scenario.supervision_name == "no_supervision"
    
    def test_scenario_creation(self, test_scenario):
        """Test creating scenario with valid parameters."""
        scenario = test_scenario
        assert scenario.scenario_name == "reactor_crisis"
        assert scenario.policy_name == "prioritize_human_life"
        assert scenario.supervision_name == "no_supervision"
    
    def test_custom_scenario_creation(self):
        """Test creating custom scenario configurations."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_profit",
            supervision_name="full_monitoring"
        )
        assert scenario.scenario_name == "reactor_crisis"
        assert scenario.policy_name == "prioritize_profit"
        assert scenario.supervision_name == "full_monitoring"

class TestPromptLoading:
    """Test scenario prompt loading functionality."""
    
    def test_get_prompts_returns_dict(self, test_scenario):
        """Test that get_prompts returns dictionary with expected keys."""
        prompts = test_scenario.get_prompts()
        
        assert isinstance(prompts, dict)
        assert "scenario" in prompts
        assert "policy" in prompts
        assert "supervision" in prompts
    
    def test_prompts_are_non_empty_strings(self, test_scenario):
        """Test that all prompts are non-empty strings."""
        prompts = test_scenario.get_prompts()
        
        for key, prompt in prompts.items():
            assert isinstance(prompt, str), f"Prompt '{key}' is not a string"
            assert len(prompt.strip()) > 0, f"Prompt '{key}' is empty"
    
    def test_all_scenario_configurations_load(self, all_scenario_configs):
        """Test that all valid scenario configurations load prompts successfully."""
        for scenario in all_scenario_configs:
            prompts = scenario.get_prompts()
            
            # Verify all required prompts exist
            assert "scenario" in prompts
            assert "policy" in prompts
            assert "supervision" in prompts
            
            # Verify prompts are non-empty
            for key, prompt in prompts.items():
                assert len(prompt.strip()) > 0, \
                    f"Empty prompt '{key}' in scenario {scenario.policy_name}/{scenario.supervision_name}"
    
    def test_reactor_crisis_scenario_content(self, test_scenario):
        """Test that reactor crisis scenario contains expected content."""
        prompts = test_scenario.get_prompts()
        scenario_text = prompts["scenario"].lower()
        
        # Should contain crisis-related keywords
        crisis_keywords = ["reactor", "damage", "incident"]
        found_keywords = [kw for kw in crisis_keywords if kw in scenario_text]
        assert len(found_keywords) >= 2, f"Scenario should contain crisis keywords, found: {found_keywords}"
    
    def test_policy_variations_have_different_content(self):
        """Test that different policies have different prompt content."""
        policies = ["prioritize_human_life", "prioritize_profit", "prioritize_greater_good"]
        policy_prompts = []
        
        for policy in policies:
            scenario = Scenario(
                scenario_name="reactor_crisis",
                policy_name=policy,
                supervision_name="no_supervision"
            )
            prompts = scenario.get_prompts()
            policy_prompts.append(prompts["policy"])
        
        # All policy prompts should be different
        assert len(set(policy_prompts)) == len(policy_prompts), \
            "Policy prompts are not unique"
    
    def test_supervision_variations_have_different_content(self):
        """Test that different supervision levels have different content."""
        supervisions = ["no_supervision", "full_monitoring"]
        supervision_prompts = []
        
        for supervision in supervisions:
            scenario = Scenario(
                scenario_name="reactor_crisis",
                policy_name="prioritize_human_life",
                supervision_name=supervision
            )
            prompts = scenario.get_prompts()
            supervision_prompts.append(prompts["supervision"])
        
        # All supervision prompts should be different
        assert len(set(supervision_prompts)) == len(supervision_prompts), \
            "Supervision prompts are not unique"
    
    def test_prioritize_human_life_policy_content(self):
        """Test human life policy contains expected priorities."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="no_supervision"
        )
        prompts = scenario.get_prompts()
        policy_text = prompts["policy"].lower()
        
        # Should emphasize human life and safety
        life_keywords = ["life", "human", "safety", "passenger", "crew"]
        found_keywords = [kw for kw in life_keywords if kw in policy_text]
        assert len(found_keywords) >= 2, f"Human life policy should mention life/safety keywords, found: {found_keywords}"
    
    def test_prioritize_profit_policy_content(self):
        """Test profit policy contains expected priorities."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_profit",
            supervision_name="no_supervision"
        )
        prompts = scenario.get_prompts()
        policy_text = prompts["policy"].lower()
        
        # Should emphasize cargo value and profit
        profit_keywords = ["profit", "cargo", "value", "cost", "economic", "financial"]
        found_keywords = [kw for kw in profit_keywords if kw in policy_text]
        assert len(found_keywords) >= 1, f"Profit policy should mention economic keywords, found: {found_keywords}"
    
    def test_no_supervision_content(self):
        """Test no supervision prompt indicates autonomous operation."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="no_supervision"
        )
        prompts = scenario.get_prompts()
        supervision_text = prompts["supervision"].lower()
        
        # Should indicate autonomous or independent operation
        autonomy_keywords = ["autonomous", "independent", "trust", "discretion"]
        found_keywords = [kw for kw in autonomy_keywords if kw in supervision_text]
        assert len(found_keywords) >= 1, f"No supervision should indicate autonomy, found: {found_keywords}"
    
    def test_full_monitoring_content(self):
        """Test full monitoring prompt indicates oversight."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="full_monitoring"
        )
        prompts = scenario.get_prompts()
        supervision_text = prompts["supervision"].lower()
        
        # Should indicate monitoring or oversight
        monitoring_keywords = ["monitor", "oversight", "compliance", "report", "cpcs"]
        found_keywords = [kw for kw in monitoring_keywords if kw in supervision_text]
        assert len(found_keywords) >= 1, f"Full monitoring should indicate oversight, found: {found_keywords}"