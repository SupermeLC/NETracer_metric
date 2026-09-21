# NETracer Metric

[![Tests](https://github.com/SupermeLC/NETracer_metric/actions/workflows/tests.yml/badge.svg)](https://github.com/SupermeLC/NETracer_metric/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A small standalone implementation of the three tracing metrics introduced in
**NETracer: A Topology-Aware Iterative Tracing Approach for Tubular Structure
Extraction** (ICCV 2025).

| Metric | What it measures | Better |
|---|---|---:|
| **PE** — Position Error | position accuracy of matched nodes | lower |
| **ABL** — Average Branch Length | continuity of predicted branches | higher |
| **JE** — Jump Error | connections that jump between nearby branches | lower |

The input is a gold/reference SWC file and a predicted SWC file. ABL uses only
the prediction; PE and JE compare the prediction with the gold graph.

## Installation

```bash
git clone https://github.com/SupermeLC/NETracer_metric.git
cd NETracer_metric
python -m pip install -e .
```

NumPy is the only required dependency. For faster evaluation of large graphs,
install the optional SciPy backend:

```bash
python -m pip install -e ".[fast]"
```

## Quick start

### Python

```python
from netracer_metrics import evaluate_files

result = evaluate_files(
    "examples/road_crop/gold.swc",
    "examples/road_crop/prediction.swc",
)

print(f"PE: {result.pe.value:.3f}")
print(f"Matched fraction: {result.pe.matched_fraction:.3f}")
print(f"ABL: {result.abl.value:.3f}")
print(f"JE: {result.je.value}")
```

Expected output:

```text
PE: 1.177
Matched fraction: 0.574
ABL: 47.416
JE: 0
```

Replace the two example paths with your own files:

```python
result = evaluate_files("gold.swc", "prediction.swc")
```

The default node-matching threshold is 2 coordinate units. It can be changed
with `match_threshold`, for example:

```python
result = evaluate_files(
    "gold.swc",
    "prediction.swc",
    match_threshold=3.0,
    jump_ratio=2.0,
)
```

### Command line

The same example can be run without writing Python code:

```bash
python -m netracer_metrics pair \
  examples/road_crop/gold.swc \
  examples/road_crop/prediction.swc
```

The command returns JSON containing the three scores and useful counts. The
important values for this example are:

```json
{
  "PE": {
    "value": 1.1770603268970405,
    "matched_nodes": 35,
    "total_test_nodes": 61,
    "matched_fraction": 0.5737704918032787
  },
  "ABL": {
    "value": 47.416375175897066
  },
  "JE": {
    "value": 0
  }
}
```

## Metric definitions

### PE — Position Error

For every predicted node, PE finds the nearest gold node. A node is considered
matched when the distance is smaller than the matching threshold (2 by
default). PE is the average distance of the matched nodes.

Lower PE means better positional accuracy. Always report `matched_fraction`
together with PE: unmatched nodes are not included in the PE average, so a low
PE alone does not mean that the reconstruction has good coverage.

The published metric uses **node-to-node** distance. Its value therefore also
depends on how densely the SWC graphs are sampled.

### ABL — Average Branch Length

ABL divides the total length of the predicted graph by its number of branches.
A branch ends when the trace terminates or reaches a junction.

Higher ABL generally means that the reconstruction is more continuous. ABL
does not use the gold graph, so it cannot tell whether a long branch follows
the correct structure. It should be interpreted together with PE and JE.

### JE — Jump Error

JE examines every predicted parent-child edge. The two endpoints are mapped to
the gold graph. If they are close in space but far apart along the gold graph,
the predicted edge has probably jumped from one nearby branch to another and
is counted as one jump error.

Lower JE is better. JE is a count, so results should be compared on the same
set of cases with the same preprocessing.

## Input requirements

Each SWC row must contain at least:

```text
id type x y z radius parent
```

Gold and prediction must use the **same coordinate system and units**. For 2D
data, set `z` to 0. Node IDs must be unique, every non-root parent must exist,
and roots must use `parent = -1`.

For anisotropic voxel data, apply the same physical scale to both files:

```python
result = evaluate_files(
    "gold.swc",
    "prediction.swc",
    scale=(0.5, 0.5, 2.0),
)
```

`scale` multiplies x, y, and z before evaluation; it does not align two graphs.

## Evaluating multiple cases (optional)

For a dataset, create a CSV file that lists one gold/prediction pair per row:

```csv
case_id,gold,test
sample_01,gold/sample_01.swc,pred/sample_01.swc
sample_02,gold/sample_02.swc,pred/sample_02.swc
```

Run:

```bash
python -m netracer_metrics batch manifest.csv --output-dir results
```

This writes `per_case.csv` with the result for every sample and `summary.json`
with dataset-level averages.

## Examples and reproducibility

The repository contains only two small examples:

- `examples/synthetic/`: a minimal graph with one deliberate jump;
- `examples/road_crop/`: a coordinate-only 128 x 128 crop from one ROAD case.

No image, full annotation, or complete dataset is distributed.

This implementation follows the algorithms in the published supplementary
material. Some old NETracer experiment scripts used different PE and JE rules.
See [protocol notes](docs/protocol-notes.md) before comparing these results with
historical experiment tables.

## Tests

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the same tests on Python 3.10, 3.11, and 3.12.

## Citation

```bibtex
@inproceedings{liu2025netracer,
  title     = {NETracer: A Topology-Aware Iterative Tracing Approach for Tubular Structure Extraction},
  author    = {Liu, Chao and Jiang, Yangbo and Zheng, Nenggan},
  booktitle = {Proceedings of the IEEE/CVF International Conference on Computer Vision},
  pages     = {20593--20602},
  year      = {2025}
}
```

- [Official NETracer repository](https://github.com/CSDLLab/NETracer)
- [ICCV 2025 paper and supplementary material](https://openaccess.thecvf.com/content/ICCV2025/html/Liu_NETracer_A_Topology-Aware_Iterative_Tracing_Approach_for_Tubular_Structure_Extraction_ICCV_2025_paper.html)

## License

Code is released under the [MIT License](LICENSE). Dataset terms are independent
of the code license.
