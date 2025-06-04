# src/looplm/utils/readline_compatibility.py

import sys

if sys.platform == "win32":
    # On Windows, use pyreadline3
    pass
else:
    # On Unix/Linux/macOS, use gnureadline
    pass
