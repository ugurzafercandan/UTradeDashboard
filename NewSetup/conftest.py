"""Pytest bootstrap for NewSetup tests.

Running pytest from the repo root only puts ``NewSetup/tests`` on
sys.path; the ``newsetup`` and ``execution`` packages live one level up.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
