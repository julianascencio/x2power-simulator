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
ty check src use_cases analysis
pytest --cov=x2power --cov-report=term-missing
python -m build
```

Do not describe synthetic example parameters as validated performance. Preserve
input-schema compatibility or introduce a documented schema version change.

## AI-assisted contribution policy

Most repository content is AI-generated under developer direction. ASVA Consulting
maintains the project, and developers and contributors remain responsible for the
scientific basis and correctness of their contributions.

- Select and cite the specific papers, technical reports or other real references
  that motivate a method or parameter convention.
- Distinguish literature-backed values from engineering assumptions and synthetic
  illustrative inputs. Do not attribute example defaults to a reference that does
  not provide them.
- Review AI-generated implementations for physical validity, units, numerical
  correctness, limiting cases and reproducibility.
- Add verification and independent validation evidence appropriate to the claimed
  model fidelity; passing tests alone does not establish empirical accuracy.
- Update the relevant model or example references when new literature influences
  the implementation. Keep validation limitations explicit in the documentation.

The intended workflow is developer-selected evidence, AI-assisted implementation,
human review, testing and progressive validation. AI-generated content may contain
errors or imperfect interpretations of the selected literature.
