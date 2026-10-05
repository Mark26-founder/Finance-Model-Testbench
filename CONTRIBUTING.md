# Contributing

1. Create a Python 3.10+ virtual environment and install `.[dev]`.
2. Make a focused change within the currently authorized phase.
3. Add or update regression tests for changed behavior.
4. Run `python -m pytest -ra -v` and the documented benchmark where relevant.
5. Check for secrets, caches, `.pyc` files, temporary environments, and absolute-path output.
6. Keep financial rules explicit and preserve source-workbook immutability.

Do not add network services, LLM dependencies, dashboards, automated repair, or generic spreadsheet-auditing features without an approved scope change.
