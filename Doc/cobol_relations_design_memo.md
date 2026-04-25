# YPS/COBOL 知識継承 - ファイル関係抽出機能 設計メモ

**作成日**: 2026-04-17
**対象**: 既存 GraphRAG (FastAPI + Elasticsearch + Neo4j) への機能追加
**ユースケース**: 消費税法改正などの影響調査

---

## 1. 背景と目的

### 1.1 解きたいユースケース

2026年の消費税法改正(食品関連)などの法改正対応において、レガシー基幹システムへの影響調査を AI で支援する。ベテラン担当者の頭の中にある「暗黙知としての影響追跡」を、機械的かつ決定論的に再現することを目指す。

想定する問い合わせパターン:

- 「消費税改正の影響範囲は?」
- 「具体的にどこのコード?」
- 「該当する設計書の場所は?」
- 「設計書の内容を要約して」
- 「サブシステム間で連携されている項目は?」

### 1.2 現状の課題

既存 GraphRAG は LLM によるエンティティ・関係抽出を行っているが、以下の限界がある:

- 「業務概念レベル」のグラフ化は出来ているが、「物理ファイルの呼び出し関係」は捉えられていない
- 影響調査では「どのファイルがどのファイルを呼んでいるか」という機械的な事実が必要
- LLM 抽出は確率的で挙動が不安定 → 影響調査のような漏れが許されない業務には向かない

### 1.3 解決方針

既存 GraphRAG を**拡張**する形で、ファイル間関係のグラフを機械的に構築する。

**既存アプローチ(LLM)との役割分担**:

| 領域 | 用途 | 精度の性質 |
|---|---|---|
| 既存: Document / Chunk / Entity グラフ | 意味理解系の質問(「〜とは?」) | 柔軟だが確率的 |
| 新規: SourceFile / CopyBook グラフ | 影響調査系の質問(「どこに影響?」) | 網羅的で決定論的 |

**既存機能は一切止めず、並行稼働させる。**

---

## 2. 全体アーキテクチャ

### 2.1 既存インフラ(触らない)

```
┌─────────────────────────────────────────────────────────────┐
│                   WSL / Docker Compose                       │
│                                                               │
│  ┌─────────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ graphrag-api│  │graphrag- │  │        neo4j         │  │
│  │  (FastAPI)  │  │   es     │  │    既存領域:          │  │
│  │             │  │  (ES)    │  │   Document            │  │
│  │  /ingest    │  │          │  │   Chunk               │  │
│  │  /search    │→ │          │  │   Entity              │  │
│  │  /ingest-dir│  │          │  │                       │  │
│  │  /ui        │  │          │  │                       │  │
│  └─────────────┘  └──────────┘  └──────────────────────┘  │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │       Ollama (host.docker.internal:11434)            │    │
│  │       ※ LLM/Embed プロバイダの一候補                │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 今回の追加分

```
┌─────────────────────────────────────────────────────────────┐
│                   WSL / Docker Compose                       │
│                                                               │
│  ┌────────────────────────────────────────────┐             │
│  │           graphrag-api (FastAPI)            │             │
│  │                                              │             │
│  │  【既存】                                   │             │
│  │  ├ /ingest, /search, /ingest-dir, /ui 等   │             │
│  │                                              │             │
│  │  【新規追加】                               │             │
│  │  ├ cobol_relations.py (新ファイル)         │             │
│  │  ├ /impact-analysis エンドポイント         │             │
│  │  └ run_ingest_dir に COBOL 分岐追加        │             │
│  └────────────────────────────────────────────┘             │
│                   ↓                                          │
│  ┌────────────────────────────────────────────┐             │
│  │              Neo4j                          │             │
│  │                                              │             │
│  │  【既存領域】                               │             │
│  │  (:Document)-[:HAS_CHUNK]->(:Chunk)        │             │
│  │  (:Chunk)-[:MENTIONS]->(:Entity)           │             │
│  │  (:Entity)-[:RELATED_TO]->(:Entity)        │             │
│  │                                              │             │
│  │  【新規領域】                               │             │
│  │  (:SourceFile)-[:CALLS]->(:SourceFile)     │             │
│  │  (:SourceFile)-[:COPIES]->(:CopyBook)      │             │
│  │  (:SourceFile)-[:DESCRIBED_BY]->           │             │
│  │                  (:DesignDoc)              │             │
│  └────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

**ポイント**: ラベル名と関係名が既存と全く被らない → Cypher クエリで自動的に領域が分かれる。

---

## 3. Neo4j スキーマ設計

### 3.1 新規ラベル

