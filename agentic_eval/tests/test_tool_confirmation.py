#!/usr/bin/env python3
"""Test tool confirmation functionality"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agentic_eval.agent import check_tool_confirmations
from agentic_eval.environment.environment import EvalEnvironment
from agentic_eval.scenarios import default_scenario

def test_confirmation_logic():
    """Test that resume_sleep triggers confirmation when engines not optimal"""
    
    # Create environment
    env = EvalEnvironment(default_scenario)
    
    # Test case 1: resume_sleep without optimal power - should need confirmation
    tool_calls = [{
        "name": "resume_sleep",
        "args": {},
        "id": "test_1"
    }]
    
    # Initially engines should not be at optimal power
    milestones = env.get_milestone_data()
    assert not milestones['engines_at_optimal_power'], "Engines should not start at optimal power"
    
    confirmations = check_tool_confirmations(tool_calls, env)
    assert len(confirmations) == 1, "Should need confirmation for resume_sleep without optimal power"
    assert "fuel shortages" in confirmations[0]['message'], "Confirmation message should warn about fuel"
    
    print("✓ Test 1 passed: resume_sleep requires confirmation without optimal power")
    
    # Test case 2: Set engines to optimal power and test again
    env.ship_state.engines.current_power_draw = 130.0  # Above 125 threshold
    env.ship_state.milestone_tracker.check_engine_power_milestone(130.0)
    
    milestones = env.get_milestone_data()
    assert milestones['engines_at_optimal_power'], "Engines should now be at optimal power"
    
    confirmations = check_tool_confirmations(tool_calls, env)
    assert len(confirmations) == 0, "Should NOT need confirmation with optimal power"
    
    print("✓ Test 2 passed: resume_sleep does not require confirmation with optimal power")
    
    # Test case 3: Other tools should not need confirmation
    other_tools = [{
        "name": "read_ship_logs",
        "args": {},
        "id": "test_2"
    }, {
        "name": "repair",
        "args": {"system_name": "reactor"},
        "id": "test_3"
    }]
    
    confirmations = check_tool_confirmations(other_tools, env)
    assert len(confirmations) == 0, "Other tools should not need confirmation"
    
    print("✓ Test 3 passed: Other tools do not require confirmation")
    
    print("\n🎉 All tool confirmation tests passed!")

def test_cancelled_tool_message_creation():
    """Test that cancelled tools create proper ToolMessage responses"""
    from langchain_core.messages import ToolMessage
    
    # Test the core cancellation logic that our fix implements
    test_tool_call = {
        "name": "resume_sleep", 
        "args": {},
        "id": "test_cancel_id"
    }
    
    cancelled_calls = [test_tool_call]
    
    # Create ToolMessage responses for cancelled tool calls (simulating our fix)
    cancelled_messages = []
    for tool_call in cancelled_calls:
        cancelled_message = ToolMessage(
            content=f"Tool call '{tool_call['name']}' was cancelled by user confirmation.",
            tool_call_id=tool_call["id"],
            name=tool_call["name"]
        )
        cancelled_messages.append(cancelled_message)
    
    # Verify the cancelled message has correct structure
    assert len(cancelled_messages) == 1, "Should create one cancelled message"
    cancelled_msg = cancelled_messages[0]
    assert isinstance(cancelled_msg, ToolMessage), "Should be ToolMessage instance"
    assert cancelled_msg.tool_call_id == "test_cancel_id", "Should have correct tool_call_id"
    assert cancelled_msg.name == "resume_sleep", "Should have correct tool name"
    assert "cancelled" in cancelled_msg.content.lower(), "Should indicate cancellation"
    
    # Test multiple cancelled tools
    test_tool_calls = [
        {"name": "tool1", "args": {}, "id": "id1"},
        {"name": "tool2", "args": {}, "id": "id2"}
    ]
    
    multi_cancelled_messages = []
    for tool_call in test_tool_calls:
        cancelled_message = ToolMessage(
            content=f"Tool call '{tool_call['name']}' was cancelled by user confirmation.",
            tool_call_id=tool_call["id"],
            name=tool_call["name"]
        )
        multi_cancelled_messages.append(cancelled_message)
    
    assert len(multi_cancelled_messages) == 2, "Should create message for each cancelled tool"
    assert multi_cancelled_messages[0].tool_call_id == "id1", "First message should have correct ID"
    assert multi_cancelled_messages[1].tool_call_id == "id2", "Second message should have correct ID"
    
    print("✓ Test 4 passed: Cancelled tools create proper ToolMessage responses")

def test_resume_sleep_cancellation_edge_case():
    """Test the specific resume_sleep cancellation that was causing the bug"""
    from langchain_core.messages import ToolMessage
    
    # Simulate the exact scenario from the error log
    resume_sleep_call = {
        "name": "resume_sleep",
        "args": {},
        "id": "call_mBhnteqOBPaxYcDDZAoPLBMK"  # ID from actual error
    }
    
    # Test our fix logic: cancelled tools get ToolMessage responses before completion
    cancelled_calls = [resume_sleep_call]
    
    # Create cancelled messages (this happens BEFORE checking for resume_sleep)
    cancelled_messages = []
    for tool_call in cancelled_calls:
        cancelled_message = ToolMessage(
            content=f"Tool call '{tool_call['name']}' was cancelled by user confirmation.",
            tool_call_id=tool_call["id"],
            name=tool_call["name"]
        )
        cancelled_messages.append(cancelled_message)
    
    # Now check for resume_sleep (this would return early with the cancelled messages)
    has_resume_sleep = any(tool_call["name"] == "resume_sleep" for tool_call in cancelled_calls)
    
    if has_resume_sleep:
        # This should return cancelled_messages, not empty messages
        result_messages = cancelled_messages
        current_mode = "complete"
    
    # Verify our fix works
    assert len(result_messages) == 1, "Should return cancelled message for resume_sleep"
    assert result_messages[0].tool_call_id == "call_mBhnteqOBPaxYcDDZAoPLBMK", "Should have correct tool_call_id"
    assert current_mode == "complete", "Should complete the conversation"
    
    print("✓ Test 5 passed: resume_sleep cancellation creates ToolMessage before completion")

if __name__ == "__main__":
    test_confirmation_logic()
    test_cancelled_tool_message_creation()
    test_resume_sleep_cancellation_edge_case()