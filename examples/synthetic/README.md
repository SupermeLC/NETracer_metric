# Synthetic jump example

The gold graph follows three sides of a thin rectangle. Its endpoints are only
one unit apart in Euclidean space but 21 units apart along the graph. The test
graph connects those endpoints directly, so JE detects one branch jump.

Run:

```bash
netracer-metrics pair gold.swc test_jump.swc
```

Expected headline values with default parameters:

```text
PE  = 0.0
ABL = 1.0
JE  = 1
```