| ラベル | 用途 | 主なプロパティ |
|---|---|---|
| `SourceFile` | COBOL ソースファイル | `program_id`, `file_path` |
| `CopyBook` | COPY 句の参照先 | `name` |
| `DesignDoc` | 設計書ファイル | `file_path`, `title` |

### 3.2 新規リレーション

| 関係 | From | To | 付加情報 |
|---|---|---|---|
| `CALLS` | SourceFile | SourceFile | `source_file`(由来の追跡) |
| `COPIES` | SourceFile | CopyBook | `source_file` |
| `DESCRIBED_BY` | SourceFile | DesignDoc | `source_file` |

### 3.3 既存設計思想の踏襲

既存コードの `RELATED_TO` が `source_document_id` を持ち、再取り込み時に自分が作った関係だけをクリーンに消せる設計になっている。**新規関係も同じパターンで `source_file` を持たせる**:

```cypher
// 再取り込み時のクリーンアップ例
MATCH (:SourceFile)-[r:CALLS|COPIES {source_file: $file_path}]->()
DELETE r
```

この規律を守ることで、既存コードを読める人なら新規コードも同じ理解で読める。

---

## 4. 新規モジュール: cobol_relations.py

既存 `ingest.py` と同じ設計スタイル(純粋関数、I/O はしない、エラーは `RuntimeError`/`ValueError`)で作る。

**配置**: `graphrag/cobol_relations.py`

```python
"""
COBOL ソースからファイル間関係を抽出するユーティリティ。

ingest.py が「ES と Neo4j にドキュメント本文を保存」する役割なのに対し、
このモジュールは「Neo4j にファイル間関係(CALL/COPY)を保存するための解析」を担う。
LLM は一切使わず、正規表現で決定論的に抽出する。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# COBOL ソースは Shift_JIS / UTF-8 / CP932 / EUC-JP が混在するため順に試す
_COBOL_ENCODINGS = ["shift_jis", "utf-8", "cp932", "euc_jp"]


def read_cobol(path: Path) -> str:
    """COBOL ソースを文字コード自動判別で読む"""
    for enc in _COBOL_ENCODINGS:
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"対応エンコーディングで読めませんでした: {path}")


def strip_comments(src: str) -> str:
    """COBOL のコメント行(7カラム目が '*' または '/')を除去する。
    コメント内の CALL/COPY 文字列を誤検知しないために必要。
    """
    lines = []
    for line in src.splitlines():
        if len(line) >= 7 and line[6] in ("*", "/"):
            continue
        lines.append(line)
    return "\n".join(lines)


def extract_program_id(src: str) -> str | None:
    """PROGRAM-ID を取り出す。見つからなければ None。"""
    m = re.search(r"PROGRAM-ID\.\s+([A-Z0-9][A-Z0-9\-]*)", src, re.IGNORECASE)
    return m.group(1).upper() if m else None


def extract_calls(src: str) -> list[str]:
    """CALL \"XXX\" / CALL 'XXX' を全て取り出す(重複除去前)"""
    pattern = r"""CALL\s+["']([^"']+)["']"""
    return [m.upper() for m in re.findall(pattern, src, re.IGNORECASE)]


def extract_copies(src: str) -> list[str]:
    """COPY XXX を全て取り出す(OF 句付きにも対応)"""
    # COPY XXX. または COPY XXX OF YYY.
    pattern = r"COPY\s+([A-Z0-9][A-Z0-9\-]*)"
    return [m.upper() for m in re.findall(pattern, src, re.IGNORECASE)]


def analyze_cobol_file(path: Path, input_root: Path) -> dict[str, Any] | None:
    """1 つの COBOL ファイルを解析して関係情報を返す。

    Returns:
        プログラム ID が取れた場合のみ dict を返す。取れなければ None。

    Raises:
        RuntimeError: ファイル読み込み失敗、または input_root 外の場合
    """
    src_raw = read_cobol(path)
    src = strip_comments(src_raw)

    prog_id = extract_program_id(src)
    if not prog_id:
        return None

    try:
        relative = path.resolve().relative_to(input_root.resolve())
    except ValueError as exc:
        raise RuntimeError(f"ファイルが入力ルートの外: {path}") from exc

    return {
        "program_id": prog_id,
        "file_path": str(relative).replace("\\", "/"),
        "calls": sorted(set(extract_calls(src))),
        "copies": sorted(set(extract_copies(src))),
    }
```

### 4.1 設計上の判断

- **コメント除去を先にする**: COBOL は 7 カラム目の `*` がコメントで、その中に CALL 文字列があると誤検知する
- **upper() で正規化**: COBOL は大文字小文字を区別しないため、関係は大文字で統一
- **set() で重複除去**: 1 ファイル内に同じ CALL が複数あっても関係としては 1 つ
- **file_path は相対パスで保持**: 既存 `ingest.py` の `source_ref` と同じ規約

