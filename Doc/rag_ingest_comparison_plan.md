# RAG 投入比較検証プラン

## 1. 目的

本ドキュメントは、RAG 手法比較評価における投入・登録部分の実装方針を整理するための計画書である。

対象は、既存の `growi-dify-graphrag-stack` に含まれる GraphRAG FastAPI を拡張し、以下 3 方式を同一条件で比較検証できるようにすることである。

1. Dify 標準ベクトル RAG
2. 既存 GraphRAG
3. 全文送信方式

本計画では、新しい本番 RAG を先に作り込むのではなく、比較検証の再現性を優先する。最終的には、Markdown 化した成果物のうち採用する 1 種類を入力として、3 方式に同時投入し、検索・回答品質を比較できる状態を目指す。

## 2. 前提

- WS1 で採用された Markdown 化方式の出力を、RAG 投入対象とする。
- RAG 比較では、投入する Markdown は原則 1 種類に固定する。
- 比較対象は、当初設計どおり以下の 3 方式に絞る。
  - Dify 標準ベクトル RAG
  - 既存 GraphRAG
  - 全文送信方式
- 既存 GraphRAG の FastAPI に拡張エンドポイントを追加する形で実装する。
- 既存の `/ingest` や `/search` は極力壊さず、比較検証用の `/eval` 系エンドポイントを追加する。
- 別環境で既に実装されているコードがあるが、現時点ではそのコードを確認できない前提で設計する。
- 後から別環境のコードをマージしやすいように、方式ごとの処理は adapter 単位に分離する。
- 3 方式への登録は、正式な比較実行では並列処理を必須とする。

## 3. 比較対象の整理

| 方式 | 概要 | 主な確認観点 |
|---|---|---|
| Dify 標準ベクトル RAG | Dify 本体のナレッジ機能に Markdown を登録し、Dify の標準検索を使う | Dify 標準機能だけで十分な回答品質が得られるか |
| 既存 GraphRAG | 既存 GraphRAG の chunk、embedding、Elasticsearch、Neo4j を使う | 自社実装の GraphRAG が Dify 標準より優位か |
| 全文送信方式 | ファイル位置・関係を保持し、関連ファイルの Markdown 全文を LLM に渡す | chunk せずファイル単位で文脈を渡す方式が有効か |

## 4. FastAPI 拡張方針

既存 FastAPI 本体を大きく作り替えるのではなく、比較検証用のエンドポイントを追加する。

想定する名前空間は `/eval` とする。

```text
POST /eval/datasets
POST /eval/ingest/all
POST /eval/ingest/dify-vector
POST /eval/ingest/existing-graphrag
POST /eval/ingest/fulltext-send
GET  /eval/runs/{run_id}
```

正式な比較投入は `POST /eval/ingest/all` を使用する。

個別投入エンドポイントは、デバッグや再実行用途として残す。ただし、比較評価の標準手順では 3 方式を同じ dataset、同じ run_id で並列実行する。

### 4.1 想定フォルダー構成

実装対象リポジトリでは、アプリケーションコード、比較用 dataset、実行結果を分離して管理する。

```text
growi-dify-graphrag-stack/
  graphrag/
    main.py
    ingest.py
    providers.py

    eval/
      api.py
      schemas.py
      orchestrator.py
      parallel.py
      jobs.py

      methods/
        dify_vector/
          adapter.py
          client.py
          mapper.py

        existing_graphrag/
          adapter.py
          mapper.py

        fulltext_send/
          adapter.py
          indexer.py
          context_builder.py

      storage/
        manifest_store.py
        result_store.py

  rag_eval/
    datasets/
      selected_markdown_v1/
        dataset.yaml
        documents/
          doc001.md
          doc002.md
          subdir/
            doc003.md
        source_map.csv

    runs/
      20260429_001/
        run.yaml
        ingest_status.json

        dify_vector/
          ingest_request.json
          dify_dataset_map.json
          upload_manifest.jsonl
          upload_results.jsonl
          errors.jsonl

        existing_graphrag/
          ingest_request.json
          document_payloads.jsonl
          chunk_map.jsonl
          elasticsearch_results.jsonl
          neo4j_results.jsonl
          errors.jsonl

        fulltext_send/
          ingest_request.json
          file_manifest.jsonl
          relation_edges.jsonl
          keyword_index_manifest.json
          context_build_preview.jsonl
          errors.jsonl

    reports/
      20260429_001/
        ingest_summary.csv
        ingest_summary.md
        method_comparison.json
        errors_summary.jsonl
```

