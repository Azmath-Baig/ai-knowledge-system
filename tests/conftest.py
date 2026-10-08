from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return DATA_DIR
