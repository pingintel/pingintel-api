# pingintel-api
Python-based API for Ping Data Technology products.

### Usage

To submit an SOV to Ping SOV Fixer and poll for completion:

```python
from pingintel_api import SOVFixerAPIClient

api_client = SOVFixerAPIClient()
api_client.fix_sov("test_sov.xlsx")
```

### API Documentation

For complete documentation on the REST API, please see https://api.sovfixer.com/docs/.