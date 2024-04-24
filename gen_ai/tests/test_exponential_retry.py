from gen_ai.common.exponential_retry import LLMExponentialRetryWrapper
import pytest
from unittest.mock import Mock, patch
from google.api_core.exceptions import InternalServerError


def test_successful_execution_no_retry():
    mock_chain = Mock()
    mock_chain.run.return_value = "Success"
    wrapper = LLMExponentialRetryWrapper(mock_chain)

    assert wrapper.run("test") == "Success"
    mock_chain.run.assert_called_once_with("test")


def test_retry_logic_on_failure():
    mock_chain = Mock()
    mock_chain.run.side_effect = [InternalServerError("Temporary error"), "Success"]

    wrapper = LLMExponentialRetryWrapper(mock_chain)
    with patch("time.sleep") as mock_sleep:
        assert wrapper.run("test") == "Success"

    assert mock_chain.run.call_count == 2
    mock_sleep.assert_called_once()


def test_max_retry_exceeded():
    mock_chain = Mock()
    mock_chain.run.side_effect = InternalServerError("Persistent error")

    wrapper = LLMExponentialRetryWrapper(mock_chain)
    with patch("time.sleep"), pytest.raises(Exception) as exc_info:
        wrapper.run("test")

    assert "failed after 15 retries" in str(exc_info.value)
    assert mock_chain.run.call_count == 15