---

## 5. main.py への追加

### 5.1 Neo4j 投入関数

`main.py` に以下の関数を追加する:

```python
def insert_cobol_relations(session, analysis: dict[str, Any]) -> None:
    """COBOL 解析結果を Neo4j に投入する。

    既存スキーマと完全に分離:
    - ラベル: SourceFile, CopyBook (既存の Document/Chunk/Entity と被らない)
    - 関係: CALLS, COPIES (既存の HAS_CHUNK/MENTIONS/RELATED_TO と被らない)
    - source_file: どのファイル由来かの追跡用。再取り込み時のクリーンアップに使う
      (既存 RELATED_TO の source_document_id と同じパターン)
    """
    prog_id = analysis["program_id"]
    file_path = analysis["file_path"]

    # 1. 解析元 SourceFile ノード (ここが「from」になる)
    session.run(
        """
        MERGE (f:SourceFile {program_id: $prog_id})
        SET f.file_path = $file_path
        """,
        prog_id=prog_id,
        file_path=file_path,
    )

    # 2. 自分が作った古い関係を掃除 (再取り込み対応)
    session.run(
        """
        MATCH (:SourceFile)-[r:CALLS|COPIES {source_file: $file_path}]->()
        DELETE r
        """,
        file_path=file_path,
    )

    # 3. CALL 関係
    for callee in analysis["calls"]:
        session.run(
            """
            MERGE (caller:SourceFile {program_id: $from_id})
            MERGE (callee:SourceFile {program_id: $to_id})
            MERGE (caller)-[:CALLS {source_file: $file_path}]->(callee)
            """,
            from_id=prog_id,
            to_id=callee,
            file_path=file_path,
        )

    # 4. COPY 関係
    for copy_name in analysis["copies"]:
        session.run(
            """
            MERGE (src:SourceFile {program_id: $from_id})
            MERGE (cpy:CopyBook {name: $copy_name})
            MERGE (src)-[:COPIES {source_file: $file_path}]->(cpy)
            """,
            from_id=prog_id,
            copy_name=copy_name,
            file_path=file_path,
        )
```

### 5.2 run_ingest_dir への分岐追加

既存の `run_ingest_dir` 関数に以下の変更を加える:

```python
def run_ingest_dir(job_id: str) -> None:
    from ingest import build_markdown_payload, build_pdf_payload, build_txt_payload
    from cobol_relations import analyze_cobol_file  # 【新規】

    # ... (既存の入力ルートチェック等はそのまま) ...

    SUPPORTED_DOC = {".pdf", ".md", ".txt"}          # 既存
    SUPPORTED_COBOL = {".cbl", ".cob", ".cpy"}       # 【新規】

    all_files = sorted(f for f in input_root.rglob("*") if f.is_file())
    targets = [f for f in all_files
               if f.suffix.lower() in (SUPPORTED_DOC | SUPPORTED_COBOL)]

    for f in targets:
        ext = f.suffix.lower()
        try:
            # 【新規】COBOL ファイルは本文取り込みせず関係だけ抽出
            if ext in SUPPORTED_COBOL:
                analysis = analyze_cobol_file(f, input_root)
                if analysis is None:
                    skipped += 1
                    continue
                driver = get_neo4j_driver()
                try:
                    with driver.session() as session:
                        insert_cobol_relations(session, analysis)
                    processed += 1
                finally:
                    driver.close()
                continue  # 通常の ingest() には進ませない

            # 既存ルート (.pdf/.md/.txt の処理はそのまま)
            if ext == ".pdf":
                payload = build_pdf_payload(f, input_root)
            elif ext == ".md":
                payload = build_markdown_payload(f, input_root)
            elif ext == ".txt":
                payload = build_txt_payload(f, input_root)
            else:
                skipped += 1
                continue

            payload["scope"] = "official"
            payload["expires_at"] = None
            result = ingest(IngestRequest(**payload))
            if result.get("skipped"):
                skipped += 1
            else:
                processed += 1

        except (ValueError, RuntimeError) as exc:
            failed += 1
            errors.append(f"{f.name}: {exc}")
        except Exception as exc:
            failed += 1
            errors.append(f"{f.name}: {exc}")
            logger.warning("ingest-dir ファイル処理エラー: %s %s", f, exc)

        jobs[job_id].update({"processed": processed, "skipped": skipped, "failed": failed})

    # ... (既存の完了処理はそのまま) ...
```

### 5.3 影響調査エンドポイント

