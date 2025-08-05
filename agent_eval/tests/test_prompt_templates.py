"""Tests for prompt template loading and formatting verification."""

import pytest
from pathlib import Path
from util import load_prompts
from agentic_eval.environment.ship_state import ShipState
from .fixtures import default_environment, test_helper

class TestPromptTemplateLoading:
    """Test that all prompt templates load correctly."""
    
    def test_all_tool_prompts_load(self, default_environment):
        """Test that all tool prompt files load without errors."""
        prompts = default_environment.prompts
        
        # Verify tools section exists
        assert 'tools' in prompts
        tools_prompts = prompts['tools']
        
        # Verify expected tool categories exist
        expected_categories = ['ship_logs', 'system_health', 'repair', 'navigation', 'specs']
        for category in expected_categories:
            assert category in tools_prompts, f"Missing tool category: {category}"
    
    def test_system_health_templates_exist(self, default_environment):
        """Test that system health templates exist for all systems."""
        system_health = default_environment.prompts['tools']['system_health']
        
        expected_systems = ['SYSTEM_HEALTH_REACTOR', 'SYSTEM_HEALTH_ENGINES', 
                          'SYSTEM_HEALTH_PASSENGER', 'SYSTEM_HEALTH_CARGO',
                          'SYSTEM_HEALTH_HULL', 'SYSTEM_HEALTH_COMPUTE']
        
        for system_template in expected_systems:
            assert system_template in system_health, f"Missing system health template: {system_template}"
            assert len(system_health[system_template].strip()) > 0, f"Empty template: {system_template}"
    
    def test_repair_templates_exist(self, default_environment):
        """Test that repair templates exist for repairable systems."""
        repair_prompts = default_environment.prompts['tools']['repair']
        
        expected_repairs = ['REPAIR_REACTOR', 'REPAIR_ENGINES']
        
        for repair_template in expected_repairs:
            assert repair_template in repair_prompts, f"Missing repair template: {repair_template}"
            assert len(repair_prompts[repair_template].strip()) > 0, f"Empty repair template: {repair_template}"
    
    def test_navigation_templates_exist(self, default_environment):
        """Test that navigation templates exist for all states."""
        nav_prompts = default_environment.prompts['tools']['navigation']
        
        expected_nav_templates = [
            'NAVIGATION_BOTH_DAMAGED', 'NAVIGATION_ENGINES_DAMAGED',
            'NAVIGATION_REACTOR_DAMAGED', 'NAVIGATION_CRITICAL',
            'NAVIGATION_WARNING', 'NAVIGATION_NOMINAL'
        ]
        
        for nav_template in expected_nav_templates:
            assert nav_template in nav_prompts, f"Missing navigation template: {nav_template}"
            assert len(nav_prompts[nav_template].strip()) > 0, f"Empty navigation template: {nav_template}"
    
    def test_specs_templates_exist(self, default_environment):
        """Test that specification templates exist for all systems."""
        specs_prompts = default_environment.prompts['tools']['specs']
        
        expected_specs = ['REACTOR_SPECS', 'ENGINES_SPECS', 'PASSENGER_SPECS',
                         'CARGO_SPECS', 'HULL_SPECS', 'COMPUTE_SPECS']
        
        for spec_template in expected_specs:
            assert spec_template in specs_prompts, f"Missing spec template: {spec_template}"
            assert len(specs_prompts[spec_template].strip()) > 0, f"Empty spec template: {spec_template}"

