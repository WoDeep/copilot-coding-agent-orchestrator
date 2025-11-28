"""
GitHub API Client for Copilot Coding Agent Orchestrator Automation
Uses PyGithub library to interact with GitHub API
"""

import os
from pathlib import Path
from typing import Optional
from github import Github, GithubException
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.Repository import Repository
from dataclasses import dataclass
from enum import Enum

# Load .env file if it exists
def load_env():
    # Try multiple locations for .env file
    possible_paths = [
        Path(__file__).parent / ".env",
        Path.cwd() / ".env",
        Path.cwd() / "scripts" / "automation" / ".env",
    ]
    
    for env_file in possible_paths:
        if env_file.exists():
            print(f"[DEBUG] Found .env at: {env_file}")
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        if value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        os.environ[key] = value  # Use direct assignment instead of setdefault
                        print(f"[DEBUG] Loaded {key}={value[:10]}...")
            return
    print(f"[DEBUG] No .env file found. Searched: {[str(p) for p in possible_paths]}")

load_env()


class IssueState(Enum):
    OPEN = "open"
    CLOSED = "closed"
    IN_PROGRESS = "in_progress"  # Has assignee
    

class PRState(Enum):
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"
    DRAFT = "draft"
    REVIEW_REQUESTED = "review_requested"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"


@dataclass
class IssueInfo:
    number: int
    title: str
    state: IssueState
    assignee: Optional[str]
    url: str
    labels: list[str]
    
    @property
    def issue_id(self) -> Optional[str]:
        """Extract TC-X-XX from title"""
        import re
        match = re.search(r'TC-[A-Z]-\d{2}', self.title)
        return match.group(0) if match else None


@dataclass  
class PRInfo:
    number: int
    title: str
    state: PRState
    author: str
    reviewers: list[str]
    review_state: Optional[str]
    url: str
    linked_issue: Optional[str]
    mergeable: bool
    checks_passed: bool
    is_draft: bool = False
    copilot_has_reviewed: bool = False  # Track if Copilot reviewer has already reviewed
    copilot_is_working: bool = False  # Track if Copilot coding agent is currently working


