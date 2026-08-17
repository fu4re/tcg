"""Non-code data shipped inside the `tcg` package (importlib.resources anchor).

theory/patches/ghost.diff in the repo is the canonical, human-edited source;
this copy is what actually ships in a non-editable `pip install` (a
site-packages install has no theory/ tree on disk at all), so `tcg init`
reads it from here via importlib.resources rather than a path relative to
this file's location on disk.
"""
