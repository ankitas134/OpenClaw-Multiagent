import unittest
import os
import sys
from unittest.mock import MagicMock

# Ensure backend package can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

# Mock docker package if not installed in local environment
if "docker" not in sys.modules:
    try:
        import docker
    except ImportError:
        mock_docker = MagicMock()
        sys.modules["docker"] = mock_docker

from pydantic import ValidationError
from app.core.sandbox_config import SERVER_SANDBOX_SETTINGS, AgentCustomConfigSchema
from app.core.config import settings
from app.sandboxing.docker_manager import spinup_agent_container

class TestSandboxSecurity(unittest.TestCase):

    def test_client_config_extra_forbidden(self):
        """Verify client cannot supply arbitrary sandbox security fields via config."""
        # Allowed custom fields
        valid_custom = AgentCustomConfigSchema(displayName="Test Display", notes="Test Note")
        self.assertEqual(valid_custom.displayName, "Test Display")

        # Forbidden security override attempt
        with self.assertRaises(ValidationError):
            AgentCustomConfigSchema.model_validate({
                "sandboxDockerNetwork": "bridge",
                "memoryLimit": 1073741824
            })

    def test_server_sandbox_settings_defaults(self):
        """Verify server sandbox settings are strict constants."""
        self.assertEqual(SERVER_SANDBOX_SETTINGS.sandboxDockerNetwork, "none")
        self.assertEqual(SERVER_SANDBOX_SETTINGS.sandboxDockerReadOnlyRoot, True)
        self.assertEqual(SERVER_SANDBOX_SETTINGS.sandboxDockerCapDrop, ["ALL"])
        self.assertEqual(SERVER_SANDBOX_SETTINGS.memoryLimit, 268435456)
        self.assertEqual(SERVER_SANDBOX_SETTINGS.cpuLimit, 500000000)

    def test_docker_manager_fails_hard_when_unsandboxed_disabled(self):
        """Verify spinup_agent_container raises RuntimeError when Docker fails and dev mode is False."""
        settings.ALLOW_UNSANDBOXED_DEV_MODE = False
        
        # Force Docker ping error
        sys.modules["docker"].from_env.return_value.ping.side_effect = Exception("Docker daemon unreachable test")

        with self.assertRaises(RuntimeError) as ctx:
            spinup_agent_container(
                agent_id="test-agent-id",
                team_name="TestTeam",
                team_context="Context",
                agent_name="TestAgent",
                task_context="Task"
            )
        self.assertIn("Docker daemon unavailable", str(ctx.exception))

    def test_docker_manager_dev_mode_fallback_when_enabled(self):
        """Verify spinup_agent_container falls back to local-dev-agent when dev mode is True."""
        settings.ALLOW_UNSANDBOXED_DEV_MODE = True
        
        # Force Docker ping error
        sys.modules["docker"].from_env.return_value.ping.side_effect = Exception("Docker daemon unreachable test")

        result = spinup_agent_container(
            agent_id="test-agent-id-dev",
            team_name="TestTeam",
            team_context="Context",
            agent_name="TestAgent",
            task_context="Task"
        )
        self.assertEqual(result, "local-dev-agent-test-agent-id-dev")

    def test_gitignore_contains_env(self):
        """Verify .gitignore exists and includes .env."""
        gitignore_path = os.path.join(os.path.dirname(__file__), ".gitignore")
        self.assertTrue(os.path.exists(gitignore_path), ".gitignore must exist")
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn(".env", content, ".gitignore must contain .env")

if __name__ == "__main__":
    unittest.main()
