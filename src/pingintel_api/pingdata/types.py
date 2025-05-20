# Copyright 2021-2024 Ping Data Intelligence
from typing import Any, Dict, List, NotRequired, Optional, TypedDict, Literal
from datetime import datetime
import enum
import functools


class Choices(enum.Enum):
    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, description: str = None):
        self._description_ = description

    def __str__(self):
        return str(self.value)

    @property
    def description(self):
        return self._description_

    @classmethod
    def get_options(cls):
        return [v.value for k, v in cls.__members__.items()]

    @functools.cache
    def _get_ordering(self):
        return {name: idx for idx, name in enumerate(self.__class__)}

    def __lt__(self, other):
        ordering = self._get_ordering()
        return ordering[self] < ordering[other]

    def __gt__(self, other):
        ordering = self._get_ordering()
        return ordering[self] > ordering[other]


class SOURCES(Choices):

    AZURE_GEOCODING = "AZG", "Azure Geocoding"
    BETTERVIEW = "BV", "Betterview"
    CORELOGICSPATIAL_COASTAL_STORM_RISK_SCORE = "CLS_CSRS", "CoreLogic Spatial Coastal Storm Risk Score"
    CORELOGICSPATIAL_CRIME_RISK_SCORE = "CLS_CRS", "CoreLogic Spatial Crime Risk Score"
    CORELOGICSPATIAL_DISTANCE_TO_FIRESTATION = "CLS_DTFST", "CoreLogic Spatial Distance to FireStation"
    CORELOGICSPATIAL_EARTHQUAKE_RISK_SCORE = "CLS_EQRS", "CoreLogic Spatial Earthquake Risk Score"
    CORELOGICSPATIAL_FLASH_FLOOD_RISK_SCORE = "CLS_FFRS", "CoreLogic Spatial Flash Flood Risk Score"
    CORELOGICSPATIAL_FLOOD_RISK_SCORE = "CLS_FRS", "CoreLogic Spatial Flood Risk Score"
    CORELOGICSPATIAL_HAIL_INSIGHT = "CLS_HI", "CoreLogic Spatial Hail Insight"
    CORELOGICSPATIAL_HAIL_RISK = "CLS_HR", "CoreLogic Spatial Hail Risk"
    CORELOGICSPATIAL_NON_WEATHER_FIRERISK_SCORE = "CLS_NWFRS", "CoreLogic Spatial Non-Weather FireRisk Score"
    CORELOGICSPATIAL_NON_WEATHER_WATERRISK_SCORE = "CLS_NWWRS", "CoreLogic Spatial Non-Weather WaterRisk Score"
    CORELOGICSPATIAL_WILDFIRE_RISK_SCORE = "CLS_WFRS", "CoreLogic Spatial Wildfire Risk Score"
    CORELOGICSPATIAL_WIND_RISK_SCORE = "CLS_WRS", "CoreLogic Spatial Wind Risk Score"
    DISTANCE_TO_COAST = "DTC", "Distance To Coast"
    DISTANCE_TO_FIRE_HYDRANT = "DTFH", "Ping Distance To Fire Hydrant"
    DISTANCE_TO_FIRE_STATION = "DTFST", "Ping Distance To Fire Station"
    E2VALUE_COMM_LITE = "E2V", "E2Value Commercial Lite"
    E2VALUE_RES_LITE = "E2VR", "E2Value Residential Lite"
    EASI_CRIME = "EC", "Easi Crime"
    ESRI_GEOCODING = "EG", "Esri Geocoding"
    ESRI_REVERSE_GEOCODING = "EGR", "Esri Reverse Geocoding"
    FEMA_NATIONAL_RISK_INDEX = "FNRI", "Fema National Risk Index"
    GEOCODIO = "GIO", "Geocodio"
    GOOGLE_ELEVATION = "GEV", "Google Elevation"
    GOOGLE_GEOCODING = "GG", "Google Geocoding"
    GOOGLE_REVERSE_GEOCODING = "GGR", "Google Reverse Geocoding"
    HAZARDHUB = "HH", "Hazardhub"
    HERE_GEOCODING = "HG", "Here Geocoding"
    INTERMAP_FLOOD = "IMF", "Intermap Flood"
    KATRISK = "KR", "Katrisk"
    LIBPOSTAL = "LP", "LibPostal"
    LIGHTBOX = "LB", "Lightbox"
    LIGHTBOX_FLOOD_ZONE = "LBFZ", "Lightbox Flood Zone"
    LIGHTBOX_GEOCODING = "LBG", "Lightbox Geocoding"
    LIGHTBOX_PARCEL = "LBP", "Lightbox Parcel"
    LIGHTBOX_REVERSE_GEOCODING = "LBGR", "Lightbox Reverse Geocoding"
    LIGHTBOX_SPATIAL_STREAM = "LBSS", "Lightbox SpatialStream"
    LIGHTBOX_STRUCTURES = "LBS", "Lightbox Structures"
    PING_DISTANCE_TO_FLORIDA_SINKHOLE = "DTFS", "Ping Distance To Florida Sinkhole"
    PING_FEMA_FLOOD_ZONE = "PFF", "Ping Fema Flood Zone"
    PING_FIRE_PROTECTION_CLASSIFICATION = "PFPC", "Ping Fire Protection Classification"
    PING_GEOCODING = "PG", "Ping Geocoding"
    PING_HAZARD = "PH", "Ping Hazard"
    PING_OCCUPANCY = "PO", "Ping Occupancy"
    PING_SLOSH_ZONE = "PSZ", "Ping Slosh Zone"
    PING_USA_CONSTRUCTION = "PUC", "Ping USA Construction"
    PING_USDA_WILDFIRE = "PUSDAW", "Ping USDA Wildfire"
    PRECISELY_GEOCODING = "PSG", "Precisely Geocoding"
    REASK_METRYC = "REASKM", "Reask Metryc"
    REDZONE_RISK = "RZR", "Redzone Risk"
    RMS_LOSS_COST_PRICING = "RMSLCP", "RMS Loss Cost Pricing"
    RMS_US_EXPOSURESOURCE_DATABASE = "RMS_US_ESDB", "RMS US ExposureSource Database"
    SMARTY_STREET_ADDRESS = "SM", "Smarty Street Address"
    TENSORFLIGHT = "TF", "Tensorflight"
    TEREN4D = "T4D", "Teren4d"
    TIGER_GEOCODING = "TG", "Tiger Geocoding"
    VERISK_PROPERTY = "VP", "Verisk Property"
    VEXCEL_PROPERTY_DAMAGE = "VPD", "Vexcel Property Damage"
    VEXCEL_PROPERTY_INFORMATION = "VPI", "Vexcel Property Information"


