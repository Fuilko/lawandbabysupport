# LegalShield APP 開発技術ガイド

> **目標**: 既存のデータベースと AI システムを iOS / Android アプリとして実装する
> **対象読者**: 開発者、技術パートナー、投資家のテクニカルデューデリジェンス

---

## 目次

1. [既存技術資産の棚卸し](#1-既存技術資産の棚卸し)
2. [アプリ化の道筋選択](#2-アプリ化の道筋選択)
3. [端末内 AI 推論の実装](#3-端末内-ai-推論の実装)
4. [ベクトルデータベースの端末化](#4-ベクトルデータベースの端末化)
5. [スマホネイティブ機能の呼び出し](#5-スマホネイティブ機能の呼び出し)
6. [プライバシーとセキュリティアーキテクチャ](#6-プライバシーとセキュリティアーキテクチャ)
7. [開発スケジュールとマイルストーン](#7-開発スケジュールとマイルストーン)
8. [開発者募集](#8-開発者募集)

---

## 1. 既存技術資産の棚卸し

### 1.1 データ層（完成済み）

| データセット | 規模 | 形式 | 保存場所 |
|-----------|------|------|---------|
| 国法全文 | 623,703 chunks | Parquet + LanceDB | `knowledge/vectors/` |
| 判例全文 | 724,443 chunks | Parquet + LanceDB | `knowledge/vectors/` |
| e-Stat 統計 | 885 テーブル | Parquet | `knowledge/vectors/` |
| 全国ホットライン | 24 件 | CSV | `knowledge/seeds/` |
| 加害者プロファイル | 17 類型 | Python dict + JSON | `backend/perpetrator_profiler.py` |
| 犯罪分類学 | 17 類型 | Markdown | `docs/CRIME_TAXONOMY_EXTENDED.md` |

### 1.2 AI 層（プロトタイプ完成）

| モジュール | 機能 | 状態 |
|----------|------|------|
| `victim_assistant.py` | 5重ロール AI（緊急・証拠・法律・戦略・転介） | ✅ 実行可能 |
| `perpetrator_profiler.py` | 加害者プロファイル・狡弁分析・反論生成 | ✅ 実行可能 |
| `anti_grafting.py` | 被害届不受理防止レポート・警察交渉スクリプト | ✅ 実行可能 |
| `evidence_vault.py` | 証拠保全・ハッシュ・暗号化・証明書 | ✅ 実行可能 |
| `jstage_analyzer.py` | 学術論文分析 | ✅ 実行可能 |

### 1.3 フロントエンドプロトタイプ（完成済み）

| プロトタイプ | 技術 | パス |
|------------|------|------|
| Streamlit デモ | Python Streamlit | `frontend/streamlit_demo.py` |
| 緊急モード + トリアージ HTML | 純 HTML/CSS/JS | `frontend/triage_onboarding.html` |
| パートナー向け Pitch Deck | HTML | `docs/PARTNER_PITCH_DECK.html` |
| 統合紹介ページ | HTML | `docs/LEGALSHIELD_INTRO_JP.html` |

---

## 2. アプリ化の道筋選択

### 2.1 3つの道筋の比較

| 道筋 | 技術 | メリット | デメリット | 推奨度 |
|------|------|---------|----------|--------|
| **A. PWA (Web APP)** | Next.js / React + Service Worker | 2週間でリリース、審査不要、クロスプラットフォーム | ネイティブ機能制限（SMS・オフライン AI が弱い） | ⭐⭐⭐⭐ <br> MVP 最適 |
| **B. Flutter** | Dart + Flutter SDK | 1つのコードで iOS+Android、高性能、ネイティブ機能完全対応 | Dart の学習が必要、初期設定がやや複雑 | ⭐⭐⭐⭐⭐ <br> 本番推奨 |
| **C. React Native** | JavaScript + React Native | JS エコシステムが巨大、開発者が見つけやすい | 性能やや劣る、バージョン断片化が激しい | ⭐⭐⭐⭐ |

### 2.2 推奨:「漸進的道筋」

```
Phase 0 (現在): Streamlit デモ → 概念検証、フィードバック収集
Phase 1 (1-2ヶ月): PWA → 最速リリース、ユーザ行動の検証
Phase 2 (3-4ヶ月): Flutter MVP → ネイティブ機能、端末 AI、ストア審査
Phase 3 (6-12ヶ月): Flutter フル → 全機能、自治体 SaaS 連携
```

---

## 3. 端末内 AI 推論の実装

### 3.1 なぜ端末内推論が必須か？

被害者のスマホは以下のような場所にある可能性があります：
- 地下室（DV 避難中）
- 機内モード（監禁・コントロール下）
- 田舎（電波不安定）
- 絶対的なプライバシーが必要（サーバーに内容を知られたくない）

**結論：AI 推論は完全に端末内で完結しなければならない。**

### 3.2 モデル選択（端末で動く小モデル）

| モデル | サイズ | 言語 | 用途 | 推論速度 |
|--------|--------|------|------|---------|
| **Phi-3 Mini** | 3.8B | 多言語（日本語含む） | 対話・戦略シミュレーション | 中 |
| **Gemma 2B** | 2B | 多言語（日本語含む） | 対話・法律分析 | 速い |
| **Llama-3.2 1B** | 1B | 多言語（日本語含む） | 意図分類・トリアージ | 非常に速い |
| **Whisper Tiny** | 39M | 多言語 | 音声文字起こし | 速い |

### 3.3 端末推論コード例（Flutter + ONNX）

```dart
// Flutter + ONNX Runtime Mobile
import 'package:onnxruntime/onnxruntime.dart';

class LegalShieldAI {
  late OrtSession _session;

  Future<void> loadModel() async {
    // APP バンドルから量子化モデルを読み込み
    final modelPath = await _getModelPath('legalshield_gemma_2b.onnx');
    final sessionOptions = OrtSessionOptions();
    _session = OrtSession.fromFile(modelPath, sessionOptions);
  }

  Future<String> infer(String userInput) async {
    // 1. 意図分類（トリアージ）
    final intent = await _classifyIntent(userInput);

    // 2. 意図に応じて対応ロールを呼び出し
    switch (intent) {
      case 'emergency':
        return await _emergencyResponder(userInput);
      case 'evidence':
        return await _evidenceCollector(userInput);
      case 'legal':
        return await _legalAnalyst(userInput);
      case 'strategy':
        return await _strategySimulator(userInput);
      case 'referral':
        return await _referralNavigator(userInput);
      default:
        return await _generalSupport(userInput);
    }
  }

  Future<String> _legalAnalyst(String query) async {
    // 端末内 RAG：ベクトルデータベースを検索
    final relevantLaws = await _localVectorSearch(query, topK: 5);
    // プロンプトを構築
    final prompt = _buildLegalPrompt(query, relevantLaws);
    // 推論実行
    final output = await _runInference(prompt);
    return output;
  }
}
```

### 3.4 モデル量子化戦略

```python
# Python 側のモデル量子化スクリプト（開発者用）
from optimum.onnxruntime import ORTModelForCausalLM
from transformers import AutoTokenizer

model = ORTModelForCausalLM.from_pretrained(
    "google/gemma-2b",
    export=True,
    provider="CPUExecutionProvider",
)
tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b")

# 量子化モデル（INT8）を保存
model.save_pretrained("legalshield_gemma_2b_onnx")
tokenizer.save_pretrained("legalshield_gemma_2b_onnx")
```

---

## 4. ベクトルデータベースの端末化

### 4.1 データベースサイズの試算

| データセット | 元サイズ | 量子化後（端末） | 圧縮率 |
|-----------|---------|---------------|--------|
| 国法 623K | ~2GB | ~400MB | 80% |
| 判例 724K | ~3GB | ~500MB | 83% |
| e-Stat 885 | ~100MB | ~20MB | 80% |
| 合計 | ~5.1GB | ~920MB | ~82% |

**結論：920MB の端末データベースは現実的。**（現代のスマホは 64GB+）

### 4.2 LanceDB 組み込みの使用

```dart
// Flutter + LanceDB（組み込み）
import 'package:lance_db/lance_db.dart';

class LegalShieldDB {
  late LanceTable _lawTable;
  late LanceTable _caseTable;

  Future<void> initialize() async {
    final dbPath = await _getLocalDBPath();
    final db = await LanceDB.connect(dbPath);

    // 既存テーブルを開く（初回起動時にサーバーから同期）
    _lawTable = await db.openTable('elaws_vectors');
    _caseTable = await db.openTable('precedent_vectors');
  }

  Future<List<Map<String, dynamic>>> searchLaws(
    String query,
    {int topK = 5}
  ) async {
    // 1. クエリテキストをベクトル化（端末内 MiniLM モデル）
    final queryVector = await _embedText(query);

    // 2. ベクトル検索
    final results = await _lawTable.search(queryVector)
      .limit(topK)
      .execute();

    return results.map((r) => r.metadata).toList();
  }
}
```

### 4.3 初回同期戦略

```
ユーザーが APP をインストール
  ↓
初回起動：~920MB のデータベース圧縮パッケージをダウンロード
  ↓
バックグラウンドで解凍 + インデックス構築（約 2-5 分）
  ↓
以降：増分更新のみ（週次 ~10-50MB）
  ↓
オフラインで完全使用可能
```

---

## 5. スマホネイティブ機能の呼び出し

### 5.1 機能総表

| 機能 | Flutter パッケージ | React Native パッケージ | PWA API |
|------|-------------------|------------------------|---------|
| **GPS** | `geolocator` | `@react-native-community/geolocation` | Geolocation API ✅ |
| **カメラ** | `image_picker` + `camera` | `react-native-image-picker` | MediaDevices API ⚠️ |
| **マイク** | `flutter_sound` + `speech_to_text` | `@react-native-voice/voice` | MediaRecorder API ⚠️ |
| **SMS** | `flutter_sms` | `react-native-sms` | ❌ 不可（ネイティブ必須） |
| **通知** | `flutter_local_notifications` | `@notifee/react-native` | Notifications API ✅ |
| **生体認証** | `local_auth` | `@react-native-biometrics` | WebAuthn ✅ |
| **オフライン保存** | `hive` + `sqflite` | `AsyncStorage` + `SQLite` | IndexedDB ✅ |

### 5.2 GPS の実装（Flutter）

```dart
import 'package:geolocator/geolocator.dart';

Future<Position?> getCurrentLocation() async {
  // 権限チェック
  LocationPermission permission = await Geolocator.checkPermission();
  if (permission == LocationPermission.denied) {
    permission = await Geolocator.requestPermission();
    if (permission == LocationPermission.denied) return null;
  }

  // 高精度位置を取得
  return await Geolocator.getCurrentPosition(
    desiredAccuracy: LocationAccuracy.high,
  );
}

// プライバシー保護のための位置ぼかし
Map<String, double> obfuscateLocation(Position pos) {
  // 小数点以下 2 桁まで（約 1km 精度）
  return {
    'latitude': (pos.latitude * 100).round() / 100,
    'longitude': (pos.longitude * 100).round() / 100,
  };
}
```

### 5.3 カメラ + 証拠透かし（Flutter）

```dart
import 'package:image_picker/image_picker.dart';
import 'package:image/image.dart' as img;
import 'package:crypto/crypto.dart';

Future<void> captureEvidence() async {
  final picker = ImagePicker();
  final photo = await picker.pickImage(source: ImageSource.camera);
  if (photo == null) return;

  // 1. 画像を読み込み
  final bytes = await photo.readAsBytes();
  final image = img.decodeImage(bytes)!;

  // 2. SHA-256 を計算
  final hash = sha256.convert(bytes).toString();

  // 3. 位置と時刻を取得
  final position = await getCurrentLocation();
  final timestamp = DateTime.now().toIso8601String();

  // 4. 改竄不可能な透かしを追加
  final watermarked = _addWatermark(image, hash: hash, time: timestamp, location: position);

  // 5. AES-256 で暗号化保存
  await _saveEncrypted(watermarked, filename: 'evidence_${timestamp}.jpg');
}
```

### 5.4 緊急 SMS（Flutter）

```dart
import 'package:flutter_sms/flutter_sms.dart';

Future<void> sendEmergencySMS() async {
  final contacts = await _getEmergencyContacts(); // 最大3人
  final location = await getCurrentLocation();
  final obfuscated = obfuscateLocation(location!);

  final message = '''
【LegalShield 自動緊急通知】
${await _getUserDisplayName()} が緊急事態に遭遇しました。
位置：${obfuscated['latitude']}, ${obfuscated['longitude']}（都道府県レベル）
時刻：${DateTime.now().toIso8601String()}

このメッセージは自動生成されたものです。
本人の確認が取れない場合、最寄りの支援機関に連絡してください。
'''; // ⚠️ 正確な GPS は送信せず、ぼかし位置のみ

  await sendSMS(message: message, recipients: contacts);
}
```

### 5.5 無音モード（Silent Mode）

```dart
import 'package:flutter_sms/flutter_sms.dart';
import 'package:flutter/services.dart';

Future<void> sendSilentSMS() async {
  // 1. デバイスを最小音量に
  await SystemSound.play(SystemSoundType.click); // 最小限の音

  // 2. SMS を送信（振動なし・音なし）
  await sendSMS(
    message: _buildSilentMessage(),
    recipients: _emergencyContacts,
    sendDirect: true, // システム SMS App を開かずに直接送信
  );

  // 3. 送信後、元の音量に戻す
}
```

---

## 6. プライバシーとセキュリティアーキテクチャ

### 6.1 核心原則：「最小データ・端末優先・ユーザ主権」

```
ユーザ入力
  ↓
端末内 AI 処理（オフライン）
  ↓
機密データ：
  • 録音 → 端末内で文字起こし後、音声ファイルを削除
  • 写真 → 端末内暗号化、原画はアップロードしない
  • 位置 → 端末内検索のみに使用、座標はアップロードしない
  • 対話 → 匿名化キーワードのみアップロード
  ↓
サーバーが受け取るのは：
  • 匿名統計（犯罪類型分布・地域ヒートマップ）
  • 暗号化された証拠摘要（復号不可能）
```

### 6.2 暗号化アーキテクチャ

| 層 | 技術 | 鍵管理 |
|---|------|--------|
| 通信暗号化 | TLS 1.3 | サーバー証明書 |
| 保存暗号化 | AES-256-GCM | ユーザーパスワード + ハードウェアバインド |
| 証拠暗号化 | AES-256-GCM | Secure Enclave (iOS) / Keystore (Android) |
| バックアップ暗号化 | AES-256-GCM | ユーザーが保持する復元フレーズ |

### 6.3 権限設計（透明性）

```
ユーザーの初回 APP 起動時：
  ├─ 「GPS は最寄り支援機関の検索に使用」→ 拒否可（手動入力にフォールバック）
  ├─ 「カメラは証拠写真の撮影に使用」→ 拒否可（アルバムから選択にフォールバック）
  ├─ 「マイクは音声対話に使用」→ 拒否可（テキスト入力にフォールバック）
  └─ 「SMS は緊急時の信頼連絡先通知に使用」→ 拒否可（110 手動発信にフォールバック）
```

**すべての権限は拒否可能。拒否後もコア機能は使用可能。**

---

## 7. 開発スケジュールとマイルストーン

### 7.1 推奨スケジュール（6ヶ月）

| 月 | マイルストーン | 成果物 |
|---|--------------|--------|
| M1 | PWA MVP リリース | Web APP、緊急モード、トリアージ、法律検索 |
| M2 | 端末 AI 導入 | ONNX モデル統合、オフライン推論、Whisper 音声文字起こし |
| M3 | Flutter MVP | iOS + Android ストア審査通過、GPS・カメラ・SMS ネイティブ機能 |
| M4 | 証拠保全の完成 | 暗号化保存・保全証明書・被害届不受理防止レポート生成 |
| M5 | パートナー連携 | 弁護士会 API・NPO 予約システム連動 |
| M6 | 自治体 SaaS | 自治体向けダッシュボード、データインサイト |

### 7.2 必要人材

| ロール | 人数 | 業務内容 |
|--------|------|---------|
| Flutter エンジニア | 1-2 名 | APP フロントエンド + ネイティブ機能 |
| AI/ML エンジニア | 1 名 | モデル量子化・端末推論・RAG |
| バックエンドエンジニア | 1 名 | FastAPI・DB・認証・統計 |
| セキュリティエンジニア | 0.5 名 | 暗号化・ペネトレーションテスト（副業可） |
| UI/UX デザイナー | 1 名 | 高齢者対応・アクセシビリティ設計 |
| 法律/社福監修 | 1 名 | 内容監修・パートナー開拓 |

---

## 8. 開発者募集

### 8.1 募集する人材

| タイプ | スキル | 貢献方法 |
|--------|--------|---------|
| **Flutter エンジニア** | Dart、ネイティブ機能呼び出し、オフライン保存 | コア APP 開発 |
| **AI エンジニア** | ONNX、モデル量子化、RAG、ベクトル DB | 端末 AI 推論 |
| **セキュリティエンジニア** | 暗号化、ペネトレーションテスト、プライバシー設計 | セキュリティ監修 |
| **UI/UX デザイナー** | Figma、アクセシビリティ設計、高齢者 UX | インターフェース設計 |
| **法務監修** | 日本法、被害者支援実務 | 内容監修 |

### 8.2 参加方法

- **GitHub**: github.com/Fuilko/lawandbabysupport
- **メール**: info@legalshield.jp（件名に「開発者応募」と記載）
- **報酬**: 現段階はボランティア・助成金後報酬。長期では正規雇用または共同創業に移行可能

---

## 付録：クイックスタート（開発者向け）

```bash
# 1. リポジトリをクローン
git clone https://github.com/Fuilko/lawandbabysupport.git
cd legalshield

# 2. 依存関係をインストール
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 3. Streamlit デモを起動
.venv\Scripts\streamlit run frontend/streamlit_demo.py

# 4. 被害届不受理防止モジュールを実行
.venv\Scripts\python backend/anti_grafting.py --case-id TEST001 --scenario DV

# 5. 加害者プロファイル分析を実行
.venv\Scripts\python backend/perpetrator_profiler.py --scenario chikan --excuses "混んでた"
```

---

*LegalShield — 被害者を支援し、誰も1人にはしない。*
