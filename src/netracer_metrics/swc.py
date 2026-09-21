"""SWC parsing and weighted-tree utilities used by the metrics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

try:  # Optional accelerator; the NumPy fallback is exact and dependency-light.
    from scipy.spatial import cKDTree
except ImportError:  # pragma: no cover - exercised in minimal installations
    cKDTree = None


class SWCFormatError(ValueError):
    """Raised when an SWC file cannot be interpreted as a rooted forest."""


@dataclass(frozen=True)
class SWCGraph:
    """A validated SWC rooted forest with physical-coordinate edge lengths."""

    ids: np.ndarray
    node_types: np.ndarray
    points: np.ndarray
    radii: np.ndarray
    parent_index: np.ndarray
    children: tuple[tuple[int, ...], ...]
    scale: tuple[float, float, float]
    source: str | None
    component: np.ndarray
    depth: np.ndarray
    distance_to_root: np.ndarray
    ancestors: tuple[np.ndarray, ...]

    @classmethod
    def read(
        cls,
        path: str | Path,
        scale: Sequence[float] = (1.0, 1.0, 1.0),
    ) -> "SWCGraph":
        """Read an SWC file.

        ``scale`` is applied to x, y and z before any distance is measured.
        Use it to convert voxel coordinates to physical units.
        """

        path = Path(path)
        rows: list[tuple[int, int, float, float, float, float, int]] = []
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = path.read_text(encoding="latin-1")

        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) < 7:
                raise SWCFormatError(
                    f"{path}:{line_number}: expected at least 7 columns, got {len(fields)}"
                )
            try:
                node_id = int(fields[0])
                node_type = int(fields[1])
                x, y, z, radius = map(float, fields[2:6])
                parent_id = int(fields[6])
            except ValueError as exc:
                raise SWCFormatError(
                    f"{path}:{line_number}: invalid numeric value"
                ) from exc
            rows.append((node_id, node_type, x, y, z, radius, parent_id))

        return cls.from_rows(rows, scale=scale, source=str(path))

    @classmethod
    def from_rows(
        cls,
        rows: Iterable[Sequence[float | int]],
        scale: Sequence[float] = (1.0, 1.0, 1.0),
        source: str | None = None,
    ) -> "SWCGraph":
        parsed = list(rows)
        if not parsed:
            raise SWCFormatError(f"{source or '<memory>'}: SWC graph is empty")
        if len(scale) != 3 or not np.all(np.isfinite(scale)) or np.any(np.asarray(scale) <= 0):
            raise ValueError("scale must contain three finite positive values")

        ids = np.asarray([int(row[0]) for row in parsed], dtype=np.int64)
        if len(set(ids.tolist())) != len(ids):
            raise SWCFormatError(f"{source or '<memory>'}: duplicate node id")
        node_types = np.asarray([int(row[1]) for row in parsed], dtype=np.int64)
        points = np.asarray([[float(row[2]), float(row[3]), float(row[4])] for row in parsed])
        radii = np.asarray([float(row[5]) for row in parsed])
        parent_ids = np.asarray([int(row[6]) for row in parsed], dtype=np.int64)
        scale_tuple = tuple(float(value) for value in scale)
        points = points * np.asarray(scale_tuple, dtype=float)
        radii = radii.astype(float, copy=False)

        if not np.all(np.isfinite(points)) or not np.all(np.isfinite(radii)):
            raise SWCFormatError(f"{source or '<memory>'}: coordinates and radii must be finite")
        if np.any(radii < 0):
            raise SWCFormatError(f"{source or '<memory>'}: radius must be non-negative")

        id_to_index = {int(node_id): index for index, node_id in enumerate(ids)}
        parent_index = np.full(len(ids), -1, dtype=np.int64)
        children_lists: list[list[int]] = [[] for _ in ids]
        for index, parent_id in enumerate(parent_ids):
            if parent_id < 0:
                continue
            if int(parent_id) not in id_to_index:
                raise SWCFormatError(
                    f"{source or '<memory>'}: node {ids[index]} references missing parent {parent_id}"
                )
            parent = id_to_index[int(parent_id)]
            if parent == index:
                raise SWCFormatError(f"{source or '<memory>'}: node {ids[index]} is its own parent")
            parent_index[index] = parent
            children_lists[parent].append(index)

        roots = np.flatnonzero(parent_index < 0)
        if roots.size == 0:
            raise SWCFormatError(f"{source or '<memory>'}: no root node")

        component = np.full(len(ids), -1, dtype=np.int64)
        depth = np.zeros(len(ids), dtype=np.int64)
        distance_to_root = np.zeros(len(ids), dtype=float)
        stack = [(int(root), component_id) for component_id, root in enumerate(roots)]
        visited = 0
        while stack:
            index, component_id = stack.pop()
            if component[index] >= 0:
                raise SWCFormatError(f"{source or '<memory>'}: cycle detected")
            component[index] = component_id
            visited += 1
            for child in children_lists[index]:
                depth[child] = depth[index] + 1
                distance_to_root[child] = distance_to_root[index] + float(
                    np.linalg.norm(points[child] - points[index])
                )
                stack.append((child, component_id))
        if visited != len(ids):
            raise SWCFormatError(f"{source or '<memory>'}: cycle detected")

        first_ancestor = parent_index.copy()
        first_ancestor[first_ancestor < 0] = np.flatnonzero(parent_index < 0)
        ancestor_levels = [first_ancestor]
        level_count = max(1, int(len(ids)).bit_length())
        for _ in range(1, level_count):
            previous = ancestor_levels[-1]
            ancestor_levels.append(previous[previous])

        return cls(
            ids=ids,
            node_types=node_types,
            points=points,
            radii=radii,
            parent_index=parent_index,
            children=tuple(tuple(items) for items in children_lists),
            scale=scale_tuple,
            source=source,
            component=component,
            depth=depth,
            distance_to_root=distance_to_root,
            ancestors=tuple(ancestor_levels),
        )

    @property
    def size(self) -> int:
        return int(len(self.ids))

    @property
    def root_count(self) -> int:
        return int(np.count_nonzero(self.parent_index < 0))

    @property
    def branching_node_count(self) -> int:
        return sum(len(children) > 1 for children in self.children)

    @property
    def leaf_count(self) -> int:
        return sum(len(children) == 0 for children in self.children)

    @property
    def total_length(self) -> float:
        return float(
            sum(
                np.linalg.norm(self.points[index] - self.points[parent])
                for index, parent in enumerate(self.parent_index)
                if parent >= 0
            )
        )

    def nearest(self, query_points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return nearest-node distances and indices for query points."""

        query_points = np.asarray(query_points, dtype=float)
        if query_points.ndim != 2 or query_points.shape[1] != 3:
            raise ValueError("query_points must have shape (N, 3)")
        if cKDTree is not None:
            tree = cKDTree(self.points)
            if self.size == 1:
                distances, indices = tree.query(query_points, k=1)
                return np.asarray(distances, dtype=float), np.asarray(indices, dtype=np.int64)

            # Query two neighbours so exact-distance ties can be resolved in a
            # backend-independent way. The public tie rule is: choose the gold
            # node that appears first in the SWC file.
            candidate_distances, candidate_indices = tree.query(query_points, k=2)
            distances = np.asarray(candidate_distances[:, 0], dtype=float)
            indices = np.asarray(candidate_indices[:, 0], dtype=np.int64)
            tied = np.isclose(
                candidate_distances[:, 0],
                candidate_distances[:, 1],
                rtol=1e-12,
                atol=1e-12,
            )
            for query_index in np.flatnonzero(tied):
                base_distance = float(distances[query_index])
                radius = base_distance + max(1e-12, abs(base_distance) * 1e-12)
                candidates = np.asarray(
                    tree.query_ball_point(query_points[query_index], radius),
                    dtype=np.int64,
                )
                exact = np.linalg.norm(
                    self.points[candidates] - query_points[query_index], axis=1
                )
                minimum = float(np.min(exact))
                equal = candidates[
                    np.isclose(exact, minimum, rtol=1e-12, atol=1e-12)
                ]
                indices[query_index] = int(np.min(equal))
                distances[query_index] = minimum
            return distances, indices

        # Exact, bounded-memory fallback. Chunk both axes so large SWC files do
        # not allocate the full query-by-gold distance matrix.
        query_chunk_size = 1024
        gold_chunk_size = 4096
        all_distances = np.empty(len(query_points), dtype=float)
        all_indices = np.empty(len(query_points), dtype=np.int64)
        for query_start in range(0, len(query_points), query_chunk_size):
            query_block = query_points[query_start : query_start + query_chunk_size]
            best_squared = np.full(len(query_block), np.inf, dtype=float)
            best_indices = np.zeros(len(query_block), dtype=np.int64)
            for gold_start in range(0, self.size, gold_chunk_size):
                gold_block = self.points[gold_start : gold_start + gold_chunk_size]
                squared = np.sum(
                    (query_block[:, None, :] - gold_block[None, :, :]) ** 2,
                    axis=2,
                )
                local_indices = np.argmin(squared, axis=1)
                local_squared = squared[np.arange(len(query_block)), local_indices]
                improved = local_squared < best_squared
                best_squared[improved] = local_squared[improved]
                best_indices[improved] = gold_start + local_indices[improved]
            query_stop = query_start + len(query_block)
            all_distances[query_start:query_stop] = np.sqrt(best_squared)
            all_indices[query_start:query_stop] = best_indices
        return all_distances, all_indices

    def lowest_common_ancestor(self, left: int, right: int) -> int | None:
        """Return the LCA index, or ``None`` when nodes are disconnected."""

        if self.component[left] != self.component[right]:
            return None
        if self.depth[left] < self.depth[right]:
            left, right = right, left
        difference = int(self.depth[left] - self.depth[right])
        bit = 0
        while difference:
            if difference & 1:
                left = int(self.ancestors[bit][left])
            difference >>= 1
            bit += 1
        if left == right:
            return left
        for level in range(len(self.ancestors) - 1, -1, -1):
            next_left = int(self.ancestors[level][left])
            next_right = int(self.ancestors[level][right])
            if next_left != next_right:
                left, right = next_left, next_right
        return int(self.ancestors[0][left])

    def graph_distance(self, left: int, right: int) -> float:
        """Weighted shortest-path distance in the SWC forest."""

        ancestor = self.lowest_common_ancestor(left, right)
        if ancestor is None:
            return float("inf")
        return float(
            self.distance_to_root[left]
            + self.distance_to_root[right]
            - 2.0 * self.distance_to_root[ancestor]
        )