class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class ResultStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"


class Location(TypedDict):
    id: str
    address: NotRequired[str | None]
    latitude: NotRequired[float | None]
    longitude: NotRequired[float | None]
    limits__building_limit: NotRequired[float | None]
    limits__bpp_limit: NotRequired[float | None]
    limits__bi_limit: NotRequired[float | None]
    address_line_1: NotRequired[str | None]
    address_line_2: NotRequired[str | None]
    city: NotRequired[str | None]
    state: NotRequired[str | None]
    postal_code: NotRequired[str | None]
    country: NotRequired[str | None]
    county: NotRequired[str | None]
    bldg_name: NotRequired[str | None]
    # ping_occupancy_data: NotRequired[str | None]
    # llm_text_blob: NotRequired[str | None]
    # address_field_data: NotRequired[str | None]
    occupancy__type_desc: NotRequired[str | None]
    occupancy__desc_ping: NotRequired[str | None]
    occupancy__code_air: NotRequired[str | None]
    occupancy__code_atc: NotRequired[str | None]
    const__desc_ping: NotRequired[str | None]
    const__code_rms: NotRequired[str | None]
    const__code_air: NotRequired[str | None]
    const__roof_covering: NotRequired[str | None]
    const__wall_type: NotRequired[str | None]
    const__bldg_year_built: NotRequired[int | None]
    const__num_stories: NotRequired[int | None]
    const__bldg_area: NotRequired[int | None]
    dtc_include_coastline_within_miles: NotRequired[float | None]
    dtc_return_connected_coastlines: NotRequired[bool | None]
    insured_name: NotRequired[str | None]


class EnhanceResponse(TypedDict):
    id: str
    location_data: dict[SOURCES, dict]


class BulkEnhanceResponseCheckProgressResultOutputFile(TypedDict):
    url: str
    filename: str
    description: str


class BulkEnhanceResponseOutputFile(BulkEnhanceResponseCheckProgressResultOutputFile):
    local_filepath: str | None


class BulkEnhanceResponseCheckProgressRequest(TypedDict):
    status: Literal["PENDING", "QUEUED", "IN_PROGRESS", "COMPLETE", "FAILED"]
    requested_at: datetime
    progress_started_at: datetime | None
    num_requested: int | None
    num_completed: int | None
    num_problems: int | None
    num_canceled: int | None
    completed_at: datetime | None


class BulkEnhanceResponseCheckProgressResult(TypedDict):
    status: str
    message: str
    total_processing_time: float
    outputs: NotRequired[list[BulkEnhanceResponseCheckProgressResultOutputFile]]
    additional_info: NotRequired[dict]
    sources: NotRequired[list[dict]]


class BulkEnhanceResponseCheckProgress(TypedDict):
    request: BulkEnhanceResponseCheckProgressRequest
    result: NotRequired[BulkEnhanceResponseCheckProgressResult]


class BulkEnhanceResponse(TypedDict):
    id: str
    success: bool
    output_files: NotRequired[list[BulkEnhanceResponseOutputFile]]
