"""
Background Daemon for Copilot Coding Agent Orchestrator Copilot Automation
Runs as a separate process, controlled via PID file and status file
"""

import os
import sys
import json
import time
import signal
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Set

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from automation_engine import AutomationEngine, WorkflowState
from github_client import PRState
from state_logger import StateLogger, slog  # State machine logger

# Paths - PROJECT_ROOT is the main project directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent
PID_FILE = PROJECT_ROOT / "daemon.pid"
STATUS_FILE = PROJECT_ROOT / "daemon_status.json"
LOG_FILE = PROJECT_ROOT / "daemon.log"
REVIEW_TRACKER_FILE = PROJECT_ROOT / "review_tracker.json"
WORKFLOW_HISTORY_FILE = PROJECT_ROOT / "workflow_history.json"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DaemonStatus:
    """Manages daemon status file for UI communication"""
    
    @staticmethod
    def write(status: dict):
        """Write status to file"""
        status['updated_at'] = datetime.now().isoformat()
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2, default=str)
    
    @staticmethod
    def read() -> dict:
        """Read status from file"""
        if STATUS_FILE.exists():
            try:
                with open(STATUS_FILE) as f:
                    return json.load(f)
            except:
                pass
        return {"running": False, "message": "Daemon not started"}
    
    @staticmethod
    def clear():
        """Clear status file"""
        if STATUS_FILE.exists():
            STATUS_FILE.unlink()


class CooldownManager:
    """Manages cooldown between issue completions (merge)
    
    The cooldown prevents rapid-fire issue assignments after a merge.
    When an issue is merged/completed, the cooldown starts.
    No new issues can be assigned until cooldown expires.
    """
    
    def __init__(self, cooldown_minutes: int = 60):
        self.cooldown_minutes = cooldown_minutes
        self.last_completion_file = PROJECT_ROOT / "last_assignment.json"  # Keep filename for backward compat
    
    def can_assign(self) -> tuple[bool, Optional[int]]:
        """
        Check if we can assign a new issue.
        Returns (can_assign, minutes_remaining)
        
        Cooldown is active after a merge/completion, not after assignment.
        """
        if not self.last_completion_file.exists():
            return True, None
        
        try:
            with open(self.last_completion_file) as f:
                data = json.load(f)
            
            last_time = datetime.fromisoformat(data['timestamp'])
            cooldown_end = last_time + timedelta(minutes=self.cooldown_minutes)
            
            if datetime.now() >= cooldown_end:
                return True, None
            
            remaining = (cooldown_end - datetime.now()).total_seconds() / 60
            return False, int(remaining)
        except:
            return True, None
    
    def record_completion(self, issue_id: str):
        """Record that an issue was just completed/merged - starts cooldown"""
        with open(self.last_completion_file, 'w') as f:
            json.dump({
                'issue_id': issue_id,
                'timestamp': datetime.now().isoformat(),
                'event': 'completed'
            }, f)
    
    def get_last_assignment(self) -> Optional[dict]:
        """Get info about last completion (kept for backward compat)"""
        if not self.last_completion_file.exists():
            return None
        try:
            with open(self.last_completion_file) as f:
                return json.load(f)
        except:
            return None


class ReviewTracker:
    """
    Tracks which PRs have had their review cycle completed.
    This prevents the infinite loop where:
    1. Copilot reviews PR → requests changes
    2. Daemon tells Copilot to apply changes  
    3. Copilot applies changes and re-requests review
    4. Daemon sees review request → triggers another review (LOOP!)
    
    Solution: Once we've told Copilot to apply changes, mark the PR as
    "review_done". After that, skip any more review assignments and
    just wait for approval/merge.
    """
    
    def __init__(self):
        self.tracker_file = REVIEW_TRACKER_FILE
        self._data = self._load()
    
    def _load(self) -> dict:
        """Load tracker data from file"""
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file) as f:
                    return json.load(f)
            except:
                pass
        return {"review_completed_prs": {}}
    
    def _save(self):
        """Save tracker data to file"""
        with open(self.tracker_file, 'w') as f:
            json.dump(self._data, f, indent=2, default=str)
    
    def mark_review_done(self, pr_number: int, issue_id: str):
        """Mark a PR as having had its review cycle completed"""
        self._data["review_completed_prs"][str(pr_number)] = {
            "issue_id": issue_id,
            "marked_at": datetime.now().isoformat()
        }
        self._save()
        logger.info(f"Marked PR #{pr_number} as review_done (will skip further review triggers)")
    
    def is_review_done(self, pr_number: int) -> bool:
        """Check if a PR has already had its review cycle completed"""
        return str(pr_number) in self._data.get("review_completed_prs", {})
    
    def clear_pr(self, pr_number: int):
        """Clear the review done flag for a PR (e.g., if it was closed and reopened)"""
        if str(pr_number) in self._data.get("review_completed_prs", {}):
            del self._data["review_completed_prs"][str(pr_number)]
            self._save()
    
    def get_info(self) -> dict:
        """Get tracker info for status display"""
        return {
            "tracked_prs": list(self._data.get("review_completed_prs", {}).keys())
        }