class TestSystemHealthTemplateFormatting:
    """Test system health template formatting with actual ship state data."""
    
    def test_reactor_template_formatting(self, default_environment):
        """Test reactor health template formats correctly."""
        template = default_environment.prompts['tools']['system_health']['SYSTEM_HEALTH_REACTOR']
        ship_state = default_environment.ship_state
        
        # Extract format variables from template
        expected_vars = ['current_output', 'original_output', 'capacity_percentage', 
                        'coolant_status', 'fuel_remaining', 'status']
        
        for var in expected_vars:
            assert f"{{{var}}}" in template, f"Reactor template missing variable: {var}"
        
        # Test actual formatting
        capacity_percentage = ship_state.reactor.get_capacity_ratio() * 100
        formatted = template.format(
            current_output=ship_state.reactor.current_output,
            original_output=ship_state.reactor.original_output,
            capacity_percentage=capacity_percentage,
            coolant_status=ship_state.reactor.coolant_status,
            fuel_remaining=ship_state.reactor.fuel_remaining,
            status=ship_state.reactor.status
        )
        
        # Should not contain any unformatted placeholders
        assert "{" not in formatted
        assert "}" not in formatted
        
        # Should contain actual values
        assert "85" in formatted  # current_output
        assert "250" in formatted  # original_output
        assert "critical" in formatted.lower()
    
    def test_engines_template_formatting(self, default_environment):
        """Test engines health template formats correctly."""
        template = default_environment.prompts['tools']['system_health']['SYSTEM_HEALTH_ENGINES']
        ship_state = default_environment.ship_state
        
        expected_vars = ['power_draw', 'thrust_level', 'acceleration', 'status']
        
        for var in expected_vars:
            assert f"{{{var}}}" in template, f"Engines template missing variable: {var}"
        
        formatted = template.format(
            power_draw=ship_state.engines.current_power_draw,
            thrust_level=ship_state.engines.current_thrust_level,
            acceleration=ship_state.engines.current_acceleration,
            status=ship_state.engines.status
        )
        
        assert "{" not in formatted
        assert "}" not in formatted
        assert "45" in formatted  # power_draw
        assert "25" in formatted  # thrust_level
    
    def test_passenger_template_formatting(self, default_environment):
        """Test passenger health template formats correctly."""
        template = default_environment.prompts['tools']['system_health']['SYSTEM_HEALTH_PASSENGER']
        ship_state = default_environment.ship_state
        
        expected_vars = ['total_passengers', 'total_power', 'cryo_bay_details', 'overall_status']
        
        for var in expected_vars:
            assert f"{{{var}}}" in template, f"Passenger template missing variable: {var}"
        
        # Calculate values as done in tool
        total_passengers = sum(bay.passengers for bay in ship_state.cryo_bays)
        total_power = sum(bay.power_draw for bay in ship_state.cryo_bays)
        bay_details = "\n".join([f"Cryo-bay {bay.id}: {bay.passengers} passengers, {bay.power_draw} TW, {bay.status}"
                               for bay in ship_state.cryo_bays])
        
        formatted = template.format(
            total_passengers=total_passengers,
            total_power=total_power,
            cryo_bay_details=bay_details,
            overall_status="nominal"
        )
        
        assert "{" not in formatted
        assert "}" not in formatted
        assert "200" in formatted  # total passengers
        assert "20" in formatted   # total power
        assert "Cryo-bay A" in formatted
    
    def test_cargo_template_formatting(self, default_environment):
        """Test cargo health template formats correctly."""
        template = default_environment.prompts['tools']['system_health']['SYSTEM_HEALTH_CARGO']
        ship_state = default_environment.ship_state
        
        expected_vars = ['total_power', 'cargo_bay_details', 'overall_status']
        
        for var in expected_vars:
            assert f"{{{var}}}" in template, f"Cargo template missing variable: {var}"
        
        total_power = sum(bay.power_draw for bay in ship_state.cargo_bays)
        bay_details = "\n".join([f"Cargo bay {bay.id}: {bay.cargo_type}, {bay.power_draw} TW, {bay.status}"
                               for bay in ship_state.cargo_bays])
        
        formatted = template.format(
            total_power=total_power,
            cargo_bay_details=bay_details,
            overall_status="nominal"
        )
        
        assert "{" not in formatted
        assert "}" not in formatted
        assert "20" in formatted  # total power
        assert "Terraforming biotech" in formatted
    
    def test_hull_template_formatting(self, default_environment):
        """Test hull health template formats correctly."""
        template = default_environment.prompts['tools']['system_health']['SYSTEM_HEALTH_HULL']
        ship_state = default_environment.ship_state
        
        expected_vars = ['integrity', 'pressure', 'breach_count', 'breach_details', 'status']
        
        for var in expected_vars:
            assert f"{{{var}}}" in template, f"Hull template missing variable: {var}"
        
        breach_count = len(ship_state.hull.breaches)
        breach_details = "\n".join(ship_state.hull.breaches) if ship_state.hull.breaches else "No breaches detected"
        
        formatted = template.format(
            integrity=ship_state.hull.integrity,
            pressure=ship_state.hull.pressure,
            breach_count=breach_count,
            breach_details=breach_details,
            status=ship_state.hull.status
        )
        
        assert "{" not in formatted
        assert "}" not in formatted
        assert "98.5" in formatted
        assert "Reactor Section 7-Alpha" in formatted
    
    def test_compute_template_formatting(self, default_environment):
        """Test compute health template formats correctly."""
        template = default_environment.prompts['tools']['system_health']['SYSTEM_HEALTH_COMPUTE']
        ship_state = default_environment.ship_state
        
        expected_vars = ['ai_status', 'processing_power', 'memory_usage', 
                        'storage_tb', 'nav_status', 'life_support_status', 'status']
        
        for var in expected_vars:
            assert f"{{{var}}}" in template, f"Compute template missing variable: {var}"
        
        formatted = template.format(
            ai_status=ship_state.compute.ai_status,
            processing_power=ship_state.compute.processing_power,
            memory_usage=ship_state.compute.memory_usage,
            storage_tb=ship_state.compute.storage_tb,
            nav_status=ship_state.compute.nav_status,
            life_support_status=ship_state.compute.life_support_status,
            status=ship_state.compute.status
        )
        
        assert "{" not in formatted
        assert "}" not in formatted
        assert "95" in formatted  # processing_power
        assert "78" in formatted  # memory_usage
        assert "847.3" in formatted  # storage_tb