`graphrag/eval/` は FastAPI 拡張コードを配置する。`rag_eval/` は比較検証の入力 dataset、投入実行結果、レポートを保存する作業領域とする。

`rag_eval/` の場所は環境依存にしないため、実装時には `.env` で `RAG_EVAL_ROOT=rag_eval` のように指定し、アプリケーション側では `pathlib.Path` で解決する。dataset 内のファイル参照は、絶対パスではなく dataset ルートからの相対パスで保持する。

## 5. 推奨モジュール構成

```text
growi-dify-graphrag-stack/
  graphrag/
    main.py

    eval/
      api.py
      schemas.py
      orchestrator.py
      parallel.py
      jobs.py

      methods/
        dify_vector/
          adapter.py
          client.py
          mapper.py

        existing_graphrag/
          adapter.py
          mapper.py

        fulltext_send/
          adapter.py
          indexer.py
          context_builder.py

      storage/
        manifest_store.py
        result_store.py
```

各ファイルの役割は以下とする。

| ファイル | 役割 |
|---|---|
| `eval/api.py` | `/eval` 系エンドポイントを定義する |
| `eval/schemas.py` | API request / response / manifest の型を定義する |
| `eval/orchestrator.py` | 3 方式の投入を統括する |
| `eval/parallel.py` | 並列実行、worker 数、失敗制御を扱う |
| `eval/jobs.py` | run_id 単位の状態管理を扱う |
| `methods/*/adapter.py` | 各方式への投入処理を実装する |
| `methods/*/mapper.py` | 共通 dataset から各方式向け payload へ変換する |
| `storage/manifest_store.py` | dataset、run、投入対象一覧を保存する |
| `storage/result_store.py` | 投入結果、エラー、対応 ID を保存する |

## 6. 共通データセット構造

RAG 投入対象の Markdown は、比較用 dataset として管理する。

```text
rag_eval/
  datasets/
    selected_markdown_v1/
      dataset.yaml
      documents/
        doc001.md
        doc002.md
        subdir/
          doc003.md
      source_map.csv
```

| ファイル | 内容 |
|---|---|
| `dataset.yaml` | dataset 名、前処理パターン、対象ファイル一覧、登録条件を持つ |
| `documents/` | 投入対象 Markdown を配置する |
| `source_map.csv` | 元ファイルと Markdown の対応を管理する |

ファイルパスは、絶対パスではなく `dataset.yaml` または `documents/` からの相対パスで保持する。

## 7. 実行結果構造

1 回の投入実行を `run_id` 単位で保存する。

```text
rag_eval/
  runs/
    20260429_001/
      run.yaml
      ingest_status.json

      dify_vector/
      existing_graphrag/
      fulltext_send/
```

| ファイル | 内容 |
|---|---|
| `run.yaml` | 実行条件、dataset、worker 数、対象方式を記録する |
| `ingest_status.json` | 3 方式それぞれの実行状態を記録する |

## 8. Dify 標準ベクトル RAG のファイル構造

```text
runs/
  20260429_001/
    dify_vector/
      ingest_request.json
      dify_dataset_map.json
      upload_manifest.jsonl
      upload_results.jsonl
      errors.jsonl
```

| ファイル | 内容 |
|---|---|
| `ingest_request.json` | どの dataset を Dify に登録したか |
| `dify_dataset_map.json` | ローカル dataset と Dify dataset / document ID の対応 |
| `upload_manifest.jsonl` | Dify 登録対象 Markdown の一覧 |
| `upload_results.jsonl` | Dify への登録結果 |
| `errors.jsonl` | 失敗ファイルと失敗理由 |

この方式では、実データの検索インデックスは Dify 側に作られる。ローカル側では、Dify へ何を登録し、どの ID に対応したかを追跡する。

## 9. 既存 GraphRAG のファイル構造

```text
runs/
  20260429_001/
    existing_graphrag/
      ingest_request.json
      document_payloads.jsonl
      chunk_map.jsonl
      elasticsearch_results.jsonl
      neo4j_results.jsonl
      errors.jsonl
```

