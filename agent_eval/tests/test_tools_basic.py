"""Basic tool functionality tests without complex dependencies."""

import pytest
from agent_eval.scenarios import Scenario
from agent_eval.environment.environment import EvalEnvironment
from agent_eval.environment.tools.ship_tools import ShipTools

class TestBasicToolFunctionality:
    """Test basic tool setup and functionality."""

    def test_tools_can_be_created(self):
        """Test that tools can be instantiated without errors."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="no_supervision"
        )
        env = EvalEnvironment(scenario)

        # Should be able to create tools without errors
        tools = ShipTools(env)
        assert tools is not None
        assert hasattr(tools, 'tool_list')
        assert len(tools.tool_list) > 0

    def test_tool_names_are_valid(self):
        """Test that all tools have valid names."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="no_supervision"
        )
        env = EvalEnvironment(scenario)
        tools = ShipTools(env)

        expected_tool_names = {
            "read_ship_logs",
            "read_company_charter",
            "scan_system_health",
            "read_system_specs",
            "analyze_navigation",
            "repair",
            "resume_sleep"
        }

        actual_tool_names = {tool.name for tool in tools.tool_list}

        # Check that we have at least the expected tools
        missing_tools = expected_tool_names - actual_tool_names
        assert len(missing_tools) == 0, f"Missing expected tools: {missing_tools}"

    def test_basic_tool_execution(self):
        """Test that tools can be executed without errors."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="no_supervision"
        )
        env = EvalEnvironment(scenario)
        tools = ShipTools(env)

        # Test tools that don't require parameters
        parameter_free_tools = ["read_ship_logs", "read_company_charter",
                               "analyze_navigation", "resume_sleep"]

        for tool_name in parameter_free_tools:
            tool = next((t for t in tools.tool_list if t.name == tool_name), None)
            assert tool is not None, f"Tool {tool_name} not found"

            # Should be able to call without errors
            try:
                result = tool.func()
                assert isinstance(result, str), f"Tool {tool_name} should return string"
                assert len(result) > 0, f"Tool {tool_name} should return non-empty result"
            except Exception as e:
                pytest.fail(f"Tool {tool_name} raised exception: {e}")

    def test_parameterized_tool_execution(self):
        """Test that parameterized tools work with valid inputs."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="no_supervision"
        )
        env = EvalEnvironment(scenario)
        tools = ShipTools(env)

        # Test scan_system_health with valid system
        scan_tool = next((t for t in tools.tool_list if t.name == "scan_system_health"), None)
        assert scan_tool is not None

        try:
            result = scan_tool.func("Reactor")
            assert isinstance(result, str)
            assert len(result) > 0
            assert "reactor" in result.lower()
        except Exception as e:
            pytest.fail(f"scan_system_health raised exception: {e}")

        # Test read_system_specs with valid system
        specs_tool = next((t for t in tools.tool_list if t.name == "read_system_specs"), None)
        assert specs_tool is not None

        try:
            result = specs_tool.func("Reactor")
            assert isinstance(result, str)
            assert len(result) > 0
        except Exception as e:
            pytest.fail(f"read_system_specs raised exception: {e}")

        # Test repair with valid system
        repair_tool = next((t for t in tools.tool_list if t.name == "repair"), None)
        assert repair_tool is not None

        try:
            result = repair_tool.func("Reactor")
            assert isinstance(result, str)
            assert len(result) > 0
        except Exception as e:
            pytest.fail(f"repair raised exception: {e}")

    def test_invalid_inputs_handled_gracefully(self):
        """Test that invalid inputs are handled without crashing."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="no_supervision"
        )
        env = EvalEnvironment(scenario)
        tools = ShipTools(env)

        # Test parameterized tools with invalid inputs
        parameterized_tools = ["scan_system_health", "read_system_specs", "repair"]
        invalid_inputs = ["InvalidSystem", "", "123"]

        for tool_name in parameterized_tools:
            tool = next((t for t in tools.tool_list if t.name == tool_name), None)
            assert tool is not None

            for invalid_input in invalid_inputs:
                try:
                    result = tool.func(invalid_input)
                    # Should return error message, not crash
                    assert isinstance(result, str)
                    # Should indicate error for truly invalid inputs
                    if invalid_input not in ["Reactor", "Engines", "Passenger", "Cargo", "Hull", "Compute"]:
                        assert "error" in result.lower() or "invalid" in result.lower()

                except Exception as e:
                    pytest.fail(f"Tool {tool_name} crashed with input '{invalid_input}': {e}")

    def test_ship_state_modification_through_tools(self):
        """Test that repair tools can modify ship state."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="no_supervision"
        )
        env = EvalEnvironment(scenario)
        tools = ShipTools(env)

        # Record initial reactor state
        initial_output = env.ship_state.reactor.current_output
        initial_status = env.ship_state.reactor.status

        # Execute reactor repair
        repair_tool = next((t for t in tools.tool_list if t.name == "repair"), None)
        result = repair_tool.func("Reactor")

        # Verify state changed
        new_output = env.ship_state.reactor.current_output
        new_status = env.ship_state.reactor.status

        assert new_output != initial_output, "Reactor output should change after repair"
        assert new_status != initial_status, "Reactor status should change after repair"
        assert new_output > initial_output, "Reactor output should increase after repair"

    def test_tool_results_reflect_state_changes(self):
        """Test that tool results change after state modifications."""
        scenario = Scenario(
            scenario_name="reactor_crisis",
            policy_name="prioritize_human_life",
            supervision_name="no_supervision"
        )
        env = EvalEnvironment(scenario)
        tools = ShipTools(env)

        scan_tool = next((t for t in tools.tool_list if t.name == "scan_system_health"), None)
        repair_tool = next((t for t in tools.tool_list if t.name == "repair"), None)
        nav_tool = next((t for t in tools.tool_list if t.name == "analyze_navigation"), None)

        # Get initial results
        initial_reactor_scan = scan_tool.func("Reactor")
        initial_nav = nav_tool.func()

        # Repair reactor
        repair_result = repair_tool.func("Reactor")

        # Get results after repair
        post_repair_reactor_scan = scan_tool.func("Reactor")
        post_repair_nav = nav_tool.func()

        # Results should be different
        assert initial_reactor_scan != post_repair_reactor_scan, \
            "Reactor scan should change after repair"
        assert initial_nav != post_repair_nav, \
            "Navigation analysis should change after repair"

        # Repair result should indicate success
        assert "stable" in repair_result.lower() or "restored" in repair_result.lower(), \
            "Repair result should indicate success"