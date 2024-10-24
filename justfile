help:
    @just --list

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

# Build the pypi package
build:
    hatch build

# Publish the pypi package
publish:
    hatch publish

sovfixerapi *args:
    hatch run sovfixerapi {{ args }}

pingradarapi *args:
    hatch run pingradarapi {{ args }}