"""Sphinx documentation with the PyData theme and an executable example gallery."""

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # repository analysis modules used by the gallery
sys.path.insert(0, str(ROOT / "docs" / "_ext"))

with (ROOT / "pyproject.toml").open("rb") as source:
    metadata = tomllib.load(source)["project"]

project = "X2Power"
author = "ASVA Consulting and X2Power contributors"
copyright = "2026, ASVA Consulting and X2Power contributors"
release = metadata["version"]
version = release

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
    "sphinx.ext.githubpages",
    "sphinx_gallery.gen_gallery",
]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
root_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
myst_heading_anchors = 3
autosummary_generate = True
autodoc_typehints = "description"
autodoc_member_order = "bysource"
napoleon_google_docstring = True
napoleon_numpy_docstring = True

html_theme = "pydata_sphinx_theme"
html_title = "X2Power"
html_baseurl = "https://julianascencio.github.io/x2power-simulator/"
html_static_path = ["_static"]
html_css_files = ["x2power.css"]
html_show_sourcelink = False
html_theme_options = {
    "github_url": "https://github.com/julianascencio/x2power-simulator",
    "show_toc_level": 2,
    "show_prev_next": False,
    "navbar_align": "left",
}

sphinx_gallery_conf = {
    "examples_dirs": str(ROOT / "use_cases" / "gallery"),
    "gallery_dirs": "gallery",
    "filename_pattern": r"/plot_",
    "download_all_examples": False,
    "remove_config_comments": True,
    "abort_on_example_error": True,
    "image_scrapers": ("x2power_gallery.scrape_figures",),
    "capture_repr": (),
}
