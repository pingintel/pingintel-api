help:
    @just --list

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

# Build the pypi package. Everything should already be committed to main before using.
publish version:
    python -c "import sys; sys.exit(0 if '{{ version }}'[0:1].isdigit() else sys.exit('Version must start with a number'))"
    git checkout main
    hatch version {{ version }}
    git add src/pingintel_api/__about__.py
    git commit -m "Bump version to v{{ version }}"
    git push origin main
    gh release create --target main --generate-notes v{{ version }}
    hatch build
    hatch publish

sovfixerapi *args:
    hatch run sovfixerapi {{ args }}

pingvisionapi *args:
    hatch run pingvisionapi {{ args }}

pingdataapi *args:
    hatch run pingdataapi {{ args }}

pingmapsapi *args:
    hatch run pingmapsapi {{ args }}
