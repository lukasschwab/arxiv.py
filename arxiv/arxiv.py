# flake8:noqa
from .api import *

import warnings
warnings.warn(
    "The 'arxiv.arxiv' module is deprecated, use 'arxiv.api' instead",
    DeprecationWarning,
    stacklevel=2
)
