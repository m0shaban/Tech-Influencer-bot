import os
from pathlib import Path
from typing import Optional


def _env(name: str) -> str:
    return str(os.getenv(name, "") or "").strip()


def _env_any(*names: str) -> str:
    for name in names:
        val = _env(name)
        if val:
            return val
    return ""


def r2_is_configured() -> bool:
    # Check if either R2 or Storj is fully configured
    required_vars = [
        ("R2_ACCESS_KEY_ID", "STORJ_ACCESS_KEY_ID"),
        ("R2_SECRET_ACCESS_KEY", "STORJ_SECRET_ACCESS_KEY"),
        ("R2_ENDPOINT_URL", "STORJ_ENDPOINT_URL"),
        ("R2_BUCKET", "STORJ_BUCKET"),
        ("R2_PUBLIC_BASE_URL", "STORJ_PUBLIC_BASE_URL"),
    ]

    return all(bool(_env_any(*names)) for names in required_vars)


def upload_file_to_r2(
    local_path: str, key: str, content_type: Optional[str] = None
) -> str:
    """Upload a local file to Cloudflare R2 (S3-compatible) and return its public URL.

    Requires env vars:
      - R2_ACCESS_KEY_ID
      - R2_SECRET_ACCESS_KEY
      - R2_ENDPOINT_URL (e.g. https://<accountid>.r2.cloudflarestorage.com)
      - R2_BUCKET
      - R2_PUBLIC_BASE_URL (e.g. https://pub-xxxx.r2.dev or a custom domain)

    Optional:
      - R2_PREFIX (folder prefix inside the bucket)
    """
    if not r2_is_configured():
        raise RuntimeError("R2 is not configured")

    from boto3.session import Session

    file_path = Path(local_path)
    if not file_path.exists():
        raise FileNotFoundError(local_path)

    session = Session(
        aws_access_key_id=_env_any("R2_ACCESS_KEY_ID", "STORJ_ACCESS_KEY_ID"),
        aws_secret_access_key=_env_any(
            "R2_SECRET_ACCESS_KEY", "STORJ_SECRET_ACCESS_KEY"
        ),
    )
    s3 = session.client(
        "s3",
        endpoint_url=_env_any("R2_ENDPOINT_URL", "STORJ_ENDPOINT_URL"),
        region_name="auto",
    )

    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type

    bucket = _env_any("R2_BUCKET", "STORJ_BUCKET")
    s3.upload_file(str(file_path), bucket, key, ExtraArgs=extra_args or None)

    public_base = _env_any("R2_PUBLIC_BASE_URL", "STORJ_PUBLIC_BASE_URL").rstrip("/")
    return f"{public_base}/{key.lstrip('/')}"


def upload_image_if_configured(local_path: str, filename: str) -> Optional[str]:
    """Best-effort uploader. Returns public URL if uploaded, else None."""
    if not r2_is_configured():
        return None

    # Check if using Storj (STORJ_ prefixed env vars)
    use_storj = bool(os.getenv("STORJ_ACCESS_KEY_ID"))

    if use_storj:
        # Storj: Upload directly to bucket without additional prefix
        # (STORJ_PUBLIC_BASE_URL already includes bucket path)
        key = filename
    else:
        # R2: Use optional R2_PREFIX
        prefix = _env_any("R2_PREFIX", "STORJ_PREFIX").strip("/")
        key = f"{prefix}/{filename}" if prefix else filename

    return upload_file_to_r2(local_path=local_path, key=key, content_type="image/png")
