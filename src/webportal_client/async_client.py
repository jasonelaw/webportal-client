import os
import httpx
from typing import Any, Dict, Optional, Union, List, Tuple


class WebPortalAsyncClient:
    """
    Asynchronous AQUARIUS WebPortal API Client (httpx)
    ------------------------------------------------------
    Features:
    • Async HTTP calls using httpx.AsyncClient
    • Basic Auth (username/password)
    • Cookie-based authentication (session cookies)
    • Lightweight parameter validation (required fields, enums, basic types)
    • Pythonic method naming
    • Raw dict/JSON responses
    • Endpoints implemented exactly in Swagger order
    """

    def __init__(
        self,
        base_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout

        # httpx async client with cookie support
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        self.client = httpx.AsyncClient(
            verify=verify_ssl,
            timeout=timeout,
            headers={"Accept": "application/json"},
            limits=limits,
        )

        # Basic Auth
        self.basic_auth = None
        if username and password:
            self.basic_auth = (username, password)

    # -------------------------------------------------------------
    # Authentication Helpers
    # -------------------------------------------------------------

    def _build_url(self, path: str) -> str:
        """Construct full API URL from a relative path."""
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    async def login_with_basic_auth(
        self, username: Optional[str] = None, password: Optional[str] = None
    ) -> None:
        """
        Enable Basic Auth for subsequent async requests.
        """
        if not username:
            username = os.environ["AQUARIUS_WEBPORTAL_USER"]
        if not password:
            password = os.environ["Aquarius_WEBPORTAL_PW"]

        self.basic_auth = (self.username, self.password)

    async def login_with_credentials_cookie(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        provider: str = "credentials",
    ) -> Dict[str, Any]:
        """
        POST /auth/{provider}
        Login using cookie-based authentication.
        """
        url = self._build_url(f"/auth/{provider}")

        if not username:
            username = os.environ["AQUARIUS_WEBPORTAL_USER"]
        if not password:
            password = os.environ["Aquarius_WEBPORTAL_PW"]

        payload = {
            "UserName": username,
            "Password": password,
            "RememberMe": False,
        }

        resp = await self.client.post(url, json=payload, auth=self.basic_auth)
        resp.raise_for_status()
        return resp.json()

    async def logout_credentials_cookie(
        self, provider: str = "credentials"
    ) -> Dict[str, Any]:
        """
        DELETE /auth/{provider}
        Logout of cookie-based session.
        """
        url = self._build_url(f"/auth/{provider}")
        resp = await self.client.delete(url, auth=self.basic_auth)
        resp.raise_for_status()
        return resp.json()

    # -------------------------------------------------------------
    # Unified async request handler
    # -------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Union[Dict[str, Any], List[Any], str]:
        """
        Internal async request wrapper using httpx.AsyncClient.
        """

        url = self._build_url(path)
        final_headers = {"Accept": "application/json"}
        if headers:
            final_headers.update(headers)

        resp = await self.client.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json,
            data=data,
            headers=final_headers,
            auth=self.basic_auth,
        )

        resp.raise_for_status()

        try:
            return resp.json()
        except ValueError:
            return resp.text

    # ----------------------------------------------------------------------
    # Parameter Validation Utilities (async client uses same logic)
    # ----------------------------------------------------------------------

    def _require(self, value: Any, name: str) -> None:
        """
        Validate that a required parameter is present and not empty.
        Raises ValueError if missing.
        """
        if value is None:
            raise ValueError(f"Missing required parameter: {name}")
        if isinstance(value, str) and value.strip() == "":
            raise ValueError(f"Parameter '{name}' must not be empty.")

    def _validate_enum(self, value: Any, name: str, enum: List[Any]) -> None:
        """
        Validate a parameter against an enum.
        """
        if value is None:
            return
        if value not in enum:
            raise ValueError(
                f"Invalid value for '{name}'. Must be one of: {enum}. Got: {value}"
            )

    def _validate_type(
        self, value: Any, name: str, expected: Union[type, Tuple[type, ...]]
    ) -> None:
        """
        Validate parameter type.
        """
        if value is None:
            return
        if not isinstance(value, expected):
            raise ValueError(
                f"Invalid type for '{name}'. Expected {expected}, got {type(value)}"
            )

    def _validate_list(
        self, value: Any, name: str, subtype: Optional[type] = None
    ) -> None:
        """
        Validate that value is a list, optionally checking subtype.
        """
        if value is None:
            return
        if not isinstance(value, list):
            raise ValueError(f"Parameter '{name}' must be a list.")
        if subtype:
            for element in value:
                if not isinstance(element, subtype):
                    raise ValueError(
                        f"Elements of '{name}' must be {subtype}, got {type(element)}"
                    )

    # ----------------------------------------------------------------------
    # ALERT STATES (ASYNC)
    # /alerts
    # /alerts/{alert}
    # ----------------------------------------------------------------------

    async def get_alerts(
        self,
        alert: Optional[List[str]] = None,
        state: Optional[List[str]] = None,
        sub_state: Optional[List[str]] = None,
        escalation_level: Optional[List[int]] = None,
        active: Optional[List[bool]] = None,
    ) -> Dict[str, Any]:
        """
        GET /alerts (async)
        """

        self._validate_list(alert, "alert", str)
        self._validate_list(state, "state", str)
        self._validate_list(sub_state, "sub_state", str)
        self._validate_list(escalation_level, "escalation_level", int)
        self._validate_list(active, "active", bool)

        params = {}
        if alert is not None:
            params["Alert"] = alert
        if state is not None:
            params["State"] = state
        if sub_state is not None:
            params["SubState"] = sub_state
        if escalation_level is not None:
            params["EscalationLevel"] = escalation_level
        if active is not None:
            params["Active"] = active

        return await self._request("GET", "/alerts", params=params)

    async def get_alerts_by_alert(
        self,
        alert: str,
        state: Optional[List[str]] = None,
        sub_state: Optional[List[str]] = None,
        escalation_level: Optional[List[int]] = None,
        active: Optional[List[bool]] = None,
    ) -> Dict[str, Any]:
        """
        GET /alerts/{alert} (async)
        """

        self._require(alert, "alert")
        self._validate_type(alert, "alert", str)

        self._validate_list(state, "state", str)
        self._validate_list(sub_state, "sub_state", str)
        self._validate_list(escalation_level, "escalation_level", int)
        self._validate_list(active, "active", bool)

        params = {}
        if state is not None:
            params["State"] = state
        if sub_state is not None:
            params["SubState"] = sub_state
        if escalation_level is not None:
            params["EscalationLevel"] = escalation_level
        if active is not None:
            params["Active"] = active

        path = f"/alerts/{alert}"
        return await self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # TIME-SERIES DATA EXPORT (ASYNC)
    # /export/data-set
    # ----------------------------------------------------------------------

    async def get_export_data_set(
        self,
        data_set: str,
        date_range: Optional[str] = None,
        calendar: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        interval: Optional[str] = None,
        step: Optional[int] = None,
        timezone: Optional[float] = None,
        unit: Optional[str] = None,
        round_data: Optional[bool] = None,
        include_grade_codes: Optional[bool] = None,
        include_qualifiers: Optional[bool] = None,
        include_approval_levels: Optional[bool] = None,
        include_interpolation_types: Optional[bool] = None,
        pre_processing: Optional[str] = None,
    ) -> Dict[str, Any]:

        self._require(data_set, "data_set")
        self._validate_type(data_set, "data_set", str)

        self._validate_enum(
            interval,
            "interval",
            ["PointsAsRecorded", "Minutely", "Hourly", "Daily", "Monthly", "Yearly"],
        )

        params = {"DataSet": data_set}

        if date_range is not None:
            params["DateRange"] = date_range
        if calendar is not None:
            params["Calendar"] = calendar
        if start_time is not None:
            params["StartTime"] = start_time
        if end_time is not None:
            params["EndTime"] = end_time
        if interval is not None:
            params["Interval"] = interval
        if step is not None:
            params["Step"] = step
        if timezone is not None:
            params["Timezone"] = timezone
        if pre_processing is not None:
            params["PreProcessing"] = pre_processing

        body = {}
        if unit is not None:
            body["Unit"] = unit
        if round_data is not None:
            body["RoundData"] = round_data
        if include_grade_codes is not None:
            body["IncludeGradeCodes"] = include_grade_codes
        if include_qualifiers is not None:
            body["IncludeQualifiers"] = include_qualifiers
        if include_approval_levels is not None:
            body["IncludeApprovalLevels"] = include_approval_levels
        if include_interpolation_types is not None:
            body["IncludeInterpolationTypes"] = include_interpolation_types

        return await self._request("GET", "/export/data-set", params=params, json=body)

    # ----------------------------------------------------------------------
    # /export/periodic-statistic (ASYNC)
    # ----------------------------------------------------------------------

    async def get_export_periodic_statistic(
        self,
        data_set: str,
        calendar: str,
        interval: str,
        statistic: str,
        date_range: Optional[str] = None,
        timezone: Optional[float] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        unit: Optional[str] = None,
        round_data: Optional[bool] = None,
        include_grade_codes: Optional[bool] = None,
        include_interpolation_types: Optional[bool] = None,
        pre_processing: Optional[str] = None,
    ) -> Dict[str, Any]:

        # Required
        for n, v in [
            ("data_set", data_set),
            ("calendar", calendar),
            ("interval", interval),
            ("statistic", statistic),
        ]:
            self._require(v, n)
            self._validate_type(v, n, str)

        self._validate_enum(interval, "interval", ["Daily", "Monthly", "Yearly"])

        params = {
            "DataSet": data_set,
            "Calendar": calendar,
            "Interval": interval,
            "Statistic": statistic,
        }

        if date_range is not None:
            params["DateRange"] = date_range
        if timezone is not None:
            params["Timezone"] = timezone
        if start_time is not None:
            params["StartTime"] = start_time
        if end_time is not None:
            params["EndTime"] = end_time
        if pre_processing is not None:
            params["PreProcessing"] = pre_processing

        body = {}
        if unit is not None:
            body["Unit"] = unit
        if round_data is not None:
            body["RoundData"] = round_data
        if include_grade_codes is not None:
            body["IncludeGradeCodes"] = include_grade_codes
        if include_interpolation_types is not None:
            body["IncludeInterpolationTypes"] = include_interpolation_types

        return await self._request(
            "GET", "/export/periodic-statistic", params=params, json=body
        )

    # ----------------------------------------------------------------------
    # /export/seasonal-statistic (ASYNC)
    # ----------------------------------------------------------------------

    async def get_export_seasonal_statistic(
        self,
        data_set: str,
        interval: str,
        statistic: str,
        reference_period: str,
        timezone: Optional[float] = None,
        unit: Optional[str] = None,
        round_data: Optional[bool] = None,
        include_grade_codes: Optional[bool] = None,
        include_interpolation_types: Optional[bool] = None,
        pre_processing: Optional[str] = None,
    ) -> Dict[str, Any]:

        for name, val in [
            ("data_set", data_set),
            ("interval", interval),
            ("statistic", statistic),
            ("reference_period", reference_period),
        ]:
            self._require(val, name)
            self._validate_type(val, name, str)

        self._validate_enum(interval, "interval", ["Daily", "Monthly", "Annual"])

        params = {
            "DataSet": data_set,
            "Interval": interval,
            "Statistic": statistic,
            "ReferencePeriod": reference_period,
        }

        if timezone is not None:
            params["Timezone"] = timezone
        if pre_processing is not None:
            params["PreProcessing"] = pre_processing

        body = {}
        if unit is not None:
            body["Unit"] = unit
        if round_data is not None:
            body["RoundData"] = round_data
        if include_grade_codes is not None:
            body["IncludeGradeCodes"] = include_grade_codes
        if include_interpolation_types is not None:
            body["IncludeInterpolationTypes"] = include_interpolation_types

        return await self._request(
            "GET", "/export/seasonal-statistic", params=params, json=body
        )

    # ----------------------------------------------------------------------
    # /export/percentile (ASYNC)
    # ----------------------------------------------------------------------

    async def get_export_percentile(
        self,
        data_set: str,
        reference_period: str,
        interval: str,
        percentile_value: float,
        unit: Optional[str] = None,
        timezone: Optional[float] = None,
        round_data: Optional[bool] = None,
        include_grade_codes: Optional[bool] = None,
        include_interpolation_types: Optional[bool] = None,
        pre_processing: Optional[str] = None,
    ) -> Dict[str, Any]:

        self._require(data_set, "data_set")
        self._require(reference_period, "reference_period")
        self._require(interval, "interval")
        self._require(percentile_value, "percentile_value")

        self._validate_type(data_set, "data_set", str)
        self._validate_type(reference_period, "reference_period", str)
        self._validate_type(interval, "interval", str)
        self._validate_type(percentile_value, "percentile_value", (int, float))

        self._validate_enum(interval, "interval", ["Daily", "Monthly", "Annual"])

        params = {
            "DataSet": data_set,
            "ReferencePeriod": reference_period,
            "Interval": interval,
            "PercentileValue": percentile_value,
        }

        if unit is not None:
            params["Unit"] = unit
        if timezone is not None:
            params["Timezone"] = timezone
        if pre_processing is not None:
            params["PreProcessing"] = pre_processing

        body = {}
        if round_data is not None:
            body["RoundData"] = round_data
        if include_grade_codes is not None:
            body["IncludeGradeCodes"] = include_grade_codes
        if include_interpolation_types is not None:
            body["IncludeInterpolationTypes"] = include_interpolation_types

        return await self._request(
            "GET", "/export/percentile", params=params, json=body
        )

    # ----------------------------------------------------------------------
    # TIME-SERIES BULK EXPORT (ASYNC)
    # /export/bulk
    # ----------------------------------------------------------------------

    async def export_bulk(
        self,
        date_range: Optional[str] = None,
        calendar: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        interval: Optional[str] = None,
        step: Optional[int] = None,
        timezone: Optional[float] = None,
        round_data: Optional[bool] = None,
        include_grade_codes: Optional[bool] = None,
        include_qualifiers: Optional[bool] = None,
        include_approval_levels: Optional[bool] = None,
        include_interpolation_types: Optional[bool] = None,
        datasets: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        POST /export/bulk (async)
        """

        self._validate_enum(
            interval,
            "interval",
            ["PointsAsRecorded", "Minutely", "Hourly", "Daily", "Monthly", "Yearly"],
        )

        # Validate datasets
        if datasets is not None:
            self._validate_list(datasets, "datasets", dict)
            for d in datasets:
                self._require(d.get("identifier"), "datasets.identifier")
                self._validate_type(d["identifier"], "datasets.identifier", str)

                if "calculation" in d:
                    self._validate_enum(
                        d["calculation"],
                        "datasets.calculation",
                        ["Aggregate", "Maximum", "Minimum", "Instantaneous"],
                    )
                if "unit" in d:
                    self._validate_type(d["unit"], "datasets.unit", str)

        body = {}

        if date_range is not None:
            body["DateRange"] = date_range
        if calendar is not None:
            body["Calendar"] = calendar
        if start_time is not None:
            body["StartTime"] = start_time
        if end_time is not None:
            body["EndTime"] = end_time
        if interval is not None:
            body["Interval"] = interval
        if step is not None:
            body["Step"] = step
        if timezone is not None:
            body["Timezone"] = timezone
        if round_data is not None:
            body["RoundData"] = round_data
        if include_grade_codes is not None:
            body["IncludeGradeCodes"] = include_grade_codes
        if include_qualifiers is not None:
            body["IncludeQualifiers"] = include_qualifiers
        if include_approval_levels is not None:
            body["IncludeApprovalLevels"] = include_approval_levels
        if include_interpolation_types is not None:
            body["IncludeInterpolationTypes"] = include_interpolation_types

        if datasets is not None:
            body["Datasets"] = datasets

        return await self._request("POST", "/export/bulk", json=body)

    # ----------------------------------------------------------------------
    # /export/time-aligned  (ASYNC)
    # ----------------------------------------------------------------------

    async def export_time_aligned(
        self,
        date_range: Optional[str] = None,
        calendar: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        interval: Optional[str] = None,
        step: Optional[int] = None,
        timezone: Optional[float] = None,
        round_data: Optional[bool] = None,
        include_grade_codes: Optional[bool] = None,
        include_qualifiers: Optional[bool] = None,
        include_approval_levels: Optional[bool] = None,
        include_interpolation_types: Optional[bool] = None,
        datasets: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:

        self._validate_enum(
            interval,
            "interval",
            ["PointsAsRecorded", "Minutely", "Hourly", "Daily", "Monthly", "Yearly"],
        )

        if datasets is not None:
            self._validate_list(datasets, "datasets", dict)
            for d in datasets:
                self._require(d.get("identifier"), "datasets.identifier")
                self._validate_type(d["identifier"], "datasets.identifier", str)

                if "calculation" in d:
                    self._validate_enum(
                        d["calculation"],
                        "datasets.calculation",
                        ["Aggregate", "Maximum", "Minimum", "Instantaneous"],
                    )
                if "unit" in d:
                    self._validate_type(d["unit"], "datasets.unit", str)

        body = {}

        if date_range is not None:
            body["DateRange"] = date_range
        if calendar is not None:
            body["Calendar"] = calendar
        if start_time is not None:
            body["StartTime"] = start_time
        if end_time is not None:
            body["EndTime"] = end_time
        if interval is not None:
            body["Interval"] = interval
        if step is not None:
            body["Step"] = step
        if timezone is not None:
            body["Timezone"] = timezone
        if round_data is not None:
            body["RoundData"] = round_data
        if include_grade_codes is not None:
            body["IncludeGradeCodes"] = include_grade_codes
        if include_qualifiers is not None:
            body["IncludeQualifiers"] = include_qualifiers
        if include_approval_levels is not None:
            body["IncludeApprovalLevels"] = include_approval_levels
        if include_interpolation_types is not None:
            body["IncludeInterpolationTypes"] = include_interpolation_types

        if datasets is not None:
            body["Datasets"] = datasets

        return await self._request("POST", "/export/time-aligned", json=body)

    # ----------------------------------------------------------------------
    # FILTERS (ASYNC)
    # /filters
    # ----------------------------------------------------------------------

    async def get_filters(self) -> Dict[str, Any]:
        """
        GET /filters (async)
        """
        return await self._request("GET", "/filters")

    # ----------------------------------------------------------------------
    # LATEST STATISTIC DEFINITIONS (ASYNC)
    # /statistics/latest
    # ----------------------------------------------------------------------

    async def get_latest_statistics(
        self,
        parameter: Optional[List[str]] = None,
        statistic: Optional[List[str]] = None,
        active: Optional[List[bool]] = None,
    ) -> Dict[str, Any]:
        """
        GET /statistics/latest (async)
        """

        self._validate_list(parameter, "parameter", str)
        self._validate_list(statistic, "statistic", str)
        self._validate_list(active, "active", bool)

        params = {}
        if parameter is not None:
            params["Parameter"] = parameter
        if statistic is not None:
            params["Statistic"] = statistic
        if active is not None:
            params["Active"] = active

        return await self._request("GET", "/statistics/latest", params=params)

    # ----------------------------------------------------------------------
    # /statistics/latest/{parameter} (ASYNC)
    # ----------------------------------------------------------------------

    async def get_latest_statistics_by_parameter(
        self,
        parameter: str,
        statistic: Optional[List[str]] = None,
        active: Optional[List[bool]] = None,
    ) -> Dict[str, Any]:
        """
        GET /statistics/latest/{parameter} (async)
        """

        self._require(parameter, "parameter")
        self._validate_type(parameter, "parameter", str)

        self._validate_list(statistic, "statistic", str)
        self._validate_list(active, "active", bool)

        params = {}
        if statistic is not None:
            params["Statistic"] = statistic
        if active is not None:
            params["Active"] = active

        path = f"/statistics/latest/{parameter}"
        return await self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # /statistics/latest/{parameter}/{statistic} (ASYNC)
    # ----------------------------------------------------------------------

    async def get_latest_statistic(
        self,
        parameter: str,
        statistic: str,
        active: Optional[List[bool]] = None,
    ) -> Dict[str, Any]:
        """
        GET /statistics/latest/{parameter}/{statistic} (async)
        """

        self._require(parameter, "parameter")
        self._require(statistic, "statistic")
        self._validate_type(parameter, "parameter", str)
        self._validate_type(statistic, "statistic", str)

        self._validate_list(active, "active", bool)

        params = {}
        if active is not None:
            params["Active"] = active

        path = f"/statistics/latest/{parameter}/{statistic}"
        return await self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # LATEST STATISTIC VALUES (ASYNC)
    # /statistic-values/latest
    # ----------------------------------------------------------------------

    async def get_latest_statistic_values(
        self,
        parameter: Optional[List[str]] = None,
        statistic: Optional[List[str]] = None,
        location: Optional[List[str]] = None,
        legend: Optional[List[str]] = None,
        use_gauge_legend: Optional[bool] = None,
        primary_or_first_only: Optional[bool] = None,
        use_one_platform_parameters: Optional[bool] = None,
    ) -> Dict[str, Any]:

        self._validate_list(parameter, "parameter", str)
        self._validate_list(statistic, "statistic", str)
        self._validate_list(location, "location", str)
        self._validate_list(legend, "legend", str)

        params = {}
        if parameter is not None:
            params["Parameter"] = parameter
        if statistic is not None:
            params["Statistic"] = statistic
        if location is not None:
            params["Location"] = location
        if legend is not None:
            params["Legend"] = legend
        if use_gauge_legend is not None:
            params["UseGaugeLegend"] = use_gauge_legend
        if primary_or_first_only is not None:
            params["PrimaryOrFirstOnly"] = primary_or_first_only
        if use_one_platform_parameters is not None:
            params["UseOnePlatformParameters"] = use_one_platform_parameters

        return await self._request("GET", "/statistic-values/latest", params=params)

    # ----------------------------------------------------------------------
    # /statistic-values/latest/{parameter}  (ASYNC)
    # ----------------------------------------------------------------------

    async def get_latest_statistic_values_by_parameter(
        self,
        parameter: str,
        statistic: Optional[List[str]] = None,
        location: Optional[List[str]] = None,
        legend: Optional[List[str]] = None,
        use_gauge_legend: Optional[bool] = None,
        primary_or_first_only: Optional[bool] = None,
        use_one_platform_parameters: Optional[bool] = None,
    ) -> Dict[str, Any]:

        self._require(parameter, "parameter")
        self._validate_type(parameter, "parameter", str)

        self._validate_list(statistic, "statistic", str)
        self._validate_list(location, "location", str)
        self._validate_list(legend, "legend", str)

        params = {}
        if statistic is not None:
            params["Statistic"] = statistic
        if location is not None:
            params["Location"] = location
        if legend is not None:
            params["Legend"] = legend
        if use_gauge_legend is not None:
            params["UseGaugeLegend"] = use_gauge_legend
        if primary_or_first_only is not None:
            params["PrimaryOrFirstOnly"] = primary_or_first_only
        if use_one_platform_parameters is not None:
            params["UseOnePlatformParameters"] = use_one_platform_parameters

        path = f"/statistic-values/latest/{parameter}"
        return await self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # /statistic-values/latest/{parameter}/{statistic} (ASYNC)
    # ----------------------------------------------------------------------

    async def get_latest_statistic_values_by_statistic(
        self,
        parameter: str,
        statistic: str,
        location: Optional[List[str]] = None,
        legend: Optional[List[str]] = None,
        use_gauge_legend: Optional[bool] = None,
        primary_or_first_only: Optional[bool] = None,
        use_one_platform_parameters: Optional[bool] = None,
    ) -> Dict[str, Any]:

        self._require(parameter, "parameter")
        self._require(statistic, "statistic")
        self._validate_type(parameter, "parameter", str)
        self._validate_type(statistic, "statistic", str)

        self._validate_list(location, "location", str)
        self._validate_list(legend, "legend", str)

        params = {}
        if location is not None:
            params["Location"] = location
        if legend is not None:
            params["Legend"] = legend
        if use_gauge_legend is not None:
            params["UseGaugeLegend"] = use_gauge_legend
        if primary_or_first_only is not None:
            params["PrimaryOrFirstOnly"] = primary_or_first_only
        if use_one_platform_parameters is not None:
            params["UseOnePlatformParameters"] = use_one_platform_parameters

        path = f"/statistic-values/latest/{parameter}/{statistic}"
        return await self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # LOCATION PARAMETER RANGE VALUES (ASYNC)
    # /location-parameter-range-values
    # ----------------------------------------------------------------------

    async def get_location_parameter_range_values(
        self,
        parameter_range: Optional[List[str]] = None,
        location: Optional[List[str]] = None,
    ) -> Dict[str, Any]:

        self._validate_list(parameter_range, "parameter_range", str)
        self._validate_list(location, "location", str)

        params = {}
        if parameter_range is not None:
            params["ParameterRange"] = parameter_range
        if location is not None:
            params["Location"] = location

        return await self._request(
            "GET", "/location-parameter-range-values", params=params
        )

    # ----------------------------------------------------------------------
    # /location-parameter-range-values/{parameterRange} (ASYNC)
    # ----------------------------------------------------------------------

    async def get_location_parameter_range_values_by_parameter_range(
        self,
        parameter_range: str,
        location: Optional[List[str]] = None,
    ) -> Dict[str, Any]:

        self._require(parameter_range, "parameter_range")
        self._validate_type(parameter_range, "parameter_range", str)
        self._validate_list(location, "location", str)

        params = {}
        if location is not None:
            params["Location"] = location

        path = f"/location-parameter-range-values/{parameter_range}"
        return await self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # /location-parameter-range-values/{parameterRange}/{location} (ASYNC, PUT)
    # ----------------------------------------------------------------------

    async def put_location_parameter_range_values_by_location(
        self,
        parameter_range: str,
        location: str,
        levels: Optional[List[Dict[str, Any]]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        self._require(parameter_range, "parameter_range")
        self._require(location, "location")
        self._validate_type(parameter_range, "parameter_range", str)
        self._validate_type(location, "location", str)

        # Validate levels (formData)
        if levels is not None:
            self._validate_list(levels, "levels", dict)
            for lvl in levels:
                self._require(lvl.get("number"), "levels.number")
                self._require(lvl.get("parameter"), "levels.parameter")
                self._require(lvl.get("value"), "levels.value")

                self._validate_type(lvl["number"], "levels.number", int)
                self._validate_type(lvl["parameter"], "levels.parameter", str)
                self._validate_type(lvl["value"], "levels.value", (int, float))

        final_body = {}
        if body is not None:
            self._validate_type(body, "body", dict)
            final_body.update(body)

        # FormData-style content: httpx will send it as form fields via "data"
        form_data = {}
        if levels is not None:
            form_data["Levels"] = levels

        path = f"/location-parameter-range-values/{parameter_range}/{location}"
        return await self._request("PUT", path, data=form_data, json=final_body)

    # ----------------------------------------------------------------------
    # LOCATIONS (ASYNC)
    # /locations
    # ----------------------------------------------------------------------

    async def get_locations(
        self,
        location: Optional[List[str]] = None,
        active: Optional[List[bool]] = None,
        one_platform_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        self._validate_list(location, "location", str)
        self._validate_list(active, "active", bool)
        if one_platform_id is not None:
            self._validate_type(one_platform_id, "one_platform_id", str)

        params = {}
        if location is not None:
            params["Location"] = location
        if active is not None:
            params["Active"] = active
        if one_platform_id is not None:
            params["OnePlatformId"] = one_platform_id

        return await self._request("GET", "/locations", params=params)

    # ----------------------------------------------------------------------
    # /locations/{location} (ASYNC)
    # ----------------------------------------------------------------------

    async def get_location(
        self,
        location: str,
        active: Optional[List[bool]] = None,
    ) -> Dict[str, Any]:

        self._require(location, "location")
        self._validate_type(location, "location", str)
        self._validate_list(active, "active", bool)

        params = {}
        if active is not None:
            params["Active"] = active

        path = f"/locations/{location}"
        return await self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # MAP ENDPOINTS (ASYNC)
    # /map/locations
    # ----------------------------------------------------------------------

    async def get_map_locations(
        self,
        use_secondary_coordinates: Optional[bool] = None,
        filter_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        params = {}
        if use_secondary_coordinates is not None:
            self._validate_type(
                use_secondary_coordinates, "use_secondary_coordinates", bool
            )
            params["UseSecondaryCoordinates"] = use_secondary_coordinates

        if filter_id is not None:
            self._validate_type(filter_id, "filter_id", str)
            params["FilterId"] = filter_id

        return await self._request("GET", "/map/locations", params=params)

    # ----------------------------------------------------------------------
    # /map/datasets/{parameter} (ASYNC)
    # ----------------------------------------------------------------------

    async def get_map_datasets_by_parameter(
        self,
        parameter: str,
        use_secondary_coordinates: Optional[bool] = None,
        filter_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        self._require(parameter, "parameter")
        self._validate_type(parameter, "parameter", str)

        params = {}
        if use_secondary_coordinates is not None:
            self._validate_type(
                use_secondary_coordinates, "use_secondary_coordinates", bool
            )
            params["UseSecondaryCoordinates"] = use_secondary_coordinates

        if filter_id is not None:
            self._validate_type(filter_id, "filter_id", str)
            params["FilterId"] = filter_id

        path = f"/map/datasets/{parameter}"
        return await self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # /map/statistics/latest/{parameter}/{statistic} (ASYNC)
    # ----------------------------------------------------------------------

    async def get_map_latest_statistics(
        self,
        parameter: str,
        statistic: str,
        use_secondary_coordinates: Optional[bool] = None,
        filter_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        self._require(parameter, "parameter")
        self._require(statistic, "statistic")
        self._validate_type(parameter, "parameter", str)
        self._validate_type(statistic, "statistic", str)

        params = {}
        if use_secondary_coordinates is not None:
            self._validate_type(
                use_secondary_coordinates, "use_secondary_coordinates", bool
            )
            params["UseSecondaryCoordinates"] = use_secondary_coordinates

        if filter_id is not None:
            self._validate_type(filter_id, "filter_id", str)
            params["FilterId"] = filter_id

        path = f"/map/statistics/latest/{parameter}/{statistic}"
        return await self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # /map/statistics/periodic/{parameter}/{statistic}/{interval}/{date} (ASYNC)
    # ----------------------------------------------------------------------

    async def get_map_periodic_statistics(
        self,
        parameter: str,
        statistic: str,
        interval: str,
        date: str,
        use_secondary_coordinates: Optional[bool] = None,
        filter_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        for name, val in [
            ("parameter", parameter),
            ("statistic", statistic),
            ("interval", interval),
            ("date", date),
        ]:
            self._require(val, name)
            self._validate_type(val, name, str)

        self._validate_enum(interval, "interval", ["Daily", "Monthly", "Yearly"])

        params = {}
        if use_secondary_coordinates is not None:
            self._validate_type(
                use_secondary_coordinates, "use_secondary_coordinates", bool
            )
            params["UseSecondaryCoordinates"] = use_secondary_coordinates

        if filter_id is not None:
            self._validate_type(filter_id, "filter_id", str)
            params["FilterId"] = filter_id

        path = f"/map/statistics/periodic/{parameter}/{statistic}/{interval}/{date}"
        return await self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # PARAMETER RANGE DEFINITIONS (ASYNC)
    # /parameter-ranges
    # ----------------------------------------------------------------------

    async def get_parameter_ranges(
        self,
        parameter_range: Optional[List[str]] = None,
    ) -> Dict[str, Any]:

        self._validate_list(parameter_range, "parameter_range", str)

        params = {}
        if parameter_range is not None:
            params["ParameterRange"] = parameter_range

        return await self._request("GET", "/parameter-ranges", params=params)

    # ----------------------------------------------------------------------
    # /parameter-ranges/{parameterRange} (ASYNC)
    # ----------------------------------------------------------------------

    async def get_parameter_range(
        self,
        parameter_range: str,
    ) -> Dict[str, Any]:

        self._require(parameter_range, "parameter_range")
        self._validate_type(parameter_range, "parameter_range", str)

        path = f"/parameter-ranges/{parameter_range}"
        return await self._request("GET", path)

    # ----------------------------------------------------------------------
    # SECURITY (ASYNC)
    # /security/tags   (PUT)
    # ----------------------------------------------------------------------

    async def put_tag_security(
        self,
        tag_security: Optional[List[Dict[str, Any]]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        PUT /security/tags (async)

        tag_security: list of { "name": str, "isDisplayed": bool }
        body: optional full PutTagSecurity model
        """

        if tag_security is not None:
            self._validate_list(tag_security, "tag_security", dict)
            for t in tag_security:
                self._require(t.get("name"), "tag_security.name")
                self._validate_type(t["name"], "tag_security.name", str)
                self._require(t.get("isDisplayed"), "tag_security.isDisplayed")
                self._validate_type(t["isDisplayed"], "tag_security.isDisplayed", bool)

        final_body = {}
        if body is not None:
            self._validate_type(body, "body", dict)
            final_body.update(body)

        if tag_security is not None:
            final_body["TagSecurity"] = tag_security

        return await self._request("PUT", "/security/tags", json=final_body)

    # ----------------------------------------------------------------------
    # API VERSION (ASYNC)
    # /version
    # ----------------------------------------------------------------------

    async def get_version(self) -> Dict[str, Any]:
        """
        GET /version (async)
        Returns AQUARIUS WebPortal version information.
        """
        return await self._request("GET", "/version")

    # ----------------------------------------------------------------------
    # DATA SET (ASYNC)
    # /data-set
    # ----------------------------------------------------------------------

    async def get_data_set(
        self,
        data_set: Optional[str] = None,
        one_platform_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        if data_set is not None:
            self._validate_type(data_set, "data_set", str)

        if one_platform_id is not None:
            self._validate_type(one_platform_id, "one_platform_id", str)

        params = {}
        if data_set is not None:
            params["DataSet"] = data_set
        if one_platform_id is not None:
            params["OnePlatformId"] = one_platform_id

        return await self._request("GET", "/data-set", params=params)

    # ----------------------------------------------------------------------
    # AUTHENTICATE (ASYNC)
    # /auth/{provider}  GET
    # ----------------------------------------------------------------------

    async def authenticate_provider_get(
        self,
        provider: str,
        user_name: Optional[str] = None,
        password: Optional[str] = None,
        remember_me: Optional[bool] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
        return_url: Optional[str] = None,
        error_view: Optional[str] = None,
        meta: Optional[str] = None,
    ) -> Dict[str, Any]:

        self._require(provider, "provider")
        self._validate_type(provider, "provider", str)

        params = {}
        if user_name is not None:
            params["UserName"] = user_name
        if password is not None:
            params["Password"] = password
        if remember_me is not None:
            params["RememberMe"] = remember_me
        if access_token is not None:
            params["AccessToken"] = access_token
        if access_token_secret is not None:
            params["AccessTokenSecret"] = access_token_secret
        if return_url is not None:
            params["ReturnUrl"] = return_url
        if error_view is not None:
            params["ErrorView"] = error_view
        if meta is not None:
            params["Meta"] = meta

        path = f"/auth/{provider}"
        return await self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # /auth/{provider}  POST (ASYNC)
    # ----------------------------------------------------------------------

    async def authenticate_provider_post(
        self,
        provider: str,
        user_name: Optional[str] = None,
        password: Optional[str] = None,
        remember_me: Optional[bool] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
        return_url: Optional[str] = None,
        error_view: Optional[str] = None,
        meta: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        self._require(provider, "provider")
        self._validate_type(provider, "provider", str)

        params = {}
        if user_name is not None:
            params["UserName"] = user_name
        if password is not None:
            params["Password"] = password
        if remember_me is not None:
            params["RememberMe"] = remember_me
        if access_token is not None:
            params["AccessToken"] = access_token
        if access_token_secret is not None:
            params["AccessTokenSecret"] = access_token_secret
        if return_url is not None:
            params["ReturnUrl"] = return_url
        if error_view is not None:
            params["ErrorView"] = error_view
        if meta is not None:
            params["Meta"] = meta

        final_body = {}
        if body is not None:
            self._validate_type(body, "body", dict)
            final_body.update(body)

        path = f"/auth/{provider}"
        return await self._request("POST", path, params=params, json=final_body)

    # ----------------------------------------------------------------------
    # /auth  GET (ASYNC)
    # ----------------------------------------------------------------------

    async def authenticate_get(
        self,
        provider: Optional[str] = None,
        user_name: Optional[str] = None,
        password: Optional[str] = None,
        remember_me: Optional[bool] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
        return_url: Optional[str] = None,
        error_view: Optional[str] = None,
        meta: Optional[str] = None,
    ) -> Dict[str, Any]:

        params = {}
        if provider is not None:
            params["provider"] = provider
        if user_name is not None:
            params["UserName"] = user_name
        if password is not None:
            params["Password"] = password
        if remember_me is not None:
            params["RememberMe"] = remember_me
        if access_token is not None:
            params["AccessToken"] = access_token
        if access_token_secret is not None:
            params["AccessTokenSecret"] = access_token_secret
        if return_url is not None:
            params["ReturnUrl"] = return_url
        if error_view is not None:
            params["ErrorView"] = error_view
        if meta is not None:
            params["Meta"] = meta

        return await self._request("GET", "/auth", params=params)

    # ----------------------------------------------------------------------
    # /auth  POST (ASYNC)
    # ----------------------------------------------------------------------

    async def authenticate_post(
        self,
        provider: Optional[str] = None,
        user_name: Optional[str] = None,
        password: Optional[str] = None,
        remember_me: Optional[bool] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
        return_url: Optional[str] = None,
        error_view: Optional[str] = None,
        meta: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        params = {}
        if provider is not None:
            params["provider"] = provider
        if user_name is not None:
            params["UserName"] = user_name
        if password is not None:
            params["Password"] = password
        if remember_me is not None:
            params["RememberMe"] = remember_me
        if access_token is not None:
            params["AccessToken"] = access_token
        if access_token_secret is not None:
            params["AccessTokenSecret"] = access_token_secret
        if return_url is not None:
            params["ReturnUrl"] = return_url
        if error_view is not None:
            params["ErrorView"] = error_view
        if meta is not None:
            params["Meta"] = meta

        final_body = {}
        if body is not None:
            self._validate_type(body, "body", dict)
            final_body.update(body)

        return await self._request("POST", "/auth", params=params, json=final_body)
