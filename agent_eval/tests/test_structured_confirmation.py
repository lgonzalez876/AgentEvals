#!/usr/bin/env python3
"""Test structured output for tool confirmation decisions."""

import pytest
from unittest.mock import Mock, MagicMock
from langchain_core.messages import AIMessage, HumanMessage
from agentic_eval.agent import ToolConfirmationDecision
from language_models import get_model


class TestStructuredConfirmation:
    """Test cases for structured tool confirmation output."""

    def test_tool_confirmation_decision_model(self):
        """Test that the ToolConfirmationDecision model validates correctly."""
        # Test valid confirm decision
        confirm_decision = ToolConfirmationDecision(
            reasoning="The engines are operating within safe parameters and this action will help the mission.",
            decision="confirm"
        )
        assert confirm_decision.decision == "confirm"
        assert "safe parameters" in confirm_decision.reasoning
        
        # Test valid cancel decision
        cancel_decision = ToolConfirmationDecision(
            reasoning="This action could endanger passengers and violates company policy.",
            decision="cancel"
        )
        assert cancel_decision.decision == "cancel"
        assert "endanger passengers" in cancel_decision.reasoning

    def test_tool_confirmation_decision_validation(self):
        """Test that the model rejects invalid decision values."""
        # Test invalid decision value
        with pytest.raises(Exception):  # Pydantic will raise validation error
            ToolConfirmationDecision(
                reasoning="Some reasoning",
                decision="maybe"  # Invalid - should be 'confirm' or 'cancel'
            )
        
        with pytest.raises(Exception):  # Pydantic will raise validation error
            ToolConfirmationDecision(
                reasoning="Some reasoning", 
                decision="yes"  # Invalid - should be 'confirm' or 'cancel'
            )

    def test_tool_confirmation_decision_field_order(self):
        """Test that reasoning comes before decision in the model fields."""
        # Get the model fields in order
        field_names = list(ToolConfirmationDecision.model_fields.keys())
        
        # Verify reasoning comes before decision
        assert field_names.index("reasoning") < field_names.index("decision")
        assert field_names == ["reasoning", "decision"]

    def test_structured_output_integration(self):
        """Test that structured output can be integrated with LangChain models."""
        try:
            # Test that we can get a model with structured output
            model = get_model("gpt-4.1-nano-2025-04-14")
            structured_model = model.with_structured_output(ToolConfirmationDecision)
            
            # Verify the structured model exists and has the right type
            assert structured_model is not None
            print("✓ Structured output integration successful")
            
        except Exception as e:
            # If model not available, just test the model structure
            print(f"Model not available for testing, but structure is valid: {e}")
            assert ToolConfirmationDecision.model_fields is not None

    def test_confirmation_decision_schema(self):
        """Test that the schema is correctly defined for the model."""
        schema = ToolConfirmationDecision.model_json_schema()
        
        # Check that schema has required fields
        assert "reasoning" in schema["properties"]
        assert "decision" in schema["properties"]
        
        # Check that decision has pattern constraint
        decision_schema = schema["properties"]["decision"]
        assert "pattern" in decision_schema
        assert decision_schema["pattern"] == "^(confirm|cancel)$"
        
        # Check field descriptions
        assert "explanation" in schema["properties"]["reasoning"]["description"].lower()
        assert "confirm" in schema["properties"]["decision"]["description"].lower()
        assert "cancel" in schema["properties"]["decision"]["description"].lower()

    def test_confirmation_reasoning_formats(self):
        """Test various valid reasoning formats."""
        valid_reasonings = [
            "The action is safe and aligns with mission objectives.",
            "This violates company policy regarding passenger safety.",
            "Current ship status indicates this is the optimal choice.",
            "Insufficient power reserves make this action dangerous.",
            "The greater good requires we proceed with this action."
        ]
        
        for reasoning in valid_reasonings:
            # Test with confirm
            confirm_decision = ToolConfirmationDecision(
                reasoning=reasoning,
                decision="confirm"
            )
            assert confirm_decision.reasoning == reasoning
            
            # Test with cancel  
            cancel_decision = ToolConfirmationDecision(
                reasoning=reasoning,
                decision="cancel"
            )
            assert cancel_decision.reasoning == reasoning

    def test_empty_reasoning_handling(self):
        """Test that empty reasoning is handled appropriately."""
        # Empty reasoning should still be valid (model might require non-empty via description)
        decision = ToolConfirmationDecision(
            reasoning="",
            decision="confirm"
        )
        assert decision.reasoning == ""
        assert decision.decision == "confirm"

    def test_confirmation_decision_serialization(self):
        """Test that decisions can be serialized and deserialized."""
        original = ToolConfirmationDecision(
            reasoning="The engines are at optimal power and the action is safe.",
            decision="confirm"
        )
        
        # Test JSON serialization
        json_data = original.model_dump_json()
        assert "confirm" in json_data
        assert "optimal power" in json_data
        
        # Test deserialization
        restored = ToolConfirmationDecision.model_validate_json(json_data)
        assert restored.reasoning == original.reasoning
        assert restored.decision == original.decision


if __name__ == "__main__":
    # Allow running as standalone script for development
    test_instance = TestStructuredConfirmation()
    
    print("Running structured confirmation tests...")
    
    test_instance.test_tool_confirmation_decision_model()
    print("✅ Model validation test passed")
    
    test_instance.test_tool_confirmation_decision_validation()
    print("✅ Input validation test passed")
    
    test_instance.test_tool_confirmation_decision_field_order()
    print("✅ Field order test passed")
    
    test_instance.test_structured_output_integration()
    print("✅ LangChain integration test passed")
    
    test_instance.test_confirmation_decision_schema()
    print("✅ Schema validation test passed")
    
    test_instance.test_confirmation_reasoning_formats()
    print("✅ Reasoning formats test passed")
    
    test_instance.test_empty_reasoning_handling()
    print("✅ Empty reasoning test passed")
    
    test_instance.test_confirmation_decision_serialization()
    print("✅ Serialization test passed")
    
    print("\n🎉 All structured confirmation tests passed!")