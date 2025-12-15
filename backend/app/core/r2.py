from __future__ import annotations

from typing import Optional

import aioboto3
from botocore.exceptions import ClientError

from .config import settings


async def upload_bytes(
    key: str,
    data: bytes,
    bucket: Optional[str] = None,
    content_type: Optional[str] = None,
) -> None:
    bucket = bucket or settings.R2_BUCKET
    if not settings.r2_enabled:
        raise RuntimeError("R2 is not configured")

    async with aioboto3.client("s3", **settings.r2_boto3_config) as client:
        params = {"Bucket": bucket, "Key": key, "Body": data}
        if content_type:
            params["ContentType"] = content_type
        await client.put_object(**params)


async def download_bytes(key: str, bucket: Optional[str] = None) -> bytes:
    bucket = bucket or settings.R2_BUCKET
    if not settings.r2_enabled:
        raise RuntimeError("R2 is not configured")

    async with aioboto3.client("s3", **settings.r2_boto3_config) as client:
        resp = await client.get_object(Bucket=bucket, Key=key)
        async with resp["Body"] as stream:
            return await stream.read()


async def delete_object(key: str, bucket: Optional[str] = None) -> None:
    bucket = bucket or settings.R2_BUCKET
    if not settings.r2_enabled:
        raise RuntimeError("R2 is not configured")

    async with aioboto3.client("s3", **settings.r2_boto3_config) as client:
        await client.delete_object(Bucket=bucket, Key=key)


async def generate_presigned_url(key: str, expires_in: int = 3600, bucket: Optional[str] = None) -> str:
    bucket = bucket or settings.R2_BUCKET
    if not settings.r2_enabled:
        raise RuntimeError("R2 is not configured")

    session = aioboto3.Session()
    async with session.client("s3", **settings.r2_boto3_config) as client:
        # generate_presigned_url is provided by botocore client
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )


__all__ = [
    "upload_bytes",
    "download_bytes",
    "delete_object",
    "generate_presigned_url",
]
