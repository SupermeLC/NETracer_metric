# Contributing

Changes to metric behavior require more care than ordinary refactoring because
small threshold or matching changes can invalidate reported comparisons.

Please include:

1. a concise description of the mathematical/protocol change;
2. a source or rationale for the change;
3. tests covering boundary conditions and expected values;
4. an explicit note when historical scores will change;
5. updates to `README.md` and `docs/protocol-notes.md` when applicable.

Before opening a pull request:

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
netracer-metrics pair examples/synthetic/gold.swc examples/synthetic/test_jump.swc
```

Do not commit complete datasets, private paths, model checkpoints, or generated
evaluation outputs. Small redistributable examples should contain only what is
needed to test the software and must document their provenance.
