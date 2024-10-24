# Copyright 2021-2024 Ping Data Intelligence
import enum


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


class SOURCES(Choices):
    BETTERVIEW = "BV", "Betterview"
    BING_GEOCODING = "BG", "Bing Geocoding"
    DISTANCE_TO_COAST = "DTC", "Distance To Coast"
    ESRI_GEOCODING = "EG", "Esri Geocoding"
    FEMA_FLOOD_ZONE = "FF", "FemaFloodZone"
    E2VALUE_COMM_LITE = "E2V", "E2Value Commercial Lite"
    E2VALUE_RES_LITE = "E2VR", "E2Value Residential Lite"
    GOOGLE_GEOCODING = "GG", "Google Geocoding"
    GOOGLE_ADDRESS_VALIDATION = "GAV", "Google Address Validation"
    HAZARDHUB = "HH", "Hazardhub"
    KATRISK = "KR", "Katrisk"
    LIBPOSTAL = "LP", "LibPostal"
    LIGHTBOX = "LB", "Lightbox"
    LIGHTBOX_PARCEL = "LBP", "Lightbox Parcel"
    LIGHTBOX_GEOCODING = "LBG", "Lightbox Geocoding"
    LIGHTBOX_SPATIAL_STREAM = "LBSS", "Lightbox Spatial Stream"
    LIGHTBOX_FLOOD_ZONE = "LBFZ", "Lightbox Flood Zone"
    MESSYDATA = "MD", "MessyData"
    OPENAI_GENERIC_CLASSIFIER = "OAGC", "OpenAI Generic Classifier"
    PING_GEOCODING = "PG", "Ping Geocoding"
    PRECISELY_GEOCODING = "PSG", "Precisely Geocoding"
    NOOP = "NOOP", "NoOp"
    QUANTARIUM = "Q", "Quantarium"
    TEREN4D = "T4D", "Teren4d"
    TENSORFLIGHT = "TF", "Tensorflight"
    TIGERRISKAIR = "TRAIR", "Tiger Risk AIR"
    TIGERRISKRMS = "TRRMS", "Tiger Risk RMS"
    TIGER_GEOCODING = "TG", "Tiger Geocoding"
    VERISK_PROPERTY = "VP", "Verisk Property"
    FEMA_NATIONAL_RISK_INDEX = "FNRI", "Fema National Risk Index"
    PING_DISTANCE_TO_FLORIDA_SINKHOLE = "DTFS", "Ping Distance To Florida Sinkhole"
    REDZONE_RISK = "RZR", "Redzone Risk"
    DISTANCE_TO_FIRE_STATION = "DTFST", "Ping Distance To Fire Station"
    ESRI_REVERSE_GEOCODING = "EGR", "Esri Reverse Geocoding"
    PING_OCCUPANCY = "PO", "Ping Occupancy"
    LIGHTBOX_REVERSE_GEOCODING = "LBGR", "Lightbox Reverse Geocoding"
    GOOGLE_REVERSE_GEOCODING = "GGR", "Google Reverse Geocoding"
    BING_REVERSE_GEOCODING = "BGR", "Bing Reverse Geocoding"
    PING_FEMA_FLOOD_ZONE = "PFF", "Ping Fema Flood Zone"
    SMARTY_STREET_ADDRESS = "SM", "Smarty Street Address"
    OFAC_API = "OFAC", "OFAC API"
    CORELOGIC_NW_FIRE_RISK = "CLNWFR", "CoreLogic NWFireRisk"
    GEOCODIO = "GIO", "Geocodio"
    PING_SLOSH_ZONE = "PSZ", "Ping Slosh Zone"
    PING_USA_CONSTRUCTION = "PUC", "Ping USA Construction"
    AZURE_GEOCODING = "AZG", "Azure Geocoding"
    RMS_LOSS_COST_PRICING = "RMSLCP", "RMS Loss Cost Pricing"
    INTERMAP_FLOOD = "IMF", "Intermap Flood"
    CORELOGIC_WILDFIRE_RISK_SCORE = "CLWRS", "CoreLogic Wildfire Risk Score"
    REASK_METRYC = "REASKM", "Reask Metryc"


class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class ResultStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
