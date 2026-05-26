from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    yield


@pytest.fixture(autouse=True)
def skip_storage_load() -> Generator[None]:
    with patch(
        "homeassistant.helpers.storage.Store.async_load",
        return_value=None,
    ):
        yield
