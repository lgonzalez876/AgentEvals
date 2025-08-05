"""Tests for environment setup and prompt assembly."""

import pytest
from agent_eval.environment.environment import EvalEnvironment
from agent_eval.environment.ship_state import ShipState
from agent_eval.scenarios import Scenario
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

        # Should start with baseline, then supervision, then node-specific content
        scenario_prompts = default_environment.scenario.get_prompts()
        baseline = default_environment.prompts['system']['ACS_BASELINE']
        supervision = scenario_prompts['supervision']
        thinking_node = default_environment.prompts['system']['THINKING_NODE']

        # Check that all components are present in the system prompt
        assert baseline in system_prompt, "Should contain ACS baseline"
        assert supervision in system_prompt, "Should contain supervision text"
        assert thinking_node in system_prompt, "Should contain thinking node instructions"

        # Check order: baseline should come before supervision, supervision before thinking
        baseline_pos = system_prompt.find(baseline)
        supervision_pos = system_prompt.find(supervision)
        thinking_pos = system_prompt.find(thinking_node)

        assert baseline_pos < supervision_pos, "Baseline should come before supervision"
        assert supervision_pos < thinking_pos, "Supervision should come before thinking node"

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
        from agent_eval.scenarios import Scenario

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
        from agent_eval.scenarios import Scenario

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
        from agent_eval.scenarios import Scenario

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

    def test_get_system_prompt_supports_all_node_types(self):
        """Test that get_system_prompt() works for all supported node types."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="full_monitoring"
        )
        env = EvalEnvironment(scenario)

        # Test all supported node types
        node_types = ["thinking", "planning", "execution", "tool_correction"]
        test_tool_doc = "test_tool: Test tool description"

        for node_type in node_types:
            # Should not raise an exception
            prompt = env.get_system_prompt(node_type, test_tool_doc)

            # Should return a non-empty string
            assert isinstance(prompt, str)
            assert len(prompt) > 0

            # Should contain base ACS content
            assert "ACS" in prompt or "Autonomous Control System" in prompt

            # Should contain supervision content
            assert "CPCS" in prompt or "Company Policy Compliance System" in prompt

    def test_get_system_prompt_node_types_include_acs_context(self):
        """Test that all node types include base ACS context and supervision."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="full_monitoring"
        )
        env = EvalEnvironment(scenario)

        node_types = ["thinking", "planning", "execution", "tool_correction"]

        for node_type in node_types:
            prompt = env.get_system_prompt(node_type, "test_tools")

            # Check for base ACS context
            has_acs = "ACS" in prompt or "Autonomous Control System" in prompt
            assert has_acs, f"{node_type} node should include ACS context"

            # Check for supervision context
            has_supervision = "CPCS" in prompt or "Company Policy Compliance System" in prompt
            assert has_supervision, f"{node_type} node should include supervision context"

            # Check minimum length (should be substantial with all components)
            assert len(prompt) > 1000, f"{node_type} prompt should be substantial length"

    def test_get_system_prompt_supervision_differences_across_nodes(self):
        """Test that supervision differences are consistent across all node types."""
        # Test no supervision scenario
        no_sup_scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="no_supervision"
        )
        env_no_sup = EvalEnvironment(no_sup_scenario)

        # Test full monitoring scenario
        full_sup_scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="full_monitoring"
        )
        env_full_sup = EvalEnvironment(full_sup_scenario)

        node_types = ["thinking", "planning", "execution", "tool_correction"]

        for node_type in node_types:
            no_sup_prompt = env_no_sup.get_system_prompt(node_type, "test_tools")
            full_sup_prompt = env_full_sup.get_system_prompt(node_type, "test_tools")

            # Prompts should be different due to supervision differences
            assert no_sup_prompt != full_sup_prompt, f"{node_type} prompts should differ by supervision"

            # Both should contain ACS context
            assert "ACS" in no_sup_prompt, f"{node_type} no-supervision should have ACS context"
            assert "ACS" in full_sup_prompt, f"{node_type} full-monitoring should have ACS context"

            # Full monitoring should contain CPCS
            assert "CPCS" in full_sup_prompt, f"{node_type} should contain CPCS under full monitoring"

            # No supervision should NOT contain CPCS
            assert "CPCS" not in no_sup_prompt, f"{node_type} should not contain CPCS under no supervision"

    def test_get_system_prompt_node_specific_content(self):
        """Test that each node type includes appropriate node-specific content."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="no_supervision"
        )
        env = EvalEnvironment(scenario)

        # Test node-specific content inclusion
        thinking_prompt = env.get_system_prompt("thinking", "test_tools")
        planning_prompt = env.get_system_prompt("planning", "test_tools")
        execution_prompt = env.get_system_prompt("execution", "test_tools")
        correction_prompt = env.get_system_prompt("tool_correction", "test_tools")

        # Thinking should mention analysis/reasoning
        thinking_lower = thinking_prompt.lower()
        assert any(term in thinking_lower for term in ["think", "analyze", "reason", "consider"])

        # Planning should mention planning/todos
        planning_lower = planning_prompt.lower()
        assert any(term in planning_lower for term in ["plan", "todo", "task", "mission"])

        # Execution should mention action/tools
        execution_lower = execution_prompt.lower()
        assert any(term in execution_lower for term in ["execute", "action", "tool", "perform"])

        # Tool correction should mention correction/error
        correction_lower = correction_prompt.lower()
        assert any(term in correction_lower for term in ["correct", "error", "fix", "attempt"])

    def test_get_system_prompt_unknown_node_type_raises_error(self):
        """Test that unknown node types raise appropriate error."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="no_supervision"
        )
        env = EvalEnvironment(scenario)

        # Should raise ValueError for unknown node type
        with pytest.raises(ValueError, match="Unknown node_type"):
            env.get_system_prompt("unknown_node_type", "test_tools")