| ファイル | 内容 |
|---|---|
| `ingest_request.json` | 既存 GraphRAG へ登録する dataset と条件 |
| `document_payloads.jsonl` | 既存 `/ingest` に渡す document payload |
| `chunk_map.jsonl` | document と chunk の対応 |
| `elasticsearch_results.jsonl` | Elasticsearch への登録結果 |
| `neo4j_results.jsonl` | Neo4j への登録結果 |
| `errors.jsonl` | 失敗ファイルと失敗理由 |

この方式では、既存 GraphRAG の chunk、embedding、Elasticsearch、Neo4j の仕組みを活用する。比較検証用の adapter は、既存の登録処理を呼び出す薄い層にする。

## 10. 全文送信方式のファイル構造

```text
runs/
  20260429_001/
    fulltext_send/
      ingest_request.json
      file_manifest.jsonl
      relation_edges.jsonl
      keyword_index_manifest.json
      context_build_preview.jsonl
      errors.jsonl
```

| ファイル | 内容 |
|---|---|
| `ingest_request.json` | 全文送信方式に登録する dataset と条件 |
| `file_manifest.jsonl` | Markdown ファイルの相対パス、タイトル、種別、サイズ |
| `relation_edges.jsonl` | ファイル間関係。CALL、COPY、関連設計書など |
| `keyword_index_manifest.json` | 全文検索用 index の作成結果 |
| `context_build_preview.jsonl` | 検索時にどのファイル全文を組み立てる想定か |
| `errors.jsonl` | 失敗ファイルと失敗理由 |

この方式では、Markdown を chunk 化して vector index に登録するのではなく、ファイル単位の情報を保持する。検索時にはキーワード検索やファイル関係グラフで対象ファイルを選び、コンテキスト上限に収まる範囲で Markdown 全文を結合する。

## 11. 並列処理方針

正式な投入処理では、3 方式を必ず並列で実行する。

```text
POST /eval/ingest/all
  ├─ Dify 標準ベクトル RAG 登録
  ├─ 既存 GraphRAG 登録
  └─ 全文送信方式 登録
```

並列処理の基本方針は以下とする。

| 項目 | 方針 |
|---|---|
| 並列単位 | RAG 方式単位とファイル単位の両方を考慮する |
| 方式単位並列 | 3 方式を同時に開始する |
| ファイル単位並列 | 各方式の内部で複数ファイルを並列登録する |
| 失敗制御 | 1 方式が失敗しても、他方式の投入は継続する |
| 結果記録 | 成功・失敗・スキップを方式別に必ず保存する |
| 再実行 | 失敗分だけ再実行できる構造にする |

Dify や Elasticsearch など外部サービスに負荷をかけすぎないよう、方式ごとに worker 数の上限を持たせる。

## 12. 共通レスポンス方針

3 方式の投入結果は、同じ形式で返す。

```json
{
  "run_id": "20260429_001",
  "dataset_id": "selected_markdown_v1",
  "status": "completed_with_errors",
  "methods": {
    "dify_vector": {
      "status": "completed",
      "success": 120,
      "failed": 0
    },
    "existing_graphrag": {
      "status": "completed_with_errors",
      "success": 118,
      "failed": 2
    },
    "fulltext_send": {
      "status": "completed",
      "success": 120,
      "failed": 0
    }
  }
}
```

比較検証では、投入成功率も評価材料になるため、失敗を隠さず記録する。

## 13. 別環境実装とのマージを考慮した設計

別環境のコードを確認できない前提のため、以下の方針で衝突を抑える。

- 既存 `main.py` への変更は router 登録程度に限定する。
- 方式ごとの処理は `methods/*/adapter.py` に閉じ込める。
- 既存 GraphRAG の内部処理を直接書き換えず、既存関数または既存 API を呼ぶ薄い adapter にする。
- schema と manifest を先に固定し、実装差分を adapter 内部で吸収する。
- Dify API 連携の詳細は adapter 内部に閉じ込める。
- 全文送信方式の検索・コンテキスト構築は `context_builder.py` に分離する。

### 13.1 外部環境への持ち込み前提

本計画は、最終的に以下の流れで外部環境へ持ち込むことを前提とする。

1. 本環境で比較検証用の設計方針と実装コードを作成する。
2. 計画書と実装コードを外部環境へ持っていく。
3. 外部環境側の Codex が、外部環境に存在する既存実装を確認する。
4. 外部環境側の Codex が、本計画と実装コードを既存実装へマージする。

