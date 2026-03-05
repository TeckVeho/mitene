"""
複数のCSVファイルを1つのNotebookLMノートブックにソースとして追加するスクリプト

使い方:
    python3 create_notebook_from_csvs.py \
        --title "ノートブック名" \
        --csvs file1.csv file2.csv file3.csv
"""

import argparse
import asyncio
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="複数のCSVファイルを1つのNotebookLMノートブックにまとめて追加します"
    )
    parser.add_argument(
        "--title",
        default="CSV分析レポート",
        help="作成するノートブックのタイトル",
    )
    parser.add_argument(
        "--csvs",
        nargs="+",
        required=True,
        type=Path,
        help="追加するCSVファイルのパス（複数指定可）",
    )
    return parser.parse_args()


async def wait_for_source_ready(client, nb_id: str, source_id: str, name: str) -> None:
    poll_interval = 5
    max_wait = 300
    elapsed = 0
    while elapsed < max_wait:
        src = await client.sources.get(nb_id, source_id)
        if hasattr(src, "status") and src.status == 2:
            print(f"      [{name}] インデックス作成完了")
            return
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
        print(f"      [{name}] 処理中… ({elapsed}秒経過)")
    print(f"      [{name}] 警告: タイムアウト。処理が完了していない可能性があります。")


async def run(args: argparse.Namespace) -> None:
    try:
        from notebooklm import NotebookLMClient
    except ImportError:
        print(
            "[ERROR] notebooklm-py がインストールされていません。\n"
            '  pip install "notebooklm-py[browser]" を実行してください。',
            file=sys.stderr,
        )
        sys.exit(1)

    csv_paths: list[Path] = [p.resolve() for p in args.csvs]

    for p in csv_paths:
        if not p.exists():
            print(f"[ERROR] CSVファイルが見つかりません: {p}", file=sys.stderr)
            sys.exit(1)

    print("=" * 60)
    print("  NotebookLM: 複数CSV → ノートブック ソース追加スクリプト")
    print("=" * 60)
    print(f"  ノートブック名 : {args.title}")
    print(f"  追加するCSV    :")
    for p in csv_paths:
        print(f"    - {p.name}")
    print("=" * 60)

    async with await NotebookLMClient.from_storage() as client:

        # ── Step 1: ノートブック作成 ──────────────────────────────
        print(f"\n[1/3] ノートブックを作成中: {args.title!r}")
        nb = await client.notebooks.create(args.title)
        print(f"      ノートブックID: {nb.id}")

        # ── Step 2: 全CSVをソースとして追加 ──────────────────────
        print(f"\n[2/3] CSVファイルをソースに追加中…")
        sources = []
        for p in csv_paths:
            print(f"      追加中: {p.name}")
            source = await client.sources.add_file(nb.id, p)
            print(f"      ソースID: {source.id}")
            sources.append((p.name, source.id))

        # ── Step 3: 全ソースのインデックス完了を待機 ─────────────
        print(f"\n[3/3] 全ソースのインデックス作成を待機中…")
        for name, source_id in sources:
            await wait_for_source_ready(client, nb.id, source_id, name)

    print("\n" + "=" * 60)
    print("  完了！")
    print(f"  ノートブックID : {nb.id}")
    print(f"  追加ソース数   : {len(sources)}")
    print("=" * 60)
    print("\nノートブックをアクティブにするには:")
    print(f"  notebooklm use {nb.id}")


def main() -> None:
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
