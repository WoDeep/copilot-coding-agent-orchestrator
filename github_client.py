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
        # Determine review state
        reviews = list(pr.get_reviews())
        review_state = None
        has_suggestions = False
        if reviews:
            latest_review = reviews[-1]
            review_state = latest_review.state
            
            # Check if there are review comments with suggestions
            # COMMENTED reviews with suggestions should be treated like CHANGES_REQUESTED
            if review_state == "COMMENTED":
                try:
                    review_comments = list(pr.get_review_comments())
                    for comment in review_comments:
                        if "```suggestion" in (comment.body or ""):
                            has_suggestions = True
                            break
                except:
                    pass
        
        # Get requested reviewers BEFORE determining state
        requested_reviewers = [r.login for r in pr.get_review_requests()[0]]
        
        # Check PR state - order matters!
        # Priority: merged > closed > approved > changes_requested > suggestions > review_requested > draft > open
        state = PRState.OPEN
        if pr.merged:
            state = PRState.MERGED
        elif pr.state == "closed":
            state = PRState.CLOSED
        elif review_state == "APPROVED":
            state = PRState.APPROVED
        elif review_state == "CHANGES_REQUESTED":
            state = PRState.CHANGES_REQUESTED
        elif has_suggestions:
            # COMMENTED review with suggestions = needs changes applied
            state = PRState.CHANGES_REQUESTED
        elif requested_reviewers:
            # If review has been requested, this takes priority over draft
            # Because Copilot requests review when it's ready for feedback
            state = PRState.REVIEW_REQUESTED
        elif pr.draft:
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
            checks_passed=checks_passed
        )
    
    # ========== UTILITY ==========
    
    def get_current_user(self) -> str:
        """Get the authenticated user's login"""
        return self.gh.get_user().login