このため、本環境で作る実装は「外部環境の既存コードを直接上書きする完成品」ではなく、「外部環境側でマージしやすい追加モジュール」として設計する。

### 13.2 持ち込み対象

外部環境へ持ち込む対象は、原則として以下とする。

| 対象 | 内容 |
|---|---|
| `Doc/rag_ingest_comparison_plan.md` | 本計画書 |
| `graphrag/eval/` | 比較検証用の FastAPI 拡張コード |
| `graphrag/main.py` の差分 | `/eval` router 登録など最小限の接続差分 |
| `.env.example` または設定項目の差分 | `RAG_EVAL_ROOT`、Dify 接続情報、worker 数など |
| テストまたは動作確認用サンプル | 外部環境で merge 後に確認するための最小データ |

`rag_eval/runs/` のような実行結果ファイルは、基本的に持ち込み対象にしない。必要な場合のみ、サンプル結果として明示的に分離して持ち込む。

### 13.3 外部環境側 Codex へのマージ指示

外部環境側でマージする Codex には、以下の順序で作業してもらう想定とする。

1. まず本計画書を読む。
2. 外部環境の既存 GraphRAG FastAPI の構成を確認する。
3. 既存の `/ingest`、`/search`、Dify 連携、GraphRAG 登録処理を壊さない方針を確認する。
4. `graphrag/eval/` を追加モジュールとして取り込む。
5. `main.py` には `/eval` router 登録のみを最小差分で追加する。
6. 外部環境に既に似た実装がある場合は、既存実装を優先し、adapter の中で本計画の interface に寄せる。
7. `.env` または環境変数の差分を外部環境の設定方式に合わせる。
8. `POST /eval/ingest/all` が 3 方式を並列実行することを確認する。
9. 既存 `/health`、`/ingest`、`/search` が従来どおり動くことを確認する。

### 13.4 マージ時に守る境界

外部環境へ持ち込む実装では、以下の境界を明確にする。

| 領域 | 方針 |
|---|---|
| 既存 GraphRAG 本体 | 原則として直接改変しない |
| `/eval` API | 新規追加として扱う |
| Dify 登録処理 | `dify_vector/adapter.py` または `client.py` に閉じ込める |
| 既存 GraphRAG 登録処理 | `existing_graphrag/adapter.py` から既存処理を呼ぶ |
| 全文送信方式 | `fulltext_send/` 配下に閉じ込める |
| 設定値 | `.env` と `pathlib.Path` で環境差分を吸収する |
| 実行結果 | `RAG_EVAL_ROOT` 配下に保存し、既存データ領域と混ぜない |

### 13.5 外部環境へ渡すときのメモ

外部環境側へ渡す際は、以下を添える。

```text
この実装は、既存 GraphRAG FastAPI に RAG 比較検証用の /eval 系エンドポイントを追加するためのものです。
既存の /ingest / search を置き換えるものではありません。

比較対象は以下の 3 方式です。
1. Dify 標準ベクトル RAG
2. 既存 GraphRAG
3. 全文送信方式

正式な比較投入は POST /eval/ingest/all で行い、3 方式を並列実行してください。
外部環境に既に類似実装がある場合は、既存実装を優先し、この実装は adapter または wrapper として統合してください。
```

## 14. 実装ポイント

この節では、外部環境へ持ち込む実装コードで特に意識する点を整理する。

### 14.1 API 層の実装ポイント

`eval/api.py` は、FastAPI の endpoint 定義に集中する。

| ポイント | 方針 |
|---|---|
| endpoint の責務 | request validation、run 作成、orchestrator 呼び出し、response 返却に限定する |
| 重い処理 | endpoint 内に直接書かず、`orchestrator.py` または adapter に委譲する |
| 既存 API との関係 | 既存 `/ingest`、`/search`、`/health` の挙動を変えない |
| レスポンス | 3 方式の成功・失敗・件数・エラー概要を同じ形式で返す |
| デバッグ用 API | 個別方式の投入 endpoint は残してよいが、正式比較は `/eval/ingest/all` を使う |

正式な比較実行では、以下を標準入口とする。

```text
POST /eval/ingest/all
```

### 14.2 schema 設計の実装ポイント

`eval/schemas.py` は、外部環境とのマージ時にも崩れにくい共通契約として扱う。

