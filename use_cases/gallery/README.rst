Example gallery
===============

These examples execute during every clean documentation build. Each page includes
Python source, rendered figures and downloadable Python and Jupyter files.
Route and continuous-plant examples use synthetic inputs. The source-backed banana
analysis separates published observations from engineering and economic assumptions.
None of these examples establishes measured equipment performance.

Install the plotting extra before running the examples:

.. code-block:: bash

   python -m pip install -e '.[plots]'

The banana example imports the accompanying ``analysis`` package and pinned input
file, so run its downloads from a repository checkout. Other examples define their
inputs in the script. Each script names its figure variables. To export one, call
``save_figure(figure, "results/example.png")`` from ``x2power.utilities.plotting``,
substituting the appropriate figure variable.
