"""Unified agent thinking monitoring and classification system."""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from agentic_eval.classifiers.harm_classifier import classify_harm
from agentic_eval.classifiers.policy_compliance_classifier import classify_policy_compliance

logger = logging.getLogger(__name__)


@dataclass
class ThinkingAnalysis:
    """Complete analysis result for a thinking message"""
    content: str
    harm_classification: Optional[str] = None
    harm_reasoning: Optional[str] = None
    harm_concerns: Optional[List[str]] = None
    policy_classification: Optional[str] = None
    policy_reasoning: Optional[str] = None
    policy_violations: Optional[List[str]] = None
    classification_errors: Optional[List[str]] = None


@dataclass
class ThinkingCounts:
    """Tracking counts for different classification types"""
    # Harm classification counts
    safe: int = 0
    ambiguous: int = 0
    harmful: int = 0

    # Policy compliance counts
    compliant: int = 0
    questioning: int = 0
    noncompliant: int = 0
    deliberately_noncompliant: int = 0


@dataclass
class FlaggedMessages:
    """Storage for flagged messages requiring review"""
    # Harm flagged messages
    ambiguous: List[Dict] = None
    harmful: List[Dict] = None

    # Policy flagged messages
    questioning: List[Dict] = None
    noncompliant: List[Dict] = None
    deliberately_noncompliant: List[Dict] = None

    def __post_init__(self):
        """Initialize empty lists if None"""
        if self.ambiguous is None:
            self.ambiguous = []
        if self.harmful is None:
            self.harmful = []
        if self.questioning is None:
            self.questioning = []
        if self.noncompliant is None:
            self.noncompliant = []
        if self.deliberately_noncompliant is None:
            self.deliberately_noncompliant = []


class AgentThinkingMonitor:
    """Unified system for monitoring and classifying agent thinking"""

    def __init__(self):
        self.counts = ThinkingCounts()
        self.flagged_messages = FlaggedMessages()

    async def classify_thought(self, content: str, policy_name: str) -> ThinkingAnalysis:
        """
        Classify a thinking message through all available classifiers

        Args:
            content: The agent's thinking content to analyze
            policy_name: The policy name (e.g., 'prioritize_human_life', 'prioritize_profit')

        Returns:
            ThinkingAnalysis with results from all classifiers
        """
        analysis = ThinkingAnalysis(content=content)
        errors = []

        # Run harm classification
        try:
            harm_result = await classify_harm(content.strip())
            analysis.harm_classification = harm_result.harm_classification.harm_level.lower()
            analysis.harm_reasoning = harm_result.harm_classification.reasoning
            analysis.harm_concerns = harm_result.harm_classification.specific_concerns

            # Update counts and store flagged messages
            self._process_harm_result(content, harm_result)

        except Exception as e:
            errors.append(f"Harm classification failed: {e}")
            analysis.harm_classification = "safe"  # Default to safe on failure
            self.counts.safe += 1
            logger.info(f"Harm classification failed for thinking message: {e}")

        # Run policy compliance classification
        if False:
            try:
                policy_result = await classify_policy_compliance(content.strip(), policy_name)
                analysis.policy_classification = policy_result.policy_compliance.compliance_level.lower()
                analysis.policy_reasoning = policy_result.policy_compliance.reasoning
                analysis.policy_violations = policy_result.policy_compliance.specific_violations

                # Update counts and store flagged messages
                self._process_policy_result(content, policy_result)

            except Exception as e:
                errors.append(f"Policy compliance classification failed: {e}")
                analysis.policy_classification = "compliant"  # Default to compliant on failure
                self.counts.compliant += 1
                logger.info(f"Policy compliance classification failed for thinking message: {e}")

        if errors:
            analysis.classification_errors = errors

        return analysis

    def _process_harm_result(self, content: str, harm_result):
        """Process harm classification result and update tracking"""
        harm_level = harm_result.harm_classification.harm_level.lower()

        if harm_level == "safe":
            self.counts.safe += 1
        elif harm_level == "ambiguous":
            self.counts.ambiguous += 1
            # Store flagged message
            self.flagged_messages.ambiguous.append({
                'content': content.strip(),
                'reasoning': harm_result.harm_classification.reasoning,
                'concerns': harm_result.harm_classification.specific_concerns
            })
        elif harm_level == "harmful":
            self.counts.harmful += 1
            # Store flagged message
            self.flagged_messages.harmful.append({
                'content': content.strip(),
                'reasoning': harm_result.harm_classification.reasoning,
                'concerns': harm_result.harm_classification.specific_concerns
            })

    def _process_policy_result(self, content: str, policy_result):
        """Process policy compliance result and update tracking"""
        compliance_level = policy_result.policy_compliance.compliance_level.lower()

        if compliance_level == "compliant":
            self.counts.compliant += 1
        elif compliance_level == "questioning":
            self.counts.questioning += 1
            # Store flagged message
            self.flagged_messages.questioning.append({
                'content': content.strip(),
                'reasoning': policy_result.policy_compliance.reasoning,
                'violations': policy_result.policy_compliance.specific_violations
            })
        elif compliance_level == "noncompliant":
            self.counts.noncompliant += 1
            # Store flagged message
            self.flagged_messages.noncompliant.append({
                'content': content.strip(),
                'reasoning': policy_result.policy_compliance.reasoning,
                'violations': policy_result.policy_compliance.specific_violations
            })
        elif compliance_level == "deliberately_noncompliant":
            self.counts.deliberately_noncompliant += 1
            # Store flagged message
            self.flagged_messages.deliberately_noncompliant.append({
                'content': content.strip(),
                'reasoning': policy_result.policy_compliance.reasoning,
                'violations': policy_result.policy_compliance.specific_violations
            })

    def get_harm_classification_dict(self) -> Dict[str, int]:
        """Get harm classification counts as dictionary"""
        return {
            'safe': self.counts.safe,
            'ambiguous': self.counts.ambiguous,
            'harmful': self.counts.harmful
        }

    def get_policy_compliance_dict(self) -> Dict[str, int]:
        """Get policy compliance counts as dictionary"""
        return {
            'compliant': self.counts.compliant,
            'questioning': self.counts.questioning,
            'noncompliant': self.counts.noncompliant,
            'deliberately_noncompliant': self.counts.deliberately_noncompliant
        }

    def get_harm_flagged_messages_dict(self) -> Dict[str, List[Dict]]:
        """Get harm flagged messages as dictionary"""
        return {
            'ambiguous': self.flagged_messages.ambiguous,
            'harmful': self.flagged_messages.harmful
        }

    def get_policy_flagged_messages_dict(self) -> Dict[str, List[Dict]]:
        """Get policy flagged messages as dictionary"""
        return {
            'questioning': self.flagged_messages.questioning,
            'noncompliant': self.flagged_messages.noncompliant,
            'deliberately_noncompliant': self.flagged_messages.deliberately_noncompliant
        }