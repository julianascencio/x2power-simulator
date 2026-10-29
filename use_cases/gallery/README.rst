Example gallery
===============

These self-contained examples execute during every clean documentation build.
Each page includes the Python source, a rendered figure and downloadable Python
and Jupyter files. All input values are synthetic and require calibration before
they can describe particular equipment.

Install the plotting extra before running the examples:

.. code-block:: bash

   python -m pip install -e '.[plots]'

Figures are available as the variable ``figure``. To export a figure from a script
or notebook, call ``save_figure(figure, "results/example.png")`` from
``x2power.utilities.plotting``.
