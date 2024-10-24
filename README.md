# pingintel-api
Python-based API for Ping Data Technology products.

### Setup

`pip install pingintel-api`

You will probably also want to create a `~/.pingintel.ini` file, which can store your API keys.  (They can also be provided in the environment, via `--auth-token` on the commandline, or passed as arguments):

Example `~/.pingintel_ini` file:
```
[sovfixer]
# use this by default
SOVFIXER_AUTH_TOKEN = abcdxxxx
# use _STG for staging environment. if not provided, fall back to SOVFIXER_AUTH_TOKEN.
SOVFIXER_AUTH_TOKEN_STG = efghxxxx
# use _DEV for staging environment. if not provided, fall back to SOVFIXER_AUTH_TOKEN.
SOVFIXER_AUTH_TOKEN_DEV = efghxxxx

[pingradar]
# use _DEV or _STG  versions as desired
PINGRADAR_AUTH_TOKEN = abcdxxxx

[pingmaps]
# use _DEV or _STG  versions as desired
PINGMAPS_AUTH_TOKEN = abcdxxxx
```

### Usage

This package installs a number of commandline tools:

`sovfixerapi`
`pingradarapi`
`pingmapsapi`

These tools are thin wrappers around the client API libraries.

See the examples/ directory for some usage examples.  For instance, to submit an SOV to Ping SOV Fixer and poll for completion:

```python
from pingintel_api import SOVFixerAPIClient

api_client = SOVFixerAPIClient()
api_client.fix_sov("test_sov.xlsx")
```

### API Documentation

For complete documentation on the REST API, please see https://api.sovfixer.com/docs/.

### Release New Versions

`pingintel-api` uses `hatch` for pypi packaging and updates.  Install it for your platform first.

1) Update the `__about__.py` file with the new version number. 
2) `hatch build`: Create the necessary pypi packages.
3) Create a `~/.pypirc` file.  It should look something like this:

    ```
    [distutils]
    index-servers = pypi testpypi

    [pypi]
    repository = https://upload.pypi.org/legacy/
    username = __token__
    password = <your pypi token here>
    ```

4) `hatch publish`: Push the new package(s) to pypi.  (Note that you'll need a pypi account and to be a member of our organization for this step.)