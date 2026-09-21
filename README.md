# NETracer Metric

[![Tests](https://github.com/SupermeLC/NETracer_metric/actions/workflows/tests.yml/badge.svg)](https://github.com/SupermeLC/NETracer_metric/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A small, auditable implementation of the three iterative tracing metrics
introduced in **NETracer: A Topology-Aware Iterative Tracing Approach for
Tubular Structure Extraction** (ICCV 2025):

| Metric | Measures | Direction | Needs gold graph? |
|---|---|---:|---:|
| **PE** — Position Error | local geometric accuracy | lower is better | yes |
| **ABL** — Average Branch Length | continuity of reconstructed branches | higher is better | no |
| **JE** — Jump Error | critical branch-jumping topology errors | lower is better | yes |

The package evaluates 2D or 3D rooted forests stored in standard SWC files. It
is independent of the NETracer training code and PyNeval.


## Installation

```bash
git clone https://github.com/SupermeLC/NETracer_metric.git
cd NETracer_metric
python -m pip install -e .
```

Only NumPy is required. SciPy provides faster nearest-neighbour queries for
large graphs:

```bash
python -m pip install -e ".[fast]"
```

Without SciPy, an exact bounded-memory NumPy implementation is used.

## Quick start

```bash
netracer-metrics pair gold.swc prediction.swc
```

Equivalent module invocation:

```bash
python -m netracer_metrics pair gold.swc prediction.swc
```

Typical JSON fields:

```json
{
  "PE": {
    "value": 0.82,
    "matched_nodes": 91,
    "total_test_nodes": 120,
    "matched_fraction": 0.758
  },
  "ABL": {
    "value": 74.4,
    "total_length": 2232.0,
    "branch_count": 30
  },
  "JE": {
    "value": 2,
    "eligible_edges": 87,
    "jump_test_node_ids": [42, 105]
  }
}
```

The additional counts make every denominator and failure case visible rather
than returning three opaque scalar values.

## Metric definitions

Let the gold graph be \(G_g\), the test graph be \(G_t\), and \(x(v)\) be the
physical coordinate of node \(v\). Defaults are matching threshold
\(\varepsilon=2\) and jump ratio \(\alpha=2\).

### Position Error (PE)

For each test node \(t\), find its nearest **gold node**:

\[
m(t)=\arg\min_{g\in G_g}\lVert x(t)-x(g)\rVert_2,
\qquad d_t=\lVert x(t)-x(m(t))\rVert_2.
\]

Only strict matches \(d_t < \varepsilon\) are retained. If
\(M=\{t\in G_t:d_t<\varepsilon\}\), then

\[
\mathrm{PE}=\frac{1}{|M|}\sum_{t\in M}d_t.
\]

PE asks: **when a traced node is close enough to the annotation, how accurately
is it positioned?** Lower is better.

Always inspect `matched_fraction = |M| / |G_t|`. Unmatched nodes do not enter the
PE mean, so PE alone does not measure coverage. If no node matches, PE is
reported as JSON `null`, never NaN or a silent division by zero.

> [!WARNING]
> Published PE uses node-to-node distance. It is sensitive to graph sampling.
> If gold nodes are farther apart than \(2\varepsilon\), a point on the correct
> gold edge can still fail to match either endpoint. Resample graphs to a
> documented spacing before comparison, or report node spacing and the matched
> fraction. Do not silently switch to point-to-edge distance under the same
> metric name.

### Average Branch Length (ABL)

The experiment-code definition recovered for ABL is

\[
\mathrm{ABL}=\frac{\sum_{(u,v)\in E_t}\lVert x(u)-x(v)\rVert_2}
{N_{\mathrm{root}}+N_{\mathrm{branch}}},
\]

where \(N_{\mathrm{branch}}\) counts test nodes with more than one child.
For a binary rooted forest, the denominator equals the number of terminal
branches.

ABL asks: **how long is a typical reconstructed branch before the reconstruction
terminates, breaks, or splits?** Higher is better.

ABL is reference-free and does not know whether a long branch is geometrically
or topologically correct. Interpret it together with PE and JE. The exact
denominator is returned as `branch_count`.

### Jump Error (JE)

For each non-root test node \(t\) whose nearest gold-node distance satisfies
\(d_t<\varepsilon\):

1. map \(t\) and its parent \(\rho(t)\) to nearest gold nodes
   \(m(t)\) and \(m(\rho(t))\);
2. compute their weighted shortest-path distance on the gold graph,
   \(d_{\mathrm{graph}}\);
3. compute their straight-line distance,
   \(d_{\mathrm{euclidean}}\);
4. count a jump when

\[
d_{\mathrm{graph}} > \alpha\, d_{\mathrm{euclidean}}.
\]

JE asks: **did a short predicted edge connect two locations that are spatially
near but topologically far apart on the correct graph?** This captures jumps
between adjacent roads, vessels, or neurites. Lower is better.

Gold nodes in disconnected components have infinite graph distance and count as
a jump. JE is a raw count, so comparisons must use the same cases and
preprocessing. The output includes eligible and total edge counts.

## Coordinate units and SWC input

SWC rows must contain at least seven columns:

```text
id type x y z radius parent
```

- node IDs must be unique;
- every non-root parent must exist;
- input must be an acyclic rooted forest;
- use `parent = -1` for roots;
- for 2D data, set `z = 0`.

Distances are expressed in the units of x/y/z. Gold and prediction must be in
the same coordinate system. For anisotropic voxels, apply physical spacing to
both graphs:

```bash
netracer-metrics pair gold.swc prediction.swc --scale 0.5 0.5 2.0
```

`--scale` multiplies x, y, and z respectively before any metric is computed.
It is not an alignment operation.

## Dataset evaluation

Create a UTF-8 CSV manifest. Paths can be absolute or relative to the manifest:

```csv
case_id,gold,test
sample_01,gold/sample_01.swc,pred/sample_01.swc
sample_02,gold/sample_02.swc,pred/sample_02.swc
```

```bash
netracer-metrics batch manifest.csv --output-dir results
```

Outputs:

- `per_case.csv`: PE, ABL, JE and all denominators for every case;
- `summary.json`: parameters and dataset-level aggregation.

Aggregation is explicit:

- `PE_macro`: arithmetic mean of valid per-case PE values;
- `PE_pooled`: all matched-node distances pooled across cases (diagnostic);
- `ABL_macro`: arithmetic mean of per-case ABL;
- `JE_mean`: arithmetic mean of per-case JE;
- `JE_total`: total jump count.

The paper-style headline values are `PE_macro`, `ABL_macro`, and `JE_mean`.

## Python API

```python
from netracer_metrics import evaluate_files

result = evaluate_files(
    "gold.swc",
    "prediction.swc",
    scale=(1.0, 1.0, 1.0),
    match_threshold=2.0,
    jump_ratio=2.0,
)

print("PE", result.pe.value, "matched", result.pe.matched_fraction)
print("ABL", result.abl.value)
print("JE", result.je.value, "jump nodes", result.je.jump_test_node_ids)
```

Lower-level functions are also public:

```python
from netracer_metrics import SWCGraph, average_branch_length, jump_error, position_error

gold = SWCGraph.read("gold.swc")
test = SWCGraph.read("prediction.swc")

pe = position_error(gold, test, match_threshold=2.0)
abl = average_branch_length(test)
je = jump_error(gold, test, match_threshold=2.0, jump_ratio=2.0)
```

## Included examples

Only small examples are included; this repository does **not** distribute any
full training or test dataset.

- `examples/synthetic/`: a two-edge construction with one obvious jump;
- `examples/road_crop/`: a tiny coordinate-only 128×128 crop from one ROAD
  case, translated to local coordinates. No source image or full annotation is
  included.

```bash
netracer-metrics pair examples/synthetic/gold.swc examples/synthetic/test_jump.swc

netracer-metrics batch examples/road_crop/manifest.csv --output-dir example-results
```

Sample data are provided only for software verification and API demonstration.
Obtain complete datasets from their original providers and follow their terms.

## Reproducibility notes

The old NETracer workspace and the published supplementary algorithms differ in
several important ways, including point-to-edge versus point-to-node PE and an
additional legacy JE cutoff. We do not hide those differences behind defaults.
Read [docs/protocol-notes.md](docs/protocol-notes.md) before comparing against
historical paper tables.

Nearest-node ties are resolved deterministically by choosing the gold node that
appears first in the SWC file. Threshold comparisons are strict (`<` for
matching and `>` for jump detection).

## Development and tests

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
```

The test suite covers PE threshold behavior, ABL denominator semantics, JE
detection, disconnected components, anisotropic scaling, deterministic ties,
invalid SWC references, and cycle rejection. GitHub Actions runs the suite on
Python 3.10–3.12.

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

A machine-readable citation record is provided in [CITATION.cff](CITATION.cff).

## License

Code is released under the [MIT License](LICENSE). Dataset terms are independent
of the code license; this repository contains no complete dataset.
