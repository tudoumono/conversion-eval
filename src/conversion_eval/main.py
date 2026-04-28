"""Description: conversion-evalのCLI引数を処理し、評価パイプラインを起動します。"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from conversion_eval.config.env import load_env
from conversion_eval.config.loader import load_noise_config, load_patterns
from conversion_eval.folder_markers import write_existing_generated_folder_markers
from conversion_eval.pipeline.runner import collect_input_files, run_patterns
from conversion_eval.reports.human_eval import write_human_eval_template
from conversion_eval.reports.raw_writer import write_raw_report
from conversion_eval.reports.summary import write_summaries
from conversion_eval.sampling.stratified import create_stratified_sample


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    root = Path(args.root)
    load_env(root)
    patterns = load_patterns(root / "config" / "patterns.yaml")
    noise_config = load_noise_config(root / "config" / "noise_rules.yaml")
    run_id = f"run_{_timestamp()}"

    if args.make_sample:
        selected = create_stratified_sample(root / args.full_input, root / args.sample_output, args.seed)
        print(f"Created sample with {len(selected)} files: {root / args.sample_output}")
        return 0

    write_existing_generated_folder_markers(patterns, root / "intermediate", root / "output", root / "reports")

    selected_patterns = _select_patterns(patterns, args.patterns)
    if args.human_template:
        out = root / "reports" / "human_eval" / run_id / "eval_sheet.csv"
        write_human_eval_template(out, root / args.input, selected_patterns)
        print(f"Wrote human evaluation template: {out}")
        return 0

    input_dir = root / args.input
    files = collect_input_files(input_dir)
    if not files:
        print(f"No supported input files found under: {input_dir}")
        return 1

    intermediate_root = root / "intermediate" / run_id
    output_root = root / "output" / run_id
    summary_dir = root / "reports" / "summary" / run_id
    records = run_patterns(
        patterns=selected_patterns,
        input_dir=input_dir,
        intermediate_root=intermediate_root,
        output_root=output_root,
        noise_config=noise_config,
        workers=args.workers,
        ocr_workers=args.ocr_workers,
    )

    raw_path = root / "reports" / "raw" / run_id / "raw.csv"
    write_raw_report(raw_path, records)
    write_summaries(summary_dir, records)

    print(f"Processed {len(records)} pattern/file combinations.")
    print(f"Run ID: {run_id}")
    print(f"Intermediate: {intermediate_root}")
    print(f"Output: {output_root}")
    print(f"Raw report: {raw_path}")
    print(f"Summary: {summary_dir}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the conversion evaluation PoC pipeline.")
    parser.add_argument("--root", default=".", help="Project root directory.")
    parser.add_argument("--input", default="input/sample", help="Input directory relative to root.")
    parser.add_argument(
        "--patterns",
        default="pattern_e",
        help="Comma-separated pattern ids. Use 'all' for every configured pattern.",
    )
    parser.add_argument("--human-template", action="store_true", help="Generate a human evaluation CSV template.")
    parser.add_argument("--make-sample", action="store_true", help="Create input/sample from input/full.")
    parser.add_argument("--full-input", default="input/full", help="Full input dir for --make-sample.")
    parser.add_argument("--sample-output", default="input/sample", help="Sample output dir for --make-sample.")
    parser.add_argument("--seed", type=int, default=42, help="Sampling random seed.")
    parser.add_argument("--workers", type=_positive_int, default=1, help="Number of parallel workers for non-COM patterns.")
    parser.add_argument("--ocr-workers", type=_positive_int, default=1, help="Number of parallel workers for OCR patterns.")
    return parser.parse_args(argv)


def _select_patterns(patterns: list, spec: str) -> list:
    if spec.lower() == "all":
        return patterns
    wanted = {item.strip() for item in spec.split(",") if item.strip()}
    aliases = {item.removeprefix("pattern_") for item in wanted}
    selected = [p for p in patterns if p.id in wanted or p.id.removeprefix("pattern_") in aliases]
    missing = wanted - {p.id for p in selected} - {p.id.removeprefix("pattern_") for p in selected}
    if missing:
        raise SystemExit(f"Unknown pattern id(s): {', '.join(sorted(missing))}")
    return selected


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be 1 or greater")
    return number


if __name__ == "__main__":
    raise SystemExit(main())
