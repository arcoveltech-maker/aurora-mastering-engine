"""
S3/MinIO storage service.
"""
from __future__ import annotations

import asyncio
import functools
import re
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.errors import AuroraHTTPException


def _get_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4"),
    )


_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._\-]")


def _safe_name(filename: str) -> str:
    name = _SAFE_NAME_RE.sub("_", filename)
    return name[:200]


def build_key(user_id: str, session_id: str, filename: str) -> str:
    return f"users/{user_id}/{session_id}/{_safe_name(filename)}"


def validate_key_ownership(key: str, user_id: str) -> None:
    if not key.startswith(f"users/{user_id}/"):
        raise AuroraHTTPException("AURORA-E602", f"Key '{key}' does not belong to user {user_id}")


async def generate_presigned_upload_url(key: str, content_type: str, expires: int = 300) -> str:
    loop = asyncio.get_event_loop()
    client = _get_client()
    url = await loop.run_in_executor(
        None,
        functools.partial(
            client.generate_presigned_url,
            "put_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key, "ContentType": content_type},
            ExpiresIn=expires,
        ),
    )
    return url


async def generate_presigned_download_url(key: str, expires: int = 3600) -> str:
    loop = asyncio.get_event_loop()
    client = _get_client()
    url = await loop.run_in_executor(
        None,
        functools.partial(
            client.generate_presigned_url,
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=expires,
        ),
    )
    return url


async def upload_file(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    loop = asyncio.get_event_loop()
    client = _get_client()
    await loop.run_in_executor(
        None,
        functools.partial(
            client.put_object,
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
        ),
    )


async def delete_file(key: str) -> None:
    loop = asyncio.get_event_loop()
    client = _get_client()
    try:
        await loop.run_in_executor(
            None,
            functools.partial(client.delete_object, Bucket=settings.S3_BUCKET, Key=key),
        )
    except ClientError:
        pass


async def object_exists(key: str) -> bool:
    loop = asyncio.get_event_loop()
    client = _get_client()
    try:
        await loop.run_in_executor(
            None,
            functools.partial(client.head_object, Bucket=settings.S3_BUCKET, Key=key),
        )
        return True
    except ClientError:
        return False


async def get_object_size(key: str) -> int:
    loop = asyncio.get_event_loop()
    client = _get_client()
    resp = await loop.run_in_executor(
        None,
        functools.partial(client.head_object, Bucket=settings.S3_BUCKET, Key=key),
    )
    return resp["ContentLength"]


def _get_user_storage_usage_sync(user_id: str) -> int:
    client = _get_client()
    prefix = f"users/{user_id}/"
    total = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            total += obj["Size"]
    return total


async def get_user_storage_usage(user_id: str) -> int:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_user_storage_usage_sync, user_id)


def _delete_user_data_sync(user_id: str) -> None:
    client = _get_client()
    prefix = f"users/{user_id}/"
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.S3_BUCKET, Prefix=prefix):
        objects = [{"Key": o["Key"]} for o in page.get("Contents", [])]
        if objects:
            client.delete_objects(Bucket=settings.S3_BUCKET, Delete={"Objects": objects})


async def delete_user_data(user_id: str) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _delete_user_data_sync, user_id)
