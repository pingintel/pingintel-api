help:
    @just --list

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]


# Build the pypi package
publish version:
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