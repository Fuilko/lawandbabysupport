# LegalShield 緊急音声 ASR 評価セット 仕様書

**目標**：200 件、合計約 60 分、人手書き起こし付き

## カテゴリと配分

| Category | 件数 | 比率 | 説明 |
|---|---|---|---|
| `whispered` | 30 | 15% | 耳語・気息音（小声で「助けて…」など） |
| `disfluent` | 40 | 20% | 「あー…えーっと…そ、その人が…」断片的 |
| `emotional_cry` | 50 | 25% | 泣きながらの発話（**最重要**）|
| `panic` | 30 | 15% | パニック・早口（災害・事件時の通報） |
| `multilingual` | 30 | 15% | 在留外国人の非ネイティブ日本語 + 母語混在 |
| `child_speech` | 20 | 10% | 5–10 歳児の発話（虐待被害者想定） |

## 言語比率（multilingual カテゴリ内）

在留外国人比率に従う：
- 中国語 25.6% (8 件)
- ベトナム語 18.7% (6 件)
- 韓国語 12.8% (4 件)
- フィリピン英語 / タガログ 10.0% (3 件)
- ポルトガル語 6.7% (2 件)
- ネパール語 5.5% (2 件)
- インドネシア語 4.7% (1 件)
- 英語 + その他 16% (4 件)

## 各 segment の構成

```json
{
  "audio_path": "eval_set/audio/whispered_001.wav",
  "duration": 8.5,
  "category": "whispered",
  "lang": "ja",
  "text": "[気息音] お…おねがい…たすけて…",
  "nonverbal_events": [
    {"start": 0.0, "end": 1.2, "label": "気息音"},
    {"start": 5.3, "end": 6.0, "label": "嗚咽"}
  ],
  "speaker_age_estimate": "adult",
  "speaker_emotion": "fear",
  "noise_level_db": -42,
  "source": "self_recorded | audioset | curated_youtube",
  "transcribed_by": "human",
  "verified_by": "human_2nd"
}
```

## 書き起こし規約

- **逐字保留**：「あ、あ、あの人が」を「あの人が」に縮めない
- **非言語タグ**：`[泣]` `[嗚咽 3s]` `[激しい呼吸]` `[沈黙 5s]` `[衣擦れ]`
- **不確実部分**：`[?]` または `(聞き取り不能)`
- **多言語混在**：`<lang=zh>救命</lang> たすけて` のように lang タグ付与
- **音量極小**：`[小声] ...` プレフィックス

## 収集ルート

| Category | 収集元 | 同意・倫理 |
|---|---|---|
| `whispered` | ASMR チャンネル抜粋 + 自録音 | 公開済 + 本人同意 |
| `disfluent` | ドキュメンタリー + Common Voice ja | クリエイティブコモンズ |
| `emotional_cry` | AudioSet (Crying ラベル) + 公開記者会見 | AudioSet ライセンス + 公開資料 |
| `panic` | 110/119 公開録音 + 災害アーカイブ | 公開済 |
| `multilingual` | Common Voice 各言語 + 自録音協力者 | CV0 / 同意済 |
| `child_speech` | NHK こどもニュース + 教育コンテンツ | 公共放送・教育用途 |

## 二重書き起こし

各 segment を 2 名で独立に書き起こし、Inter-Annotator Agreement (CER) > 95% を確認。
不一致部分は第 3 者が裁定。

## ライセンス

評価セット自体は **非配布**。重みと評価結果のみ公開可。
