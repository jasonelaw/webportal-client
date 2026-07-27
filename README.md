# Aquarius API Client

This package provides both synchronous and asynchronous Python clients for the AQUARIUS WebPortal API.

## Installation

Using pyproject.toml:

    pip install .

Or using setup.py:

    python setup.py install

## Usage
There are two clients in the package: a standard client that uses the `requests` module and an asynchronous client that uses the `httpx` module. I recommend using the standard client for most use cases. For downloading a very large amount of data for multiple 
time series, you can use the asynchronous client.

Both clients can be passed the username and password directly to the client constructor. They can also use usernames and passwords defined using environment variables. The examples below assume the user has a .env file in the current directory that has 
### Synchronous client

```python
from dotenv import load_dotenv
from webportal_client.client import WebPortalClient
load_dotenv()

client = WebPortalClient("https://aquarius.portlandoregon.gov/api/v1")#, username="user", password="password")
client.login_with_credentials_cookie()
client.get_version()
```

### Asynchronous Client
The asynchronous client can be used to access the API to perform a large group of long running API calls simultaneously. The client is limited to 10 concurrent requests for right now to avoid putting too much pressure on the server.

Here's an example of calling the `get_export_data_set` method to return several large data sets asyncrhonously. These data
sets are collected into a Polars DataFrame for fast data manipulation.
```python
from dotenv import load_dotenv
import asyncio
import polars as pl
from webportal_client.async_client import WebPortalAsyncClient

load_dotenv()

async def main():
    client = WebPortalAsyncClient("https://aquarius.portlandoregon.gov/api/v1")
    await client.login_with_credentials_cookie()
    datasets = [f"Precip Increm.Primary@HYDRA-{location}" for location in [111, 160, 193]]
    tasks = [client.get_export_data_set(data_set = dataset, date_range = "Years1") for dataset in datasets]
    result = await asyncio.gather(*tasks)
    return result
 
ts = asyncio.run(main())
tsdf = pl.DataFrame(ts, strict = False)
tsdf = tsdf.unnest("dataset")
tsdf = tsdf.unnest("timeRange")
tsdf = tsdf.explode("points").unnest("points")
print(tsdf)
```