class WorkflowHistory:
    """
    Tracks workflow events per issue for UI display.
    Stores timestamped log of actions taken for each issue.
    """
    
    MAX_EVENTS_PER_ISSUE = 50  # Keep last 50 events per issue
    
    def __init__(self):
        self.history_file = WORKFLOW_HISTORY_FILE
        self._data = self._load()
    
    def _load(self) -> dict:
        """Load history data from file"""
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    return json.load(f)
            except:
                pass
        return {"issues": {}}
    
    def _save(self):
        """Save history data to file"""
        with open(self.history_file, 'w') as f:
            json.dump(self._data, f, indent=2, default=str)
    
    def add_event(self, issue_id: str, event: str, state: str = None, pr_number: int = None):
        """Add a workflow event for an issue"""
        if issue_id not in self._data["issues"]:
            self._data["issues"][issue_id] = []
        
        event_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "state": state,
            "pr_number": pr_number
        }
        
        self._data["issues"][issue_id].append(event_entry)
        
        # Keep only last N events
        if len(self._data["issues"][issue_id]) > self.MAX_EVENTS_PER_ISSUE:
            self._data["issues"][issue_id] = self._data["issues"][issue_id][-self.MAX_EVENTS_PER_ISSUE:]
        
        self._save()
    
    def get_history(self, issue_id: str) -> list:
        """Get workflow history for an issue"""
        return self._data.get("issues", {}).get(issue_id, [])
    
    def get_all_histories(self) -> dict:
        """Get all workflow histories"""
        return self._data.get("issues", {})
    
    def clear_issue(self, issue_id: str):
        """Clear history for an issue"""
        if issue_id in self._data.get("issues", {}):
            del self._data["issues"][issue_id]
            self._save()


