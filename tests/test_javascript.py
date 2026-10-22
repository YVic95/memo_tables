import shutil
import subprocess
from pathlib import Path

import pytest

JAVASCRIPT_TEST_DIR = Path(__file__).parent / "js"
JAVASCRIPT_TEST_FILES = sorted(JAVASCRIPT_TEST_DIR.glob("test_*.js"))


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize("test_file", JAVASCRIPT_TEST_FILES, ids=lambda path: path.name)
def test_javascript_test_file_passes(test_file):
    result = subprocess.run(
        ["node", "--test", str(test_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
