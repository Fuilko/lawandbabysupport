#!/usr/bin/env bash
# LegalShield Bedrock Proxy — One-shot deploy to AWS Lambda
#
# 前提:
#   - awscli v2 + jq がインストール済
#   - 既定 profile （または AWS_PROFILE 環境変数）が hiiforest IAM user に紐付く
#   - 当該 IAM user / role が IAM ロール作成権限を持つ
#
# 使い方:
#   cd aws/bedrock_proxy
#   ./deploy.sh                    # 既定: ap-northeast-1
#   AWS_REGION=us-east-1 ./deploy.sh
#
# 結果:
#   - Lambda 関数 legalshield-bedrock-proxy を作成
#   - Function URL を発行
#   - Bedrock InvokeModel 権限つきの IAM ロールを作成
#   - 共有秘密 (SHARED_SECRET) を openssl で生成し標準出力へ表示
#   - iOS 側の LLMSettings に貼る URL と Bearer トークンを表示

set -euo pipefail

REGION="${AWS_REGION:-ap-northeast-1}"
FN_NAME="legalshield-bedrock-proxy"
ROLE_NAME="legalshield-bedrock-proxy-role"
RUNTIME="python3.12"
HANDLER="lambda_function.lambda_handler"
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "▶ Region: $REGION"
echo "▶ Function: $FN_NAME"
echo

# ── 1. 共有秘密を生成 (再 deploy 時は既存値を流用) ──
SECRET_FILE="$DIR/.shared_secret"
if [[ -f "$SECRET_FILE" ]]; then
  SHARED_SECRET=$(cat "$SECRET_FILE")
  echo "✓ 既存の SHARED_SECRET を流用"
else
  SHARED_SECRET=$(openssl rand -hex 32)
  echo "$SHARED_SECRET" > "$SECRET_FILE"
  chmod 600 "$SECRET_FILE"
  echo "✓ SHARED_SECRET 生成 → $SECRET_FILE"
fi

# ── 2. IAM ロール作成 (なければ) ──
TRUST_POLICY='{
  "Version":"2012-10-17",
  "Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]
}'
BEDROCK_POLICY='{
  "Version":"2012-10-17",
  "Statement":[
    {"Effect":"Allow","Action":["bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream"],"Resource":"*"},
    {"Effect":"Allow","Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],"Resource":"*"}
  ]
}'

if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo "✓ IAM ロール既存: $ROLE_NAME"
else
  echo "▶ IAM ロール作成: $ROLE_NAME"
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document "$TRUST_POLICY" >/dev/null
  aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "bedrock-invoke" \
    --policy-document "$BEDROCK_POLICY" >/dev/null
  echo "  IAM 反映待機 10 秒..."
  sleep 10
fi
ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
echo "  ROLE_ARN: $ROLE_ARN"

# ── 3. Lambda zip 作成 ──
ZIP="$DIR/lambda.zip"
rm -f "$ZIP"
( cd "$DIR" && zip -q "$ZIP" lambda_function.py )
echo "✓ zip 作成: $ZIP"

# ── 4. Lambda 関数 作成 or 更新 ──
ENV_VARS="Variables={SHARED_SECRET=$SHARED_SECRET}"

if aws lambda get-function --region "$REGION" --function-name "$FN_NAME" >/dev/null 2>&1; then
  echo "▶ Lambda 既存 → コード更新"
  aws lambda update-function-code \
    --region "$REGION" \
    --function-name "$FN_NAME" \
    --zip-file "fileb://$ZIP" >/dev/null
  echo "  関数コード更新済"

  # 環境変数も最新化
  aws lambda update-function-configuration \
    --region "$REGION" \
    --function-name "$FN_NAME" \
    --environment "$ENV_VARS" \
    --timeout 60 \
    --memory-size 256 >/dev/null
  echo "  環境変数更新済"
else
  echo "▶ Lambda 関数作成"
  aws lambda create-function \
    --region "$REGION" \
    --function-name "$FN_NAME" \
    --runtime "$RUNTIME" \
    --role "$ROLE_ARN" \
    --handler "$HANDLER" \
    --zip-file "fileb://$ZIP" \
    --timeout 60 \
    --memory-size 256 \
    --environment "$ENV_VARS" >/dev/null
  echo "  関数作成完了"
fi

# ── 5. Function URL 発行 ──
if aws lambda get-function-url-config --region "$REGION" --function-name "$FN_NAME" >/dev/null 2>&1; then
  FN_URL=$(aws lambda get-function-url-config --region "$REGION" --function-name "$FN_NAME" --query 'FunctionUrl' --output text)
  echo "✓ Function URL 既存"
else
  echo "▶ Function URL 発行"
  FN_URL=$(aws lambda create-function-url-config \
    --region "$REGION" \
    --function-name "$FN_NAME" \
    --auth-type NONE \
    --cors '{"AllowOrigins":["*"],"AllowMethods":["POST","GET"],"AllowHeaders":["content-type","authorization"]}' \
    --query 'FunctionUrl' --output text)
  # Public 呼び出し許可
  aws lambda add-permission \
    --region "$REGION" \
    --function-name "$FN_NAME" \
    --statement-id "FunctionURLAllowPublicAccess" \
    --action "lambda:InvokeFunctionUrl" \
    --principal "*" \
    --function-url-auth-type NONE >/dev/null 2>&1 || true
fi

# Function URL の末尾スラッシュ正規化
FN_URL="${FN_URL%/}"

echo
echo "═══════════════════════════════════════════════"
echo "✅ デプロイ完了"
echo "═══════════════════════════════════════════════"
echo
echo "iOS App → 設定 → AI モデル設定 → AWS Bedrock を選択し、以下を貼付："
echo
echo "  Bedrock プロキシ URL : $FN_URL"
echo "  モデル ID            : anthropic.claude-3-5-sonnet-20241022-v2:0"
echo "  API キー             : $SHARED_SECRET"
echo
echo "ヘルスチェック:"
echo "  curl $FN_URL/health"
echo
echo "テスト呼出:"
cat <<EOF
  curl -X POST $FN_URL/invoke \\
    -H "Authorization: Bearer $SHARED_SECRET" \\
    -H "Content-Type: application/json" \\
    -d '{"messages":[{"role":"user","content":"こんにちは"}],"max_tokens":50}'
EOF
echo
echo "⚠ Bedrock console → Model access で Claude 3.5 Sonnet v2 を有効化していない"
echo "  と AccessDeniedException になります。先に enable してください："
echo "  https://${REGION}.console.aws.amazon.com/bedrock/home?region=${REGION}#/modelaccess"
