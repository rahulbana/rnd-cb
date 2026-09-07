"""Enable ``python -m product_intel ...`` as an alias for the CLI.

Note: use the underscore import name (``product_intel``), not the distribution
name (``product-intel``); ``python -m`` never accepts hyphens. The installed
``product-intel`` console script remains the simplest entrypoint.
"""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
