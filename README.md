# pingintel-api

Python client library for API and commandline tools for Ping products.

### Setup

`pip install pingintel-api`

You will probably want to create a `~/.pingintel.ini` file, which can store your API keys. (They can also be provided in the environment, via `--auth-token` on the commandline, or passed as arguments):

Example `~/.pingintel_ini` file:

```
[sovfixer]
# use this by default
SOVFIXER_AUTH_TOKEN = abcdxxxx
# use _STG for staging environment. if not provided, fall back to SOVFIXER_AUTH_TOKEN.
SOVFIXER_AUTH_TOKEN_STG = efghxxxx
# use _DEV for staging environment. if not provided, fall back to SOVFIXER_AUTH_TOKEN.
SOVFIXER_AUTH_TOKEN_DEV = efghxxxx

[pingvision]
# use _DEV or _STG  versions as desired
PINGVISION_AUTH_TOKEN = abcdxxxx

[pingdata]
# use _DEV or _STG  versions as desired
PINGDATA_AUTH_TOKEN = abcdxxxx

[pingmaps]
# use _DEV or _STG  versions as desired
PINGMAPS_AUTH_TOKEN = abcdxxxx

```

### Usage

This package installs a number of commandline tools:

`sovfixerapi`
`pingvisionapi`
`pingdataapi`

These tools are thin wrappers around the client API libraries.

See the examples/ directory for some usage examples. For instance, to submit an SOV to Ping SOV Fixer and poll for completion:

```python
from pingintel_api import SOVFixerAPIClient

api_client = SOVFixerAPIClient()
api_client.fix_sov("test_sov.xlsx")
```

### API Documentation

#### pingvisionapi

```
Usage: pingvisionapi [OPTIONS] COMMAND [ARGS]...

Options:
  -e, --environment [prod|prodeu|staging|dev]
  -u, --api-url TEXT              Provide base url (instead of environment,
                                  primarily for debugging)
  --auth-token TEXT               Provide auth token via --auth-token or
                                  PINGVISION_AUTH_TOKEN environment variable.
  -v, --verbose                   Can be used multiple times. -v for INFO, -vv
                                  for DEBUG, -vvv for very DEBUG.
  --help                          Show this message and exit.

Commands:
  activity                  List submission activity.
  create                    Create new submission from file(s).
  download-document         Download document by document URL.
  get                       Get submission detail.
  list-submission-statuses  List submission statuses.
  list-teams                List teams.
```

### sovfixerapi

```
Usage: sovfixerapi [OPTIONS] COMMAND [ARGS]...

Options:
  -e, --environment [prod|prodeu|staging|dev]
  -u, --api-url TEXT              Provide base url (instead of environment,
                                  primarily for debugging)
  --auth-token TEXT               Provide auth token via --auth-token or
                                  SOVFIXER_AUTH_TOKEN environment variable.
  -v, --verbose                   Can be used multiple times. -v for INFO, -vv
                                  for DEBUG, -vvv for very DEBUG.
  --help                          Show this message and exit.

Commands:
  activity        List submission activity.
  check-progress  Check the progress of a submission.
  fix             Extract insurance information from file(s).
  get-output      Fetch or generate an output from a previous extraction.
```

#### pingdataapi

```
Usage: pingdataapi [OPTIONS] COMMAND [ARGS]...

Options:
  -e, --environment [prod|prodeu|staging|dev]
  -u, --api-url TEXT              Provide base url (instead of environment,
                                  primarily for debugging)
  --auth-token TEXT               Provide auth token via --auth-token or
                                  PINGDATA_AUTH_TOKEN environment variable.
  -v, --verbose                   Can be used multiple times. -v for INFO, -vv
                                  for DEBUG, -vvv for very DEBUG.
  -D, --delegate-to ORG_SHORT_NAME
                                  Delegate to another organization. Provide
                                  the 'short name' of the desired delegatee.
                                  Requires the `delegate` permission.
  --help                          Show this message and exit.

Commands:
  bulk-enhance  Request data about multiple addresses using async API.
  enhance       Request data synchronously about a single address.
```

For complete documentation on the REST API, please see https://docs.pingintel.com/.

### Contributing

`pingintel-api` uses `hatch` for pypi packaging and updates. Install it for your platform first.

1. Update the `__about__.py` file with the new version number.
2. `hatch build`: Create the necessary pypi packages.
3. Create a `~/.pypirc` file. It should look something like this:

   ```
   [distutils]
   index-servers = pypi testpypi

   [pypi]
   repository = https://upload.pypi.org/legacy/
   username = __token__
   password = <your pypi token here>
   ```

4. `hatch publish`: Push the new package(s) to pypi. (Note that you'll need a pypi account and to be a member of our organization for this step.)
