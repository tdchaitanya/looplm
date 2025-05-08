# src/looplm/utils/readline_compatibility.py

import sys
if sys.platform == "win32":
    # On Windows, use pyreadline3
    import pyreadline3 as readline
else:
    # On Unix/Linux/macOS, use gnureadline
    import gnureadline as readline