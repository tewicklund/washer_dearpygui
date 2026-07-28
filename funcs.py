# helper functions for washer_dearpygui.py

from screeninfo import get_monitors
import struct
import urllib
import json
import urllib.request
from datetime import datetime
import time
import requests


HUB_URL = "http://192.168.99.162"
HUB_USERNAME="washer_test_user"
HUB_PASSWORD="washer_test_password"
COLD_TEMP_ALIAS = "master1port0"
HOT_TEMP_ALIAS = "master1port1"
COLD_PRESSURE_ALIAS = "master1port2"
HOT_PRESSURE_ALIAS = "master1port3"
COLD_FLOW_SENSOR_ALIAS = "master1port4"
HOT_FLOW_SENSOR_ALIAS = "master1port5"
NEAR_AMBIENT_ALIAS = "master1port6"
NEAR_AMBIENT_ALIAS = "master1port7"


# function for sizing UI window (viewport) based on primary monitor width and height
def compute_window_size(width=None, height=None):

    all_monitors=get_monitors()

    main_monitor=max(all_monitors,key=lambda monitor: monitor.width * monitor.height)
    main_width=main_monitor.width
    main_height=main_monitor.height

    # defaults to 75% of biggest monitor's width and height
    viewport_width=int(main_width*0.9)
    viewport_height=int(main_height*0.9)

    # OVERRIDE: User can enter their own custom viewport size
    if width is not None and height is not None:
        viewport_width=width
        viewport_height=height

    return viewport_width,viewport_height

def ordinal_suffix(day: int) -> str:
    """Return a day number with its English ordinal suffix."""
    if 11 <= day % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    return f"{day}{suffix}"


def make_timestamp(sample_number: int) -> dict:
    """Generate identifiers and timestamps for one logged sample."""
    now = datetime.now()

    epoch_ms = time.time_ns() // 1_000_000

    readable_time = (
        f"{now.strftime('%B')} "
        f"{ordinal_suffix(now.day)} "
        f"{now.year} at "
        f"{now.strftime('%H:%M:%S')}"
    )

    return {
        "sample_num": sample_number,
        "epoch_timestamp_ms": epoch_ms,
        "human_timestamp": readable_time,
    }

def _get_byte_array(url: str) -> list[int]:
    """GET an IO-Link value and return its byte array."""
    with urllib.request.urlopen(url, timeout=1.0) as response:
        data = json.load(response)

    if not isinstance(data, dict):
        raise TypeError(f"Expected a dictionary, got {data!r}")

    # Process-data responses are wrapped inside "iolink".
    payload = data.get("iolink", data)

    if not isinstance(payload, dict):
        raise TypeError(f"Unexpected response structure: {data!r}")

    # Some responses include a validity flag; parameter reads may not.
    if payload.get("valid") is False:
        raise RuntimeError(f"IO-Link value is marked invalid: {data!r}")

    value = payload.get("value")

    if value is None:
        raise KeyError(f"No 'value' field in hub response: {data!r}")

    if not isinstance(value, list):
        raise TypeError(
            f"Expected 'value' to be a list, got {type(value).__name__}: {value!r}"
        )

    return value

def get_cold_temp():
    return "UNKNOWN"
def get_cold_temp_unit():
    return "°F"
def get_hot_temp():
    return "UNKNOWN"
def get_hot_temp_unit():
    return "°F"

def get_cold_pres():
    return "UNKNOWN"
def get_cold_pres_unit():
    return "psig"
def get_hot_pres():
    return "UNKNOWN"
def get_hot_pres_unit():
    return "psig"


def get_cold_flow() -> float:
    """Return the current flow rate."""
    url = (
        f"{HUB_URL}/iolink/v1/devices/{COLD_FLOW_SENSOR_ALIAS}"
        "/processdata/getdata/value?format=byteArray"
    )

    process_data = _get_byte_array(url)

    if len(process_data) != 15:
        raise ValueError(f"Expected 15 process-data bytes, got {len(process_data)}.")


    return struct.unpack(">f", bytes(process_data[8:12]))[0]


def get_cold_flow_unit() -> str:
    """Return the flow unit selected in the Picomag configuration."""
    url = (
        f"{HUB_URL}/iolink/v1/devices/{COLD_FLOW_SENSOR_ALIAS}"
        "/parameters/550/value/?format=byteArray"
    )

    unit_bytes = _get_byte_array(url)
    unit_number = int.from_bytes(unit_bytes, byteorder="big")

    units = {
        0: "L/s",
        1: "m³/h",
        2: "L/min",
        3: "gal/min",
        4: "fl oz/min",
        5: "L/h",
    }

    return units.get(unit_number, f"unknown unit ({unit_number})")
def get_hot_flow():
    return '*****'
def get_hot_flow_unit():
    return 'gal/min'
def get_temp_rh_near():
    return '*****'
def get_temp_rh_near_unit():
    return """°F/%RH"""
def get_temp_rh_far():
    return '*****'
def get_temp_rh_far_unit():
    return """°F/%RH"""

def set_flow_unit_gpm() -> str:
    """Set the cold Picomag flow-rate unit to US gal/min."""

    aliases=[COLD_FLOW_SENSOR_ALIAS,HOT_FLOW_SENSOR_ALIAS]

    for sensor in aliases:

        url = (
            f"{HUB_URL}/iolink/v1/devices/{sensor}"
            "/parameters/550/value"
        )

        response = requests.post(
            url,
            json={"value": [3]},
            auth=(HUB_USERNAME, HUB_PASSWORD),
            timeout=5,
        )
        response.raise_for_status()

        # Confirm that the sensor accepted the new setting.
        if sensor==aliases[0]:
            selected_unit = get_cold_flow_unit()
        else:
            selected_unit = get_hot_flow_unit()

        if selected_unit != "gal/min":
            raise RuntimeError(
                f"Flow-unit write did not take effect; sensor reports {selected_unit!r}"
            )

# example usage
#print(f"Cold water flow: {get_flow()} {get_flow_unit()}")