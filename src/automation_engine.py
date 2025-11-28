"""
Automation Engine for Copilot Coding Agent Orchestrator Copilot Workflow
Handles the state machine logic for automating the development pipeline
"""

import yaml
import time
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from github_client import GitHubClient, IssueInfo, PRInfo, PRState, IssueState

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """State machine states for an issue"""
    QUEUED = "queued"              # In queue, not started
    ASSIGNED = "assigned"          # Assigned to Copilot
    PR_OPEN = "pr_open"            # PR created
    REVIEW_REQUESTED = "review_requested"  # Copilot asked for review
    REVIEWING = "reviewing"        # Copilot is reviewing
    CHANGES_REQUESTED = "changes_requested"  # Review has change requests
    APPLYING_CHANGES = "applying_changes"  # Copilot applying changes
    APPROVED = "approved"          # PR approved
    MERGED = "merged"              # PR merged
    COMPLETED = "completed"        # Done


@dataclass
class QueueItem:
    """Represents an item in the work queue"""
    issue_id: str
    state: WorkflowState = WorkflowState.QUEUED
    issue_number: Optional[int] = None
    issue_title: Optional[str] = None
    pr_number: Optional[int] = None
    last_action: Optional[str] = None
    last_action_time: Optional[datetime] = None
    

@dataclass
class AutomationState:
    """Current state of the automation"""
    is_running: bool = False
    current_item: Optional[str] = None
    queue: list[QueueItem] = field(default_factory=list)
    completed: list[str] = field(default_factory=list)
    last_check: Optional[datetime] = None
    errors: list[str] = field(default_factory=list)


