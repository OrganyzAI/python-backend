from __future__ import annotations

from typing import cast

import aioboto3  # type: ignore[import-untyped]

from .config import settings


async def upload_bytes(
    key: str,
    data: bytes,
    bucket: str | None = None,
    content_type: str | None = None,
) -> None:
    bucket = bucket or settings.R2_BUCKET
    if not settings.r2_enabled:
        raise RuntimeError("R2 is not configured")

    async with aioboto3.client("s3", **settings.r2_boto3_config) as client:
        params = {"Bucket": bucket, "Key": key, "Body": data}
        if content_type:
            params["ContentType"] = content_type
        await client.put_object(**params)


async def download_bytes(key: str, bucket: str | None = None) -> bytes:
    bucket = bucket or settings.R2_BUCKET
    if not settings.r2_enabled:
        raise RuntimeError("R2 is not configured")

    async with aioboto3.client("s3", **settings.r2_boto3_config) as client:
        resp = await client.get_object(Bucket=bucket, Key=key)
        async with resp["Body"] as stream:
            data = await stream.read()
            return cast(bytes, data)


async def delete_object(key: str, bucket: str | None = None) -> None:
    bucket = bucket or settings.R2_BUCKET
    if not settings.r2_enabled:
        raise RuntimeError("R2 is not configured")

    async with aioboto3.client("s3", **settings.r2_boto3_config) as client:
        await client.delete_object(Bucket=bucket, Key=key)


async def generate_presigned_url(
    key: str, expires_in: int = 3600, bucket: str | None = None
) -> str:
    bucket = bucket or settings.R2_BUCKET
    if not settings.r2_enabled:
        raise RuntimeError("R2 is not configured")

    session = aioboto3.Session()
    async with session.client("s3", **settings.r2_boto3_config) as client:
        # generate_presigned_url is provided by botocore client
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return cast(str, url)


__all__ = [
    "upload_bytes",
    "download_bytes",
    "delete_object",
    "generate_presigned_url",
]
