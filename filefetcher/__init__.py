# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
#  Purpose: pull GPS images
#   Author: Tom Parker
#
# -----------------------------------------------------------------------------
"""
filefetcher
=========

Pull daily GPS files

:license:
    CC0 1.0 Universal
    http://creativecommons.org/publicdomain/zero/1.0/
"""


import tomputils.util as tutil
from filefetcher.version import __version__

logger = tutil.setup_logging("filefetcher - errors")
__all__ = ["__version__"]
