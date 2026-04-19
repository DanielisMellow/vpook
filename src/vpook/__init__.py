"""vpook package.

This package provides the runtime pieces for the local overlay service.
"""

import logging

__all__ = ["__version__"]

__version__ = "0.1.0"

logging.getLogger("vpook").addHandler(logging.NullHandler())
