# maxdiff textconv (vendored from Ableton/maxdevtools, MIT)

Human-readable git diffs for `.maxpat` / `.gendsp` / `.amxd`. One-time setup:

    git config diff.maxpat.textconv "python3 tools/maxdiff/maxpat_textconv.py"
    git config diff.amxd.textconv  "python3 tools/maxdiff/amxd_textconv.py"

`.gitattributes` in the repo root routes the file types to these drivers.
