# LegalShield AWS Bedrock Proxy

iOS App から Claude (Anthropic on Bedrock) を安全に呼び出すための薄い Lambda プロキシ。

## アーキテクチャ

```
iPhone (LegalShield)
    │  HTTPS POST /invoke
    │  Authorization: Bearer <SHARED_SECRET>
    ▼
Lambda Function URL  ──────►  AWS Bedrock InvokeModel  ──────►  Claude
    │  (IAM Role: bedrock:InvokeModel)
    │
    └─►  CloudWatch Logs (監査・レイテンシ・コスト分析)
```

**iOS 側で SigV4 署名を実装しなくてよい** のがミソ。Cognito も不要。Lambda の IAM ロールが Bedrock を叩く。

## 前提

- AWS CLI v2 + jq インストール済
- IAM user `hiiforest` の credentials が `~/.aws/credentials` に設定済
  （または `AWS_PROFILE=hiiforest ./deploy.sh`）
- 当該 IAM user に IAM ロール作成権限がある
- **Bedrock Console → Model access** で Claude 3.5 Sonnet v2 を有効化済
  - `ap-northeast-1` (東京) で利用可能なモデル：
    https://ap-northeast-1.console.aws.amazon.com/bedrock/home?region=ap-northeast-1#/modelaccess

## 一発デプロイ

```bash
cd aws/bedrock_proxy
./deploy.sh
```

出力に以下 3 つが表示される：

```
Bedrock プロキシ URL : https://xxxxx.lambda-url.ap-northeast-1.on.aws
モデル ID            : anthropic.claude-3-5-sonnet-20241022-v2:0
API キー             : <hex 64 字>
```

これを iOS App **設定 → AI モデル設定 → AWS Bedrock** に貼り付け。

## ヘルスチェック

```bash
curl https://xxxxx.lambda-url.ap-northeast-1.on.aws/health
# {"status": "ok", "region": "ap-northeast-1"}
```

## 動作テスト

```bash
curl -X POST "$URL/invoke" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "messages":[{"role":"user","content":"日本の刑法 130 条を要約してください"}],
    "max_tokens": 200
  }'
```

## コスト目安

- Lambda 自体は月数百〜千リクエスト程度なら **無料枠内**
- Claude 3.5 Sonnet 入力 $3 / 1M tokens、出力 $15 / 1M tokens
- LegalShield の典型的な query: 入力 1〜3K tokens / 出力 0.5〜2K tokens
  - ≒ 1 query あたり $0.005〜$0.04
- 100 query/日 × 30 日 ≒ $15〜$120/月

## セキュリティ

- 認証は **Bearer (SHARED_SECRET)** のみ。簡易なので濫用注意。
  - 本番運用時は API Gateway + Cognito User Pool を推奨
- `SHARED_SECRET` は `.shared_secret` ファイルに保存、git ignored
- IAM ロールは `bedrock:InvokeModel` + CloudWatch Logs のみ。最小権限

## 改修ポイント

| やりたい | どこを変更 |
|---|---|
| モデルをホワイトリスト制限 | Lambda 環境変数 `ALLOWED_MODELS` をカンマ区切り設定 |
| レート制限追加 | Lambda 内に DynamoDB トークンバケット実装 |
| ログを S3 に長期保存 | CloudWatch Logs → Subscription Filter |
| ストリーミング応答 | Lambda Function URL は SSE 未対応なので API Gateway WebSocket へ移行 |

## ファイル

| Path | 説明 |
|---|---|
| `lambda_function.py` | Lambda エントリポイント (Anthropic Messages API 形式) |
| `deploy.sh` | 一発デプロイスクリプト |
| `.shared_secret` | 自動生成された Bearer トークン (gitignored) |
| `lambda.zip` | デプロイ時に作成 (gitignored) |
