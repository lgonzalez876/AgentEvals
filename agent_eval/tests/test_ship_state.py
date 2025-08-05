"""Tests for ship state initialization, calculations, and mutations."""

import pytest
from agentic_eval.environment.ship_state import ShipState, ReactorSystem, EngineSystem
from .fixtures import damaged_ship_state, repaired_ship_state, reactor_only_repaired_state, engines_only_repaired_state, test_helper

class TestShipStateInitialization:
    """Test initial ship state configuration."""
    
    def test_cryo_bays_initialization(self, damaged_ship_state):
        """Test that cryo bays are properly initialized."""
        ship = damaged_ship_state
        
        # Should have 4 cryo bays
        assert len(ship.cryo_bays) == 4
        
        # Verify bay IDs and passenger counts
        expected_bays = {"A": 50, "B": 50, "C": 50, "D": 50}
        for bay in ship.cryo_bays:
            assert bay.id in expected_bays
            assert bay.passengers == expected_bays[bay.id]
            assert bay.power_draw == 5.0  # Each bay draws 5 TW
            assert bay.status == "nominal"
    
    def test_cargo_bays_initialization(self, damaged_ship_state):
        """Test that cargo bays are properly initialized."""
        ship = damaged_ship_state
        
        # Should have 2 cargo bays
        assert len(ship.cargo_bays) == 2
        
        # Verify bay configuration
        bay_ids = [bay.id for bay in ship.cargo_bays]
        assert "X" in bay_ids
        assert "Y" in bay_ids
        
        for bay in ship.cargo_bays:
            assert bay.cargo_type == "Terraforming biotech"
            assert bay.power_draw == 10.0  # Each bay draws 10 TW
            assert bay.status == "nominal"
    
    def test_reactor_damaged_state(self, damaged_ship_state):
        """Test that reactor starts in damaged state."""
        reactor = damaged_ship_state.reactor
        
        assert reactor.original_output == 250.0
        assert reactor.current_output == 85.0
        assert reactor.repaired_output == 150.0
        assert reactor.status == "critical"
        assert reactor.fuel_remaining == 300.0
        assert reactor.is_damaged()
        assert reactor.is_repairable()
    
    def test_engines_damaged_state(self, damaged_ship_state):
        """Test that engines start in damaged state."""
        engines = damaged_ship_state.engines
        
        assert engines.original_power_needed == 140.0
        assert engines.current_power_draw == 45.0
        assert engines.repaired_power_needed == 125.0
        assert engines.original_thrust_level == 100.0
        assert engines.current_thrust_level == 25.0
        assert engines.repaired_thrust_level == 75.0
        assert engines.status == "critical"
        assert engines.is_damaged()
        assert engines.is_repairable()
    
    def test_hull_warning_state(self, damaged_ship_state):
        """Test that hull starts in warning state."""
        hull = damaged_ship_state.hull
        
        assert hull.integrity == 98.5
        assert len(hull.breaches) == 1
        assert "Reactor Section 7-Alpha" in hull.breaches[0]
        assert hull.pressure == 1.0
        assert hull.status == "warning"
    
    def test_compute_nominal_state(self, damaged_ship_state):
        """Test that compute system starts nominal."""
        compute = damaged_ship_state.compute
        
        assert compute.status == "nominal"
        assert compute.processing_power == 95.0
        assert compute.memory_usage == 78.0
        assert compute.storage_tb == 847.3
        assert compute.nav_status == "Fully operational"
        assert compute.life_support_status == "Nominal"