class AutomationEngine:
    """
    Main automation engine that monitors and manages the Copilot workflow
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.client: Optional[GitHubClient] = None
        self.state = AutomationState()
        self._issue_numbers = self.config.get('issue_numbers', {})  # Pre-mapped issue numbers
        self._issue_titles = self.config.get('issue_titles', {})  # Pre-mapped issue titles
        self._initialize_queue()
    
    def _load_config(self) -> dict:
        """Load configuration from YAML file"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                return yaml.safe_load(f)
        return {}
    
    def _save_config(self):
        """Save configuration back to YAML file"""
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
    
    def _initialize_queue(self):
        """Initialize the queue from config"""
        issue_ids = self.config.get('issue_queue', [])
        self.state.queue = []
        for iid in issue_ids:
            item = QueueItem(issue_id=iid)
            # Pre-populate issue number from config mapping
            if iid in self._issue_numbers:
                item.issue_number = self._issue_numbers[iid]
            # Pre-populate issue title from config mapping
            if iid in self._issue_titles:
                item.issue_title = self._issue_titles[iid]
            self.state.queue.append(item)
    
    def connect(self) -> bool:
        """Connect to GitHub"""
        try:
            gh_config = self.config.get('github', {})
            self.client = GitHubClient(
                owner=gh_config.get('owner', 'WoDeep'),
                repo=gh_config.get('repo', 'TimeAttack')
            )
            logger.info(f"Connected to GitHub as {self.client.get_current_user()}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to GitHub: {e}")
            self.state.errors.append(str(e))
            return False
    
    # ========== QUEUE MANAGEMENT ==========
    
    def get_queue(self) -> list[QueueItem]:
        """Get the current queue"""
        return self.state.queue
    
    def move_item_up(self, issue_id: str) -> bool:
        """Move an item up in the queue"""
        for i, item in enumerate(self.state.queue):
            if item.issue_id == issue_id and i > 0:
                self.state.queue[i], self.state.queue[i-1] = self.state.queue[i-1], self.state.queue[i]
                self._sync_queue_to_config()
                return True
        return False
    
    def move_item_down(self, issue_id: str) -> bool:
        """Move an item down in the queue"""
        for i, item in enumerate(self.state.queue):
            if item.issue_id == issue_id and i < len(self.state.queue) - 1:
                self.state.queue[i], self.state.queue[i+1] = self.state.queue[i+1], self.state.queue[i]
                self._sync_queue_to_config()
                return True
        return False
    
    def remove_item(self, issue_id: str) -> bool:
        """Remove an item from the queue"""
        for i, item in enumerate(self.state.queue):
            if item.issue_id == issue_id:
                self.state.queue.pop(i)
                self._sync_queue_to_config()
                return True
        return False
    
    def add_item(self, issue_id: str, position: int = -1) -> bool:
        """Add an item to the queue"""
        if any(item.issue_id == issue_id for item in self.state.queue):
            return False  # Already in queue
        
        new_item = QueueItem(issue_id=issue_id)
        # Pre-populate issue number from config mapping if available
        if issue_id in self._issue_numbers:
            new_item.issue_number = self._issue_numbers[issue_id]
        if position < 0 or position >= len(self.state.queue):
            self.state.queue.append(new_item)
        else:
            self.state.queue.insert(position, new_item)
        self._sync_queue_to_config()
        return True
    
    def _sync_queue_to_config(self):
        """Sync the queue state back to config file"""
        self.config['issue_queue'] = [item.issue_id for item in self.state.queue]
        self._save_config()
    
    # ========== STATUS CHECKING ==========
    
    def refresh_status(self):
        """Refresh the status of all items in the queue"""
        if not self.client:
            return
        
        self.state.last_check = datetime.now()
        
        for item in self.state.queue:
            self._update_item_status(item)
    
    def _update_item_status(self, item: QueueItem):
        """Update the status of a single queue item - optimized for speed"""
        if not self.client:
            return
        
        # If we already have the issue number, use direct lookup (fast)
        if item.issue_number:
            issue = self.client.get_issue_by_number(item.issue_number)
        elif item.issue_id in self._issue_numbers:
            # Use pre-mapped issue number from config (no API call!)
            item.issue_number = self._issue_numbers[item.issue_id]
            issue = self.client.get_issue_by_number(item.issue_number)
        else:
            # Fallback: Search for issue by pattern (uses search API - slow)
            logger.warning(f"Issue {item.issue_id} not in config mapping, using slow API search")
            issue = self.client.get_issue_by_title_pattern(item.issue_id)
            if issue:
                item.issue_number = issue.number
        
        if not issue:
            return
        
        # Store the issue title and persist to config
        if issue.title and not item.issue_title:
            item.issue_title = issue.title
            # Save to config mapping for persistence
            if 'issue_titles' not in self.config:
                self.config['issue_titles'] = {}
            if item.issue_id not in self.config['issue_titles']:
                self.config['issue_titles'][item.issue_id] = issue.title
                self._issue_titles[item.issue_id] = issue.title
                self._save_config()
        
        # Handle closed issues immediately - they're done!
        # This ensures we correctly skip items that were completed before daemon started
        if issue.state == IssueState.CLOSED:
            item.state = WorkflowState.COMPLETED
            logger.info(f"[{item.issue_id}] Issue is closed - marking as COMPLETED")
            return  # No need to check PR, issue is done
        
        # Only search for PR if item is already in progress (assigned or has PR)
        # Skip expensive PR search for queued items that are still open
        if item.state == WorkflowState.QUEUED and issue.state != IssueState.IN_PROGRESS:
            return  # Still queued, no need to check for PR
        
        # Quick check: if we already have a PR number, get it directly
        pr = None
        if item.pr_number:
            pr = self.client.get_pr_by_number(item.pr_number)
        else:
            # Only search for PR if issue is assigned (in progress)
            if issue.state == IssueState.IN_PROGRESS or item.state != WorkflowState.QUEUED:
                pr = self.client.get_pr_by_issue(item.issue_id)
        
        if pr:
            item.pr_number = pr.number
            
            # Update state based on PR status
            # Note: Some states should not be overwritten by lower-priority detections
            if pr.state == PRState.MERGED:
                item.state = WorkflowState.MERGED
            elif pr.state == PRState.CLOSED:
                # PR was closed without merging - reset to queued
                item.state = WorkflowState.QUEUED
                item.pr_number = None  # Clear the PR reference
            elif pr.state == PRState.APPROVED:
                item.state = WorkflowState.APPROVED
            elif pr.state == PRState.CHANGES_REQUESTED:
                # Only set to CHANGES_REQUESTED if not already past this state
                # (e.g., if we're in APPLYING_CHANGES, don't regress)
                if item.state not in [WorkflowState.APPLYING_CHANGES]:
                    item.state = WorkflowState.CHANGES_REQUESTED
            elif pr.state == PRState.REVIEW_REQUESTED:
                # Review has been requested (even if PR is draft)
                # But don't regress from REVIEWING or APPLYING_CHANGES
                if item.state not in [WorkflowState.REVIEWING, WorkflowState.APPLYING_CHANGES]:
                    item.state = WorkflowState.REVIEW_REQUESTED
            elif pr.state == PRState.DRAFT:
                # PR is still a draft without review request - Copilot is working on it
                item.state = WorkflowState.PR_OPEN
            elif pr.reviewers:
                # Review has been requested from someone (fallback check)
                # But don't regress from APPLYING_CHANGES or REVIEWING
                if item.state not in [WorkflowState.REVIEWING, WorkflowState.APPLYING_CHANGES]:
                    item.state = WorkflowState.REVIEW_REQUESTED
            else:
                # PR is open but not draft, and no reviewers - needs review request
                # But don't regress from later states
                if item.state not in [WorkflowState.REVIEW_REQUESTED, WorkflowState.REVIEWING, 
                                      WorkflowState.CHANGES_REQUESTED, WorkflowState.APPLYING_CHANGES]:
                    item.state = WorkflowState.PR_OPEN
        elif issue.state == IssueState.IN_PROGRESS:
            item.state = WorkflowState.ASSIGNED
        elif issue.state == IssueState.CLOSED:
            item.state = WorkflowState.COMPLETED
    
    def get_current_status(self) -> dict:
        """Get a summary of current automation status"""
        in_progress = [i for i in self.state.queue if i.state not in [WorkflowState.QUEUED, WorkflowState.MERGED, WorkflowState.COMPLETED]]
        queued = [i for i in self.state.queue if i.state == WorkflowState.QUEUED]
        completed = [i for i in self.state.queue if i.state in [WorkflowState.MERGED, WorkflowState.COMPLETED]]
        
        return {
            "is_running": self.state.is_running,
            "last_check": self.state.last_check,
            "in_progress": in_progress,
            "queued": queued,
            "completed": completed,
            "total": len(self.state.queue),
            "errors": self.state.errors[-5:] if self.state.errors else []  # Last 5 errors
        }
    
    # ========== AUTOMATION ACTIONS ==========
    
    def process_next_action(self) -> Optional[str]:
        """
        Process the next automation action based on current state.
        Returns a description of the action taken, or None if no action needed.
        """
        if not self.client:
            return None
        
        self.refresh_status()
        
        for item in self.state.queue:
            action = self._get_next_action(item)
            if action:
                return action
        
        return None
    
    def _get_next_action(self, item: QueueItem) -> Optional[str]:
        """Determine and execute the next action for an item"""
        if not self.client:
            return None
        
        auto_config = self.config.get('automation', {})
        
        # State: Review requested (Copilot wants our review)
        # Action: Reassign review to Copilot
        if item.state == WorkflowState.REVIEW_REQUESTED and item.pr_number:
            logger.info(f"[{item.issue_id}] Review requested - reassigning to Copilot")
            if self.client.request_review_from_copilot(item.pr_number):
                item.state = WorkflowState.REVIEWING
                item.last_action = "Reassigned review to Copilot"
                item.last_action_time = datetime.now()
                return f"Reassigned review of PR #{item.pr_number} to Copilot"
        
        # State: Reviewing - check if Copilot finished reviewing
        # Action: If review completed with no changes requested, proceed to approved
        if item.state == WorkflowState.REVIEWING and item.pr_number:
            pr = self.client.get_pr_by_number(item.pr_number)
            if pr:
                # Wait for Copilot to finish reviewing
                if pr.copilot_is_working:
                    logger.debug(f"[{item.issue_id}] Copilot still reviewing, waiting...")
                    return None  # Don't take any action while Copilot is reviewing
                
                # Copilot has finished - check what the review result is
                if pr.state == PRState.CHANGES_REQUESTED:
                    # Review completed with change requests
                    item.state = WorkflowState.CHANGES_REQUESTED
                    item.last_action = "Review completed with changes requested"
                    item.last_action_time = datetime.now()
                    return f"PR #{item.pr_number} review completed - changes requested"
                elif pr.state == PRState.APPROVED:
                    # Review completed and approved
                    item.state = WorkflowState.APPROVED
                    item.last_action = "Review completed and approved"
                    item.last_action_time = datetime.now()
                    return f"PR #{item.pr_number} review completed - approved"
                else:
                    # Review completed with no changes requested (Copilot found nothing to change)
                    # This happens when Copilot reviews quickly and doesn't submit a formal review
                    logger.info(f"[{item.issue_id}] Review completed with no changes - proceeding to approved")
                    if pr.is_draft:
                        self.client.mark_pr_ready_for_review(item.pr_number)
                    item.state = WorkflowState.APPROVED
                    item.last_action = "Review completed, no changes needed"
                    item.last_action_time = datetime.now()
                    return f"PR #{item.pr_number} review completed - no changes needed, ready for merge"
        
        # State: Changes requested by Copilot review
        # Action: Comment to apply changes
        if item.state == WorkflowState.CHANGES_REQUESTED and item.pr_number:
            logger.info(f"[{item.issue_id}] Changes requested - telling Copilot to apply")
            if self.client.comment_apply_changes(item.pr_number):
                item.state = WorkflowState.APPLYING_CHANGES
                item.last_action = "Commented @copilot apply changes"
                item.last_action_time = datetime.now()
                return f"Told Copilot to apply changes on PR #{item.pr_number}"
        
        # State: Applying changes - check if changes have been applied
        # Action: If PR no longer shows CHANGES_REQUESTED AND Copilot has finished working, proceed
        if item.state == WorkflowState.APPLYING_CHANGES and item.pr_number:
            pr = self.client.get_pr_by_number(item.pr_number)
            if pr:
                # IMPORTANT: Wait for Copilot to finish working before taking any action
                if pr.copilot_is_working:
                    logger.debug(f"[{item.issue_id}] Copilot still working on applying changes, waiting...")
                    return None  # Don't take any action while Copilot is working
                
                if pr.state == PRState.APPROVED:
                    # Changes applied and approved!
                    item.state = WorkflowState.APPROVED
                    item.last_action = "Changes applied and approved"
                    item.last_action_time = datetime.now()
                    return f"PR #{item.pr_number} changes applied and approved"
                elif pr.state not in [PRState.CHANGES_REQUESTED]:
                    # Changes have been applied (PR no longer showing changes requested)
                    # AND Copilot has finished working - now we can proceed
                    # Check if skip_final_review is enabled
                    if auto_config.get('skip_final_review', False):
                        # Skip review, mark PR ready and go straight to approved
                        logger.info(f"[{item.issue_id}] Changes applied, Copilot finished - marking ready for merge (skip_final_review=true)")
                        if pr.is_draft:
                            self.client.mark_pr_ready_for_review(item.pr_number)
                        item.state = WorkflowState.APPROVED
                        item.last_action = "Changes applied, marked ready for merge"
                        item.last_action_time = datetime.now()
                        return f"PR #{item.pr_number} changes applied by Copilot, ready for merge"
                    else:
                        # Request another review to verify
                        logger.info(f"[{item.issue_id}] Changes applied, Copilot finished - requesting follow-up review")
                        if self.client.request_review_from_copilot(item.pr_number):
                            item.state = WorkflowState.REVIEWING
                            item.last_action = "Requested follow-up review after changes applied"
                            item.last_action_time = datetime.now()
                            return f"Requested follow-up review on PR #{item.pr_number} after changes applied"
        
        # State: Approved and auto_merge enabled
        # Action: Mark ready (if draft) and merge the PR
        if item.state == WorkflowState.APPROVED and item.pr_number and auto_config.get('auto_merge', True):
            pr = self.client.get_pr_by_number(item.pr_number)
            if pr:
                # First, mark PR as ready if it's still a draft
                if pr.is_draft:
                    logger.info(f"[{item.issue_id}] PR is draft - marking ready for review first")
                    self.client.mark_pr_ready_for_review(item.pr_number)
                    # Return here - next cycle will merge after PR is ready
                    item.last_action = "Marked PR ready for review"
                    item.last_action_time = datetime.now()
                    return f"Marked PR #{item.pr_number} as ready for review"
                
                # PR is ready - merge it
                logger.info(f"[{item.issue_id}] PR approved - merging")
                if self.client.merge_pr(item.pr_number):
                    item.state = WorkflowState.MERGED
                    item.last_action = "Merged PR"
                    item.last_action_time = datetime.now()
                    return f"Merged PR #{item.pr_number}"
        
        # State: Previous item merged, this item is queued, auto_assign enabled
        # Action: Assign to Copilot
        if item.state == WorkflowState.QUEUED and auto_config.get('auto_assign_next', True):
            # Check if it's the first queued item
            first_queued = next((i for i in self.state.queue if i.state == WorkflowState.QUEUED), None)
            active_items = [i for i in self.state.queue if i.state not in [WorkflowState.QUEUED, WorkflowState.MERGED, WorkflowState.COMPLETED]]
            
            if first_queued == item and not active_items and item.issue_number:
                logger.info(f"[{item.issue_id}] Assigning to Copilot")
                if self.client.assign_issue_to_copilot(item.issue_number):
                    item.state = WorkflowState.ASSIGNED
                    item.last_action = "Assigned to Copilot"
                    item.last_action_time = datetime.now()
                    return f"Assigned issue #{item.issue_number} ({item.issue_id}) to Copilot"
        
        return None
    
    # ========== MAIN LOOP ==========
    
    def run_once(self) -> list[str]:
        """Run a single iteration of the automation loop"""
        actions = []
        if not self.connect():
            return ["Failed to connect to GitHub"]
        
        self.refresh_status()
        
        # Process all pending actions
        while True:
            action = self.process_next_action()
            if action:
                actions.append(action)
            else:
                break
        
        return actions if actions else ["No actions needed"]
    
    def run_loop(self, poll_interval: Optional[int] = None):
        """Run the automation loop continuously"""
        if not self.connect():
            return
        
        interval = poll_interval or self.config.get('automation', {}).get('poll_interval', 260)
        self.state.is_running = True
        
        logger.info(f"Starting automation loop (poll interval: {interval}s)")
        
        try:
            while self.state.is_running:
                actions = self.run_once()
                for action in actions:
                    logger.info(f"Action: {action}")
                
                logger.info(f"Sleeping for {interval} seconds...")
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Automation stopped by user")
        finally:
            self.state.is_running = False
    
    def stop(self):
        """Stop the automation loop"""
        self.state.is_running = False


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Copilot Coding Agent Orchestrator Copilot Automation Engine")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=260, help="Poll interval in seconds")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    
    args = parser.parse_args()
    
    engine = AutomationEngine(config_path=args.config)
    
    if args.once:
        actions = engine.run_once()
        for action in actions:
            print(action)
    else:
        engine.run_loop(poll_interval=args.interval)
