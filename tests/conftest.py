import pytest
from pathlib import Path


@pytest.fixture
def assets_path():
    current_path = Path(__file__).parent
    _assets_path = current_path / "assets"
    return _assets_path
