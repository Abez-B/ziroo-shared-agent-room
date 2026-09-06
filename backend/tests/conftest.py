import os
import pytest

# Ensure all automated pytest suites use mock mode for fast, deterministic, offline execution
os.environ["MOCK_LLM"] = "true"

@pytest.fixture(autouse=True)
def set_test_env():
    os.environ["MOCK_LLM"] = "true"
    yield
