import requests
import os
from requests.auth import HTTPBasicAuth
from typing import Any, Dict, Optional, Union, List, Tuple


class WebPortalClient:
    """
    Synchronous AQUARIUS WebPortal API Client
    ------------------------------------------------------
    Features:
    • Basic Auth (username/password)
    • Cookie-based authentication (POST /auth or /auth/{provider})
    • Lightweight parameter validation (required fields, enums, basic types)
    • Pythonic method naming
    • Raw JSON/dict responses (no typed models)
    • Endpoints implemented in the exact order they appear in Swagger
    """

    def __init__(
        self,
        base_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        """
        Initialize the AQUARIUS API Client.

        base_url: e.g., "https://aquarius.portlandoregon.gov/api/v1"
        username/password: optional; used for Basic Auth if provided
        timeout: request timeout in seconds
        verify_ssl: SSL certificate verification
        """

        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # session for cookie-based auth + persistent headers
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({"Accept": "application/json"})

        # If basic authentication is provided, store it
        self.basic_auth = None
        if username and password:
            self.basic_auth = HTTPBasicAuth(username, password)

    # -------------------------------------------------------------
    # Authentication Helpers
    # -------------------------------------------------------------

    def _build_url(self, path: str) -> str:
        """Construct full API URL from a path."""
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def login_with_basic_auth(
        self, username: Optional[str] = None, password: Optional[str] = None
    ) -> None:
        """
        Enables Basic Auth for all subsequent requests.
        Only works if username/password were provided at init.
        """

        self.username = username or os.getenv("AQUARIUS_WEBPORTAL_USER")
        self.password = password or os.getenv("AQUARIUS_WEBPORTAL_PW")

        if not self.username or not self.password:
            raise ValueError(
                (
                    "WebPortal username and password must be provided "
                    "or set as AQUARIUS_WEBPORTAL_USER and AQUARIUS_WEBPORTAL_PW environment keys"
                )
            )
        self.basic_auth = HTTPBasicAuth(self.username, self.password)

    def login_with_credentials_cookie(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        provider: str = "credentials",
    ) -> Dict[str, Any]:
        """
        POST /auth/{provider} or POST /auth
        Logs in using WebPortal credentials and stores session cookies.

        Returns JSON response from the server.
        """

        url = self._build_url(f"/auth/{provider}")
        username = username or os.getenv("AQUARIUS_WEBPORTAL_USER")
        password = password or os.getenv("AQUARIUS_WEBPORTAL_PW")

        if not username or not password:
            raise ValueError(
                (
                    "WebPortal username and password must be provided "
                    "or set as AQUARIUS_WEBPORTAL_USER and AQUARIUS_WEBPORTAL_PW environment keys"
                )
            )

        payload = {
            "UserName": username,
            "Password": password,
            "RememberMe": False,
        }

        resp = self.session.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def logout_credentials_cookie(
        self, provider: str = "credentials"
    ) -> Dict[str, Any]:
        """
        DELETE /auth/{provider} — logs out a cookie-auth session.
        """
        url = self._build_url(f"/auth/{provider}")
        resp = self.session.delete(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # Unified request handler ---------------------------------------------------

    def _request(
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
        Internal unified request handler:
        • Basic Auth or cookie session
        • JSON parsing
        • Error handling
        """

        url = self._build_url(path)
        hdrs = {"Accept": "application/json"}
        if headers:
            hdrs.update(headers)

        resp = self.session.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json,
            data=data,
            auth=self.basic_auth,
            timeout=self.timeout,
            headers=hdrs,
        )

        # Raise exceptions for non-200 responses
        resp.raise_for_status()

        # Try JSON, otherwise return text
        try:
            return resp.json()
        except ValueError:
            return resp.text

    # ----------------------------------------------------------------------
    # Parameter Validation Utilities
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
    # TIME-SERIES DATA EXPORT
    # /export/data-set
    # ----------------------------------------------------------------------

    def get_export_data_set(
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
        """
        GET /export/data-set
        """

        # Required
        self._require(data_set, "data_set")
        self._validate_type(data_set, "data_set", str)

        # Enums
        self._validate_enum(
            interval,
            "interval",
            ["PointsAsRecorded", "Minutely", "Hourly", "Daily", "Monthly", "Yearly"],
        )

        # Build query params
        params = {
            "DataSet": data_set,
        }
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

        # Body fields (this endpoint mixes query and body)
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

        return self._request("GET", "/export/data-set", params=params, json=body)

    # ----------------------------------------------------------------------
    # /export/periodic-statistic
    # ----------------------------------------------------------------------

    def get_export_periodic_statistic(
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
        """
        GET /export/periodic-statistic
        """

        # Required
        for param_name, param_value in [
            ("data_set", data_set),
            ("calendar", calendar),
            ("interval", interval),
            ("statistic", statistic),
        ]:
            self._require(param_value, param_name)
            self._validate_type(param_value, param_name, str)

        # Enum validation
        self._validate_enum(interval, "interval", ["Daily", "Monthly", "Yearly"])

        # Query params
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

        # Body params
        body = {}
        if unit is not None:
            body["Unit"] = unit
        if round_data is not None:
            body["RoundData"] = round_data
        if include_grade_codes is not None:
            body["IncludeGradeCodes"] = include_grade_codes
        if include_interpolation_types is not None:
            body["IncludeInterpolationTypes"] = include_interpolation_types

        return self._request(
            "GET", "/export/periodic-statistic", params=params, json=body
        )

    # ----------------------------------------------------------------------
    # /export/seasonal-statistic
    # ----------------------------------------------------------------------

    def get_export_seasonal_statistic(
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
        """
        GET /export/seasonal-statistic
        """

        required_params = [
            ("data_set", data_set),
            ("interval", interval),
            ("statistic", statistic),
            ("reference_period", reference_period),
        ]
        for name, val in required_params:
            self._require(val, name)
            self._validate_type(val, name, str)

        # Enum
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

        return self._request(
            "GET", "/export/seasonal-statistic", params=params, json=body
        )

    # ----------------------------------------------------------------------
    # /export/percentile
    # ----------------------------------------------------------------------

    def get_export_percentile(
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
        """
        GET /export/percentile
        """

        # Required
        for name, val in [
            ("data_set", data_set),
            ("reference_period", reference_period),
            ("interval", interval),
            ("percentile_value", percentile_value),
        ]:
            self._require(val, name)

        self._validate_type(data_set, "data_set", str)
        self._validate_type(reference_period, "reference_period", str)
        self._validate_type(interval, "interval", str)
        self._validate_type(percentile_value, "percentile_value", (int, float))

        # Enum
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

        return self._request("GET", "/export/percentile", params=params, json=body)

    # ----------------------------------------------------------------------
    # TIME-SERIES BULK EXPORT
    # /export/bulk  (POST)
    # ----------------------------------------------------------------------

    def export_bulk(
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
        POST /export/bulk
        Export multiple data sets at once.

        datasets is a list of { "identifier": str, "calculation": str?, "unit": str? }
        """

        # Enum validation
        self._validate_enum(
            interval,
            "interval",
            ["PointsAsRecorded", "Minutely", "Hourly", "Daily", "Monthly", "Yearly"],
        )

        # Validate dataset list
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

        return self._request("POST", "/export/bulk", json=body)

    # ----------------------------------------------------------------------
    # /export/time-aligned  (POST)
    # ----------------------------------------------------------------------

    def export_time_aligned(
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
        POST /export/time-aligned
        Export multiple datasets aligned on timestamp.
        """

        # Enum validation
        self._validate_enum(
            interval,
            "interval",
            ["PointsAsRecorded", "Minutely", "Hourly", "Daily", "Monthly", "Yearly"],
        )

        # Validate dataset list
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

        return self._request("POST", "/export/time-aligned", json=body)

    # ----------------------------------------------------------------------
    # FILTERS
    # /filters
    # ----------------------------------------------------------------------

    def get_filters(self) -> Dict[str, Any]:
        """
        GET /filters
        Gets all Filters (used for GeoJSON map endpoints).
        """
        return self._request("GET", "/filters")

    # ----------------------------------------------------------------------
    # LATEST STATISTIC DEFINITIONS
    # /statistics/latest
    # ----------------------------------------------------------------------

    def get_latest_statistics(
        self,
        parameter: Optional[List[str]] = None,
        statistic: Optional[List[str]] = None,
        active: Optional[List[bool]] = None,
    ) -> Dict[str, Any]:
        """
        GET /statistics/latest
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

        return self._request("GET", "/statistics/latest", params=params)

    # ----------------------------------------------------------------------
    # /statistics/latest/{parameter}
    # ----------------------------------------------------------------------

    def get_latest_statistics_by_parameter(
        self,
        parameter: str,
        statistic: Optional[List[str]] = None,
        active: Optional[List[bool]] = None,
    ) -> Dict[str, Any]:
        """
        GET /statistics/latest/{parameter}
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
        return self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # /statistics/latest/{parameter}/{statistic}
    # ----------------------------------------------------------------------

    def get_latest_statistic(
        self,
        parameter: str,
        statistic: str,
        active: Optional[List[bool]] = None,
    ) -> Dict[str, Any]:
        """
        GET /statistics/latest/{parameter}/{statistic}
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
        return self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # LATEST STATISTIC VALUES
    # /statistic-values/latest
    # ----------------------------------------------------------------------

    def get_latest_statistic_values(
        self,
        parameter: Optional[List[str]] = None,
        statistic: Optional[List[str]] = None,
        location: Optional[List[str]] = None,
        legend: Optional[List[str]] = None,
        use_gauge_legend: Optional[bool] = None,
        primary_or_first_only: Optional[bool] = None,
        use_one_platform_parameters: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        GET /statistic-values/latest
        """

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

        return self._request("GET", "/statistic-values/latest", params=params)

    # ----------------------------------------------------------------------
    # /statistic-values/latest/{parameter}
    # ----------------------------------------------------------------------

    def get_latest_statistic_values_by_parameter(
        self,
        parameter: str,
        statistic: Optional[List[str]] = None,
        location: Optional[List[str]] = None,
        legend: Optional[List[str]] = None,
        use_gauge_legend: Optional[bool] = None,
        primary_or_first_only: Optional[bool] = None,
        use_one_platform_parameters: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        GET /statistic-values/latest/{parameter}
        """

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
        return self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # /statistic-values/latest/{parameter}/{statistic}
    # ----------------------------------------------------------------------

    def get_latest_statistic_values_by_statistic(
        self,
        parameter: str,
        statistic: str,
        location: Optional[List[str]] = None,
        legend: Optional[List[str]] = None,
        use_gauge_legend: Optional[bool] = None,
        primary_or_first_only: Optional[bool] = None,
        use_one_platform_parameters: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        GET /statistic-values/latest/{parameter}/{statistic}
        """

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
        return self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # LOCATION PARAMETER RANGE VALUES
    # /location-parameter-range-values
    # ----------------------------------------------------------------------

    def get_location_parameter_range_values(
        self,
        parameter_range: Optional[List[str]] = None,
        location: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        GET /location-parameter-range-values
        """

        self._validate_list(parameter_range, "parameter_range", str)
        self._validate_list(location, "location", str)

        params = {}
        if parameter_range is not None:
            params["ParameterRange"] = parameter_range
        if location is not None:
            params["Location"] = location

        return self._request("GET", "/location-parameter-range-values", params=params)

    # ----------------------------------------------------------------------
    # /location-parameter-range-values/{parameterRange}
    # ----------------------------------------------------------------------

    def get_location_parameter_range_values_by_parameter_range(
        self,
        parameter_range: str,
        location: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        GET /location-parameter-range-values/{parameterRange}
        """

        self._require(parameter_range, "parameter_range")
        self._validate_type(parameter_range, "parameter_range", str)
        self._validate_list(location, "location", str)

        params = {}
        if location is not None:
            params["Location"] = location

        path = f"/location-parameter-range-values/{parameter_range}"
        return self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # /location-parameter-range-values/{parameterRange}/{location}
    # PUT (formData + body)
    # ----------------------------------------------------------------------

    def put_location_parameter_range_values_by_location(
        self,
        parameter_range: str,
        location: str,
        levels: Optional[List[Dict[str, Any]]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        PUT /location-parameter-range-values/{parameterRange}/{location}

        levels (formData) is a list of objects:
            {
                "number": int,
                "parameter": str,
                "value": float
            }

        body is a PutLocationParameterRangeValuesByLocation object.
        """

        self._require(parameter_range, "parameter_range")
        self._require(location, "location")
        self._validate_type(parameter_range, "parameter_range", str)
        self._validate_type(location, "location", str)

        # Validate formData "Levels"
        if levels is not None:
            self._validate_list(levels, "levels", dict)
            for lvl in levels:
                self._require(lvl.get("number"), "levels.number")
                self._require(lvl.get("parameter"), "levels.parameter")
                self._require(lvl.get("value"), "levels.value")

                self._validate_type(lvl["number"], "levels.number", int)
                self._validate_type(lvl["parameter"], "levels.parameter", str)
                self._validate_type(lvl["value"], "levels.value", (int, float))

        # "body" can contain the same list of levels, wrapped inside the official model
        final_body = {}
        if body is not None:
            self._validate_type(body, "body", dict)
            final_body.update(body)

        # For formData this API uses application/x-www-form-urlencoded,
        # but we will encode it in request data because requests handles it.
        form_data = {}
        if levels is not None:
            # Flatten list into repeated formData entries
            form_data["Levels"] = levels

        path = f"/location-parameter-range-values/{parameter_range}/{location}"
        return self._request("PUT", path, data=form_data, json=final_body)

    # ----------------------------------------------------------------------
    # LOCATIONS
    # /locations
    # ----------------------------------------------------------------------

    def get_locations(
        self,
        location: Optional[List[str]] = None,
        active: Optional[List[bool]] = None,
        one_platform_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        GET /locations
        """

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

        return self._request("GET", "/locations", params=params)

    # ----------------------------------------------------------------------
    # /locations/{location}
    # ----------------------------------------------------------------------

    def get_location(
        self,
        location: str,
        active: Optional[List[bool]] = None,
    ) -> Dict[str, Any]:
        """
        GET /locations/{location}
        """

        self._require(location, "location")
        self._validate_type(location, "location", str)

        self._validate_list(active, "active", bool)

        params = {}
        if active is not None:
            params["Active"] = active

        path = f"/locations/{location}"
        return self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # MAP DATA (GEOJSON)
    # /map/locations
    # ----------------------------------------------------------------------

    def get_map_locations(
        self,
        use_secondary_coordinates: Optional[bool] = None,
        filter_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        GET /map/locations
        """

        params = {}
        if use_secondary_coordinates is not None:
            self._validate_type(
                use_secondary_coordinates, "use_secondary_coordinates", bool
            )
            params["UseSecondaryCoordinates"] = use_secondary_coordinates
        if filter_id is not None:
            self._validate_type(filter_id, "filter_id", str)
            params["FilterId"] = filter_id

        return self._request("GET", "/map/locations", params=params)

    # ----------------------------------------------------------------------
    # /map/datasets/{parameter}
    # ----------------------------------------------------------------------

    def get_map_datasets_by_parameter(
        self,
        parameter: str,
        use_secondary_coordinates: Optional[bool] = None,
        filter_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        GET /map/datasets/{parameter}
        """

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
        return self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # /map/statistics/latest/{parameter}/{statistic}
    # ----------------------------------------------------------------------

    def get_map_latest_statistics(
        self,
        parameter: str,
        statistic: str,
        use_secondary_coordinates: Optional[bool] = None,
        filter_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        GET /map/statistics/latest/{parameter}/{statistic}
        """

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
        return self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # /map/statistics/periodic/{parameter}/{statistic}/{interval}/{date}
    # ----------------------------------------------------------------------

    def get_map_periodic_statistics(
        self,
        parameter: str,
        statistic: str,
        interval: str,
        date: str,
        use_secondary_coordinates: Optional[bool] = None,
        filter_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        GET /map/statistics/periodic/{parameter}/{statistic}/{interval}/{date}
        """

        # Required
        for name, val in [
            ("parameter", parameter),
            ("statistic", statistic),
            ("interval", interval),
            ("date", date),
        ]:
            self._require(val, name)
            self._validate_type(val, name, str)

        # Enum validation
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
        return self._request("GET", path, params=params)

    # ----------------------------------------------------------------------
    # PARAMETER RANGE DEFINITIONS
    # /parameter-ranges
    # ----------------------------------------------------------------------

    def get_parameter_ranges(
        self,
        parameter_range: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        GET /parameter-ranges
        """

        self._validate_list(parameter_range, "parameter_range", str)

        params = {}
        if parameter_range is not None:
            params["ParameterRange"] = parameter_range

        return self._request("GET", "/parameter-ranges", params=params)

    # ----------------------------------------------------------------------
    # /parameter-ranges/{parameterRange}
    # ----------------------------------------------------------------------

    def get_parameter_range(
        self,
        parameter_range: str,
    ) -> Dict[str, Any]:
        """
        GET /parameter-ranges/{parameterRange}
        """

        self._require(parameter_range, "parameter_range")
        self._validate_type(parameter_range, "parameter_range", str)

        path = f"/parameter-ranges/{parameter_range}"
        return self._request("GET", path)

    # ----------------------------------------------------------------------
    # SECURITY
    # /security/tags   (PUT)
    # ----------------------------------------------------------------------

    def put_tag_security(
        self,
        tag_security: Optional[List[Dict[str, Any]]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        PUT /security/tags

        tag_security: list of { "name": str, "isDisplayed": bool }
        body: complete PutTagSecurity object
        """

        # Validate list
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

        return self._request("PUT", "/security/tags", json=final_body)

    # ----------------------------------------------------------------------
    # API VERSION
    # /version
    # ----------------------------------------------------------------------

    def get_version(self) -> Dict[str, Any]:
        """
        GET /version
        Returns the AQUARIUS WebPortal version information.
        """
        return self._request("GET", "/version")

    # ----------------------------------------------------------------------
    # DATA SET
    # /data-set
    # ----------------------------------------------------------------------

    def get_data_set(
        self,
        data_set: Optional[str] = None,
        one_platform_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        GET /data-set
        Retrieves data set information.
        """

        if data_set is not None:
            self._validate_type(data_set, "data_set", str)
        if one_platform_id is not None:
            self._validate_type(one_platform_id, "one_platform_id", str)

        params = {}
        if data_set is not None:
            params["DataSet"] = data_set
        if one_platform_id is not None:
            params["OnePlatformId"] = one_platform_id

        return self._request("GET", "/data-set", params=params)

    # ----------------------------------------------------------------------
    # AUTHENTICATE
    # /auth/{provider}  (GET, POST)
    # /auth             (GET, POST)
    # ----------------------------------------------------------------------

    def authenticate_provider_get(
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
        """
        GET /auth/{provider}
        """

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
        return self._request("GET", path, params=params)

    def authenticate_provider_post(
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
        """
        POST /auth/{provider}
        """

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
        return self._request("POST", path, params=params, json=final_body)

    # ----------------------------------------------------------------------
    # /auth (GET)
    # ----------------------------------------------------------------------

    def authenticate_get(
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
        """
        GET /auth
        """

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

        return self._request("GET", "/auth", params=params)

    # ----------------------------------------------------------------------
    # /auth (POST)
    # ----------------------------------------------------------------------

    def authenticate_post(
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
        """
        POST /auth
        """

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

        return self._request("POST", "/auth", params=params, json=final_body)
