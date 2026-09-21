# Tiny ROAD coordinate example

This directory contains a coordinate-only crop for checking the batch interface
on a realistic graph shape.

- source case: ROAD-13 from the NETracer experiment workspace;
- crop in original coordinates: `x=[1344,1472), y=[320,448)`;
- coordinates were translated so the crop starts at `(0, 0)`;
- graph edges crossing the crop boundary become roots;
- 78 gold nodes and 61 prediction nodes;
- no image, complete annotation, or full-dataset file is included.

Run from the repository root:

```bash
netracer-metrics batch examples/road_crop/manifest.csv --output-dir example-results
```

Expected default summary (minor last-digit floating-point differences are
acceptable):

```text
PE_macro = 1.1770603269  (35 / 61 test nodes matched)
ABL_macro = 47.4163751759
JE_mean = 0.0
```

This sample is for software verification only. Obtain the complete dataset from
its original provider and follow the applicable data terms.