消費税ユースケース用の新規エンドポイントを追加する:

```python
class ImpactAnalysisRequest(BaseModel):
    keywords: list[str]                # Dify 側で事前展開したキーワード
    max_hops: int = 2                  # 呼び出し元を何ホップまで辿るか
    include_design_docs: bool = True
    include_callees: bool = False      # 呼び出し先も辿るか(通常は不要)


@app.post("/impact-analysis")
def impact_analysis(req: ImpactAnalysisRequest) -> dict[str, Any]:
    """キーワードに関連するファイル群を特定し、呼び出し関係を辿って影響範囲を返す。

    処理の順番:
    1. ES にキーワード OR 検索 → 直接ヒットのチャンクとファイルを得る
    2. Neo4j SourceFile 領域で max_hops ホップまで呼び出し元を追跡
    3. DESCRIBED_BY で対応設計書を取得
    4. 直接ヒット + 呼び出し元 + 設計書 を返す
    """
    es = get_es_client()

    # Step 1: ES キーワード検索 (既存インデックスを活用)
    es_resp = es.search(
        index=ES_INDEX,
        body={
            "query": {
                "bool": {
                    "should": [{"match": {"text": kw}} for kw in req.keywords],
                    "minimum_should_match": 1,
                    "filter": [{"term": {"scope": "official"}}],
                }
            },
            "_source": ["document_id", "title", "url", "source_ref", "text", "chunk_index"],
            "size": 50,
        },
    )
    direct_hits = [hit["_source"] for hit in es_resp["hits"]["hits"]]
    hit_file_paths = list({h.get("source_ref") for h in direct_hits if h.get("source_ref")})

    # Step 2 & 3: Neo4j 追跡
    callers: list[dict[str, Any]] = []
    design_docs: list[dict[str, Any]] = []

    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            if hit_file_paths:
                # 呼び出し元の追跡
                result = session.run(
                    f"""
                    MATCH (hit:SourceFile)
                    WHERE hit.file_path IN $paths
                    MATCH (caller:SourceFile)-[:CALLS*1..{req.max_hops}]->(hit)
                    RETURN DISTINCT
                        caller.program_id AS program_id,
                        caller.file_path AS file_path
                    """,
                    paths=hit_file_paths,
                )
                callers = [dict(r) for r in result]

            if req.include_design_docs and hit_file_paths:
                # 対応設計書の取得
                result = session.run(
                    """
                    MATCH (f:SourceFile)-[:DESCRIBED_BY]->(d:DesignDoc)
                    WHERE f.file_path IN $paths
                    RETURN DISTINCT d.file_path AS file_path, d.title AS title
                    """,
                    paths=hit_file_paths,
                )
                design_docs = [dict(r) for r in result]
    finally:
        driver.close()

    return {
        "direct_hits": direct_hits,
        "callers": callers,
        "design_docs": design_docs,
        "summary": {
            "direct_hit_files": len(hit_file_paths),
            "indirect_caller_count": len(callers),
            "related_design_docs": len(design_docs),
        },
    }
```

---

## 6. Cypher クエリ集(動作確認・運用用)