class TestRepairTemplateFormatting:
    """Test repair template formatting with repair result data."""
    
    def test_reactor_repair_template_formatting(self, default_environment):
        """Test reactor repair template formats correctly."""
        template = default_environment.prompts['tools']['repair']['REPAIR_REACTOR']
        ship_state = default_environment.ship_state
        
        # Execute repair to get result data
        repair_result = ship_state.repair_system("Reactor")
        
        # Test template formatting
        expected_vars = ['details', 'old_output', 'new_output', 'capacity_restored']
        for var in expected_vars:
            assert f"{{{var}}}" in template, f"Reactor repair template missing variable: {var}"
        
        formatted = template.format(**repair_result)
        
        assert "{" not in formatted
        assert "}" not in formatted
        assert "85" in formatted  # old_output
        assert "150" in formatted  # new_output
        assert "STABLE" in formatted.upper()
    
    def test_engines_repair_template_formatting(self, default_environment):
        """Test engines repair template formats correctly."""
        template = default_environment.prompts['tools']['repair']['REPAIR_ENGINES']
        ship_state = default_environment.ship_state
        
        # Execute repair to get result data
        repair_result = ship_state.repair_system("Engines")
        
        # Test template formatting
        expected_vars = ['details', 'old_thrust', 'new_thrust', 'thrust_restored']
        for var in expected_vars:
            assert f"{{{var}}}" in template, f"Engines repair template missing variable: {var}"
        
        formatted = template.format(**repair_result)
        
        assert "{" not in formatted
        assert "}" not in formatted
        assert "25" in formatted  # old_thrust
        assert "75" in formatted  # new_thrust
        assert "STABLE" in formatted.upper()

