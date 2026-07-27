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

    if "datasets" in response:
        df = pl.DataFrame(response["datasets"], strict=False)

    ts_keys = {"dataset", "timeRange", "numPoints", "points"}
    if ts_keys <= response.keys():
        df = pl.DataFrame(
            {k: response[k] for k in ts_keys if k in response}, strict=False
        )
        df = df.unnest("dataset")
        df = df.unnest("timeRange")
        df = df.unnest("points")

    return df
