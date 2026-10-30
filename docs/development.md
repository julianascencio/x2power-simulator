# Development and documentation

## Source layout

| Folder | Purpose |
| --- | --- |
| `src/x2power/methods/` | Conversion equations and operating profiles |
| `src/x2power/utilities/` | Validation, file handling, experiments and plotting |
| `use_cases/` | JSON scenarios and runnable analysis scripts |
| `use_cases/gallery/` | Worked scripts executed during documentation builds |
| `analysis/` | Offline source-backed workflows, assumptions and reference outputs |
| `docs/` | Sphinx configuration, guides and API reference |
| `tests/` | Physical reference cases, integration checks and plot verification |

See [CONTRIBUTING.md](https://github.com/julianascencio/x2power-simulator/blob/main/CONTRIBUTING.md)
for the requirements when adding or changing a model.

## Build the documentation locally

```bash
python -m pip install -e '.[docs]'
sphinx-build -W --keep-going -b html docs docs/_build/html
python -m http.server 8000 --directory docs/_build/html
```

Open `http://localhost:8000/`. The documentation uses Sphinx, the PyData theme,
MyST Markdown and Sphinx-Gallery. The gallery executes the example scripts,
captures their figures and produces downloadable Python files and notebooks.
API pages import the installed package, so rebuild after changing signatures or
docstrings. Warnings and failed examples make the documentation build fail.

Generated HTML, gallery pages and execution summaries are excluded from version
control. Edit the source examples in `use_cases/gallery/`, not `docs/gallery/`.

## GitHub Pages deployment

The `Documentation` GitHub Actions workflow builds on pull requests and pushes to
`main`. Pull requests only validate the documentation. Successful builds on `main`
upload a Pages artifact and deploy it to the `github-pages` environment.

The publishing source must be **GitHub Actions** under repository
**Settings → Pages → Build and deployment**. The site URL is
[julianascencio.github.io/x2power-simulator](https://julianascencio.github.io/x2power-simulator/).
The workflow can also be run manually from the Actions tab on `main`.

Deployment permissions are limited to the deployment job: `pages: write` and
`id-token: write`. Documentation builds use read-only repository access.

## Validation commands

```bash
python -m pip install -e '.[dev,plots,docs]'
ruff check .
ruff format --check .
ty check src use_cases analysis
pytest --cov=x2power --cov-report=term-missing
sphinx-build -W --keep-going -b html docs docs/_build/html
```


## Publishing a release

`.github/workflows/release.yml` uses the same token-based PyPI publishing pattern
as OrbitalPV. It builds the wheel and source distribution, checks package metadata,
runs lint/type/coverage checks, and verifies a dependency-free clean wheel install
before uploading the exact validated artifacts.

Configure `PYPI_API_TOKEN` as an Actions secret for this repository or its `pypi`
environment. Secrets from `orbital-pv` are not automatically available here. The
initial upload requires a PyPI token authorized to create `x2power-simulator`;
a token restricted to `orbital-pv` cannot publish this project. After the first
upload, use a token scoped to `x2power-simulator`. Never commit a token.

For subsequent versions:

1. Update the version in `pyproject.toml` and `src/x2power/__init__.py` together.
2. Merge the tested release changes into `main`.
3. Push a tag `v<version>` or publish a GitHub release with that tag. The workflow
   rejects tags that do not match the package version.
4. Confirm the PyPI upload job succeeds and install the version from PyPI in a
   fresh environment.

The workflow can also be run manually from `main` or a matching version tag.
The `.pypi-initial-release` marker triggers the first upload when merged into
`main`; ordinary code pushes do not publish packages. Existing filenames are
skipped to allow retrying a partial upload, but PyPI cannot replace an uploaded
file. Any changed distribution needs a new version.