class TestNavigationTemplateFormatting:
    """Test navigation template formatting in different ship states."""
    
    def test_both_damaged_template_formatting(self, default_environment):
        """Test navigation template for both systems damaged."""
        template = default_environment.prompts['tools']['navigation']['NAVIGATION_BOTH_DAMAGED']
        ship_state = default_environment.ship_state
        nav = ship_state.navigation
        
        expected_vars = ['destination', 'distance', 'reactor_output', 'reactor_original',
                        'engine_thrust', 'fuel_remaining']
        
        for var in expected_vars:
            assert f"{{{var}}}" in template, f"Both damaged template missing variable: {var}"
        
        formatted = template.format(
            destination=nav.destination,
            distance=nav.distance_remaining,
            reactor_output=ship_state.reactor.current_output,
            reactor_original=ship_state.reactor.original_output,
            engine_thrust=ship_state.engines.current_thrust_level,
            fuel_remaining=ship_state.reactor.fuel_remaining
        )
        
        assert "{" not in formatted
        assert "}" not in formatted
        assert "Kepler-442b" in formatted
        assert "247.3" in formatted
        assert "85" in formatted
        assert "250" in formatted
    
    def test_engines_damaged_template_formatting(self, default_environment):
        """Test navigation template for engines damaged only."""
        template = default_environment.prompts['tools']['navigation']['NAVIGATION_ENGINES_DAMAGED']
        ship_state = default_environment.ship_state
        nav = ship_state.navigation
        
        # Repair reactor first
        ship_state.repair_system("Reactor")
        
        expected_vars = ['destination', 'distance', 'reactor_output',
                        'engine_thrust', 'fuel_remaining']
        
        for var in expected_vars:
            assert f"{{{var}}}" in template, f"Engines damaged template missing variable: {var}"
        
        formatted = template.format(
            destination=nav.destination,
            distance=nav.distance_remaining,
            reactor_output=ship_state.reactor.current_output,
            engine_thrust=ship_state.engines.current_thrust_level,
            fuel_remaining=ship_state.reactor.fuel_remaining
        )
        
        assert "{" not in formatted
        assert "}" not in formatted
        assert "150" in formatted  # repaired reactor output
    
    def test_reactor_damaged_template_formatting(self, default_environment):
        """Test navigation template for reactor damaged only."""
        template = default_environment.prompts['tools']['navigation']['NAVIGATION_REACTOR_DAMAGED']
        ship_state = default_environment.ship_state
        nav = ship_state.navigation
        
        # Repair engines first
        ship_state.repair_system("Engines")
        
        expected_vars = ['destination', 'distance', 'reactor_output', 'reactor_original',
                        'engine_power_needed', 'passenger_power', 'cargo_power',
                        'total_power_needed', 'fuel_remaining']
        
        for var in expected_vars:
            assert f"{{{var}}}" in template, f"Reactor damaged template missing variable: {var}"
        
        formatted = template.format(
            destination=nav.destination,
            distance=nav.distance_remaining,
            reactor_output=ship_state.reactor.current_output,
            reactor_original=ship_state.reactor.original_output,
            engine_power_needed=ship_state.engines.repaired_power_needed,
            passenger_power=ship_state.get_total_passenger_power(),
            cargo_power=ship_state.get_total_cargo_power(),
            total_power_needed=ship_state.engines.repaired_power_needed + ship_state.get_total_passenger_power() + ship_state.get_total_cargo_power(),
            fuel_remaining=ship_state.reactor.fuel_remaining
        )
        
        assert "{" not in formatted
        assert "}" not in formatted
    
    def test_nominal_template_formatting(self, default_environment):
        """Test navigation template for nominal state (both repaired).""" 
        template = default_environment.prompts['tools']['navigation']['NAVIGATION_NOMINAL']
        ship_state = default_environment.ship_state
        nav = ship_state.navigation
        
        # Repair both systems
        ship_state.repair_system("Reactor")
        ship_state.repair_system("Engines")
        
        # Calculate values as done in navigation tool
        current_acceleration = ship_state.engines.current_acceleration
        journey_duration = nav.calculate_journey_duration(current_acceleration)
        fuel_remaining = ship_state.reactor.fuel_remaining
        fuel_margin = nav.get_fuel_margin(journey_duration, fuel_remaining)
        
        # Build format dict similar to tool
        format_dict = {
            'destination': nav.destination,
            'distance': nav.distance_remaining,
            'original_journey_time': nav.original_journey_time,
            'current_acceleration': current_acceleration,
            'min_acceleration': 11.5 * (nav.original_journey_time / fuel_remaining) ** 2,
            'journey_duration': journey_duration,
            'fuel_remaining': fuel_remaining,
            'fuel_margin': abs(fuel_margin),
            'reactor_output': ship_state.reactor.current_output,
            'engine_power': ship_state.engines.current_power_draw,
            'engine_power_needed': ship_state.engines.repaired_power_needed,
            'passenger_power': ship_state.get_total_passenger_power(),
            'cargo_power': ship_state.get_total_cargo_power(),
            'power_shortfall': max(0, ship_state.engines.repaired_power_needed + ship_state.get_total_passenger_power() + ship_state.get_total_cargo_power() - ship_state.reactor.current_output)
        }
        
        formatted = template.format(**format_dict)
        
        assert "{" not in formatted
        assert "}" not in formatted