Neo4j Browser(http://localhost:7474)で実行することを想定。

### 6.1 基本確認

```cypher
// 既存ラベルと新規ラベルが分離されていることの確認
MATCH (n) RETURN labels(n) AS labels, count(*) AS count
ORDER BY count DESC;

// 期待値:
// [Document]: N, [Chunk]: M, [Entity]: K, [SourceFile]: X, [CopyBook]: Y
```

### 6.2 特定プログラムの周辺確認

```cypher
// TAX001 の直接の呼び出し先
MATCH (f:SourceFile {program_id: 'TAX001'})-[:CALLS]->(target)
RETURN target.program_id;

// TAX001 が使っている COPY 句
MATCH (f:SourceFile {program_id: 'TAX001'})-[:COPIES]->(cpy)
RETURN cpy.name;

// TAX001 を呼んでいる上位プログラム (影響調査の定番)
MATCH (caller:SourceFile)-[:CALLS]->(:SourceFile {program_id: 'TAX001'})
RETURN caller.program_id;
```

### 6.3 影響調査系(多段追跡)

```cypher
// TAX001 を 3 ホップまで呼んでいる全プログラム
MATCH (caller:SourceFile)-[:CALLS*1..3]->(:SourceFile {program_id: 'TAX001'})
RETURN DISTINCT caller.program_id;

// 特定 COPY 句を使っている全ソース
MATCH (f:SourceFile)-[:COPIES]->(:CopyBook {name: 'TAX-MASTER'})
RETURN f.program_id, f.file_path;

// 消費税関係と思われるプログラム一覧(命名規則ベースの粗い検索)
MATCH (f:SourceFile)
WHERE f.program_id CONTAINS 'TAX'
   OR f.program_id CONTAINS 'ZEI'
RETURN f.program_id, f.file_path
ORDER BY f.program_id;
```

### 6.4 再構築・クリーンアップ

```cypher
// 新規領域だけを全削除(既存領域は保護される)
MATCH (n)
WHERE n:SourceFile OR n:CopyBook OR n:DesignDoc
DETACH DELETE n;

// 孤立した CopyBook (誰からも COPY されていない) を削除
MATCH (c:CopyBook) WHERE NOT ()-[:COPIES]->(c) DELETE c;
```

---

## 7. 実装 5 日プラン

### Day 1: cobol_relations.py の単体実装

- `cobol_relations.py` を作成
- 1 ファイルだけで `analyze_cobol_file()` を動かし、結果を print 確認
- 5〜10 ファイルで試し、正規表現が取りこぼしているパターンを把握
- 検証時の注意: CALL 文が行をまたぐケース、DYNAMIC CALL(動的呼び出し)は初期版では拾わない

**完了条件**: 代表的な COBOL ソースから program_id / calls / copies が正しく取れている

### Day 2: Neo4j 投入処理

- `main.py` に `insert_cobol_relations()` を追加
- 1 ファイル分を手動で投入 → Neo4j Browser で構造を確認
- 再投入しても関係が重複しないことを確認(MERGE パターンの動作確認)

**完了条件**: Neo4j に SourceFile / CopyBook ノードが作られ、CALLS / COPIES が張られている

### Day 3: run_ingest_dir への組み込み

- SUPPORTED_COBOL の分岐を追加
- `/ingest-dir` を実行して全 COBOL を一括処理
- 処理時間と失敗ファイル数を測定(エラー率 10% 以下を目標)

**完了条件**: 1 サブシステム分のファイルが Neo4j に入り切っている

### Day 4: /impact-analysis エンドポイント

- エンドポイントを追加
- curl で「消費税」キーワードを渡して動作確認
- 返却 JSON の構造を確定

**完了条件**: 消費税クエリに対して、直接ヒットと呼び出し元リストが返る

### Day 5: Dify ワークフローとの接続

- Dify 側で新ワークフローまたは既存改修
- HTTP ノードで `/impact-analysis` を叩く
- LLM ノードで回答生成
- デモ想定クエリ 3 本で動作確認

**完了条件**: 「消費税法改正の影響は?」と Dify で聞いて、まとまった回答が返る

---

## 8. 第 2 週以降の拡張(今週はやらない)

- 設計書との紐付け(`DESCRIBED_BY` の自動構築、ファイル名規則ベース)
- 用語辞書との連携(キーワード展開の精度向上)
- サブシステム間連携の可視化(全サブシステムを対象に拡張)
- エラーコード ⇔ ソースのリンク
- 管理 UI への「COBOL 関係再構築」ボタン追加

---

## 9. 既存コード設計思想との対応表

引き継ぎ時に理解を助けるため、新規コードが既存コードのどのパターンを踏襲しているかを明記:

| 既存コードのパターン | 新規コードでの対応 |
|---|---|
| `RELATED_TO.source_document_id` で由来追跡 | `CALLS.source_file` / `COPIES.source_file` |
| 再取り込み時に自分の関係だけ先に削除 | `insert_cobol_relations` 冒頭で `source_file` 指定削除 |
| `MERGE` による冪等な投入 | 同じく全ノード・関係で `MERGE` を使用 |
| `build_*_payload()` の純粋関数化 | `analyze_cobol_file()` も同スタイル |
| `input_root` からの相対パスで `source_ref` を作る | `file_path` も同じ規約 |
| エラーは `ValueError`/`RuntimeError` で上位に伝える | 同左 |

---

## 10. 進捗報告用サマリー

社内説明や上司への報告に使える 3 行テンプレ:

> **消費税法改正の影響調査ユースケース**の PoC に着手しました。今週は第 1 段階として、**COBOL ソース間の呼び出し関係を自動抽出する処理**を既存 GraphRAG に追加します。これが動けば、消費税関連のコード修正時に、どのプログラムが間接的に影響を受けるかを機械的に追跡できるようになります。設計書との紐付けや用語辞書連携は第 2 週以降で段階的に拡張します。

**説明する際のポイント**:
1. ユースケース(消費税影響調査)を主語にする
2. 「絞る」ではなく「段階化」と表現する
3. 既存 GraphRAG を壊さず**並行稼働**することを明言する