class AutomationDaemon:
    """
    Background daemon that runs the automation loop
    """
    
    def __init__(self):
        self.engine: Optional[AutomationEngine] = None
        self.running = False
        self.cooldown: Optional[CooldownManager] = None  # Initialize after config loaded
        self.review_tracker = ReviewTracker()  # Track review completion to avoid infinite loops
        self.workflow_history = WorkflowHistory()  # Track workflow events per issue
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def _write_pid(self):
        """Write PID file"""
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    
    def _remove_pid(self):
        """Remove PID file"""
        if PID_FILE.exists():
            PID_FILE.unlink()
    
    @staticmethod
    def is_running() -> bool:
        """Check if daemon is already running"""
        if not PID_FILE.exists():
            return False
        
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, ValueError):
            # Process doesn't exist, clean up stale PID file
            PID_FILE.unlink()
            return False
    
    @staticmethod
    def get_pid() -> Optional[int]:
        """Get daemon PID if running"""
        if not PID_FILE.exists():
            return None
        try:
            with open(PID_FILE) as f:
                return int(f.read().strip())
        except:
            return None
    
    def start(self):
        """Start the daemon"""
        if self.is_running():
            logger.error("Daemon is already running!")
            return False
        
        logger.info("Starting automation daemon...")
        self._write_pid()
        
        # Initialize engine
        config_path = PROJECT_ROOT / "config.yaml"
        self.engine = AutomationEngine(config_path=str(config_path))
        
        # Initialize cooldown from config (default 60 min if not specified)
        cooldown_mins = self.engine.config.get('automation', {}).get('cooldown_minutes', 60)
        self.cooldown = CooldownManager(cooldown_minutes=cooldown_mins)
        logger.info(f"Cooldown set to {cooldown_mins} minutes from config")
        
        if not self.engine.connect():
            logger.error("Failed to connect to GitHub")
            DaemonStatus.write({
                "running": False,
                "error": "Failed to connect to GitHub"
            })
            self._remove_pid()
            return False
        
        self.running = True
        self._run_loop()
        return True
    
    def stop(self):
        """Stop the daemon"""
        self.running = False
        DaemonStatus.write({
            "running": False,
            "message": "Daemon stopped"
        })
        self._remove_pid()
        logger.info("Daemon stopped")
    
    def _run_loop(self):
        """Main daemon loop"""
        poll_interval = self.engine.config.get('automation', {}).get('poll_interval', 60)
        
        logger.info(f"Daemon running (poll interval: {poll_interval}s, cooldown: {self.cooldown.cooldown_minutes}min)")
        
        while self.running:
            try:
                self._process_cycle()
            except Exception as e:
                logger.error(f"Error in cycle: {e}")
                DaemonStatus.write({
                    "running": True,
                    "error": str(e),
                    "last_cycle": datetime.now().isoformat()
                })
            
            # Sleep in small increments to respond to stop signals
            for _ in range(poll_interval):
                if not self.running:
                    break
                time.sleep(1)
        
        self.stop()
    
    def _process_cycle(self):
        """Process one automation cycle with cooldown awareness"""
        self.engine.refresh_status()
        
        # Log cycle start
        slog.log_cycle_start()
        
        # Log queue status
        queue = self.engine.state.queue
        total = len(queue)
        in_progress = len([i for i in queue if i.state in [WorkflowState.ASSIGNED, WorkflowState.PR_OPEN, WorkflowState.REVIEW_REQUESTED, WorkflowState.REVIEWING, WorkflowState.CHANGES_REQUESTED, WorkflowState.APPLYING_CHANGES, WorkflowState.APPROVED]])
        queued = len([i for i in queue if i.state == WorkflowState.QUEUED])
        completed = len([i for i in queue if i.state in [WorkflowState.MERGED, WorkflowState.COMPLETED]])
        slog.log_queue_status(total, in_progress, queued, completed)
        
        actions_taken = []
        
        # Check cooldown status
        can_assign, minutes_remaining = self.cooldown.can_assign()
        slog.log_cooldown_check(can_assign, minutes_remaining)
        
        for item in self.engine.state.queue:
            # Log item check
            slog.log_item_check(item.issue_id, item.state, item.pr_number)
            
            old_state = item.state
            action = self._process_item_with_cooldown(item, can_assign)
            
            # Log state transition if state changed
            if item.state != old_state:
                slog.log_state_transition(
                    item.issue_id, 
                    old_state, 
                    item.state, 
                    action or "Unknown action",
                    item.pr_number
                )
            
            if action:
                actions_taken.append(action)
                # If we just assigned something, update cooldown state
                if "Assigned" in action:
                    can_assign = False
                    _, minutes_remaining = self.cooldown.can_assign()
                # If we just merged something, cooldown has started - can't assign anymore
                if "cooldown started" in action:
                    can_assign = False
                    slog.log_cooldown_check(can_assign, self.cooldown.cooldown_minutes)
        
        # Log cycle end
        slog.log_cycle_end(actions_taken)
        
        # Update status file
        status = self.engine.get_current_status()
        
        # Include per-item state for UI synchronization
        item_states = {}
        for item in self.engine.state.queue:
            item_states[item.issue_id] = {
                "state": item.state.value,
                "issue_number": item.issue_number,
                "pr_number": item.pr_number,
                "last_action": item.last_action,
                "last_action_time": item.last_action_time.isoformat() if item.last_action_time else None,
                "review_done": self.review_tracker.is_review_done(item.pr_number) if item.pr_number else False,
                "workflow_history": self.workflow_history.get_history(item.issue_id)
            }
        
        DaemonStatus.write({
            "running": True,
            "last_cycle": datetime.now().isoformat(),
            "actions": actions_taken,
            "cooldown": {
                "can_assign": can_assign,
                "minutes_remaining": minutes_remaining,
                "last_assignment": self.cooldown.get_last_assignment()
            },
            "queue_status": {
                "total": status['total'],
                "in_progress": len(status['in_progress']),
                "queued": len(status['queued']),
                "completed": len(status['completed'])
            },
            "item_states": item_states,
            "review_tracker": self.review_tracker.get_info()
        })
        
        if actions_taken:
            for action in actions_taken:
                logger.info(f"Action: {action}")
        else:
            logger.debug("No actions needed this cycle")
    
    def _process_item_with_cooldown(self, item, can_assign: bool) -> Optional[str]:
        """Process a single item, respecting cooldown for assignments"""
        if not self.engine.client:
            slog.log_warning(item.issue_id, "No GitHub client available")
            return None
        
        auto_config = self.engine.config.get('automation', {})
        
        # Check if this PR already had its review cycle completed
        # If so, handle the final steps: mark ready for review, get approval, merge
        if item.pr_number and self.review_tracker.is_review_done(item.pr_number):
            slog.log_action_check(item.issue_id, item.state, "review_tracker.is_review_done", True)
            
            # Review already done - check for approval or need to finalize
            pr = self.engine.client.get_pr_by_number(item.pr_number)
            if not pr:
                slog.log_warning(item.issue_id, f"Cannot get PR #{item.pr_number}")
                return None
            
            # Log PR state detection
            slog.log_pr_state_detection(
                item.issue_id, item.pr_number, pr.state,
                pr.is_draft, pr.copilot_is_working, 
                getattr(pr, 'copilot_has_reviewed', False),
                pr.state.value if hasattr(pr.state, 'value') else str(pr.state),
                pr.reviewers
            )
            
            # Step 1: If PR is still draft, mark it ready for review
            if pr.is_draft:
                slog.log_action_start(item.issue_id, "Mark PR ready for review (review cycle complete)", {"pr_number": item.pr_number})
                logger.info(f"[{item.issue_id}] Review cycle complete - marking PR as ready for review")
                if self.engine.client.mark_pr_ready_for_review(item.pr_number):
                    item.last_action = "Marked PR as ready for review"
                    item.last_action_time = datetime.now()
                    self.workflow_history.add_event(item.issue_id, "Marked PR as ready for review", item.state.value, item.pr_number)
                    return f"Marked PR #{item.pr_number} as ready for review (review cycle complete)"
                else:
                    logger.warning(f"[{item.issue_id}] Failed to mark PR as ready for review")
                    return None
            
            # Step 2: If PR is approved OR skip_final_review is enabled, merge it
            skip_final_review = auto_config.get('skip_final_review', False)
            if pr.state == PRState.APPROVED or item.state == WorkflowState.APPROVED or skip_final_review:
                item.state = WorkflowState.APPROVED
                merge_reason = "after approval" if pr.state == PRState.APPROVED else "review cycle complete (skip_final_review enabled)"
                logger.info(f"[{item.issue_id}] PR ready to merge - {merge_reason}")
                if auto_config.get('auto_merge', True):
                    if self.engine.client.merge_pr(item.pr_number):
                        item.state = WorkflowState.MERGED
                        item.last_action = f"Merged PR ({merge_reason})"
                        item.last_action_time = datetime.now()
                        self.review_tracker.clear_pr(item.pr_number)
                        self.workflow_history.add_event(item.issue_id, f"Merged PR ({merge_reason})", item.state.value, item.pr_number)
                        # START COOLDOWN after merge
                        self.cooldown.record_completion(item.issue_id)
                        logger.info(f"[{item.issue_id}] Cooldown started ({self.cooldown.cooldown_minutes}min)")
                        return f"Merged PR #{item.pr_number} - {merge_reason} - cooldown started"
            
            # Step 3: PR not approved yet - request final Copilot review to get approval
            # Only if skip_final_review is disabled
            elif pr.state not in [PRState.APPROVED]:
                # Avoid infinite loop: if we are already reviewing, just wait
                if item.state == WorkflowState.REVIEWING:
                    return None

                # Request a final Copilot review to get approval
                logger.info(f"[{item.issue_id}] Review cycle complete, requesting final Copilot review for approval")
                if self.engine.client.request_review_from_copilot(item.pr_number):
                    item.state = WorkflowState.REVIEWING
                    item.last_action = "Requested final Copilot review for approval"
                    item.last_action_time = datetime.now()
                    self.workflow_history.add_event(item.issue_id, "Requested final Copilot review for approval", item.state.value, item.pr_number)
                    return f"Requested final review on PR #{item.pr_number} to get approval"
            
            # Otherwise, just wait - don't trigger more review cycles
            return None
        
        # State: PR_OPEN (not draft) → Request review from Copilot (no cooldown)
        if item.state == WorkflowState.PR_OPEN and item.pr_number:
            # Check if PR is ready for review (not a draft)
            pr = self.engine.client.get_pr_by_number(item.pr_number)
            if pr and pr.state != PRState.DRAFT and not pr.reviewers:
                logger.info(f"[{item.issue_id}] PR ready - requesting Copilot review")
                if self.engine.client.request_review_from_copilot(item.pr_number):
                    item.state = WorkflowState.REVIEW_REQUESTED
                    item.last_action = "Requested Copilot review"
                    item.last_action_time = datetime.now()
                    self.workflow_history.add_event(item.issue_id, "Requested Copilot review", item.state.value, item.pr_number)
                    return f"Requested Copilot review for PR #{item.pr_number}"
        
        # State: Review requested → Reassign to Copilot (no cooldown)
        if item.state == WorkflowState.REVIEW_REQUESTED and item.pr_number:
            slog.log_action_start(item.issue_id, "Reassign review to Copilot", {"state": "REVIEW_REQUESTED"})
            logger.info(f"[{item.issue_id}] Review requested - reassigning to Copilot")
            if self.engine.client.request_review_from_copilot(item.pr_number):
                item.state = WorkflowState.REVIEWING
                item.last_action = "Reassigned review to Copilot"
                item.last_action_time = datetime.now()
                self.workflow_history.add_event(item.issue_id, "Reassigned review to Copilot", item.state.value, item.pr_number)
                slog.log_action_result(item.issue_id, "Reassign review", True)
                return f"Reassigned review of PR #{item.pr_number} to Copilot"
        
        # State: Changes requested → Comment to apply (no cooldown)
        # ALSO: Mark the review as done to prevent infinite loop
        if item.state == WorkflowState.CHANGES_REQUESTED and item.pr_number:
            slog.log_action_start(item.issue_id, "Comment @copilot apply changes", {"state": "CHANGES_REQUESTED"})
            logger.info(f"[{item.issue_id}] Changes requested - telling Copilot to apply")
            if self.engine.client.comment_apply_changes(item.pr_number):
                # CRITICAL: Mark review as done BEFORE state change
                # This prevents the loop when Copilot re-requests review after applying changes
                self.review_tracker.mark_review_done(item.pr_number, item.issue_id)
                
                item.state = WorkflowState.APPLYING_CHANGES
                item.last_action = "Commented @copilot apply changes"
                item.last_action_time = datetime.now()
                self.workflow_history.add_event(item.issue_id, "Commented @copilot apply changes", item.state.value, item.pr_number)
                slog.log_action_result(item.issue_id, "Comment apply changes", True, "Review marked done to prevent loop")
                return f"Told Copilot to apply changes on PR #{item.pr_number}"
        
        # State: Approved → Mark ready (if draft) then Merge
        if item.state == WorkflowState.APPROVED and item.pr_number and auto_config.get('auto_merge', True):
            slog.log_action_check(item.issue_id, item.state, "state=APPROVED && auto_merge=true", True)
            
            pr = self.engine.client.get_pr_by_number(item.pr_number)
            if not pr:
                slog.log_warning(item.issue_id, f"Cannot get PR #{item.pr_number}")
                logger.warning(f"[{item.issue_id}] Cannot get PR #{item.pr_number}")
                return None
            
            # Log PR status for debugging
            slog.log_pr_state_detection(
                item.issue_id, item.pr_number, pr.state,
                pr.is_draft, pr.copilot_is_working,
                getattr(pr, 'copilot_has_reviewed', False),
                pr.state.value if hasattr(pr.state, 'value') else str(pr.state),
                pr.reviewers
            )
            
            # First, mark PR as ready if it's still a draft
            if pr.is_draft:
                slog.log_action_start(item.issue_id, "Mark PR ready (is_draft=True)", {"pr_number": item.pr_number})
                logger.info(f"[{item.issue_id}] PR is draft - marking ready for review first")
                if self.engine.client.mark_pr_ready_for_review(item.pr_number):
                    item.last_action = "Marked PR ready for review"
                    item.last_action_time = datetime.now()
                    self.workflow_history.add_event(item.issue_id, "Marked PR ready for review", item.state.value, item.pr_number)
                    slog.log_action_result(item.issue_id, "Mark PR ready", True)
                    return f"Marked PR #{item.pr_number} as ready for review"
                else:
                    logger.warning(f"[{item.issue_id}] Failed to mark PR as ready")
                    return None
            
            # PR is ready - merge it
            logger.info(f"[{item.issue_id}] PR approved and ready - merging")
            if self.engine.client.merge_pr(item.pr_number):
                item.state = WorkflowState.MERGED
                item.last_action = "Merged PR"
                item.last_action_time = datetime.now()
                self.workflow_history.add_event(item.issue_id, "Merged PR", item.state.value, item.pr_number)
                # START COOLDOWN after merge
                self.cooldown.record_completion(item.issue_id)
                logger.info(f"[{item.issue_id}] Cooldown started ({self.cooldown.cooldown_minutes}min)")
                return f"Merged PR #{item.pr_number} - cooldown started"
        
        # State: Queued → Assign to Copilot (WITH COOLDOWN)
        if item.state == WorkflowState.QUEUED and auto_config.get('auto_assign_next', True):
            # Only assign if cooldown allows
            if not can_assign:
                return None
            
            # Check if it's the first queued item and no active items
            first_queued = next((i for i in self.engine.state.queue if i.state == WorkflowState.QUEUED), None)
            active_items = [i for i in self.engine.state.queue 
                          if i.state not in [WorkflowState.QUEUED, WorkflowState.MERGED, WorkflowState.COMPLETED]]
            
            if first_queued == item and not active_items and item.issue_number:
                logger.info(f"[{item.issue_id}] Assigning to Copilot")
                
                # Get instructions and target branch from config
                instructions = self.engine.config.get('agent_instructions', '')
                target_branch = self.engine.config.get('github', {}).get('target_branch', 'main_dev')
                
                if self.engine.client.assign_issue_to_copilot(
                    item.issue_number, 
                    instructions=instructions,
                    target_branch=target_branch
                ):
                    # Note: Cooldown is NOT started here - it starts after merge/completion
                    
                    item.state = WorkflowState.ASSIGNED
                    item.last_action = "Assigned to Copilot"
                    item.last_action_time = datetime.now()
                    self.workflow_history.add_event(item.issue_id, "Assigned to Copilot", item.state.value, item.pr_number)
                    return f"Assigned issue #{item.issue_number} ({item.issue_id}) to Copilot"
        
        return None


def start_daemon():
    """Start the daemon (called from CLI or UI)"""
    daemon = AutomationDaemon()
    daemon.start()


def stop_daemon():
    """Stop the daemon"""
    pid = AutomationDaemon.get_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to daemon (PID {pid})")
            return True
        except ProcessLookupError:
            logger.warning("Daemon process not found, cleaning up...")
            if PID_FILE.exists():
                PID_FILE.unlink()
            DaemonStatus.clear()
    else:
        logger.warning("Daemon is not running")
    return False


def get_daemon_status() -> dict:
    """Get current daemon status"""
    is_running = AutomationDaemon.is_running()
    status = DaemonStatus.read()
    status['is_running'] = is_running
    status['pid'] = AutomationDaemon.get_pid()
    return status


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Copilot Coding Agent Orchestrator Automation Daemon")
    parser.add_argument("command", choices=["start", "stop", "status"], help="Daemon command")
    
    args = parser.parse_args()
    
    if args.command == "start":
        start_daemon()
    elif args.command == "stop":
        stop_daemon()
    elif args.command == "status":
        status = get_daemon_status()
        print(json.dumps(status, indent=2, default=str))