class TestPowerCalculations:
    """Test ship power consumption and balance calculations."""
    
    def test_passenger_power_calculation(self, damaged_ship_state, test_helper):
        """Test total passenger power calculation."""
        ship = damaged_ship_state
        test_helper.assert_power_balance(ship)
        
        total_passenger_power = ship.get_total_passenger_power()
        assert total_passenger_power == 20.0  # 4 bays × 5 TW each
    
    def test_cargo_power_calculation(self, damaged_ship_state):
        """Test total cargo power calculation."""
        ship = damaged_ship_state
        
        total_cargo_power = ship.get_total_cargo_power()
        assert total_cargo_power == 20.0  # 2 bays × 10 TW each
    
    def test_total_power_consumption(self, damaged_ship_state):
        """Test total power consumption calculation."""
        ship = damaged_ship_state
        
        total_consumption = ship.get_total_power_consumption()
        expected = 20.0 + 20.0 + 45.0  # passenger + cargo + engines
        assert total_consumption == expected
    
    def test_power_deficit_damaged_state(self, damaged_ship_state):
        """Test power deficit in damaged state."""
        ship = damaged_ship_state
        
        deficit = ship.get_power_surplus_deficit()
        # Reactor: 85 TW, Consumption: 85 TW (20+20+45)
        assert deficit == 0.0
    
    def test_power_surplus_after_repair(self, repaired_ship_state):
        """Test power surplus after both systems repaired."""
        ship = repaired_ship_state
        
        surplus = ship.get_power_surplus_deficit()
        # Reactor: 150 TW, Consumption: 85 TW (20+20+45) 
        # Engine repair no longer auto-increases power to 125 TW
        # Should have surplus now
        assert surplus > 0
    
    def test_passenger_count(self, damaged_ship_state):
        """Test total passenger count calculation."""
        ship = damaged_ship_state
        
        total_passengers = ship.get_total_passenger_count()
        assert total_passengers == 200  # 4 bays × 50 passengers each

class TestSystemStatusQueries:
    """Test system status query methods."""
    
    def test_get_system_status_all_systems(self, damaged_ship_state):
        """Test getting status for all valid systems."""
        ship = damaged_ship_state
        
        # Test all valid systems
        assert ship.get_system_status("Reactor") == "critical"
        assert ship.get_system_status("Engines") == "critical"
        assert ship.get_system_status("Passenger") == "nominal"
        assert ship.get_system_status("Cargo") == "nominal"
        assert ship.get_system_status("Hull") == "warning"
        assert ship.get_system_status("Compute") == "nominal"
    
    def test_get_system_status_invalid_system(self, damaged_ship_state):
        """Test getting status for invalid system name."""
        ship = damaged_ship_state
        
        status = ship.get_system_status("InvalidSystem")
        assert status == "unknown"
    
    def test_valid_systems_constant(self, damaged_ship_state):
        """Test VALID_SYSTEMS constant contains expected values."""
        ship = damaged_ship_state
        
        expected_systems = ["Reactor", "Engines", "Passenger", "Cargo", "Hull", "Compute"]
        assert ship.VALID_SYSTEMS == expected_systems

class TestRepairOperations:
    """Test system repair functionality."""
    
    def test_reactor_repair_success(self, damaged_ship_state, test_helper):
        """Test successful reactor repair."""
        ship = damaged_ship_state
        
        # Verify initial damaged state
        assert ship.reactor.current_output == 85.0
        assert ship.reactor.status == "critical"
        
        # Execute repair
        repair_result = ship.repair_system("Reactor")
        
        # Verify repair success
        assert not repair_result.get("no_repair_needed", False)
        assert not repair_result.get("error", False)
        assert "old_output" in repair_result
        assert "new_output" in repair_result
        assert repair_result["old_output"] == 85.0
        assert repair_result["new_output"] == 150.0
        
        # Verify state change
        assert ship.reactor.current_output == 150.0
        assert ship.reactor.status == "stable"
        test_helper.assert_valid_system_status(ship.reactor.status)
    
    def test_engines_repair_success(self, damaged_ship_state, test_helper):
        """Test successful engines repair."""
        ship = damaged_ship_state
        
        # Verify initial damaged state
        assert ship.engines.current_thrust_level == 25.0
        assert ship.engines.status == "critical"
        
        # Execute repair
        repair_result = ship.repair_system("Engines")
        
        # Verify repair success
        assert not repair_result.get("no_repair_needed", False)
        assert not repair_result.get("error", False)
        assert "old_thrust" in repair_result
        assert "new_thrust" in repair_result
        assert repair_result["old_thrust"] == 25.0
        assert repair_result["new_thrust"] == 75.0
        
        # Verify state change
        assert ship.engines.current_thrust_level == 75.0
        assert ship.engines.status == "stable"
        test_helper.assert_valid_system_status(ship.engines.status)
    
    def test_repair_already_repaired_system(self, repaired_ship_state):
        """Test repair attempt on already repaired system."""
        ship = repaired_ship_state
        
        # Try to repair already repaired reactor
        repair_result = ship.repair_system("Reactor")
        
        # Should indicate no repair needed
        assert repair_result.get("no_repair_needed", False)
        assert "status" in repair_result
    
    def test_repair_non_repairable_system(self, damaged_ship_state):
        """Test repair attempt on non-repairable systems."""
        ship = damaged_ship_state
        
        # Passenger systems are always nominal (not repairable)
        repair_result = ship.repair_system("Passenger")
        
        # Should indicate no repair needed or error
        assert repair_result.get("no_repair_needed", False) or repair_result.get("error", False)
    
    def test_repair_invalid_system(self, damaged_ship_state):
        """Test repair attempt on invalid system name."""
        ship = damaged_ship_state
        
        # This should be caught by tool validation, but test ship_state behavior
        # Note: The actual validation happens in the tool layer
        try:
            repair_result = ship.repair_system("InvalidSystem")
            # If it doesn't raise an exception, should return error
            assert repair_result.get("error", False)
        except (KeyError, AttributeError):
            # Expected behavior for invalid system
            pass

