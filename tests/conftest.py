from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent


@pytest.fixture
def tests_dir() -> Path:
    return TESTS_DIR
