"""Command-line interface for reproducible metric evaluation."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Sequence

from .metrics import EvaluationResult, aggregate, evaluate_files
from . import __version__


def _add_metric_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--match-threshold",
        type=float,
        default=2.0,
        help="PE/JE nearest-node matching threshold epsilon (default: 2)",
    )
    parser.add_argument(
        "--jump-ratio",
        type=float,
        default=2.0,
        help="JE graph-to-straight distance ratio alpha (default: 2)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        nargs=3,
        metavar=("SX", "SY", "SZ"),
        default=(1.0, 1.0, 1.0),
        help="coordinate scale/voxel spacing applied to x y z",
    )


def _write_json(payload: Any, path: Path | None) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
    if path is None:
        print(text)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")


def _read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = {"case_id", "gold", "test"}
    if not rows:
        raise ValueError(f"manifest is empty: {path}")
    if not expected.issubset(rows[0]):
        raise ValueError("manifest must contain columns: case_id,gold,test")
    return rows


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def _write_per_case_csv(results: Sequence[EvaluationResult], path: Path) -> None:
    fieldnames = [
        "case_id",
        "gold",
        "test",
        "PE",
        "PE_matched_nodes",
        "PE_total_test_nodes",
        "ABL",
        "ABL_total_length",
        "ABL_branch_count",
        "JE",
        "JE_eligible_edges",
        "JE_total_test_edges",
        "JE_jump_test_node_ids",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in results:
            writer.writerow(
                {
                    "case_id": item.case_id,
                    "gold": item.gold,
                    "test": item.test,
                    "PE": item.pe.value,
                    "PE_matched_nodes": item.pe.matched_nodes,
                    "PE_total_test_nodes": item.pe.total_test_nodes,
                    "ABL": item.abl.value,
                    "ABL_total_length": item.abl.total_length,
                    "ABL_branch_count": item.abl.branch_count,
                    "JE": item.je.value,
                    "JE_eligible_edges": item.je.eligible_edges,
                    "JE_total_test_edges": item.je.total_test_edges,
                    "JE_jump_test_node_ids": ";".join(map(str, item.je.jump_test_node_ids)),
                }
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="netracer-metrics",
        description="Evaluate NETracer Position Error, Average Branch Length and Jump Error.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    pair = subparsers.add_parser("pair", help="evaluate one gold/test SWC pair")
    pair.add_argument("gold", type=Path)
    pair.add_argument("test", type=Path)
    pair.add_argument("--case-id")
    pair.add_argument("--json", type=Path, help="write JSON instead of printing it")
    _add_metric_arguments(pair)

    batch = subparsers.add_parser("batch", help="evaluate pairs listed in a CSV manifest")
    batch.add_argument("manifest", type=Path)
    batch.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="directory for summary.json and per_case.csv",
    )
    _add_metric_arguments(batch)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "pair":
        result = evaluate_files(
            args.gold,
            args.test,
            case_id=args.case_id,
            scale=args.scale,
            match_threshold=args.match_threshold,
            jump_ratio=args.jump_ratio,
        )
        _write_json(result.to_dict(), args.json)
        return 0

    manifest_path = args.manifest.resolve()
    base = manifest_path.parent
    results = [
        evaluate_files(
            _resolve(base, row["gold"]),
            _resolve(base, row["test"]),
            case_id=row["case_id"],
            scale=args.scale,
            match_threshold=args.match_threshold,
            jump_ratio=args.jump_ratio,
        )
        for row in _read_manifest(manifest_path)
    ]
    output_dir = args.output_dir.resolve()
    _write_per_case_csv(results, output_dir / "per_case.csv")
    _write_json(
        {
            "parameters": {
                "match_threshold": args.match_threshold,
                "jump_ratio": args.jump_ratio,
                "scale": list(args.scale),
                "manifest": str(manifest_path),
            },
            "summary": aggregate(results),
        },
        output_dir / "summary.json",
    )
    print(f"Evaluated {len(results)} cases -> {output_dir}")
    return 0
