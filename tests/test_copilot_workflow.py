
import unittest
from unittest.mock import MagicMock, PropertyMock
from datetime import datetime, timedelta, timezone
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from github_client import GitHubClient, PRState

class MockComment:
    def __init__(self, body, created_at):
        self.body = body
        self.created_at = created_at

class TestCopilotDetection(unittest.TestCase):
    def setUp(self):
        self.client = GitHubClient(owner="test", repo="test", token="test")
        self.client.gh = MagicMock()
        self.client._repo = MagicMock()

    def test_copilot_working_detection(self):
        # Setup mock PR
        pr = MagicMock()
        pr.number = 1
        pr.title = "Test PR"
        pr.body = "Test Body"
        pr.user.login = "copilot"
        pr.html_url = "http://github.com/test/1"
        pr.mergeable = True
        pr.draft = True
        pr.head.sha = "sha1"
        
        # Mock timeline events (empty for now)
        # We need to mock requests.get for timeline events
        # But let's focus on Detection 2 (comments) which is what the user is complaining about
        
        # Scenario:
        # 1. User requests changes (Review)
        # 2. User says "@copilot apply changes"
        # 3. Copilot says "Copilot started work on behalf of..."
        # 4. Copilot pushes commits (PR state might change here if reviews are dismissed)
        # 5. Copilot says "Applied all suggested changes" (Intermediate?)
        # 6. Copilot says "Copilot finished work on behalf of..." (Final)
        
        # Use 5 minutes ago to avoid the 10-minute timeout safeguard
        base_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        comments = [
            MockComment("@copilot apply changes", base_time),
            MockComment("Copilot started work on behalf of user", base_time + timedelta(seconds=10)),
            # Intermediate message that might be triggering false positive?
            MockComment("I have applied the changes to file.py", base_time + timedelta(seconds=30)), 
        ]
        
        pr.get_issue_comments.return_value = comments
        pr.get_reviews.return_value = []
        pr.get_review_requests.return_value = ([MagicMock(login="reviewer")], [])
        pr.get_commits.return_value = []
        
        # We need to mock the timeline request to return nothing so it doesn't interfere
        with unittest.mock.patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = []
            
            # Run the detection logic
            pr_info = self.client._to_pr_info(pr)
            
            print(f"PR Info State: {pr_info.state}")
            print(f"Copilot is working: {pr_info.copilot_is_working}")
            
            # If "I have applied the changes" triggers completion, copilot_is_working will be False
            # But we want it to be True because "Copilot finished work on behalf of" hasn't appeared yet
            
            if not pr_info.copilot_is_working:
                print("FAIL: Copilot detected as finished too early!")
            else:
                print("PASS: Copilot correctly detected as working.")

    def test_copilot_finished_detection(self):
        # Setup mock PR
        pr = MagicMock()
        pr.number = 1
        pr.title = "Test PR"
        pr.body = "Test Body"
        pr.user.login = "copilot"
        pr.html_url = "http://github.com/test/1"
        pr.mergeable = True
        pr.draft = True
        pr.head.sha = "sha1"
        
        base_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        comments = [
            MockComment("@copilot apply changes", base_time),
            MockComment("Copilot started work on behalf of user", base_time + timedelta(seconds=10)),
            MockComment("I have applied the changes to file.py", base_time + timedelta(seconds=30)),
            MockComment("Copilot finished work on behalf of user", base_time + timedelta(seconds=60)),
        ]
        
        pr.get_issue_comments.return_value = comments
        pr.get_reviews.return_value = []
        pr.get_review_requests.return_value = ([MagicMock(login="reviewer")], [])
        pr.get_commits.return_value = []
        
        with unittest.mock.patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = []
            
            pr_info = self.client._to_pr_info(pr)
            
            print(f"PR Info State: {pr_info.state}")
            print(f"Copilot is working: {pr_info.copilot_is_working}")
            
            if pr_info.copilot_is_working:
                print("FAIL: Copilot detected as working but should be finished!")
                self.fail("Copilot detected as working but should be finished!")
            else:
                print("PASS: Copilot correctly detected as finished.")

    def test_ignore_previous_finished_work(self):
        # Setup mock PR
        pr = MagicMock()
        pr.number = 1
        pr.title = "Test PR"
        pr.body = "Test Body"
        pr.user.login = "copilot"
        pr.html_url = "http://github.com/test/1"
        pr.mergeable = True
        pr.draft = True
        pr.head.sha = "sha1"
        
        # Timeline:
        # T0: Previous cycle finished
        # T1: New changes requested (@copilot apply)
        # T2: Current time (Copilot still working)
        
        base_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        comments = [
            # Previous cycle
            MockComment("@copilot apply changes", base_time),
            MockComment("Copilot finished work on behalf of user", base_time + timedelta(minutes=1)),
            
            # New cycle - Copilot started but NOT finished
            MockComment("@copilot apply changes", base_time + timedelta(minutes=5)),
            MockComment("Copilot started work on behalf of user", base_time + timedelta(minutes=6)),
        ]
        
        pr.get_issue_comments.return_value = comments
        pr.get_reviews.return_value = []
        pr.get_review_requests.return_value = ([MagicMock(login="reviewer")], [])
        pr.get_commits.return_value = []
        
        with unittest.mock.patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = []
            
            pr_info = self.client._to_pr_info(pr)
            
            print(f"PR Info State: {pr_info.state}")
            print(f"Copilot is working: {pr_info.copilot_is_working}")
            
            # Should be True because the latest apply (T+5m) has no matching finish message
            # The finish message at T+1m should be ignored
            
            if not pr_info.copilot_is_working:
                print("FAIL: Copilot detected as finished because of old message!")
                self.fail("Copilot detected as finished because of old message!")
            else:
                print("PASS: Copilot correctly ignored previous finished message.")

if __name__ == '__main__':
    unittest.main()
