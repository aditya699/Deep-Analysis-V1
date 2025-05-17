import pytest
import os
from pathlib import Path

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    os.environ["MONGO_URI"] = "mongodb://localhost:27017"
    os.environ["OPENAI_API_KEY"] = "test_key"
    os.environ["BLOB_STORAGE_ACCOUNT_KEY"] = "test_key"
    yield
    # Cleanup
    os.environ.pop("MONGO_URI", None)
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("BLOB_STORAGE_ACCOUNT_KEY", None) 