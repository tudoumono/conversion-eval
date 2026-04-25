# Conversion Evaluation PoC

WS1（形式変換・Markdown変換比較評価）の実験用プロジェクトです。`conversion_eval_design.md` のフェーズ 1 として、設定ファイル駆動のパイプラインと複数の変換パターンを実装しています。

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

# PDF向けにDoclingの通常OCRを実行
conversion-eval --input input\sample --patterns pattern_h

# スキャンPDF向けにページ全体OCRを実行
conversion-eval --input input\sample --patterns pattern_i

# docx/pptx内の埋め込み画像をOCR
conversion-eval --input input\sample --patterns pattern_j

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

`.txt` と `.md` は、Markdown変換の品質比較から外しています。`.txt` はほぼ本文の受け渡しで、`.md` はすでにMarkdownのためです。

## 用語整理

このプロジェクトでは、似た処理を以下のように分けて呼びます。

- 形式変換: Markdown変換の前に入力形式を揃える処理です。例: `.doc` -> `.docx`, `.xls` -> `.xlsx`, `.rtf` -> `.docx`, Officeで開けるPDF -> `.docx`。
- Markdown変換: MarkItDown、Docling、Office COMなどでMarkdown本文を作る処理です。
- ノイズ正規化: Markdown変換後の本文からゼロ幅文字、BOM、余分な空行などを整える処理です。形式変換とは別の後処理です。

## Pattern Matrix

パターンは、評価したい差分が混ざらないように分けています。

- 変換エンジン差: MarkItDown と Docling
- 形式変換差: なし、Office COM、LibreOffice
- OCR差: OCRなし、通常OCR、ページ全体OCR
- Office内画像OCR差: `.docx` / `.pptx` 内の埋め込み画像OCR
- テキスト/Markdown: `.txt` / `.md` は本評価対象外
- LLM差: 今回は全パターンで使用なし

| ID | 名前 | 形式変換 | Markdown変換 | 対象 | OCR | LLM | 主な比較目的 |
|---|---|---|---|---|---|---|---|
| `pattern_a` | COM + MarkItDown | COM | MarkItDown | `.doc`, `.xls`, `.rtf`, `.pdf` | なし | なし | COM形式変換 + MarkItDown |
| `pattern_b` | COM + Docling no OCR | COM | Docling | `.doc`, `.xls`, `.rtf`, `.pdf` | なし | なし | COM形式変換 + Docling |
| `pattern_c` | LibreOffice + MarkItDown | LibreOffice | MarkItDown | `.doc`, `.xls`, `.rtf`, `.pdf` | なし | なし | LibreOffice形式変換 + MarkItDown |
| `pattern_d` | LibreOffice + Docling no OCR | LibreOffice | Docling | `.doc`, `.xls`, `.rtf`, `.pdf` | なし | なし | LibreOffice形式変換 + Docling |
| `pattern_e` | Direct + MarkItDown | なし | MarkItDown | `.docx`, `.xlsx`, `.pptx`, `.pdf` | なし | なし | 形式変換なしのMarkItDown基準 |
| `pattern_f` | Direct + Docling no OCR | なし | Docling | `.docx`, `.xlsx`, `.pptx`, `.pdf` | なし | なし | `pattern_e` とOCRなしで比較 |
| `pattern_g` | COM direct Markdown | なし | COM直接Markdown化 | `.doc`, `.docx`, `.xls`, `.xlsx`, `.rtf`, `.pdf` | なし | なし | Office COMだけでどこまでMarkdown化できるか |
| `pattern_h` | Direct + Docling OCR auto | なし | Docling | `.pdf` | 通常OCR | なし | DoclingでOCRを足した効果 |
| `pattern_i` | Direct + Docling OCR full page | なし | Docling | `.pdf` | ページ全体OCR | なし | スキャンPDF向けの強制OCR |
| `pattern_j` | Direct + MarkItDown + embedded image OCR | なし | MarkItDown + RapidOCR | `.docx`, `.pptx` | 埋め込み画像OCR | なし | Office内画像に含まれる文字の抽出 |

MarkItDown と Doclingを単純比較する場合は、まず `pattern_e` と `pattern_f` を見ます。OCRの効果は `pattern_f`、`pattern_h`、`pattern_i` のPDF結果で比較します。
`.docx` / `.pptx` 内の画像文字を見たい場合は `pattern_j` を見ます。

## Main Outputs

