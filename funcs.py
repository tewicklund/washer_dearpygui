# helper functions for washer_dearpygui.py

from screeninfo import get_monitors
import struct
import requests
import urllib
import json

HUB_URL = "http://192.168.99.167"
FLOW_SENSOR_ALIAS = "master1port4"


# def _get_byte_array(url: str) -> list[int]:
#     """Send a GET request and extract the returned byte array."""
#     response = requests.get(url, timeout=1.0)
#     response.raise_for_status()

#     data = response.json()

#     if data.get("valid") is False:
#         raise RuntimeError("The IO-Link value is marked invalid.")

#     return data["value"]
def _get_byte_array(url: str) -> list[int]:
    with urllib.request.urlopen(url, timeout=1.0) as response:
        data = json.load(response)

    if not isinstance(data, dict):
        raise TypeError(
            f"Expected a dictionary, got {type(data).__name__}: {data!r}"
        )

    if data.get("valid") is False:
        raise RuntimeError(f"IO-Link value is marked invalid: {data!r}")

    if "value" not in data:
        raise KeyError(
            f"Response has no exact 'value' key. "
            f"Keys received: {list(data.keys())!r}. "
            f"Full response: {data!r}"
        )

    value = data["value"]

    if not isinstance(value, list):
        raise TypeError(f"Expected 'value' to be a list, got: {value!r}")

    return value


def get_flow() -> float:
    """Return the current flow rate in L/s."""
    url = (
        f"{HUB_URL}/iolink/v1/devices/{FLOW_SENSOR_ALIAS}"
        "/processdata/getdata/value?format=byteArray"
    )

    process_data = _get_byte_array(url)

    if len(process_data) != 15:
        raise ValueError(f"Expected 15 process-data bytes, got {len(process_data)}.")

    return struct.unpack(">f", bytes(process_data[8:12]))[0]


def get_flow_unit() -> str:
    """Return the flow unit selected in the Picomag configuration."""
    url = (
        f"{HUB_URL}/iolink/v1/devices/{FLOW_SENSOR_ALIAS}"
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

# example usage
print(f"Cold water flow: {get_flow()} {get_flow_unit}")