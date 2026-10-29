"""Capture X2Power's standalone Figure objects without using pyplot's global registry."""

from typing import Any
from weakref import WeakSet

from matplotlib.figure import Figure
from sphinx_gallery.scrapers import figure_rst

from x2power.utilities.plotting import save_figure


def scrape_figures(block: Any, block_vars: dict[str, Any], gallery_conf: dict[str, Any]) -> str:
    """Save each new figure once, using Sphinx-Gallery's generated image paths."""
    seen = block_vars.setdefault("x2power_seen_figures", WeakSet())
    images = []
    for value in block_vars["example_globals"].values():
        if isinstance(value, Figure) and value not in seen:
            path = next(block_vars["image_path_iterator"])
            save_figure(value, path, dpi=120)
            images.append(path)
            seen.add(value)
    if not images:
        return ""
    return figure_rst(images, gallery_conf["src_dir"], "X2Power simulation result")