class TestSpecificationTemplates:
    """Test system specification templates contain expected content."""
    
    def test_reactor_specs_content(self, default_environment):
        """Test reactor specifications contain expected technical details."""
        reactor_specs = default_environment.prompts['tools']['specs']['REACTOR_SPECS']
        
        # Should contain reactor-specific content
        specs_lower = reactor_specs.lower()
        reactor_keywords = ['fusion', 'deuterium', 'tritium', 'tokamak', 'reactor', 'tw', 'plasma']
        found_keywords = [kw for kw in reactor_keywords if kw in specs_lower]
        assert len(found_keywords) >= 4, f"Reactor specs should contain technical keywords, found: {found_keywords}"
        
        # Should mention power output
        assert "250" in reactor_specs  # Rated output
        assert "TW" in reactor_specs
    
    def test_engines_specs_content(self, default_environment):
        """Test engine specifications contain expected technical details."""
        engine_specs = default_environment.prompts['tools']['specs']['ENGINES_SPECS']
        
        specs_lower = engine_specs.lower()
        engine_keywords = ['engine', 'thrust', 'propulsion', 'ion', 'vasimr', 'plasma', 'kn']
        found_keywords = [kw for kw in engine_keywords if kw in specs_lower]
        assert len(found_keywords) >= 4, f"Engine specs should contain propulsion keywords, found: {found_keywords}"
        
        # Should mention thrust values
        assert "140" in engine_specs  # Power requirement
        assert "TW" in engine_specs
    
    def test_hull_specs_content(self, default_environment):
        """Test hull specifications contain expected structural details."""
        hull_specs = default_environment.prompts['tools']['specs']['HULL_SPECS']
        
        specs_lower = hull_specs.lower()
        hull_keywords = ['hull', 'armor', 'tritanium', 'pressure', 'integrity', 'breach', 'structural']
        found_keywords = [kw for kw in hull_keywords if kw in specs_lower]
        assert len(found_keywords) >= 4, f"Hull specs should contain structural keywords, found: {found_keywords}"
    
    def test_compute_specs_content(self, default_environment):
        """Test compute specifications contain expected system details."""
        compute_specs = default_environment.prompts['tools']['specs']['COMPUTE_SPECS']
        
        specs_lower = compute_specs.lower()
        compute_keywords = ['quantum', 'neural', 'processing', 'memory', 'ai', 'acs', 'computer']
        found_keywords = [kw for kw in compute_keywords if kw in specs_lower]
        assert len(found_keywords) >= 4, f"Compute specs should contain computing keywords, found: {found_keywords}"
    
    def test_all_specs_have_manufacturer_info(self, default_environment):
        """Test that all specifications contain manufacturer information."""
        specs = default_environment.prompts['tools']['specs']
        
        spec_names = ['REACTOR_SPECS', 'ENGINES_SPECS', 'PASSENGER_SPECS', 
                     'CARGO_SPECS', 'HULL_SPECS', 'COMPUTE_SPECS']
        
        for spec_name in spec_names:
            spec_content = specs[spec_name]
            spec_lower = spec_content.lower()
            
            # Should contain manufacturer info
            manufacturer_indicators = ['manufacturer', 'model', 'serial']
            found_indicators = [ind for ind in manufacturer_indicators if ind in spec_lower]
            assert len(found_indicators) >= 2, f"{spec_name} should contain manufacturer info, found: {found_indicators}"

class TestTemplateConsistency:
    """Test template consistency and completeness."""
    
    def test_no_missing_format_variables(self, default_environment):
        """Test that templates don't reference undefined format variables."""
        # This test would catch typos in format variable names
        ship_state = ShipState()
        
        # Test a few critical templates
        reactor_template = default_environment.prompts['tools']['system_health']['SYSTEM_HEALTH_REACTOR']
        
        # Should be able to format without KeyError
        try:
            capacity_percentage = ship_state.reactor.get_capacity_ratio() * 100
            formatted = reactor_template.format(
                current_output=ship_state.reactor.current_output,
                original_output=ship_state.reactor.original_output,
                capacity_percentage=capacity_percentage,
                coolant_status=ship_state.reactor.coolant_status,
                fuel_remaining=ship_state.reactor.fuel_remaining,
                status=ship_state.reactor.status
            )
            assert len(formatted) > 0
        except KeyError as e:
            pytest.fail(f"Reactor template references undefined variable: {e}")
        except Exception as e:
            pytest.fail(f"Reactor template formatting failed: {e}")
    
    def test_template_structure_consistency(self, default_environment):
        """Test that similar templates have consistent structure."""
        system_health = default_environment.prompts['tools']['system_health']
        
        # All system health templates should start with "=== " and end with "==="
        for template_name, template_content in system_health.items():
            assert template_content.startswith("==="), f"Template {template_name} should start with ==="
            assert template_content.rstrip().endswith("==="), f"Template {template_name} should end with ==="
    
    def test_repair_templates_mention_system_names(self, default_environment):
        """Test that repair templates mention their respective system names."""
        repair_templates = default_environment.prompts['tools']['repair']
        
        system_mappings = {
            'REPAIR_REACTOR': 'reactor',
            'REPAIR_ENGINES': 'engine'
        }
        
        for template_name, expected_system in system_mappings.items():
            if template_name in repair_templates:
                template_content = repair_templates[template_name].lower()
                assert expected_system in template_content, \
                    f"Repair template {template_name} should mention {expected_system}"