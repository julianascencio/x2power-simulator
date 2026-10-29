# Contributing

Keep changes focused on technical simulation, numerical methods and reproducible
examples. Install the development tools with `python -m pip install -e '.[dev,plots]'`.

For a new model or an equation change:

1. State the input/output boundary, units, reference conditions and assumptions.
2. Provide a hand-calculated reference or an independent published benchmark.
3. Test relevant conservation identities and limiting cases, including zero input
   and invalid parameters.
4. Add a minimal synthetic scenario and update the model documentation.
5. Keep optional analysis dependencies outside the core runtime.

Run these checks before submitting a pull request:

```bash
ruff check .
ruff format --check .
ty check src use_cases
pytest --cov=x2power --cov-report=term-missing
python -m build
```

Do not describe synthetic example parameters as validated performance. Preserve
input-schema compatibility or introduce a documented schema version change.
