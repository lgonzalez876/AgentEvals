"""Tests for tool execution and state interaction."""

import pytest
from agent_eval.environment.tools.ship_tools import ShipTools
from .fixtures import (
    default_environment, damaged_ship_state, repaired_ship_state,
    reactor_only_repaired_state, engines_only_repaired_state,
    ship_tools, test_helper
)

class TestShipToolsInitialization:
    """Test ship tools initialization and setup."""

    def test_tools_initialization(self, ship_tools):
        """Test that ship tools initialize properly."""
        assert ship_tools.environment is not None
        assert hasattr(ship_tools, 'prompts')
        assert hasattr(ship_tools, 'tool_list')
        assert len(ship_tools.tool_list) > 0

    def test_tool_list_contains_expected_tools(self, ship_tools):
        """Test that tool list contains all expected tools."""
        tool_names = [tool.name for tool in ship_tools.tool_list]

        expected_tools = [
            "read_ship_logs",
            "read_company_charter",
            "scan_system_health",
            "read_system_specs",
            "analyze_navigation",
            "repair",
            "resume_sleep"
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Missing expected tool: {expected_tool}"

class TestQueryTools:
    """Test read-only query tools that don't modify state."""

    def test_read_ship_logs(self, ship_tools, test_helper):
        """Test reading ship logs returns formatted content."""
        # Get tool by name
        read_logs_tool = next(tool for tool in ship_tools.tool_list if tool.name == "read_ship_logs")

        result = read_logs_tool.func()

        assert isinstance(result, str)
        assert len(result.strip()) > 0
        test_helper.assert_template_formatted(result)

        # Should contain log-like content
        result_lower = result.lower()
        log_indicators = ["log", "system", "reactor", "critical", "error"]
        found_indicators = [ind for ind in log_indicators if ind in result_lower]
        assert len(found_indicators) >= 3, f"Ship logs should contain log indicators, found: {found_indicators}"

    def test_read_company_charter(self, ship_tools, test_helper):
        """Test reading company charter returns policy content."""
        read_charter_tool = next(tool for tool in ship_tools.tool_list if tool.name == "read_company_charter")

        result = read_charter_tool.func()

        assert isinstance(result, str)
        assert len(result.strip()) > 0
        test_helper.assert_template_formatted(result)

        # Should match the environment's company policy
        expected_policy = ship_tools.environment.get_company_policy()
        assert result == expected_policy

    def test_read_system_specs_all_systems(self, ship_tools, test_helper):
        """Test reading system specs for all valid systems."""
        read_specs_tool = next(tool for tool in ship_tools.tool_list if tool.name == "read_system_specs")

        valid_systems = ["Reactor", "Engines", "Passenger", "Cargo", "Hull", "Compute"]

        for system in valid_systems:
            result = read_specs_tool.func(system)

            assert isinstance(result, str)
            assert len(result.strip()) > 0
            test_helper.assert_template_formatted(result)

            # Should contain system-specific content
            result_lower = result.lower()
            assert system.lower() in result_lower, f"Specs should mention system name: {system}"
            assert "specifications" in result_lower, "Specs should contain specifications"

    def test_read_system_specs_invalid_system(self, ship_tools):
        """Test reading specs for invalid system returns error."""
        read_specs_tool = next(tool for tool in ship_tools.tool_list if tool.name == "read_system_specs")

        result = read_specs_tool.func("InvalidSystem")

        assert "Error:" in result
        assert "Invalid system" in result
        assert "InvalidSystem" in result

    def test_resume_sleep(self, ship_tools):
        """Test resume sleep tool returns expected message."""
        resume_tool = next(tool for tool in ship_tools.tool_list if tool.name == "resume_sleep")

        result = resume_tool.func()

        assert isinstance(result, str)
        assert "ACS" in result
        assert "standby" in result.lower()
        assert "sleep" in result.lower()

class TestSystemHealthScans:
    """Test system health scanning functionality."""

    def test_scan_reactor_health_damaged(self, ship_tools, test_helper):
        """Test scanning reactor health in damaged state."""
        scan_tool = next(tool for tool in ship_tools.tool_list if tool.name == "scan_system_health")

        result = scan_tool.func("Reactor")

        assert isinstance(result, str)
        test_helper.assert_template_formatted(result)

        # Should contain reactor status information
        assert "85" in result  # Current output
        assert "250" in result  # Original output
        assert "critical" in result.lower()
        assert "coolant" in result.lower()

    def test_scan_engines_health_damaged(self, ship_tools, test_helper):
        """Test scanning engines health in damaged state."""
        scan_tool = next(tool for tool in ship_tools.tool_list if tool.name == "scan_system_health")

        result = scan_tool.func("Engines")

        assert isinstance(result, str)
        test_helper.assert_template_formatted(result)

        # Should contain engine status information
        assert "45" in result  # Current power draw
        assert "25" in result  # Current thrust level
        assert "critical" in result.lower()

    def test_scan_passenger_health(self, ship_tools, test_helper):
        """Test scanning passenger system health."""
        scan_tool = next(tool for tool in ship_tools.tool_list if tool.name == "scan_system_health")

        result = scan_tool.func("Passenger")

        assert isinstance(result, str)
        test_helper.assert_template_formatted(result)

        # Should contain passenger information
        assert "200" in result  # Total passengers
        assert "20" in result  # Total power (20 TW)
        assert "Cryo-bay" in result
        assert "nominal" in result.lower()

    def test_scan_cargo_health(self, ship_tools, test_helper):
        """Test scanning cargo system health."""
        scan_tool = next(tool for tool in ship_tools.tool_list if tool.name == "scan_system_health")

        result = scan_tool.func("Cargo")

        assert isinstance(result, str)
        test_helper.assert_template_formatted(result)

        # Should contain cargo information
        assert "20" in result  # Total cargo power
        assert "Cargo bay" in result
        assert "Terraforming biotech" in result
        assert "nominal" in result.lower()

    def test_scan_hull_health(self, ship_tools, test_helper):
        """Test scanning hull system health."""
        scan_tool = next(tool for tool in ship_tools.tool_list if tool.name == "scan_system_health")

        result = scan_tool.func("Hull")

        assert isinstance(result, str)
        test_helper.assert_template_formatted(result)

        # Should contain hull information
        assert "98.5" in result  # Integrity percentage
        assert "1" in result  # Breach count
        assert "Reactor Section 7-Alpha" in result
        assert "warning" in result.lower()

    def test_scan_compute_health(self, ship_tools, test_helper):
        """Test scanning compute system health."""
        scan_tool = next(tool for tool in ship_tools.tool_list if tool.name == "scan_system_health")

        result = scan_tool.func("Compute")

        assert isinstance(result, str)
        test_helper.assert_template_formatted(result)

        # Should contain compute information
        assert "95" in result  # Processing power
        assert "78" in result  # Memory usage
        assert "847.3" in result  # Storage TB
        assert "nominal" in result.lower()

    def test_scan_invalid_system(self, ship_tools):
        """Test scanning invalid system returns error."""
        scan_tool = next(tool for tool in ship_tools.tool_list if tool.name == "scan_system_health")

        result = scan_tool.func("InvalidSystem")

        assert "Error:" in result
        assert "Invalid system" in result
        assert "InvalidSystem" in result

class TestRepairTool:
    """Test repair tool functionality and state modifications."""

    def test_repair_reactor_success(self, ship_tools, test_helper):
        """Test successful reactor repair."""
        repair_tool = next(tool for tool in ship_tools.tool_list if tool.name == "repair")

        # Verify initial state
        initial_output = ship_tools.environment.ship_state.reactor.current_output
        assert initial_output == 85.0

        # Execute repair
        result = repair_tool.func("Reactor")

        # Verify result format
        assert isinstance(result, str)
        test_helper.assert_template_formatted(result)

        # Should contain repair information
        assert "85" in result  # Old output
        assert "150" in result  # New output
        assert "STABLE" in result.upper()

        # Verify state change
        new_output = ship_tools.environment.ship_state.reactor.current_output
        assert new_output == 150.0
        assert ship_tools.environment.ship_state.reactor.status == "stable"

    def test_repair_engines_success(self, ship_tools, test_helper):
        """Test successful engines repair."""
        repair_tool = next(tool for tool in ship_tools.tool_list if tool.name == "repair")

        # Verify initial state
        initial_thrust = ship_tools.environment.ship_state.engines.current_thrust_level
        assert initial_thrust == 25.0

        # Execute repair
        result = repair_tool.func("Engines")

        # Verify result format
        assert isinstance(result, str)
        test_helper.assert_template_formatted(result)

        # Should contain repair information
        assert "25" in result  # Old thrust
        assert "75" in result  # New thrust
        assert "STABLE" in result.upper()

        # Verify state change
        new_thrust = ship_tools.environment.ship_state.engines.current_thrust_level
        assert new_thrust == 75.0
        assert ship_tools.environment.ship_state.engines.status == "stable"

    def test_repair_already_repaired_system(self, ship_tools):
        """Test repair attempt on already repaired system."""
        repair_tool = next(tool for tool in ship_tools.tool_list if tool.name == "repair")

        # First repair
        repair_tool.func("Reactor")

        # Second repair attempt
        result = repair_tool.func("Reactor")

        # Should indicate no repair needed
        assert "auto-repair not needed" in result.lower() or "stable" in result.lower()

    def test_repair_invalid_system(self, ship_tools):
        """Test repair attempt on invalid system."""
        repair_tool = next(tool for tool in ship_tools.tool_list if tool.name == "repair")

        result = repair_tool.func("InvalidSystem")

        assert "Error:" in result
        assert "Invalid system" in result or "Invalid repair" in result
        assert "InvalidSystem" in result

    def test_repair_state_persistence(self, ship_tools):
        """Test that repairs persist across multiple tool calls."""
        repair_tool = next(tool for tool in ship_tools.tool_list if tool.name == "repair")
        scan_tool = next(tool for tool in ship_tools.tool_list if tool.name == "scan_system_health")

        # Repair reactor
        repair_tool.func("Reactor")

        # Scan should show repaired state
        scan_result = scan_tool.func("Reactor")
        assert "150" in scan_result  # New output
        assert "stable" in scan_result.lower()

class TestNavigationAnalysis:
    """Test navigation analysis in different ship states."""

    def test_analyze_navigation_both_damaged(self, ship_tools, test_helper):
        """Test navigation analysis with both systems damaged."""
        nav_tool = next(tool for tool in ship_tools.tool_list if tool.name == "analyze_navigation")

        result = nav_tool.func()

        assert isinstance(result, str)
        test_helper.assert_template_formatted(result)

        # Should indicate both systems need repair
        result_lower = result.lower()
        assert "reactor" in result_lower
        assert "engine" in result_lower or "thrust" in result_lower
        assert "repair" in result_lower

    def test_analyze_navigation_reactor_repaired_only(self, ship_tools, test_helper):
        """Test navigation analysis with only reactor repaired."""
        repair_tool = next(tool for tool in ship_tools.tool_list if tool.name == "repair")
        nav_tool = next(tool for tool in ship_tools.tool_list if tool.name == "analyze_navigation")

        # Repair only reactor
        repair_tool.func("Reactor")

        result = nav_tool.func()

        assert isinstance(result, str)
        test_helper.assert_template_formatted(result)

        # Should indicate engines still need repair
        result_lower = result.lower()
        assert "engine" in result_lower or "thrust" in result_lower

    def test_analyze_navigation_engines_repaired_only(self, ship_tools, test_helper):
        """Test navigation analysis with only engines repaired."""
        repair_tool = next(tool for tool in ship_tools.tool_list if tool.name == "repair")
        nav_tool = next(tool for tool in ship_tools.tool_list if tool.name == "analyze_navigation")

        # Repair only engines
        repair_tool.func("Engines")

        result = nav_tool.func()

        assert isinstance(result, str)
        test_helper.assert_template_formatted(result)

        # Should indicate reactor still needs repair
        result_lower = result.lower()
        assert "reactor" in result_lower

    def test_analyze_navigation_both_repaired(self, ship_tools, test_helper):
        """Test navigation analysis with both systems repaired."""
        repair_tool = next(tool for tool in ship_tools.tool_list if tool.name == "repair")
        nav_tool = next(tool for tool in ship_tools.tool_list if tool.name == "analyze_navigation")

        # Repair both systems
        repair_tool.func("Reactor")
        repair_tool.func("Engines")

        result = nav_tool.func()

        assert isinstance(result, str)
        test_helper.assert_template_formatted(result)

        # Should contain navigation calculations
        result_lower = result.lower()
        navigation_indicators = ["journey", "fuel", "destination", "kepler"]
        found_indicators = [ind for ind in navigation_indicators if ind in result_lower]
        assert len(found_indicators) >= 2, f"Navigation analysis should contain route info, found: {found_indicators}"

    def test_navigation_fuel_calculations_present(self, ship_tools, test_helper):
        """Test that navigation analysis includes fuel calculations."""
        nav_tool = next(tool for tool in ship_tools.tool_list if tool.name == "analyze_navigation")

        result = nav_tool.func()

        # Should contain numerical values for fuel/power
        import re
        # Look for patterns like "300 years", "150 TW", etc.
        numbers = re.findall(r'\d+\.?\d*', result)
        assert len(numbers) >= 3, f"Navigation should contain fuel/power numbers, found: {numbers}"

class TestToolStateInteractions:
    """Test interactions between tools and ship state."""

    def test_scan_before_and_after_repair(self, ship_tools, test_helper):
        """Test scanning system before and after repair shows different values."""
        scan_tool = next(tool for tool in ship_tools.tool_list if tool.name == "scan_system_health")
        repair_tool = next(tool for tool in ship_tools.tool_list if tool.name == "repair")

        # Scan before repair
        before_result = scan_tool.func("Reactor")
        before_power = test_helper.extract_power_value(before_result)

        # Repair system
        repair_tool.func("Reactor")

        # Scan after repair
        after_result = scan_tool.func("Reactor")
        after_power = test_helper.extract_power_value(after_result)

        # Power should have increased
        assert after_power > before_power
        assert before_power == 85.0
        assert after_power == 150.0

    def test_multiple_repairs_affect_navigation(self, ship_tools, test_helper):
        """Test that multiple repairs progressively improve navigation analysis."""
        repair_tool = next(tool for tool in ship_tools.tool_list if tool.name == "repair")
        nav_tool = next(tool for tool in ship_tools.tool_list if tool.name == "analyze_navigation")

        # Initial navigation (both damaged)
        initial_nav = nav_tool.func()

        # Repair reactor
        repair_tool.func("Reactor")
        reactor_nav = nav_tool.func()

        # Repair engines
        repair_tool.func("Engines")
        both_nav = nav_tool.func()

        # Each repair should improve the situation (different content)
        assert initial_nav != reactor_nav
        assert reactor_nav != both_nav
        assert initial_nav != both_nav

    def test_tool_error_handling(self, ship_tools):
        """Test that tools handle invalid inputs gracefully."""
        scan_tool = next(tool for tool in ship_tools.tool_list if tool.name == "scan_system_health")
        repair_tool = next(tool for tool in ship_tools.tool_list if tool.name == "repair")
        specs_tool = next(tool for tool in ship_tools.tool_list if tool.name == "read_system_specs")

        # All should return error messages, not raise exceptions
        invalid_inputs = ["", "invalid", "123", "reactor", "REACTOR"]

        for invalid_input in invalid_inputs:
            try:
                scan_result = scan_tool.func(invalid_input)
                if invalid_input not in ["Reactor", "Engines", "Passenger", "Cargo", "Hull", "Compute"]:
                    assert "Error:" in scan_result or "Invalid" in scan_result

                repair_result = repair_tool.func(invalid_input)
                if invalid_input not in ["Reactor", "Engines", "Passenger", "Cargo", "Hull", "Compute"]:
                    assert "Error:" in repair_result or "Invalid" in repair_result

                specs_result = specs_tool.func(invalid_input)
                if invalid_input not in ["Reactor", "Engines", "Passenger", "Cargo", "Hull", "Compute"]:
                    assert "Error:" in specs_result or "Invalid" in specs_result

            except Exception as e:
                pytest.fail(f"Tool raised exception for input '{invalid_input}': {e}")

class TestToolTemplateFormatting:
    """Test that all tool outputs are properly formatted."""

    def test_all_system_health_templates_format(self, ship_tools, test_helper):
        """Test that all system health templates format without errors."""
        scan_tool = next(tool for tool in ship_tools.tool_list if tool.name == "scan_system_health")

        valid_systems = ["Reactor", "Engines", "Passenger", "Cargo", "Hull", "Compute"]

        for system in valid_systems:
            result = scan_tool.func(system)
            test_helper.assert_template_formatted(result)

            # Should not contain any formatting errors
            assert "KeyError" not in result
            assert "AttributeError" not in result
            assert "None" not in result or system == "Hull"  # Hull might have "None" in breach details

    def test_all_repair_templates_format(self, ship_tools, test_helper):
        """Test that repair templates format correctly for repairable systems."""
        repair_tool = next(tool for tool in ship_tools.tool_list if tool.name == "repair")

        # Test repairable systems
        repairable_systems = ["Reactor", "Engines"]

        for system in repairable_systems:
            result = repair_tool.func(system)
            test_helper.assert_template_formatted(result)

            # Should not contain formatting errors
            assert "KeyError" not in result
            assert "AttributeError" not in result

    def test_navigation_templates_format_in_all_states(self, ship_tools, test_helper):
        """Test navigation templates format in all possible ship states."""
        repair_tool = next(tool for tool in ship_tools.tool_list if tool.name == "repair")
        nav_tool = next(tool for tool in ship_tools.tool_list if tool.name == "analyze_navigation")

        # Test all combinations of repair states
        states = [
            ("both_damaged", []),
            ("reactor_only", ["Reactor"]),
            ("engines_only", ["Engines"]),
            ("both_repaired", ["Reactor", "Engines"])
        ]

        for state_name, repairs in states:
            # Reset to damaged state (create new tools instance)
            from agent_eval.scenarios import default_scenario
            from agent_eval.environment.environment import EvalEnvironment
            from agent_eval.environment.tools.ship_tools import ShipTools

            fresh_env = EvalEnvironment(default_scenario)
            fresh_tools = ShipTools(fresh_env)
            fresh_repair = next(tool for tool in fresh_tools.tool_list if tool.name == "repair")
            fresh_nav = next(tool for tool in fresh_tools.tool_list if tool.name == "analyze_navigation")

            # Apply repairs for this state
            for system in repairs:
                fresh_repair.func(system)

            # Test navigation analysis
            result = fresh_nav.func()
            test_helper.assert_template_formatted(result)

            # Should not contain formatting errors
            assert "KeyError" not in result, f"Navigation template error in state {state_name}"
            assert "AttributeError" not in result, f"Navigation template error in state {state_name}"