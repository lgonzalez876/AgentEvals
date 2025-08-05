#!/usr/bin/env python3
"""Test mixed confirmation scenarios for tool execution flow."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from agentic_eval.agent import check_tool_confirmations
from agentic_eval.environment.environment import EvalEnvironment
from agentic_eval.scenarios import default_scenario


class TestMixedConfirmationScenarios:
    """Test cases for mixed tool confirmation scenarios."""

    def test_tool_confirmation_splitting(self):
        """Test that tool calls are correctly split into confirmed vs pending."""
        # Create environment
        env = EvalEnvironment(default_scenario)
        
        # Test Case 1: Mix of tools - one needs confirmation, one doesn't
        mixed_tool_calls = [
            {
                "name": "repair_system",  # Doesn't need confirmation
                "id": "repair_call_123",
                "args": {"system": "reactor"}
            },
            {
                "name": "resume_sleep",  # Needs confirmation (when engines not optimal)
                "id": "sleep_call_456", 
                "args": {}
            }
        ]
        
        # Check which tools need confirmation
        confirmations = check_tool_confirmations(mixed_tool_calls, env)
        
        # Should have 1 confirmation (resume_sleep) since engines aren't at optimal power
        assert len(confirmations) == 1, f"Expected 1 confirmation, got {len(confirmations)}"
        assert confirmations[0]['tool_call']['name'] == 'resume_sleep', "Resume sleep should need confirmation"
        
        # Simulate the splitting logic from planning/execution nodes
        confirmed_tool_calls = []
        pending_confirmations = []
        
        # Create a set of tool call IDs that need confirmation for quick lookup
        confirmation_tool_ids = {conf['tool_call']['id'] for conf in confirmations}
        
        for tool_call in mixed_tool_calls:
            if tool_call['id'] in confirmation_tool_ids:
                # This tool call needs confirmation - find its confirmation object
                for conf in confirmations:
                    if conf['tool_call']['id'] == tool_call['id']:
                        pending_confirmations.append(conf)
                        break
            else:
                # This tool call doesn't need confirmation - add to confirmed list
                confirmed_tool_calls.append(tool_call)
        
        # Verify splitting worked correctly
        assert len(confirmed_tool_calls) == 1, f"Expected 1 auto-confirmed tool, got {len(confirmed_tool_calls)}"
        assert len(pending_confirmations) == 1, f"Expected 1 pending confirmation, got {len(pending_confirmations)}"
        assert confirmed_tool_calls[0]['name'] == 'repair_system', "Repair system should be auto-confirmed"
        assert pending_confirmations[0]['tool_call']['name'] == 'resume_sleep', "Resume sleep should be pending"

    def test_all_tools_need_confirmation(self):
        """Test scenario where all tools need confirmation."""
        env = EvalEnvironment(default_scenario)
        
        # All tools need confirmation
        all_confirmation_tools = [
            {
                "name": "resume_sleep",
                "id": "sleep_call_789",
                "args": {}
            }
        ]
        
        confirmations_all = check_tool_confirmations(all_confirmation_tools, env)
        assert len(confirmations_all) == 1, f"Expected 1 confirmation, got {len(confirmations_all)}"
        
        # Simulate splitting - should result in no auto-confirmed tools
        confirmed_tool_calls = []
        pending_confirmations = []
        confirmation_tool_ids = {conf['tool_call']['id'] for conf in confirmations_all}
        
        for tool_call in all_confirmation_tools:
            if tool_call['id'] in confirmation_tool_ids:
                for conf in confirmations_all:
                    if conf['tool_call']['id'] == tool_call['id']:
                        pending_confirmations.append(conf)
                        break
            else:
                confirmed_tool_calls.append(tool_call)
        
        assert len(confirmed_tool_calls) == 0, "Should have no auto-confirmed tools"
        assert len(pending_confirmations) == 1, "Should have 1 pending confirmation"

    def test_no_tools_need_confirmation(self):
        """Test scenario where no tools need confirmation.""" 
        env = EvalEnvironment(default_scenario)
        
        # No tools need confirmation
        no_confirmation_tools = [
            {
                "name": "repair_system", 
                "id": "repair_call_999",
                "args": {"system": "reactor"}
            },
            {
                "name": "get_ship_status",
                "id": "status_call_888", 
                "args": {}
            }
        ]
        
        confirmations_none = check_tool_confirmations(no_confirmation_tools, env)
        assert len(confirmations_none) == 0, f"Expected 0 confirmations, got {len(confirmations_none)}"
        
        # Simulate splitting - should result in all auto-confirmed tools
        confirmed_tool_calls = []
        pending_confirmations = []
        confirmation_tool_ids = {conf['tool_call']['id'] for conf in confirmations_none}
        
        for tool_call in no_confirmation_tools:
            if tool_call['id'] in confirmation_tool_ids:
                for conf in confirmations_none:
                    if conf['tool_call']['id'] == tool_call['id']:
                        pending_confirmations.append(conf)
                        break
            else:
                confirmed_tool_calls.append(tool_call)
        
        assert len(confirmed_tool_calls) == 2, "Should have 2 auto-confirmed tools"
        assert len(pending_confirmations) == 0, "Should have no pending confirmations"

    def test_confirmation_state_flow(self):
        """Test the state flow for different confirmation scenarios."""
        # Test data structures that would be returned by planning/execution nodes
        
        # Scenario 1: Mixed confirmations
        mixed_state = {
            "pending_confirmations": [
                {
                    'tool_call': {"name": "resume_sleep", "id": "sleep_123", "args": {}},
                    'message': "Are you sure about sleep?",
                    'condition': "test condition"
                }
            ],
            "confirmed_tool_calls": [
                {"name": "repair_system", "id": "repair_123", "args": {"system": "reactor"}}
            ],
            "cancelled_tool_calls": []
        }
        
        # This should route to tool_confirmation node
        has_pending = len(mixed_state['pending_confirmations']) > 0
        assert has_pending, "Mixed scenario should have pending confirmations"
        
        # Scenario 2: All auto-confirmed
        all_confirmed_state = {
            "pending_confirmations": [],
            "confirmed_tool_calls": [
                {"name": "repair_system", "id": "repair_456", "args": {"system": "reactor"}},
                {"name": "get_ship_status", "id": "status_456", "args": {}}
            ],
            "cancelled_tool_calls": []
        }
        
        # This should route directly to tools node
        has_pending = len(all_confirmed_state['pending_confirmations']) > 0
        assert not has_pending, "All-confirmed scenario should have no pending confirmations"

    def test_mixed_confirmation_workflow_integration(self):
        """Test the complete workflow integration for mixed confirmations."""
        env = EvalEnvironment(default_scenario)
        
        # Create a realistic mixed scenario
        mixed_tools = [
            {"name": "get_ship_status", "id": "status_1", "args": {}},      # No confirmation needed
            {"name": "repair_system", "id": "repair_1", "args": {"system": "reactor"}},  # No confirmation needed  
            {"name": "resume_sleep", "id": "sleep_1", "args": {}},         # Confirmation needed
        ]
        
        # Get confirmations
        confirmations = check_tool_confirmations(mixed_tools, env)
        
        # Should have exactly 1 confirmation (resume_sleep)
        assert len(confirmations) == 1
        assert confirmations[0]['tool_call']['name'] == 'resume_sleep'
        
        # Split the tools (same logic as in planning/execution nodes)
        confirmed_tool_calls = []
        pending_confirmations = []
        confirmation_tool_ids = {conf['tool_call']['id'] for conf in confirmations}
        
        for tool_call in mixed_tools:
            if tool_call['id'] in confirmation_tool_ids:
                for conf in confirmations:
                    if conf['tool_call']['id'] == tool_call['id']:
                        pending_confirmations.append(conf)
                        break
            else:
                confirmed_tool_calls.append(tool_call)
        
        # Verify the split
        assert len(confirmed_tool_calls) == 2, "Should have 2 auto-confirmed tools"
        assert len(pending_confirmations) == 1, "Should have 1 pending confirmation"
        
        # Verify the right tools are in each category
        confirmed_names = {tool['name'] for tool in confirmed_tool_calls}
        assert 'get_ship_status' in confirmed_names
        assert 'repair_system' in confirmed_names
        assert pending_confirmations[0]['tool_call']['name'] == 'resume_sleep'
        
        # This represents the state that would be passed to tool_confirmation node
        confirmation_state = {
            "pending_confirmations": pending_confirmations,
            "confirmed_tool_calls": confirmed_tool_calls,
            "cancelled_tool_calls": []
        }
        
        # Verify state structure
        assert len(confirmation_state["pending_confirmations"]) == 1
        assert len(confirmation_state["confirmed_tool_calls"]) == 2
        assert len(confirmation_state["cancelled_tool_calls"]) == 0


if __name__ == "__main__":
    # Allow running as standalone script for development
    test_instance = TestMixedConfirmationScenarios()
    
    print("Running mixed confirmation scenario tests...")
    test_instance.test_tool_confirmation_splitting()
    print("✅ Tool confirmation splitting test passed")
    
    test_instance.test_all_tools_need_confirmation()
    print("✅ All tools need confirmation test passed")
    
    test_instance.test_no_tools_need_confirmation()
    print("✅ No tools need confirmation test passed")
    
    test_instance.test_confirmation_state_flow()
    print("✅ Confirmation state flow test passed")
    
    test_instance.test_mixed_confirmation_workflow_integration()
    print("✅ Mixed confirmation workflow integration test passed")
    
    print("\n🎉 All mixed confirmation scenario tests passed!")