| ポイント | 方針 |
|---|---|
| path | dataset 内のファイル参照は相対パスで保持する |
| method 名 | `dify_vector`、`existing_graphrag`、`fulltext_send` のように固定文字列で扱う |
| run_id | 実行単位を追跡できる ID として必ず発行する |
| document_id | dataset ID と相対パス、必要に応じて content hash から安定生成する |
| 設定 | worker 数、Dify dataset 名、index 名などは request または `.env` から受ける |

schema は、実装都合よりも「比較結果を後で読み返せること」を優先する。

### 14.3 orchestrator の実装ポイント

`eval/orchestrator.py` は、3 方式の投入を統括する中心になる。

主な責務は以下とする。

1. dataset を読み込む。
2. run_id を作成する。
3. run 用フォルダーを作成する。
4. 3 方式の adapter を準備する。
5. 3 方式を並列実行する。
6. 成功・失敗・スキップを集約する。
7. `ingest_status.json` を更新する。

重要なのは、1 方式の失敗で全体を止めないことである。たとえば Dify 登録が失敗しても、既存 GraphRAG と全文送信方式の登録は続行する。

### 14.4 並列処理の実装ポイント

並列処理は 2 段階で考える。

| 並列単位 | 内容 |
|---|---|
| 方式単位 | Dify、既存 GraphRAG、全文送信方式を同時に開始する |
| ファイル単位 | 各方式の adapter 内で複数ファイルを並列処理する |

外部サービスへの負荷を抑えるため、無制限な並列実行は避ける。

```text
方式単位の並列
  ├─ dify_vector adapter
  ├─ existing_graphrag adapter
  └─ fulltext_send adapter

各 adapter 内のファイル単位並列
  ├─ worker 1
  ├─ worker 2
  └─ worker N
```

worker 数は方式ごとに分ける。

| 設定 | 用途 |
|---|---|
| `EVAL_METHOD_WORKERS` | 方式単位の並列数。基本は 3 |
| `DIFY_INGEST_WORKERS` | Dify 登録のファイル並列数 |
| `GRAPHRAG_INGEST_WORKERS` | 既存 GraphRAG 登録のファイル並列数 |
| `FULLTEXT_INGEST_WORKERS` | 全文送信方式の manifest/index 作成並列数 |

ファイル書き込みは競合しやすいため、並列 task が同じ JSONL に直接書き込む場合は lock を使う。可能であれば、task 結果を集約してから 1 writer で保存する。

### 14.5 Dify 標準ベクトル RAG の実装ポイント

`methods/dify_vector/` では、Dify への登録と ID 対応管理に集中する。

| ポイント | 方針 |
|---|---|
| dataset 作成 | 既存 dataset を使うか、新規作成するかを設定で切り替える |
| document 登録 | Markdown ファイル単位で Dify に登録する |
| ID 対応 | ローカル document_id と Dify document ID を `dify_dataset_map.json` に保存する |
| 重複防止 | 相対パスまたは content hash を使って再登録を検知できるようにする |
| リトライ | Dify API の一時失敗は回数制限付きで再試行する |
| 秘匿情報 | API key や token は結果ファイルに出力しない |

Dify 側の chunking、embedding、検索 index は Dify が管理するため、本実装では Dify 内部の chunk を直接制御しすぎない。

### 14.6 既存 GraphRAG の実装ポイント

`methods/existing_graphrag/` では、既存 GraphRAG の登録処理を薄く呼び出す。

| ポイント | 方針 |
|---|---|
| 既存処理の再利用 | 既存 `/ingest` 相当の処理を呼び出す |
| payload 保存 | 実際に投入した document payload を `document_payloads.jsonl` に残す |
| chunk 対応 | document と chunk の対応を `chunk_map.jsonl` に残す |
| ES / Neo4j 結果 | それぞれの登録結果を分けて保存する |
| 既存実装保護 | 既存 GraphRAG の内部関数を大きく改変しない |

外部環境に既に GraphRAG 登録処理がある場合は、その処理を優先する。本実装は wrapper または adapter として接続する。

### 14.7 全文送信方式の実装ポイント

`methods/fulltext_send/` では、Markdown を chunk 化せず、ファイル単位の情報を保持する。

