"""
State Machine Logger for Copilot Coding Agent Orchestrator

Provides detailed logging of all state machine transitions, pipeline checks,
and requested actions for debugging and monitoring purposes.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
from enum import Enum

# Project root for log file
PROJECT_ROOT = Path(__file__).parent.parent
STATE_LOG_FILE = PROJECT_ROOT / "state_machine.log"

# Create a dedicated logger for state machine events
state_logger = logging.getLogger("state_machine")
state_logger.setLevel(logging.DEBUG)

# File handler with detailed format
file_handler = logging.FileHandler(STATE_LOG_FILE)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
state_logger.addHandler(file_handler)

# Also log to console for real-time monitoring
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
console_handler.setFormatter(console_formatter)
state_logger.addHandler(console_handler)


class StateLogger:
    """
    Centralized logger for state machine events.
    Logs all transitions, checks, and actions with context.
    """
    
    @staticmethod
    def _format_value(value: Any) -> str:
        """Format a value for logging"""
        if isinstance(value, Enum):
            return value.value
        elif isinstance(value, datetime):
            return value.isoformat()
        elif value is None:
            return "None"
        return str(value)
    
    @staticmethod
    def log_separator(title: str = ""):
        """Log a separator line for readability"""
        if title:
            state_logger.info(f"{'='*20} {title} {'='*20}")
        else:
            state_logger.info("=" * 60)
    
    @staticmethod
    def log_cycle_start(cycle_number: int = 0):
        """Log the start of an automation cycle"""
        state_logger.info("")
        state_logger.info(f"{'='*20} AUTOMATION CYCLE {'='*20}")
        state_logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    @staticmethod
    def log_cycle_end(actions_taken: list[str]):
        """Log the end of an automation cycle"""
        if actions_taken:
            state_logger.info(f"Actions taken this cycle: {len(actions_taken)}")
            for action in actions_taken:
                state_logger.info(f"  ✓ {action}")
        else:
            state_logger.info("No actions taken this cycle")
        state_logger.info(f"{'='*20} CYCLE END {'='*20}")
        state_logger.info("")
    
    @staticmethod
    def log_item_check(issue_id: str, current_state: Any, pr_number: Optional[int] = None):
        """Log when checking an item's status"""
        state_logger.debug(f"[{issue_id}] Checking item - Current state: {StateLogger._format_value(current_state)}, PR: {pr_number or 'None'}")
    
    @staticmethod
    def log_state_transition(
        issue_id: str,
        from_state: Any,
        to_state: Any,
        reason: str,
        pr_number: Optional[int] = None,
        additional_context: Optional[dict] = None
    ):
        """Log a state transition with full context"""
        from_str = StateLogger._format_value(from_state)
        to_str = StateLogger._format_value(to_state)
        
        state_logger.info(f"[{issue_id}] STATE TRANSITION: {from_str} → {to_str}")
        state_logger.info(f"[{issue_id}]   Reason: {reason}")
        if pr_number:
            state_logger.info(f"[{issue_id}]   PR: #{pr_number}")
        if additional_context:
            for key, value in additional_context.items():
                state_logger.debug(f"[{issue_id}]   {key}: {StateLogger._format_value(value)}")
    
    @staticmethod
    def log_pr_state_detection(
        issue_id: str,
        pr_number: int,
        detected_state: Any,
        is_draft: bool,
        copilot_is_working: bool,
        copilot_has_reviewed: bool,
        review_state: Optional[str] = None,
        reviewers: Optional[list] = None
    ):
        """Log PR state detection details"""
        state_logger.debug(f"[{issue_id}] PR #{pr_number} State Detection:")
        state_logger.debug(f"[{issue_id}]   Detected PR State: {StateLogger._format_value(detected_state)}")
        state_logger.debug(f"[{issue_id}]   is_draft: {is_draft}")
        state_logger.debug(f"[{issue_id}]   copilot_is_working: {copilot_is_working}")
        state_logger.debug(f"[{issue_id}]   copilot_has_reviewed: {copilot_has_reviewed}")
        state_logger.debug(f"[{issue_id}]   review_state: {review_state}")
        state_logger.debug(f"[{issue_id}]   reviewers: {reviewers}")
    
    @staticmethod
    def log_action_check(issue_id: str, state: Any, check_description: str, result: bool):
        """Log when checking if an action should be taken"""
        symbol = "✓" if result else "✗"
        state_logger.debug(f"[{issue_id}] Action Check ({StateLogger._format_value(state)}): {check_description} = {symbol}")
    
    @staticmethod
    def log_action_start(issue_id: str, action: str, details: Optional[dict] = None):
        """Log when starting an action"""
        state_logger.info(f"[{issue_id}] ACTION START: {action}")
        if details:
            for key, value in details.items():
                state_logger.debug(f"[{issue_id}]   {key}: {StateLogger._format_value(value)}")
    
    @staticmethod
    def log_action_result(issue_id: str, action: str, success: bool, message: Optional[str] = None):
        """Log the result of an action"""
        symbol = "✓" if success else "✗"
        status = "SUCCESS" if success else "FAILED"
        state_logger.info(f"[{issue_id}] ACTION {status} {symbol}: {action}")
        if message:
            state_logger.info(f"[{issue_id}]   {message}")
    
    @staticmethod
    def log_api_call(issue_id: str, api_name: str, params: Optional[dict] = None):
        """Log an API call"""
        state_logger.debug(f"[{issue_id}] API Call: {api_name}")
        if params:
            for key, value in params.items():
                state_logger.debug(f"[{issue_id}]   {key}: {StateLogger._format_value(value)}")
    
    @staticmethod
    def log_api_result(issue_id: str, api_name: str, success: bool, result: Any = None, error: Optional[str] = None):
        """Log an API call result"""
        if success:
            state_logger.debug(f"[{issue_id}] API Result ({api_name}): Success")
            if result:
                state_logger.debug(f"[{issue_id}]   Result: {StateLogger._format_value(result)}")
        else:
            state_logger.warning(f"[{issue_id}] API Result ({api_name}): Failed - {error}")
    
    @staticmethod
    def log_cooldown_check(can_assign: bool, minutes_remaining: Optional[int] = None, last_completion: Optional[str] = None):
        """Log cooldown status check"""
        if can_assign:
            state_logger.debug("Cooldown Check: Can assign new issue")
        else:
            state_logger.debug(f"Cooldown Check: Cannot assign - {minutes_remaining} minutes remaining")
            if last_completion:
                state_logger.debug(f"  Last completion: {last_completion}")
    
    @staticmethod
    def log_queue_status(total: int, in_progress: int, queued: int, completed: int):
        """Log queue status summary"""
        state_logger.info(f"Queue Status: Total={total}, InProgress={in_progress}, Queued={queued}, Completed={completed}")
    
    @staticmethod
    def log_error(issue_id: str, error_type: str, error_message: str, context: Optional[dict] = None):
        """Log an error with context"""
        state_logger.error(f"[{issue_id}] ERROR ({error_type}): {error_message}")
        if context:
            for key, value in context.items():
                state_logger.error(f"[{issue_id}]   {key}: {StateLogger._format_value(value)}")
    
    @staticmethod
    def log_warning(issue_id: str, message: str, context: Optional[dict] = None):
        """Log a warning"""
        state_logger.warning(f"[{issue_id}] WARNING: {message}")
        if context:
            for key, value in context.items():
                state_logger.warning(f"[{issue_id}]   {key}: {StateLogger._format_value(value)}")
    
    @staticmethod
    def log_config_loaded(config: dict):
        """Log configuration settings"""
        state_logger.info("Configuration Loaded:")
        auto_config = config.get('automation', {})
        state_logger.info(f"  auto_assign_next: {auto_config.get('auto_assign_next', True)}")
        state_logger.info(f"  auto_merge: {auto_config.get('auto_merge', True)}")
        state_logger.info(f"  skip_final_review: {auto_config.get('skip_final_review', False)}")
        state_logger.info(f"  poll_interval: {auto_config.get('poll_interval', 260)}s")
        state_logger.info(f"  cooldown_minutes: {auto_config.get('cooldown_minutes', 60)}min")


# Convenience instance
slog = StateLogger()
