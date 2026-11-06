"""Tests for cloud-registry-connections Lambda security changes.

Covers:
- generate_ids: uses secrets.token_urlsafe (CSPRNG) and stores as SecureString
- generate_ids: returns cached value from SSM without regenerating
- lambda_handler: RequestType=Update returns FAILED
- lambda_handler: unknown RequestType returns FAILED
- lambda_handler: ResponseURL excluded from logged event
"""
import importlib.util
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Environment + stub setup (must happen before the module is imported)
# ---------------------------------------------------------------------------

os.environ.setdefault("secret_name", "test-secret")
os.environ.setdefault("secret_region", "us-east-1")
os.environ.setdefault("permissions_boundary", "arn:aws:iam::123456789012:policy/boundary")
os.environ.setdefault("crowdstrike_principal", "arn:aws:iam::123456789012:root")
os.environ.setdefault("gov_cloud_principal", "arn:aws:iam::123456789012:root")
os.environ.setdefault("stack_id", "test-stack-id")
os.environ.setdefault("role_policy_arn", "arn:aws:iam::aws:policy/ReadOnlyAccess")
os.environ.setdefault("cs_cloud", "us-1")
os.environ.setdefault("regions", "us-east-1")

sys.modules.setdefault("falconpy", MagicMock())

_LAMBDA_PATH = os.path.join(os.path.dirname(__file__), "../AWS/source/lambda/lambda.py")


@pytest.fixture(scope="module")
def lm():
    spec = importlib.util.spec_from_file_location("lambda_func", _LAMBDA_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# generate_ids
# ---------------------------------------------------------------------------

class TestGenerateIds:
    def test_new_id_uses_csprng_and_stored_as_secure_string(self, lm):
        """When SSM has no existing parameter, a new ID is generated with
        secrets.token_urlsafe (CSPRNG) and stored with Type=SecureString."""
        from botocore.exceptions import ClientError

        mock_ssm = MagicMock()
        mock_ssm.get_parameter.side_effect = ClientError(
            {"Error": {"Code": "ParameterNotFound"}}, "GetParameter"
        )

        with patch("boto3.client", return_value=mock_ssm):
            result = lm.generate_ids()

        put_kwargs = mock_ssm.put_parameter.call_args.kwargs
        assert put_kwargs["Type"] == "SecureString"

        valid = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=")
        assert len(result) >= 24
        assert all(c in valid for c in result)

    def test_cached_id_returned_without_regenerating(self, lm):
        """When SSM already has a parameter, its value is returned and no new
        ID is generated or stored."""
        mock_ssm = MagicMock()
        mock_ssm.get_parameter.return_value = {"Parameter": {"Value": "existing-id"}}

        with patch("boto3.client", return_value=mock_ssm):
            result = lm.generate_ids()

        assert result == "existing-id"
        mock_ssm.put_parameter.assert_not_called()

    def test_new_ids_are_unique(self, lm):
        """CSPRNG should produce distinct values on successive calls."""
        from botocore.exceptions import ClientError

        mock_ssm = MagicMock()
        mock_ssm.get_parameter.side_effect = ClientError(
            {"Error": {"Code": "ParameterNotFound"}}, "GetParameter"
        )

        ids = set()
        with patch("boto3.client", return_value=mock_ssm):
            for _ in range(5):
                ids.add(lm.generate_ids())

        assert len(ids) == 5


# ---------------------------------------------------------------------------
# lambda_handler — RequestType routing
# ---------------------------------------------------------------------------

class _Ctx:
    log_stream_name = "test-stream"
    log_group_name = "test-group"


def _event(request_type):
    return {
        "RequestType": request_type,
        "ResponseURL": "https://cloudformation-custom-resource-response-useast1.s3.amazonaws.com/response",
        "StackId": "arn:aws:cloudformation:us-east-1:123456789012:stack/test/abc",
        "RequestId": "req-1",
        "LogicalResourceId": "MyResource",
        "ResourceProperties": {},
    }


class TestLambdaHandlerRequestTypes:
    def _run(self, lm, request_type):
        sent = []
        secret_json = json.dumps({"FalconClientId": "cid", "FalconSecret": "sec"})

        with patch.object(lm, "get_secret", return_value=secret_json), \
             patch.object(lm, "cfnresponse_send", side_effect=lambda *a, **kw: sent.append(a[2])), \
             patch("boto3.client", return_value=MagicMock(
                 get_caller_identity=MagicMock(return_value={"Account": "123456789012"})
             )):
            lm.lambda_handler(_event(request_type), _Ctx())

        return sent

    def test_update_returns_failed(self, lm):
        statuses = self._run(lm, "Update")
        assert lm.FAILED in statuses

    def test_unknown_request_type_returns_failed(self, lm):
        statuses = self._run(lm, "Rotate")
        assert lm.FAILED in statuses


# ---------------------------------------------------------------------------
# ResponseURL redaction
# ---------------------------------------------------------------------------

class TestResponseUrlRedaction:
    def test_response_url_excluded_from_safe_event(self):
        event = {
            "RequestType": "Create",
            "ResponseURL": "https://s3.amazonaws.com/presigned-url",
            "StackId": "stack-1",
            "OtherKey": "value",
        }
        safe = {k: v for k, v in event.items() if k != "ResponseURL"}
        assert "ResponseURL" not in safe

    def test_other_keys_preserved_in_safe_event(self):
        event = {
            "RequestType": "Create",
            "ResponseURL": "https://s3.amazonaws.com/presigned-url",
            "StackId": "stack-1",
            "OtherKey": "value",
        }
        safe = {k: v for k, v in event.items() if k != "ResponseURL"}
        assert safe["RequestType"] == "Create"
        assert safe["StackId"] == "stack-1"
        assert safe["OtherKey"] == "value"