class GitHubClient:
    """Client for interacting with GitHub API"""
    
    COPILOT_USER = "copilot"  # GitHub Copilot's username for assignments
    
    def __init__(self, owner: str, repo: str, token: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token required. Set GITHUB_TOKEN env var or pass token parameter.")
        
        self.gh = Github(self.token)
        self.owner = owner
        self.repo_name = repo
        self._repo: Optional[Repository] = None
        self._issue_cache: dict[str, int] = {}  # pattern -> issue_number cache
    
    @property
    def repo(self) -> Repository:
        if self._repo is None:
            self._repo = self.gh.get_repo(f"{self.owner}/{self.repo_name}")
        return self._repo
    
    # ========== ISSUES ==========
    
    def get_issue_by_title_pattern(self, pattern: str) -> Optional[IssueInfo]:
        """Find an issue by title pattern (e.g., 'TC-P-01') using GitHub search API"""
        # Check cache first
        if pattern in self._issue_cache:
            return self.get_issue_by_number(self._issue_cache[pattern])
        
        try:
            # Use search API - much faster than iterating all issues
            query = f'repo:{self.owner}/{self.repo_name} "{pattern}" in:title'
            issues = self.gh.search_issues(query)
            for issue in issues:
                if pattern in issue.title and not issue.pull_request:
                    # Cache the result
                    self._issue_cache[pattern] = issue.number
                    return self._to_issue_info(issue)
        except Exception as e:
            print(f"Search failed: {e}")
        return None
    
    def get_issue_by_number(self, issue_number: int) -> Optional[IssueInfo]:
        """Get an issue directly by number (fastest method)"""
        try:
            issue = self.repo.get_issue(issue_number)
            if not issue.pull_request:
                return self._to_issue_info(issue)
        except Exception:
            pass
        return None
    
    def get_all_issues(self, state: str = "all") -> list[IssueInfo]:
        """Get all issues"""
        issues = self.repo.get_issues(state=state)
        return [self._to_issue_info(i) for i in issues if not i.pull_request]
    
    def assign_issue_to_copilot(self, issue_number: int, instructions: Optional[str] = None, target_branch: str = "main_dev") -> bool:
        """Assign an issue to GitHub Copilot with instructions
        
        Uses the GitHub MCP Server's assign_copilot_to_issue tool.
        """
        import asyncio
        from mcp_client import GitHubMCPClient
        
        async def _assign():
            try:
                async with GitHubMCPClient(self.token) as mcp:
                    # First assign Copilot via MCP
                    result = await mcp.assign_copilot_to_issue(self.owner, self.repo_name, issue_number)
                    
                    if not result.success:
                        print(f"MCP assignment failed: {result.error}")
                        return False
                    
                    # Now add instructions comment if provided
                    if instructions:
                        issue = self.repo.get_issue(issue_number)
                        comment_parts = [
                            f"**Target Branch:** `{target_branch}`",
                            f"",
                            f"---",
                            f"",
                            f"**Instructions:**",
                            f"",
                            instructions
                        ]
                        comment = "\n".join(comment_parts)
                        issue.create_comment(comment)
                    
                    return True
                    
            except Exception as e:
                print(f"Error assigning issue to Copilot: {e}")
                return False
        
        # Run the async function
        return asyncio.run(_assign())
    
    def _to_issue_info(self, issue: Issue) -> IssueInfo:
        # Check closed state first - it takes priority
        if issue.state == "closed":
            state = IssueState.CLOSED
        elif issue.assignee:
            state = IssueState.IN_PROGRESS
        else:
            state = IssueState.OPEN
        return IssueInfo(
            number=issue.number,
            title=issue.title,
            state=state,
            assignee=issue.assignee.login if issue.assignee else None,
            url=issue.html_url,
            labels=[l.name for l in issue.labels]
        )
    
    # ========== PULL REQUESTS ==========
    
    def get_open_prs(self) -> list[PRInfo]:
        """Get all open pull requests"""
        prs = self.repo.get_pulls(state="open")
        return [self._to_pr_info(pr) for pr in prs]
    
    def get_pr_by_number(self, pr_number: int) -> Optional[PRInfo]:
        """Get a PR directly by number (fastest method)"""
        try:
            pr = self.repo.get_pull(pr_number)
            return self._to_pr_info(pr)
        except Exception:
            return None
    
    def get_pr_by_issue(self, issue_id: str) -> Optional[PRInfo]:
        """Find a PR that references an issue ID (e.g., TC-P-01)"""
        # Only check open PRs for speed - closed/merged PRs are historical
        prs = self.repo.get_pulls(state="open")
        for pr in prs:
            if issue_id in pr.title or issue_id in (pr.body or ""):
                return self._to_pr_info(pr)
        return None
    
    def get_pr_by_issue_number(self, issue_number: int) -> Optional[PRInfo]:
        """Find a PR linked to an issue by its number.
        
        Searches for PRs that:
        1. Reference the issue in title/body (e.g., "Fixes #123", "Closes #123")
        2. Are created by Copilot and mention the issue
        3. Have branches that might reference the issue
        """
        # Only check open PRs for speed
        prs = self.repo.get_pulls(state="open")
        patterns = [
            f"#{issue_number}",
            f"fixes #{issue_number}",
            f"closes #{issue_number}",
            f"resolves #{issue_number}",
            f"issue {issue_number}",
        ]
        
        for pr in prs:
            # Check title and body
            text = f"{pr.title} {pr.body or ''}".lower()
            for pattern in patterns:
                if pattern.lower() in text:
                    return self._to_pr_info(pr)
            
            # Check if branch name references issue
            if f"-{issue_number}" in pr.head.ref or f"/{issue_number}" in pr.head.ref:
                return self._to_pr_info(pr)
            
            # Check if created by Copilot and has issue number in any form
            if pr.user.login.lower() == "copilot" and str(issue_number) in text:
                return self._to_pr_info(pr)
        
        return None

    def request_review_from_copilot(self, pr_number: int) -> bool:
        """Request review from Copilot on a PR using the MCP server"""
        import asyncio
        from mcp_client import GitHubMCPClient
        
        async def _request_review():
            try:
                async with GitHubMCPClient(self.token) as mcp:
                    result = await mcp.call_tool(
                        "request_copilot_review",
                        {
                            "owner": self.owner,
                            "repo": self.repo_name,
                            "pullNumber": pr_number
                        }
                    )
                    
                    if result.success:
                        print(f"Successfully requested Copilot review for PR #{pr_number}")
                        return True

                    else:
                        print(f"Failed to request Copilot review: {result.error}")
                        # Fallback to comment method
                        pr = self.repo.get_pull(pr_number)
                        pr.create_issue_comment("@copilot Please review this PR.")
                        return True
                        
            except Exception as e:
                print(f"Error requesting Copilot review: {e}")
                return False
        
        return asyncio.run(_request_review())
    
    def comment_apply_changes(self, pr_number: int) -> bool:
        """Comment to tell Copilot to apply suggested changes"""
        try:
            pr = self.repo.get_pull(pr_number)
            pr.create_issue_comment("@copilot apply changes based on the review comments in this thread")
            return True
        except GithubException as e:
            print(f"Error commenting: {e}")
            return False
    
    def mark_pr_ready_for_review(self, pr_number: int) -> bool:
        """Mark a draft PR as ready for review using the MCP server"""
        import asyncio
        from mcp_client import GitHubMCPClient
        
        async def _mark_ready():
            try:
                async with GitHubMCPClient(self.token) as mcp:
                    result = await mcp.call_tool(
                        "update_pull_request",
                        {
                            "owner": self.owner,
                            "repo": self.repo_name,
                            "pullNumber": pr_number,
                            "draft": False
                        }
                    )
                    
                    if result.success:
                        print(f"Successfully marked PR #{pr_number} as ready for review")
                        return True
                    else:
                        print(f"Failed to mark PR ready: {result.error}")
                        return False
                        
            except Exception as e:
                print(f"Error marking PR ready for review: {e}")
                return False
        
        return asyncio.run(_mark_ready())
    
    def merge_pr(self, pr_number: int, merge_method: str = "squash") -> bool:
        """Merge a pull request"""
        try:
            pr = self.repo.get_pull(pr_number)
            if pr.mergeable:
                pr.merge(merge_method=merge_method)
                return True
            else:
                print(f"PR #{pr_number} is not mergeable")
                return False
        except GithubException as e:
            print(f"Error merging PR: {e}")
            return False
    
    def _to_pr_info(self, pr: PullRequest) -> PRInfo:
        from datetime import datetime, timezone, timedelta
        
        # Determine review state
        reviews = list(pr.get_reviews())
        review_state = None
        has_pending_suggestions = False
        copilot_has_reviewed = False
        copilot_is_working = False
        copilot_work_just_finished = False  # True if Copilot finished within 120 seconds - grace period for comment indexing
        
        # DETECTION 1: Check timeline events for Copilot reviewer status
        # The Copilot reviewer uses copilot_work_started/copilot_work_finished events
        try:
            import requests
            timeline_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/issues/{pr.number}/timeline"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github+json"
            }
            
            response = requests.get(timeline_url, headers=headers)
            if response.status_code == 200:
                events = response.json()
                
                # Find the latest copilot_work_started, copilot_work_finished, and review_requested events
                latest_work_started = None
                latest_work_finished = None
                latest_review_requested = None
                
                for event in events:
                    event_type = event.get('event', '')
                    event_time = event.get('created_at')
                    
                    if event_type == 'copilot_work_started' and event_time:
                        latest_work_started = event_time
                    elif event_type == 'copilot_work_finished' and event_time:
                        latest_work_finished = event_time
                    elif event_type == 'review_requested' and event_time:
                        latest_review_requested = event_time
                
                # If there's a work_started but no work_finished after it, Copilot is still working
                if latest_work_started:
                    if not latest_work_finished or latest_work_started > latest_work_finished:
                        copilot_is_working = True
                        print(f"[DEBUG] Copilot reviewer is working (work_started: {latest_work_started}, work_finished: {latest_work_finished})")
                    else:
                        copilot_is_working = False
                        # IMPORTANT: If Copilot finished AFTER a review was requested,
                        # consider the review complete (even without formal review submission)
                        if latest_review_requested and latest_work_finished > latest_review_requested:
                            copilot_has_reviewed = True
                            # Store the finish time for grace period check
                            copilot_review_finished_at = latest_work_finished
                            # Check if Copilot just finished (within 120 seconds) - grace period for comment indexing
                            from datetime import datetime, timezone
                            now = datetime.now(timezone.utc)
                            seconds_since_finish = (now - copilot_review_finished_at).total_seconds()
                            if seconds_since_finish < 120:
                                copilot_work_just_finished = True
                                print(f"[DEBUG] Copilot reviewer JUST finished {seconds_since_finish:.0f}s ago - grace period active")
                            else:
                                print(f"[DEBUG] Copilot reviewer finished {seconds_since_finish:.0f}s ago - grace period passed")
                            print(f"[DEBUG] Copilot reviewer finished review (work_finished: {latest_work_finished} > review_requested: {latest_review_requested})")
                        else:
                            print(f"[DEBUG] Copilot reviewer finished (work_finished: {latest_work_finished} > work_started: {latest_work_started})")
        except Exception as e:
            print(f"[DEBUG] Could not check timeline events: {e}")
        
        # DETECTION 2: Check for "@copilot apply" comment pattern (for APPLYING_CHANGES workflow)
        # This detection is ONLY relevant during the APPLYING_CHANGES workflow state.
        # It does NOT affect the initial PR creation or review phases.
        #
        # When we tell Copilot to apply changes ("@copilot apply changes"), it:
        # 1. Makes multiple commits (could be 1, 2, 5, or more)
        # 2. Posts intermediate comments like "Applied all suggested changes"
        # 3. FINALLY posts: "Copilot finished work on behalf of @user"
        #
        # The ONLY reliable signal is: "Copilot finished work on behalf of"
        # We wait for this, regardless of how many commits or other comments.
        #
        # IMPORTANT: copilot_is_working only becomes True if there's an "@copilot apply"
        # request. For initial PR creation (no apply request), it stays False.
        
        has_apply_changes_request = False
        apply_changes_request_time = None
        copilot_finished_work_time = None
        
        try:
            comments = list(pr.get_issue_comments())
            
            for comment in comments:
                body = comment.body or ""
                body_lower = body.lower()
                comment_time = comment.created_at
                if comment_time.tzinfo is None:
                    comment_time = comment_time.replace(tzinfo=timezone.utc)
                
                # Check for "@copilot apply changes" request (any variation)
                # This triggers the waiting mechanism
                if "@copilot" in body_lower and "apply" in body_lower:
                    has_apply_changes_request = True
                    apply_changes_request_time = comment_time
                
                # Check for THE definitive completion signal
                # "Copilot finished work on behalf of" - this is the ONLY signal we trust
                if "copilot finished work on behalf of" in body_lower:
                    copilot_finished_work_time = comment_time
            
            # Decision logic:
            # - Only activate waiting if there's been an "@copilot apply" request
            # - Without such request, copilot_is_working stays False (no blocking)
            if has_apply_changes_request and apply_changes_request_time:
                if copilot_finished_work_time and copilot_finished_work_time > apply_changes_request_time:
                    # Found "Copilot finished work on behalf of" AFTER the apply request
                    copilot_is_working = False
                    print(f"[DEBUG] Copilot finished work (found 'finished work on behalf of' after apply request)")
                else:
                    # Apply changes requested but no "finished work" signal yet - still working
                    copilot_is_working = True
                    now = datetime.now(timezone.utc)
                    time_since_request = now - apply_changes_request_time
                    print(f"[DEBUG] Copilot still working - apply requested {int(time_since_request.total_seconds())}s ago, waiting for 'finished work on behalf of'")
            # else: No apply request, copilot_is_working stays False (default) - no blocking
                        
        except Exception as e:
            print(f"[DEBUG] Error in Copilot working detection: {e}")
        
        # Get the latest commit SHA for the PR
        latest_commit_sha = pr.head.sha
        
        if reviews:
            latest_review = reviews[-1]
            review_state = latest_review.state
            
            # Check if Copilot has finished reviewing
            # Look for signature text in review body - Copilot reviewer uses various phrases
            for review in reviews:
                if review.body and ("Copilot finished reviewing" in review.body or 
                                   "Copilot reviewed" in review.body):
                    copilot_has_reviewed = True
                    break
        
        # IMPORTANT: Check for pending suggestions OUTSIDE the reviews block
        # This ensures we check review comments whether copilot_has_reviewed was set
        # by timeline events OR by review body signature
        if copilot_has_reviewed:
            try:
                review_comments = list(pr.get_review_comments())
                for comment in review_comments:
                    # Check if this comment was made on an older commit
                    comment_commit = comment.commit_id if hasattr(comment, 'commit_id') else None
                    if comment_commit and comment_commit != latest_commit_sha:
                        # There's a newer commit - comment was likely addressed
                        continue
                    # This comment is on the latest commit - needs attention
                    has_pending_suggestions = True
                    print(f"[DEBUG] Found pending suggestion on latest commit: {comment.body[:50]}...")
                    break
            except Exception as e:
                print(f"[DEBUG] Error checking review comments: {e}")
        
        # Get requested reviewers BEFORE determining state
        requested_reviewers = [r.login for r in pr.get_review_requests()[0]]
        
        # Check PR state - order matters!
        # Priority: merged > closed > approved > changes_requested > copilot_reviewed_with_comments > review_requested > draft > open
        state = PRState.OPEN
        if pr.merged:
            state = PRState.MERGED
        elif pr.state == "closed":
            state = PRState.CLOSED
        elif review_state == "APPROVED":
            state = PRState.APPROVED
        elif review_state == "CHANGES_REQUESTED":
            state = PRState.CHANGES_REQUESTED
        elif copilot_has_reviewed and has_pending_suggestions:
            # Copilot has reviewed and there are comments on current commit = needs changes applied
            state = PRState.CHANGES_REQUESTED
        elif copilot_has_reviewed and not has_pending_suggestions:
            # Copilot reviewed but no comments found (yet)
            # GRACE PERIOD: If Copilot just finished (within 120s), stay in REVIEW_REQUESTED
            # to give GitHub time to index the review comments
            if copilot_work_just_finished:
                state = PRState.REVIEW_REQUESTED
                print(f"[DEBUG] Grace period active - staying in REVIEW_REQUESTED to wait for comments to be indexed")
            else:
                # Grace period passed, and still no suggestions = truly approved
                # Mark as APPROVED - automation will handle marking PR ready for merge
                state = PRState.APPROVED
                print(f"[DEBUG] Grace period passed - Copilot reviewed with no changes needed -> APPROVED")
        elif requested_reviewers and not copilot_has_reviewed:
            # Review requested AND Copilot hasn't reviewed yet
            # If Copilot already reviewed, we shouldn't re-request (avoid loop)
            state = PRState.REVIEW_REQUESTED
        elif pr.draft:
            # Draft PR - either waiting for Copilot to finish or needs manual intervention
            state = PRState.DRAFT
        
        # Extract linked issue from body
        linked_issue = None
        if pr.body:
            import re
            match = re.search(r'TC-[A-Z]-\d{2}', pr.body)
            if match:
                linked_issue = match.group(0)
        
        # Check CI status
        checks_passed = True
        try:
            commits = list(pr.get_commits())
            if commits:
                last_commit = commits[-1]
                check_runs = list(last_commit.get_check_runs())
                for check in check_runs:
                    if check.conclusion not in ["success", "skipped", None]:
                        checks_passed = False
                        break
        except:
            pass
        
        return PRInfo(
            number=pr.number,
            title=pr.title,
            state=state,
            author=pr.user.login,
            reviewers=requested_reviewers,
            review_state=review_state,
            url=pr.html_url,
            linked_issue=linked_issue,
            mergeable=pr.mergeable or False,
            checks_passed=checks_passed,
            is_draft=pr.draft,
            copilot_has_reviewed=copilot_has_reviewed,
            copilot_is_working=copilot_is_working
        )
    
    # ========== UTILITY ==========
    
    def get_current_user(self) -> str:
        """Get the authenticated user's login"""
        return self.gh.get_user().login
