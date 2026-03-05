"""
notebooklm-py を使って CSVファイルから解説動画(MP4)を生成するスクリプト

使い方:
    python3 generate_video_from_csv.py --csvs ./data.csv --output ./output_video.mp4
    python3 generate_video_from_csv.py --csvs file1.csv file2.csv file3.csv --output ./output_video.mp4

事前に `notebooklm login` で認証を済ませておく必要があります。
"""

import argparse
import asyncio
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CSVファイル(複数可)をNotebookLMに追加し、解説動画(MP4)を生成してダウンロードします"
    )
    parser.add_argument(
        "--csvs",
        nargs="+",
        required=True,
        type=Path,
        help="ソースとして追加するCSVファイルのパス (複数指定可、例: ./data.csv ./data2.csv)",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="ダウンロードするMP4ファイルの出力先 (例: ./output_video.mp4)",
    )
    parser.add_argument(
        "--notebook-title",
        default="CSV分析レポート",
        help="作成するノートブックのタイトル (デフォルト: CSV分析レポート)",
    )
    parser.add_argument(
        "--instructions",
        default="CSVデータの主要な傾向と示唆を分かりやすく解説してください",
        help="動画生成への指示文 (自然言語)",
    )
    parser.add_argument(
        "--style",
        default="whiteboard",
        choices=[
            "auto", "classic", "whiteboard", "kawaii",
            "anime", "watercolor", "retro-print", "heritage", "paper-craft",
        ],
        help="動画のビジュアルスタイル (デフォルト: whiteboard)",
    )
    parser.add_argument(
        "--format",
        default="explainer",
        choices=["explainer", "brief"],
        dest="video_format",
        help="動画のフォーマット (デフォルト: explainer)",
    )
    parser.add_argument(
        "--language",
        default="ja",
        help="出力言語コード (デフォルト: ja / 例: en, zh_Hans)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="動画生成の最大待機秒数 (デフォルト: 1800秒 = 30分)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="出力先に同名ファイルがある場合に上書きする",
    )
    return parser.parse_args()


async def wait_for_source_ready(client, nb_id: str, source_id: str, name: str, max_wait: int = 300) -> None:
    """ソースのインデックス作成完了（SourceStatus.READY = 2）まで待機する。"""
    poll_interval = 5
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
        from notebooklm import NotebookLMClient, VideoFormat, VideoStyle
    except ImportError:
        print(
            "[ERROR] notebooklm-py がインストールされていません。\n"
            "  pip install \"notebooklm-py[browser]\" を実行してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    csv_paths: list[Path] = [p.resolve() for p in args.csvs]
    output_path: Path = args.output.resolve()

    for p in csv_paths:
        if not p.exists():
            print(f"[ERROR] CSVファイルが見つかりません: {p}", file=sys.stderr)
            sys.exit(1)

    if output_path.exists() and not args.force:
        print(
            f"[ERROR] 出力先ファイルが既に存在します: {output_path}\n"
            "  上書きする場合は --force オプションを指定してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    style_map: dict[str, VideoStyle] = {
        "auto": VideoStyle.AUTO_SELECT,
        "classic": VideoStyle.CLASSIC,
        "whiteboard": VideoStyle.WHITEBOARD,
        "kawaii": VideoStyle.KAWAII,
        "anime": VideoStyle.ANIME,
        "watercolor": VideoStyle.WATERCOLOR,
        "retro-print": VideoStyle.RETRO_PRINT,
        "heritage": VideoStyle.HERITAGE,
        "paper-craft": VideoStyle.PAPER_CRAFT,
    }
    format_map: dict[str, VideoFormat] = {
        "explainer": VideoFormat.EXPLAINER,
        "brief": VideoFormat.BRIEF,
    }

    video_style = style_map[args.style]
    video_format = format_map[args.video_format]

    print("=" * 60)
    print("  notebooklm-py: CSV → 解説動画(MP4) 生成スクリプト")
    print("=" * 60)
    print(f"  CSVファイル    :")
    for p in csv_paths:
        print(f"    - {p.name}")
    print(f"  出力先         : {output_path}")
    print(f"  ノートブック名 : {args.notebook_title}")
    print(f"  スタイル       : {args.style}")
    print(f"  フォーマット   : {args.video_format}")
    print(f"  出力言語       : {args.language}")
    print(f"  最大待機時間   : {args.timeout}秒")
    print("=" * 60)

    async with await NotebookLMClient.from_storage() as client:

        # ── Step 1: ノートブック作成 ──────────────────────────────
        print(f"\n[1/5] ノートブックを作成中: {args.notebook_title!r}")
        nb = await client.notebooks.create(args.notebook_title)
        print(f"      ノートブックID: {nb.id}")

        # ── Step 2: CSVをソースとして追加 ─────────────────────────
        print(f"\n[2/5] CSVファイルをソースに追加中…")
        sources = []
        for p in csv_paths:
            print(f"      追加中: {p.name}")
            source = await client.sources.add_file(nb.id, p)
            print(f"      ソースID: {source.id}")
            sources.append((p.name, source.id))

        print("      全ソースのインデックス作成を待機中…")
        for name, source_id in sources:
            await wait_for_source_ready(client, nb.id, source_id, name)

        # ── Step 3: 解説動画を生成 ────────────────────────────────
        print(f"\n[3/5] 解説動画の生成を開始中")
        print(f"      指示: {args.instructions!r}")
        gen_status = await client.artifacts.generate_video(
            nb.id,
            instructions=args.instructions,
            video_format=video_format,
            video_style=video_style,
            language=args.language,
        )
        print(f"      タスクID: {gen_status.task_id}")

        # ── Step 4: 生成完了まで待機 ──────────────────────────────
        print(f"\n[4/5] 動画生成の完了を待機中 (最大 {args.timeout} 秒)…")
        print("      動画の生成には数分〜30分以上かかる場合があります。")

        final = await client.artifacts.wait_for_completion(
            nb.id,
            gen_status.task_id,
            timeout=args.timeout,
            poll_interval=10,
        )

        if not final.is_complete:
            print(
                f"\n[ERROR] 動画生成がタイムアウトまたは失敗しました。\n"
                f"  ステータス: {final.status}\n"
                f"  後から確認する場合: notebooklm artifact poll {gen_status.task_id}",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"      動画生成完了")

        # ── Step 5: MP4ダウンロード ───────────────────────────────
        print(f"\n[5/5] MP4ファイルをダウンロード中: {output_path}")
        downloaded = await client.artifacts.download_video(
            nb.id,
            str(output_path),
        )
        print(f"      ダウンロード完了: {downloaded}")

    print("\n" + "=" * 60)
    print("  完了！")
    print(f"  動画ファイル: {output_path}")
    print("=" * 60)


def main() -> None:
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
