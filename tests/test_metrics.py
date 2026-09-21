import math
import tempfile
import unittest
from pathlib import Path

from netracer_metrics import (
    SWCFormatError,
    SWCGraph,
    aggregate,
    average_branch_length,
    evaluate_graphs,
    jump_error,
    position_error,
)


def graph(rows):
    return SWCGraph.from_rows(rows)


class MetricTests(unittest.TestCase):
    def test_position_error_uses_nearest_gold_nodes_and_strict_threshold(self):
        gold = graph(
            [
                (1, 2, 0, 0, 0, 1, -1),
                (2, 2, 2, 0, 0, 1, 1),
            ]
        )
        test = graph(
            [
                (10, 2, 0, 1, 0, 1, -1),
                (11, 2, 4, 0, 0, 1, 10),
            ]
        )
        result = position_error(gold, test, match_threshold=2.0)
        self.assertEqual(result.matched_nodes, 1)  # distance == 2 is excluded
        self.assertAlmostEqual(result.value, 1.0)

    def test_average_branch_length_matches_original_denominator(self):
        test = graph(
            [
                (1, 2, 0, 0, 0, 1, -1),
                (2, 2, 1, 0, 0, 1, 1),
                (3, 2, 2, 1, 0, 1, 2),
                (4, 2, 2, -1, 0, 1, 2),
            ]
        )
        result = average_branch_length(test)
        self.assertEqual(result.branch_count, 2)
        self.assertAlmostEqual(result.total_length, 1 + 2 * math.sqrt(2))
        self.assertAlmostEqual(result.value, (1 + 2 * math.sqrt(2)) / 2)

    def test_jump_error_detects_topological_shortcut(self):
        # Gold path takes a long rectangular detour between nearby endpoints.
        gold = graph(
            [
                (1, 2, 0, 0, 0, 1, -1),
                (2, 2, 10, 0, 0, 1, 1),
                (3, 2, 10, 1, 0, 1, 2),
                (4, 2, 0, 1, 0, 1, 3),
            ]
        )
        test = graph(
            [
                (10, 2, 0, 0, 0, 1, -1),
                (11, 2, 0, 1, 0, 1, 10),
            ]
        )
        result = jump_error(gold, test, match_threshold=2.0, jump_ratio=2.0)
        self.assertEqual(result.value, 1)
        self.assertEqual(result.jump_test_node_ids, (11,))

    def test_jump_error_accepts_correct_edge(self):
        gold = graph(
            [
                (1, 2, 0, 0, 0, 1, -1),
                (2, 2, 1, 0, 0, 1, 1),
            ]
        )
        result = jump_error(gold, gold)
        self.assertEqual(result.value, 0)
        self.assertEqual(result.eligible_edges, 1)

    def test_jump_between_disconnected_gold_components_is_counted(self):
        gold = graph(
            [
                (1, 2, 0, 0, 0, 1, -1),
                (2, 2, 0, 1, 0, 1, -1),
            ]
        )
        test = graph(
            [
                (10, 2, 0, 0, 0, 1, -1),
                (11, 2, 0, 1, 0, 1, 10),
            ]
        )
        result = jump_error(gold, test)
        self.assertEqual(result.value, 1)

    def test_scale_changes_physical_distance(self):
        graph_scaled = SWCGraph.from_rows(
            [(1, 2, 0, 0, 0, 1, -1), (2, 2, 0, 0, 1, 1, 1)],
            scale=(1, 1, 3),
        )
        self.assertAlmostEqual(graph_scaled.total_length, 3.0)

    def test_nearest_tie_uses_first_gold_node(self):
        gold = graph(
            [
                (10, 2, -1, 0, 0, 1, -1),
                (20, 2, 1, 0, 0, 1, -1),
            ]
        )
        distances, indices = gold.nearest([[0, 0, 0]])
        self.assertAlmostEqual(distances[0], 1.0)
        self.assertEqual(indices[0], 0)

    def test_no_position_matches_is_explicit(self):
        gold = graph([(1, 2, 0, 0, 0, 1, -1)])
        test = graph([(2, 2, 100, 0, 0, 1, -1)])
        result = position_error(gold, test)
        self.assertIsNone(result.value)
        self.assertEqual(result.matched_nodes, 0)

    def test_aggregate_reports_macro_and_pooled_pe(self):
        gold = graph([(1, 2, 0, 0, 0, 1, -1)])
        first = graph([(2, 2, 1, 0, 0, 1, -1)])
        second = graph(
            [
                (3, 2, 0, 0, 0, 1, -1),
                (4, 2, 0, 0, 0, 1, 3),
                (5, 2, 0, 0, 0, 1, 4),
            ]
        )
        summary = aggregate(
            [evaluate_graphs(gold, first), evaluate_graphs(gold, second)]
        )
        self.assertAlmostEqual(summary["PE_macro"], 0.5)
        self.assertAlmostEqual(summary["PE_pooled"], 0.25)

    def test_parser_rejects_missing_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.swc"
            path.write_text("1 2 0 0 0 1 99\n", encoding="utf-8")
            with self.assertRaises(SWCFormatError):
                SWCGraph.read(path)

    def test_parser_rejects_cycle(self):
        with self.assertRaises(SWCFormatError):
            graph(
                [
                    (1, 2, 0, 0, 0, 1, -1),
                    (2, 2, 1, 0, 0, 1, 3),
                    (3, 2, 2, 0, 0, 1, 2),
                ]
            )


if __name__ == "__main__":
    unittest.main()
