"""Publication-oriented implementations of PE, ABL and JE."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .swc import SWCGraph


@dataclass(frozen=True)
class PositionErrorResult:
    value: float | None
    matched_nodes: int
    total_test_nodes: int
    distance_sum: float
    match_threshold: float

    @property
    def matched_fraction(self) -> float:
        return self.matched_nodes / self.total_test_nodes

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["matched_fraction"] = self.matched_fraction
        return result


@dataclass(frozen=True)
class AverageBranchLengthResult:
    value: float
    total_length: float
    branch_count: int
    root_count: int
    branching_node_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class JumpErrorResult:
    value: int
    eligible_edges: int
    total_test_edges: int
    jump_test_node_ids: tuple[int, ...]
    match_threshold: float
    jump_ratio: float

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["jump_test_node_ids"] = list(self.jump_test_node_ids)
        return result


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    gold: str | None
    test: str | None
    pe: PositionErrorResult
    abl: AverageBranchLengthResult
    je: JumpErrorResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "gold": self.gold,
            "test": self.test,
            "PE": self.pe.to_dict(),
            "ABL": self.abl.to_dict(),
            "JE": self.je.to_dict(),
        }


def _validate_parameters(match_threshold: float, jump_ratio: float = 2.0) -> None:
    if not np.isfinite(match_threshold) or match_threshold <= 0:
        raise ValueError("match_threshold must be finite and positive")
    if not np.isfinite(jump_ratio) or jump_ratio <= 0:
        raise ValueError("jump_ratio must be finite and positive")


def position_error(
    gold: SWCGraph,
    test: SWCGraph,
    match_threshold: float = 2.0,
) -> PositionErrorResult:
    """Compute Position Error (PE) following Supplementary Algorithm 1.

    Each test node is matched to its nearest gold node. Matches whose strict
    Euclidean distance is below ``match_threshold`` contribute to the mean.
    """

    _validate_parameters(match_threshold)
    distances, _ = gold.nearest(test.points)
    matched = distances < match_threshold
    matched_count = int(np.count_nonzero(matched))
    distance_sum = float(np.sum(distances[matched]))
    value = distance_sum / matched_count if matched_count else None
    return PositionErrorResult(
        value=value,
        matched_nodes=matched_count,
        total_test_nodes=test.size,
        distance_sum=distance_sum,
        match_threshold=float(match_threshold),
    )


def average_branch_length(test: SWCGraph) -> AverageBranchLengthResult:
    """Compute Average Branch Length (ABL) used by the original experiments.

    ``ABL = total test-graph edge length / (roots + branching nodes)``.
    This reproduces the denominator in ``stat_metric_road.py``. For a binary
    rooted forest it is equal to the number of terminal branches.
    """

    branch_count = test.root_count + test.branching_node_count
    total_length = test.total_length
    return AverageBranchLengthResult(
        value=total_length / branch_count,
        total_length=total_length,
        branch_count=branch_count,
        root_count=test.root_count,
        branching_node_count=test.branching_node_count,
    )


def jump_error(
    gold: SWCGraph,
    test: SWCGraph,
    match_threshold: float = 2.0,
    jump_ratio: float = 2.0,
) -> JumpErrorResult:
    """Compute Jump Error (JE) following Supplementary Algorithm 2.

    For every non-root test node within ``match_threshold`` of the gold graph,
    the node and its parent are mapped to nearest gold nodes. A jump is counted
    when their gold-graph distance is strictly greater than ``jump_ratio``
    times the straight-line distance between those two matched gold nodes.
    """

    _validate_parameters(match_threshold, jump_ratio)
    distances, nearest = gold.nearest(test.points)
    total_edges = int(np.count_nonzero(test.parent_index >= 0))
    eligible = 0
    jump_ids: list[int] = []
    for index, parent in enumerate(test.parent_index):
        if parent < 0 or not distances[index] < match_threshold:
            continue
        eligible += 1
        gold_node = int(nearest[index])
        gold_parent = int(nearest[parent])
        graph_distance = gold.graph_distance(gold_node, gold_parent)
        straight_distance = float(
            np.linalg.norm(gold.points[gold_node] - gold.points[gold_parent])
        )
        if graph_distance > jump_ratio * straight_distance:
            jump_ids.append(int(test.ids[index]))

    return JumpErrorResult(
        value=len(jump_ids),
        eligible_edges=eligible,
        total_test_edges=total_edges,
        jump_test_node_ids=tuple(jump_ids),
        match_threshold=float(match_threshold),
        jump_ratio=float(jump_ratio),
    )


def evaluate_graphs(
    gold: SWCGraph,
    test: SWCGraph,
    *,
    case_id: str = "case",
    match_threshold: float = 2.0,
    jump_ratio: float = 2.0,
) -> EvaluationResult:
    """Evaluate PE, ABL and JE for one gold/test graph pair."""

    return EvaluationResult(
        case_id=case_id,
        gold=gold.source,
        test=test.source,
        pe=position_error(gold, test, match_threshold),
        abl=average_branch_length(test),
        je=jump_error(gold, test, match_threshold, jump_ratio),
    )


def evaluate_files(
    gold_path: str | Path,
    test_path: str | Path,
    *,
    case_id: str | None = None,
    scale: Sequence[float] = (1.0, 1.0, 1.0),
    match_threshold: float = 2.0,
    jump_ratio: float = 2.0,
) -> EvaluationResult:
    """Read and evaluate one pair of SWC files."""

    gold_path = Path(gold_path)
    test_path = Path(test_path)
    return evaluate_graphs(
        SWCGraph.read(gold_path, scale=scale),
        SWCGraph.read(test_path, scale=scale),
        case_id=case_id or test_path.stem,
        match_threshold=match_threshold,
        jump_ratio=jump_ratio,
    )


def aggregate(results: Sequence[EvaluationResult]) -> dict[str, Any]:
    """Return transparent macro and pooled dataset summaries."""

    if not results:
        raise ValueError("cannot aggregate an empty result list")
    pe_values = [item.pe.value for item in results if item.pe.value is not None]
    matched_total = sum(item.pe.matched_nodes for item in results)
    distance_total = sum(item.pe.distance_sum for item in results)
    return {
        "cases": len(results),
        "PE_macro": float(np.mean(pe_values)) if pe_values else None,
        "PE_pooled": distance_total / matched_total if matched_total else None,
        "PE_valid_cases": len(pe_values),
        "PE_matched_nodes": matched_total,
        "PE_total_test_nodes": sum(item.pe.total_test_nodes for item in results),
        "ABL_macro": float(np.mean([item.abl.value for item in results])),
        "JE_mean": float(np.mean([item.je.value for item in results])),
        "JE_total": int(sum(item.je.value for item in results)),
        "JE_eligible_edges": int(sum(item.je.eligible_edges for item in results)),
        "JE_total_test_edges": int(sum(item.je.total_test_edges for item in results)),
    }