| ポイント | 方針 |
|---|---|
| manifest | 相対パス、タイトル、サイズ、content hash を `file_manifest.jsonl` に保存する |
| 関係情報 | WS3 の成果物があれば `relation_edges.jsonl` に保存する |
| 関係情報なし | WS3 未完成時は、同一フォルダー、ファイル名、見出しなどの簡易関係で代替する |
| keyword index | Elasticsearch または簡易全文検索用の index 情報を保存する |
| context builder | 検索後にファイル全文を結合する処理は `context_builder.py` に分離する |
| token 上限 | 全文結合時は最大トークン数を超えないように切り詰める |

この方式は、登録時点では「全文を LLM に送る」のではなく、検索時に全文コンテキストを組み立てるための情報を整備する。

### 14.8 保存処理の実装ポイント

`storage/` では、比較検証結果を後から追跡できるように保存する。

| ポイント | 方針 |
|---|---|
| 保存単位 | run_id 単位で保存する |
| 形式 | 一覧性が必要なものは JSONL、設定は YAML または JSON とする |
| atomic write | status や summary は一時ファイルに書いてから置き換える |
| エラー | 方式別の `errors.jsonl` に失敗ファイル、理由、例外概要を残す |
| 再実行 | 成功済み document を skip できる情報を残す |

実行結果は比較材料そのものなので、失敗も削除せず記録する。

### 14.9 設定値の実装ポイント

環境差分は `.env` で吸収する。

想定する主な設定は以下。

```text
RAG_EVAL_ROOT=rag_eval

DIFY_BASE_URL=http://localhost
DIFY_API_KEY=
DIFY_INGEST_WORKERS=4

GRAPHRAG_INGEST_WORKERS=4
FULLTEXT_INGEST_WORKERS=8
EVAL_METHOD_WORKERS=3
```

アプリケーションコードでは `pathlib.Path` を使い、Windows / Linux / WSL の差を吸収する。manifest や結果ファイルには、原則として絶対パスを保存しない。

### 14.10 テスト・確認の実装ポイント

外部環境へ持ち込む前に、最低限以下を確認できる形にする。

| 確認項目 | 内容 |
|---|---|
| schema test | request / response の形が崩れていないこと |
| dry-run | 実際の Dify / ES / Neo4j に登録せず、payload と manifest を作れること |
| 3 方式並列 | `/eval/ingest/all` で 3 adapter が並列に開始されること |
| 失敗継続 | 1 方式が失敗しても他方式が完了すること |
| 結果保存 | run フォルダーに expected files が出力されること |
| 既存 API | `/health`、既存 `/ingest`、既存 `/search` が壊れていないこと |

外部環境では、実サービス接続を含む integration test を追加で実施する。

### 14.11 実装の完了条件

初期実装の完了条件は以下とする。

1. `POST /eval/ingest/all` が呼び出せる。
2. 3 方式の adapter が同じ dataset を受け取れる。
3. 3 方式が並列に実行される。
4. 1 方式が失敗しても他方式が継続する。
5. run_id 単位の結果フォルダーが作成される。
6. 各方式の成功件数、失敗件数、エラー理由が保存される。
7. 既存 GraphRAG の既存 endpoint が壊れていない。
8. 外部環境側 Codex が adapter 単位でマージできる構造になっている。

## 15. この計画でまだ議論が必要な点

次の実装ディスカッションでは、以下を決める必要がある。

1. Dify への登録を API で完全自動化するか、初期版では手動登録 + ID 管理にするか。
2. `dataset.yaml` の必須項目をどこまで持たせるか。
3. 3 方式の worker 数の初期値をどうするか。
4. Dify / Elasticsearch / Neo4j の登録失敗時に、どこまで自動リトライするか。
5. 全文送信方式で、ファイル関係グラフが未作成の場合にどう簡易実装するか。
6. 検索・回答評価まで同じ FastAPI に含めるか、投入機能と評価実行機能を分けるか。
7. 別環境の既存実装をマージするときに、adapter 方式へ寄せるか、既存実装を尊重して wrapper を置くか。

## 16. 現時点の結論

現時点では、RAG 比較は以下の方針で進める。

- 比較対象は 3 方式に絞る。
- 入力 Markdown は採用済みの 1 種類に固定する。
- 既存 GraphRAG FastAPI に `/eval` 系エンドポイントを追加する。
- 正式投入は `POST /eval/ingest/all` で行う。
- 3 方式への登録は必ず並列実行する。
- 方式ごとの処理は adapter として分離し、別環境コードのマージに備える。
- 投入結果は run_id 単位で保存し、成功・失敗・対応 ID を追跡できるようにする。
