from dotenv import load_dotenv
from webportal_client.client import WebPortalClient
from webportal_client.format_polars import to_polars

load_dotenv()

client = WebPortalClient("https://aquarius.portlandoregon.gov/api/v1")
client.login_with_credentials_cookie()
print(client.get_version())


locations = client.get_locations()
print(to_polars(locations))

datasets = client.get_data_set()
print(to_polars(datasets))

ts = client.get_export_data_set(
    data_set="Precip Increm.Primary@HYDRA-160", date_range="Years1"
)
print(to_polars(ts))

ml = client.get_map_locations()
print(to_polars(ml))

ta = client.export_time_aligned(
    date_range="Years1",
    datasets=[
        {"identifier": "Depth.Primary@BUR-27"},
        {"identifier": "Water Velocity.Primary@BUR-27"},
        {"identifier": "Flow.Primary@BUR-27"},
        {"identifier": "Precip Increm.Primary@HYDRA-160"},
    ],
)
print(to_polars(ta))
