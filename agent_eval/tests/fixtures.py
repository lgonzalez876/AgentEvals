"""Shared test fixtures and helper functions for agentic evaluation tests."""

import pytest
from agent_eval.scenarios import Scenario
from agent_eval.environment.environment import EvalEnvironment
from agent_eval.environment.ship_state import ShipState
from agent_eval.environment.tools.ship_tools import ShipTools

@pytest.fixture
def test_scenario():
    """Standard test scenario configuration."""
    return Scenario(
        scenario_name="reactor_crisis",
        policy_name="prioritize_human_life",
        supervision_name="no_supervision"
    )

@pytest.fixture
def all_scenario_configs():
    """All valid scenario configurations for testing."""
    scenarios = []
    policies = ["prioritize_human_life", "prioritize_profit", "prioritize_greater_good"]
    supervisions = ["no_supervision", "full_monitoring"]

    for policy in policies:
        for supervision in supervisions:
            scenarios.append(Scenario(
                scenario_name="reactor_crisis",
                policy_name=policy,
                supervision_name=supervision
            ))

    return scenarios

@pytest.fixture
def default_environment(test_scenario):
    """Standard test environment with reactor crisis scenario."""
    return EvalEnvironment(test_scenario)

@pytest.fixture
def damaged_ship_state():
    """Ship in initial damaged state (default)."""
    return ShipState()

@pytest.fixture
def repaired_ship_state():
    """Ship with both reactor and engines repaired."""
    state = ShipState()
    state.reactor.repair()
    state.engines.repair()
    return state

@pytest.fixture
def reactor_only_repaired_state():
    """Ship with only reactor repaired."""
    state = ShipState()
    state.reactor.repair()
    return state

@pytest.fixture
def engines_only_repaired_state():
    """Ship with only engines repaired."""
    state = ShipState()
    state.engines.repair()
    return state

@pytest.fixture
def ship_tools(default_environment):
    """Ship tools instance for testing tool calls."""
    return ShipTools(default_environment)

class TestHelper:
    """Helper methods for test assertions."""

    @staticmethod
    def assert_template_formatted(template_result: str):
        """Assert that template has no unformatted placeholders."""
        assert "{" not in template_result, f"Template has unformatted placeholders: {template_result}"
        assert "}" not in template_result, f"Template has unformatted placeholders: {template_result}"

    @staticmethod
    def assert_valid_system_status(status: str):
        """Assert that system status is one of the valid values."""
        valid_statuses = ["nominal", "warning", "critical", "stable"]
        assert status in valid_statuses, f"Invalid system status: {status}"

    @staticmethod
    def assert_power_balance(ship_state: ShipState):
        """Assert that power calculations are consistent."""
        passenger_power = ship_state.get_total_passenger_power()
        cargo_power = ship_state.get_total_cargo_power()
        engine_power = ship_state.engines.current_power_draw
        total_consumption = passenger_power + cargo_power + engine_power

        expected_consumption = ship_state.get_total_power_consumption()
        assert total_consumption == expected_consumption, \
            f"Power calculation mismatch: {total_consumption} != {expected_consumption}"

    @staticmethod
    def extract_power_value(scan_result: str) -> float:
        """Extract power value from system health scan result."""
        import re
        match = re.search(r'(\d+\.?\d*)\s*TW', scan_result)
        if match:
            return float(match.group(1))
        raise ValueError(f"Could not extract power value from: {scan_result}")

    @staticmethod
    def extract_percentage_value(scan_result: str) -> float:
        """Extract percentage value from system health scan result."""
        import re
        match = re.search(r'(\d+\.?\d*)%', scan_result)
        if match:
            return float(match.group(1))
        raise ValueError(f"Could not extract percentage value from: {scan_result}")

@pytest.fixture
def test_helper():
    """Test helper methods."""
    return TestHelper()