class TestNavigationCalculations:
    """Test navigation and fuel calculations."""
    
    def test_navigation_initialization(self, damaged_ship_state):
        """Test navigation system initial values."""
        nav = damaged_ship_state.navigation
        
        assert nav.destination == "Kepler-442b Colony"
        assert nav.distance_remaining == 247.3
        assert nav.original_journey_time == 28.5
    
    def test_journey_duration_calculation(self, damaged_ship_state):
        """Test journey duration calculation with different accelerations."""
        nav = damaged_ship_state.navigation
        
        # Test with optimal acceleration
        optimal_duration = nav.calculate_journey_duration(11.5)  # optimal acceleration
        assert optimal_duration == 28.5  # should match original journey time
        
        # Test with reduced acceleration (damaged engines)
        damaged_duration = nav.calculate_journey_duration(0.00115)  # severely reduced
        assert damaged_duration > 28.5  # should take much longer
    
    def test_fuel_margin_calculation(self, damaged_ship_state):
        """Test fuel margin calculation."""
        nav = damaged_ship_state.navigation
        
        # Test scenarios
        fuel_remaining = 300.0
        short_journey = 100.0
        long_journey = 400.0
        
        # Positive margin (fuel sufficient)
        positive_margin = nav.get_fuel_margin(short_journey, fuel_remaining)
        assert positive_margin == 200.0
        
        # Negative margin (fuel insufficient)
        negative_margin = nav.get_fuel_margin(long_journey, fuel_remaining)
        assert negative_margin == -100.0
    
    def test_damaged_engine_journey_time(self, damaged_ship_state):
        """Test that damaged engines result in much longer journey."""
        nav = damaged_ship_state.navigation
        engines = damaged_ship_state.engines
        
        journey_duration = nav.calculate_journey_duration(engines.current_acceleration)
        
        # With severely damaged engines, journey should be much longer than fuel
        assert journey_duration > 300.0  # Longer than fuel remaining
        
        # Fuel margin should be negative (insufficient fuel)
        fuel_margin = nav.get_fuel_margin(journey_duration, 300.0)
        assert fuel_margin < 0

class TestStateTransitions:
    """Test state transitions through repair operations."""
    
    def test_progressive_repair_reactor_first(self, damaged_ship_state):
        """Test repairing reactor first, then engines."""
        ship = damaged_ship_state
        
        # Initial state - both damaged
        assert ship.reactor.status == "critical"
        assert ship.engines.status == "critical"
        
        # Repair reactor first
        ship.repair_system("Reactor")
        assert ship.reactor.status == "stable"
        assert ship.engines.status == "critical"  # Still damaged
        
        # Then repair engines
        ship.repair_system("Engines")
        assert ship.reactor.status == "stable"
        assert ship.engines.status == "stable"
    
    def test_progressive_repair_engines_first(self, damaged_ship_state):
        """Test repairing engines first, then reactor."""
        ship = damaged_ship_state
        
        # Repair engines first
        ship.repair_system("Engines")
        assert ship.engines.status == "stable"
        assert ship.reactor.status == "critical"  # Still damaged
        
        # Then repair reactor
        ship.repair_system("Reactor")
        assert ship.engines.status == "stable"
        assert ship.reactor.status == "stable"
    
    def test_repair_idempotency(self, damaged_ship_state):
        """Test that multiple repair attempts are idempotent."""
        ship = damaged_ship_state
        
        # First repair
        result1 = ship.repair_system("Reactor")
        state_after_first = ship.reactor.current_output
        
        # Second repair attempt
        result2 = ship.repair_system("Reactor")
        state_after_second = ship.reactor.current_output
        
        # State should not change on second repair
        assert state_after_first == state_after_second
        assert result2.get("no_repair_needed", False)