- `output/run_<timestamp>/<pattern_id>/`: Markdown変換後の出力
- `intermediate/run_<timestamp>/<format_conversion>/`: 形式変換後の中間ファイル
- `reports/raw/run_<timestamp>/raw.csv`: 1 ファイル 1 パターンの生レポート
- `reports/summary/run_<timestamp>/by_pattern.csv`: パターン別集計
- `reports/summary/run_<timestamp>/by_extension.csv`: 拡張子別集計
- `reports/summary/run_<timestamp>/extrapolation.csv`: 12 万ファイルへの処理時間外挿

`output/`、`intermediate/`、`reports/` の各フォルダには、用途が分かるように拡張子なしの説明ファイルを自動作成します。

例:

- `output/run_<timestamp>/この実行のMarkdown変換結果`
- `output/run_<timestamp>/pattern_e/Markdown変換結果_Direct + MarkItDown`
- `output/run_<timestamp>/pattern_e/contracts/nda/ノイズ正規化後Markdown`
- `intermediate/run_<timestamp>/この実行の中間ファイル`
- `intermediate/run_<timestamp>/none/形式変換なし`
- `reports/raw/変換結果の生レポート`
- `reports/raw/run_<timestamp>/実行別_変換結果の生レポート`
- `reports/summary/run_<timestamp>/実行別_集計レポート`
- `reports/human_eval/目視評価テンプレート`

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
uses_ocr: true
force_full_page_ocr: true
uses_internal_models: true
allow_network_download: false
```

各項目の意味:

| 項目 | 意味 |
|---|---|
| `uses_llm` | 外部LLMまたはローカルLLMを呼び出す場合は `true`。現状の変換パターンはすべて `false` です。 |
| `llm_provider` | `uses_llm: true` の場合だけ `ollama` または `openai` を指定します。`none` または未指定ならLLMは使いません。 |
| `uses_ocr` | OCRを使う場合は `true`。DoclingのOCRはLLMではありません。 |
| `force_full_page_ocr` | スキャンPDF向けに、ページ全体をOCRしたい場合は `true`。 |
| `uses_internal_models` | DoclingのOCR/AI-OCR/レイアウト解析など、LLMではない内部モデルを使う場合は `true`。 |
| `allow_network_download` | 実行中にモデルや追加アセットをネットワーク取得してよい場合だけ `true`。PoCでは通常 `false` です。 |

YAML読み込み時に以下を検証します。

- `uses_llm: true` なのに `llm_provider` が `none` の場合はエラー
- `llm_provider` が `ollama` / `openai` / `none` 以外の場合はエラー
- `uses_llm: false` なのに `llm_provider` が `ollama` または `openai` の場合はエラー

Docling PDF変換では、リモートサービス、画像説明、コード補完、数式補完、画像分類を明示的に無効化しています。OCRはパターンごとに制御し、表構造解析は有効です。

PDFを通常OCRで処理する場合は `pattern_h` を使います。スキャンPDFをページ全体OCRで処理する場合は `pattern_i` を使います。
`.docx` / `.pptx` 内の埋め込み画像をOCRする場合は `pattern_j` を使います。本文はMarkItDownで変換し、`word/media` または `ppt/media` の画像OCR結果をMarkdown末尾へ追記します。

`allow_network_download: false` のDocling PDF変換では、実行前に以下を確認します。

- RapidOCR のONNXモデルがローカルに存在すること
- Hugging FaceキャッシュにDocling用モデルが存在すること

不足している場合は、変換を開始せずCSVにエラーとして記録します。初回セットアップ時だけオンライン環境でモデルを取得し、air-gapped環境へ持ち込む想定です。

## Current Scope

実装済み:

- 設定読み込み（`config/patterns.yaml`, `config/noise_rules.yaml`）
- 形式変換なし（`none`）
- COM形式変換（`com`）
- `markitdown` converter（本評価対象はOffice/PDF系。`.txt` / `.md` は比較対象外）
- `docling` converter
- `com_direct` converter
- OCRパターン（`pattern_h`, `pattern_i`, `pattern_j`）
- 構造・ノイズ指標
- 失敗分類（空出力、文字化け過多、構造崩壊、タイムアウト）
- raw / summary レポート
- 目視評価テンプレート生成

未実装（フェーズ 2 以降）:

- LibreOffice形式変換
- 並列実行、タイムアウト強制終了の本格化
