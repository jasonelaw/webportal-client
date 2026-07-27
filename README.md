# Aquarius API Client

This package provides both synchronous and asynchronous Python clients for the AQUARIUS WebPortal API.

## Installation

Using pyproject.toml:

    git clone https://github.com/jasonelaw/webportal-client.git
    pip install .

If you want to convert the returned values as Polars or Pandas (not implemented yet) data frames, try:
    pip install .[polars]
    pip install .[pandas]


## Usage
There are two clients in the package: a standard client that uses the `requests` package and an asynchronous client that uses the `httpx` package. I recommend using the standard client for most use cases. For downloading a very large amount of data for multiple 
time series, you can use the asynchronous client.

Both clients can be passed the username and password directly to the client constructor. They can also use usernames and passwords defined using environment variables. The examples below assume the user has a .env file in the current directory that has environment variables defined for the `AQUARIUS_WEBPORTAL_URL`, `AQUARIUS_WEBPORTAL_USER`, `AQUARIUS_WEBPORTAL_PW` keys. These will be used to pass your username, password, and the url of the web service 
### Synchronous client

```python
from dotenv import load_dotenv
from webportal_client.client import WebPortalClient
from webportal_client.format_polars import to_polars
load_dotenv()

client = WebPortalClient()
# Or without environment variables: WebPortalClient("https://aquarius.portlandoregon.gov/api/v1", "my_username", "my_password")
client.login_with_credentials_cookie()
client.get_version()
df = to_polars(client.get_locations())
# Extended attributes for locations are pivoted by the to_polars function 
# so you can filter (this particular query only works in the City of Portand WebPortal implementation)
# df.filter(pl.col("manhole_hansen_id") == "ABQ942")
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
    client = WebPortalAsyncClient()
    # Or without environment variables: WebPortalClient("https://aquarius.portlandoregon.gov/api/v1", "my_username", "my_password")
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