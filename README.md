# Conversion Evaluation PoC

WS1（前処理ツール比較評価）の実験用プロジェクトです。`conversion_eval_design.md` のフェーズ 1 として、設定ファイル駆動のパイプラインと複数の変換パターンを実装しています。

## Quick Start

仮想環境を有効化します。

```powershell
.\.venv\Scripts\Activate.ps1
```

サンプル入力を `pattern_e`（Direct + MarkItDown）で変換します。

```powershell
conversion-eval --input input\sample --patterns pattern_e
```

ソースは `src/` レイアウトなので、未インストールで実行する場合は以下でも動きます。

```powershell
$env:PYTHONPATH = "src"
python -m conversion_eval.main --input input\sample --patterns pattern_e
```

主なオプション:

| オプション | 既定値 | 説明 |
|---|---|---|
| `--root` | `.` | プロジェクトルート。`config/`, `input/`, `output/`, `reports/` の基準になります。 |
| `--input` | `input/sample` | 変換対象ファイルを置いたフォルダ。`--root` からの相対パスで指定します。 |
| `--patterns` | `pattern_e` | 実行するパターンID。カンマ区切りで `pattern_e,pattern_f` のように指定できます。全件実行は `all` です。 |
| `--human-template` | なし | 変換は行わず、目視評価用CSVテンプレートを `reports/human_eval/` に出力します。 |
| `--make-sample` | なし | `input/full` から拡張子別にサンプルを抽出して `input/sample` を作ります。 |
| `--full-input` | `input/full` | `--make-sample` の抽出元フォルダです。 |
| `--sample-output` | `input/sample` | `--make-sample` の出力先フォルダです。 |
| `--seed` | `42` | サンプル抽出時の乱数シードです。 |

実行例:

```powershell
# Direct + MarkItDown と Direct + Docling を比較
conversion-eval --input input\sample --patterns pattern_e,pattern_f

# 設定済みの全パターンを実行
conversion-eval --input input\sample --patterns all

# 目視評価用CSVだけを作る
conversion-eval --input input\sample --patterns pattern_e,pattern_f --human-template

# input/full から input/sample を作る
conversion-eval --make-sample --full-input input\full --sample-output input\sample
```

## Offline Install

air-gapped 環境では、オンライン環境で wheel 一式を取得してから持ち込みます。

```powershell
pip install --no-index --find-links <wheel-folder> -r requirements.txt
```

MarkItDown が未導入の場合でも `.txt` / `.md` はスモークテスト用のテキスト変換で処理します。それ以外の形式は失敗として CSV に記録されます。

## Main Outputs

- `output/<pattern_id>/`: 変換後 Markdown
- `reports/raw/run_<timestamp>.csv`: 1 ファイル 1 パターンの生レポート
- `reports/summary/by_pattern.csv`: パターン別集計
- `reports/summary/by_extension.csv`: 拡張子別集計
- `reports/summary/extrapolation.csv`: 12 万ファイルへの処理時間外挿

## Environment

実行時の環境変数は `.env` から読み込みます。

パス値はプロジェクトルートからの相対パスで書きます。

```dotenv
CONVERSION_EVAL_ASCII_TMP=.tmp/docling
HF_HOME=.tmp/huggingface_nosymlink
HF_HUB_CACHE=.tmp/huggingface_nosymlink/hub
```

## Docling And Models

Docling はLLMではありませんが、PDF解析やOCR/AI-OCRで内部MLモデルを使います。

LLMを使えるパターンは、Ollama または OpenAI API を明示したものだけです。指定がない場合はLLMを使用しません。

このプロジェクトでは、モデル利用を `config/patterns.yaml` で明示します。

```yaml
uses_llm: false
llm_provider: none
uses_internal_models: true
allow_network_download: false
```

各項目の意味:

| 項目 | 意味 |
|---|---|
| `uses_llm` | 外部LLMまたはローカルLLMを呼び出す場合は `true`。現状の変換パターンはすべて `false` です。 |
| `llm_provider` | `uses_llm: true` の場合だけ `ollama` または `openai` を指定します。`none` または未指定ならLLMは使いません。 |
| `uses_internal_models` | DoclingのOCR/AI-OCR/レイアウト解析など、LLMではない内部モデルを使う場合は `true`。 |
| `allow_network_download` | 実行中にモデルや追加アセットをネットワーク取得してよい場合だけ `true`。PoCでは通常 `false` です。 |

YAML読み込み時に以下を検証します。

- `uses_llm: true` なのに `llm_provider` が `none` の場合はエラー
- `llm_provider` が `ollama` / `openai` / `none` 以外の場合はエラー
- `uses_llm: false` なのに `llm_provider` が `ollama` または `openai` の場合はエラー

Docling PDF変換では、リモートサービス、画像説明、コード補完、数式補完、画像分類を明示的に無効化しています。OCRと表構造解析は有効です。

`allow_network_download: false` のDocling PDF変換では、実行前に以下を確認します。

- RapidOCR のONNXモデルがローカルに存在すること
- Hugging FaceキャッシュにDocling用モデルが存在すること

不足している場合は、変換を開始せずCSVにエラーとして記録します。初回セットアップ時だけオンライン環境でモデルを取得し、air-gapped環境へ持ち込む想定です。

## Current Scope

実装済み:

- 設定読み込み（`config/patterns.yaml`, `config/noise_rules.yaml`）
- `none` preprocessor
- `com` preprocessor
- `markitdown` converter（MarkItDown があれば使用、`.txt` / `.md` はフォールバック可）
- `docling` converter
- `com_direct` converter
- 構造・ノイズ指標
- 失敗分類（空出力、文字化け過多、構造崩壊、タイムアウト）
- raw / summary レポート
- 目視評価テンプレート生成

未実装（フェーズ 2 以降）:

- LibreOffice preprocessor
- 並列実行、タイムアウト強制終了の本格化
