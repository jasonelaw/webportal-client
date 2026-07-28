try:
    import polars as pl
except ImportError:
    pl = None


def to_polars(response):
    """
    Convert dictionary returned by WebPortal API into a Polars DataFrame

    :param response: A dict returned by one of the client methods
    """
    if pl is None:
        raise RuntimeError(
            "Polars is required for this feature. Install it using 'pip install polars'."
        )

    if "locations" in response:
        df = pl.DataFrame(response["locations"], strict=False)
        ea = (
            df.select(["id", "extendedAttributes"])
            .rename({"id": "locationId"})
            .explode("extendedAttributes")
            .unnest("extendedAttributes")
            .pivot(index="locationId", on="name", values="value")
        )
        df = df.drop("extendedAttributes").join(ea, left_on="id", right_on="locationId")

    if "datasets" in response:
        df = pl.DataFrame(response["datasets"], strict=False)

    ts_keys = {"dataset", "timeRange", "numPoints", "points"}
    if ts_keys <= response.keys():
        df = pl.DataFrame(
            {k: response[k] for k in ts_keys if k in response}, strict=False
        )
        df = df.unnest("dataset").unnest("timeRange").unnest("points")

    geojson_keys = {"type", "features"}
    if geojson_keys <= response.keys():
        df = pl.DataFrame(response["features"])
        df = df.unnest("properties")

    if "latestStatisticValues" in response:
        df = pl.DataFrame(response["latestStatisticValues"])
        df = df.unnest("statistic", separator="_")

    return df
