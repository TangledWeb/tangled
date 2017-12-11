import os
import sys

if 'tangled' not in sys.modules:
    sys.path.insert(0, os.path.dirname(__file__))

from tangled.commands import *
