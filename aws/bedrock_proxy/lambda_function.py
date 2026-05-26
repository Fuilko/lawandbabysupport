"""
LegalShield AWS Bedrock Proxy — Lambda Function
================================================

iOS App → Lambda Function URL → Bedrock InvokeModel.

Why proxy:
- iOS から SigV4 直接署名は Cognito Identity Pool が必要で複雑
- Lambda Function URL なら IAM ロールで Bedrock を叩け、iOS は単純な HTTPS POST のみ
- 共有 Bearer トークンで簡易認証
- レート制限・ログ・監査が中央集約される

Endpoint: POST https://<func-url>/invoke
Header  : Authorization: Bearer <SHARED_SECRET>
Body    : {
            "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "system": "...",
            "messages": [{"role":"user","content":"..."}],
            "max_tokens": 2048,
            "temperature": 0.3
          }
Response: Anthropic Bedrock 標準形式（content[].text）

環境変数:
- SHARED_SECRET   : iOS 側 LLMSettings.bedrockApiKey と一致させる Bearer トークン
- ALLOWED_MODELS  : (任意) カンマ区切りのホワイトリスト
                    例 "anthropic.claude-3-5-sonnet-20241022-v2:0,anthropic.claude-3-haiku-20240307-v1:0"
- AWS_REGION      : Lambda が自動設定（明示する場合は ap-northeast-1）
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_REGION", "ap-northeast-1")
SHARED_SECRET = os.environ.get("SHARED_SECRET", "")
ALLOWED_MODELS = {
    m.strip()
    for m in os.environ.get("ALLOWED_MODELS", "").split(",")
    if m.strip()
}

# Bedrock client は cold start 時に 1 度だけ作る
_bedrock = boto3.client("bedrock-runtime", region_name=REGION)


def _resp(status: int, body: dict[str, Any] | str) -> dict[str, Any]:
    """Lambda Function URL レスポンス整形"""
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": body if isinstance(body, str) else json.dumps(body, ensure_ascii=False),
    }


def _check_auth(headers: dict[str, str]) -> bool:
    """Bearer 認証"""
    if not SHARED_SECRET:
        # 環境変数未設定時は認証必須（拒否）
        return False
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    return auth == f"Bearer {SHARED_SECRET}"


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    start = time.time()

    # ── 1. ルーティング ──────────────────────────────
    method = event.get("requestContext", {}).get("http", {}).get("method", "POST")
    path = event.get("rawPath", "/invoke")
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}

    # ヘルスチェック
    if method == "GET" and path in ("/", "/health"):
        return _resp(200, {"status": "ok", "region": REGION})

    if method != "POST":
        return _resp(405, {"error": "method_not_allowed"})

    # ── 2. 認証 ──────────────────────────────────────
    if not _check_auth(headers):
        return _resp(401, {"error": "unauthorized"})

    # ── 3. ボディ解析 ──────────────────────────────
    try:
        body_raw = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            import base64
            body_raw = base64.b64decode(body_raw).decode("utf-8")
        body = json.loads(body_raw)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
        return _resp(400, {"error": "invalid_json", "detail": str(e)})

    model_id = body.get("model_id") or "anthropic.claude-3-5-sonnet-20241022-v2:0"
    if ALLOWED_MODELS and model_id not in ALLOWED_MODELS:
        return _resp(403, {"error": "model_not_allowed", "model_id": model_id})

    system = body.get("system") or ""
    messages = body.get("messages") or []
    max_tokens = int(body.get("max_tokens") or 2048)
    temperature = float(body.get("temperature") or 0.3)

    if not messages:
        return _resp(400, {"error": "messages_required"})

    # ── 4. Bedrock 呼出（Anthropic Messages API 形式）──
    payload: dict[str, Any] = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    if system:
        payload["system"] = system

    try:
        resp = _bedrock.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload).encode("utf-8"),
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "ClientError")
        logger.exception("Bedrock ClientError: %s", code)
        status = 503 if code in {"ServiceUnavailableException", "ThrottlingException"} else 500
        return _resp(status, {"error": code, "detail": str(e)})
    except Exception as e:  # noqa: BLE001
        logger.exception("Bedrock unexpected error")
        return _resp(500, {"error": "bedrock_failed", "detail": str(e)})

    raw = resp["body"].read()
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        return _resp(502, {"error": "invalid_bedrock_response"})

    latency_ms = int((time.time() - start) * 1000)
    logger.info(
        "ok model=%s in_tokens=%s out_tokens=%s latency=%dms",
        model_id,
        out.get("usage", {}).get("input_tokens"),
        out.get("usage", {}).get("output_tokens"),
        latency_ms,
    )

    # iOS 側 AWSBedrockProvider が想定する Anthropic 形式そのまま返す
    return _resp(200, out)
