"""
S3 provider tests against an in-memory fake of AWS S3 (moto).
Proves the cloud code path works without an AWS account or any cost.
"""

from urllib.parse import parse_qs, urlparse

import pytest

moto = pytest.importorskip("moto")
boto3 = pytest.importorskip("boto3")

from cloud.storage_service import S3StorageService, StorageNotFoundError  # noqa: E402

BUCKET = "assignment-submissions-test"


@pytest.fixture
def s3(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with moto.mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        yield S3StorageService(
            bucket=BUCKET, region="us-east-1", endpoint_url=None, access_key_id=None,
            secret_access_key=None, sse="AES256", default_expiry=300,
        )


def test_upload_download_delete(s3):
    key = "assignments/assignment_001/student_003/20260925T101500Z_abcd1234.pdf"
    stored = s3.upload(key, b"%PDF-1.4 demo", "application/pdf")
    assert stored.uri == f"s3://{BUCKET}/{key}"
    assert s3.exists(key)
    assert s3.download(key) == b"%PDF-1.4 demo"

    head = boto3.client("s3", region_name="us-east-1").head_object(Bucket=BUCKET, Key=key)
    assert head["ServerSideEncryption"] == "AES256"  # encryption at rest requested
    assert head["Metadata"]["sha256"] == stored.checksum_sha256

    s3.delete(key)
    assert not s3.exists(key)
    with pytest.raises(StorageNotFoundError):
        s3.download(key)


def test_presigned_url_is_private_and_expiring(s3):
    key = "assignments/assignment_001/student_003/report.pdf"
    s3.upload(key, b"%PDF-1.4 demo", "application/pdf")
    url = s3.generate_signed_url(key, "My Report.pdf", "attachment", expires_in=120)
    query = parse_qs(urlparse(url).query)
    assert query["X-Amz-Expires"] == ["120"]
    assert "X-Amz-Signature" in query
    assert query["response-content-disposition"][0].startswith("attachment;")


def test_health_check(s3):
    assert s3.health_check() is True
