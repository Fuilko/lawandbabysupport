# iPhone 実機デプロイ クイックスタート

**対象**：USB ケーブル入手後、iPhone に LegalShield を直接インストールするまでの最短手順。

---

## 0. 用意するもの

- ✅ Mac (このリポジトリが clone 済)
- ✅ iPhone (iOS 17 以上)
- ⚠️ **USB-C ↔ Lightning** または **USB-C ↔ USB-C** ケーブル（買い物中）
  - iPhone 14 以前 = Lightning
  - iPhone 15 以降 = USB-C
- ✅ Apple ID（無料の Personal Team で 7 日間動く。Apple Developer Program 加入後は 1 年）

---

## 1. Xcode で Apple ID をサインイン（一度だけ）

1. Xcode を起動
2. メニュー: **Xcode → Settings → Accounts**
3. 左下 `+` → Apple ID → 自分の Apple ID でログイン
4. ログイン後、`Personal Team` が自動で表示されれば OK

---

## 2. プロジェクト生成

ターミナル：

```bash
cd ~/工作用/lawandbabysupport/ios/LegalShield
brew install xcodegen   # 初回のみ
xcodegen generate
open LegalShield.xcodeproj
```

Xcode が開く。

---

## 3. Signing & Capabilities 設定（一度だけ）

Xcode 左ペインで `LegalShield` ターゲット選択 → タブ **Signing & Capabilities**：

- **Team**：プルダウンから `<自分の名前> (Personal Team)` を選択
- **Bundle Identifier**：`com.legalshield.ios` のままでよい
- もし「This bundle identifier is not available」と出たら → 末尾に自分のイニシャル等を足して一意化（例: `com.legalshield.ios.kj`）

---

## 4. iPhone を Mac に接続（ケーブル買って戻ってからここから）

1. iPhone を Mac に USB ケーブルで接続
2. iPhone 側で「このコンピュータを信頼しますか？」 → **信頼**
3. iPhone 側 設定 → プライバシーとセキュリティ → 一番下の **デベロッパモード** → **オン**（再起動が要求される）
4. Xcode 上部のターゲット選択（Simulator が出ている所）をクリック → 接続中の自分の iPhone を選択

---

## 5. 実行

`⌘R`（Run）

初回ビルド ~30 秒。アプリが iPhone 上で起動する。

---

## 6. 起動時に「信頼されていない開発元」と出たら

iPhone：
1. 設定 → 一般 → **VPN とデバイス管理**
2. `<自分の Apple ID>` をタップ → **このデベロッパを信頼**
3. もう一度 LegalShield をタップして起動

---

## 7. 7 日後に起動できなくなったら（無料 Personal Team の場合）

Mac で再度 `⌘R` するだけ。署名期限が再発行される。

長期的には **Apple Developer Program (USD 99/年)** に加入すれば 1 年間有効＋ TestFlight で他人にも配布可能。

---

## 8. AWS Bedrock を繋ぐ場合

別途、`aws/bedrock_proxy/` の Lambda を一度だけデプロイ：

```bash
cd aws/bedrock_proxy
./deploy.sh
```

出力された URL / API キーを iPhone の **設定 → AI モデル設定 → AWS Bedrock** に入力。

詳細は `aws/bedrock_proxy/README.md` 参照。

---

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| `xcodegen: command not found` | `brew install xcodegen` |
| `No signing certificate "iOS Development"` | Xcode → Settings → Accounts → Manage Certificates → `+` → Apple Development |
| `iPhone is not available` | iPhone 接続後、Xcode で「Prepare for Development Use」を待つ（初回 5〜10 分） |
| `Could not launch "LegalShield"` | iPhone 設定 → VPN とデバイス管理 → 自分の Apple ID を信頼 |
| Bundle ID conflict | `project.yml` の `PRODUCT_BUNDLE_IDENTIFIER` を `com.legalshield.ios.<自分の ID>` に変更 → `xcodegen generate` |
| App 起動して即落ち | Xcode コンソール（View → Debug Area → Activate Console）でログ確認 |
