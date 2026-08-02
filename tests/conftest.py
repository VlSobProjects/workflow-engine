from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent
EXAMPLES_DIR = TESTS_DIR.parent / "examples"


@pytest.fixture
def tests_dir() -> Path:
    return TESTS_DIR


@pytest.fixture
def examples_dir() -> Path:
    return EXAMPLES_DIR
