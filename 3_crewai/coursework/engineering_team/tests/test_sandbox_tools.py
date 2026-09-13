import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from engineering_team.tools import sandbox_tools


class ResetSandboxTests(unittest.TestCase):
    @patch("engineering_team.tools.sandbox_tools.subprocess.run")
    def test_reset_sandbox_does_not_join_parent_workspace(self, run):
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            sandbox.mkdir()
            with patch.object(sandbox_tools, "SANDBOX_DIR", sandbox):
                with patch.dict(os.environ, {"VIRTUAL_ENV": "/tmp/parent-.venv"}):
                    sandbox_tools.reset_sandbox()

        init_cmd = run.call_args_list[0].args[0]
        add_cmd = run.call_args_list[1].args[0]
        init_env = run.call_args_list[0].kwargs["env"]

        self.assertIn("--no-workspace", init_cmd)
        self.assertIn("--no-sync", add_cmd)
        self.assertNotIn("VIRTUAL_ENV", init_env)
