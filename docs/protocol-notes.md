# Metric protocol and legacy-code audit

This document records details that materially affect reproducibility. It is part
of the metric specification, not merely implementation commentary.

## Public protocol implemented by default

### PE

Supplementary Algorithm 1 maps every test node to its nearest gold **node**,
retains strict matches with distance `< epsilon`, and averages the retained
Euclidean distances. The paper states `epsilon = 2`.

### JE

Supplementary Algorithm 2 maps a matched test node and its parent to nearest
gold nodes. A jump is counted when the gold-graph path distance is strictly
greater than `alpha` times the Euclidean distance between the two matched gold
nodes. This implementation uses `alpha = 2` by default, matching the ratio used
in the experiment code.

The supplementary pseudocode tests the match criterion for the child node only;
the parent is always mapped to its nearest gold node. Roots have no parent and
are skipped. If matched gold nodes belong to disconnected components, their
graph distance is infinite and the edge counts as a jump.

### ABL

The paper describes ABL conceptually but does not provide a complete algorithm
in the supplementary material. The accompanying experiment script computes:

```text
ABL = total Euclidean length of test edges
      / (number of roots + number of test nodes with >1 child)
```

This repository retains that denominator. It equals the number of leaves only
for binary rooted forests. Results for multifurcating graphs must therefore be
interpreted as the original-code definition, not as a generic mean maximal
segment length.

## Differences found in the old experiment workspace

1. `point_metric.py` measures test-point-to-gold-**edge** distance, not
   point-to-gold-node distance.
2. Its spatial search radius is hard-coded to 5, while the supplementary PE
   protocol states `epsilon = 2`.
3. `edge_metric.py` accepts a configured threshold but uses a hard-coded 2.
4. Legacy JE additionally requires gold-graph distance `> 20`; this cutoff does
   not appear in Supplementary Algorithm 2.
5. Legacy JE measures its straight-line term from the test child to the matched
   gold parent; the published pseudocode uses the two matched gold nodes.
6. Old scripts hard-code paths and aggregation and do not guard zero matches.

These changes are substantive, so this repository does not silently mix legacy
behavior into the public default protocol.

## Sampling sensitivity of PE

Nearest-node PE depends on sampling along an otherwise identical continuous
curve. A test point at the midpoint of a 5-pixel gold edge has zero distance to
the correct polyline but 2.5-pixel distance to either endpoint, failing an
`epsilon = 2` node match.

An audit of three local ROAD examples found:

- gold median node spacing around 4.5–4.8 pixels;
- test median node spacing around 7.8–8.2 pixels;
- nearest-node match fraction below 2 pixels around 41–49%;
- point-to-edge fraction below 2 pixels around 66–74%;
- point-to-edge fraction below 5 pixels around 87–91%.

The coordinate systems were aligned: both covered the 1500×1500 image, used
`z = 0`, and ROAD used scale 1. Swapping x/y or applying 0.5×/2× scaling made
matching much worse. The low node-match fraction was mainly a sampling/protocol
issue, not a coordinate-scale issue.

For fair use of the public node protocol:

1. put gold and prediction in the same physical coordinate system;
2. resample graphs to a documented maximum spacing small relative to epsilon;
3. use the same resampling rule for every method;
4. report PE's matched-node fraction;
5. keep the strict `< epsilon` rule unless declaring a new protocol.

Point-to-edge distance is a reasonable geometric alternative, but it should be
published under an explicit name rather than substituted silently for PE.

## Aggregation, determinism, and numerical rules

- Macro PE gives every case equal weight and is the headline score.
- Pooled PE gives every matched node equal weight and is diagnostic.
- ABL is macro-averaged; JE is reported as mean per case and total count.
- Matching uses strict `< epsilon`; jump detection uses strict `>`.
- Equal-distance ties choose the first gold node in the SWC file.
- Invalid or cyclic SWC forests are rejected.
- No PE matches produce `null`, not NaN.
- Distances are computed after applying x/y/z scale.

## Primary references

- [NETracer repository](https://github.com/CSDLLab/NETracer)
- [ICCV 2025 paper page](https://openaccess.thecvf.com/content/ICCV2025/html/Liu_NETracer_A_Topology-Aware_Iterative_Tracing_Approach_for_Tubular_Structure_Extraction_ICCV_2025_paper.html)
- [Supplementary material](https://openaccess.thecvf.com/content/ICCV2025/supplemental/Liu_NETracer_A_Topology-Aware_ICCV_2025_supplemental.pdf)
