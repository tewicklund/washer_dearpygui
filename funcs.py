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
COLD_TEMP_ALIAS = "master1port1"
HOT_TEMP_ALIAS = "master1port2"
COLD_PRESSURE_ALIAS = "master1port3"
HOT_PRESSURE_ALIAS = "master1port4"
COLD_FLOW_SENSOR_ALIAS = "master1port5"
HOT_FLOW_SENSOR_ALIAS = "master1port6"
NEAR_AMBIENT_ALIAS = "master1port7"
FAR_AMBIENT_ALIAS = "master1port8"


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

def _get_tm311_temperature(sensor_alias: str):
    """
    Return the TM311 process temperature in degrees Celsius.

    The TM311 sends four process-data bytes. Bytes 0-1 are a signed,
    big-endian 16-bit temperature value with one decimal place.
    """
    url = (
        f"{HUB_URL}/iolink/v1/devices/{sensor_alias}"
        "/processdata/getdata/value?format=byteArray"
    )

    try:
        process_data = _get_byte_array(url)

        if len(process_data) != 4:
            raise ValueError(
                f"Expected 4 TM311 process-data bytes, got {len(process_data)}."
            )

        raw_temperature = struct.unpack(">h", bytes(process_data[0:2]))[0]

        # TM311 special process values from the operating instructions.
        if raw_temperature == 32764:
            raise RuntimeError("TM311 reports no measurement data.")
        if raw_temperature == -32760:
            raise RuntimeError("TM311 temperature is below its measuring range.")
        if raw_temperature == 32760:
            raise RuntimeError("TM311 temperature is above its measuring range.")

        return round(raw_temperature / 10.0, 1)

    except Exception as exc:
        print(f"Failed to read TM311 temperature from {sensor_alias}: {exc}")
        return "UNKNOWN"


def _get_tm311_unit(sensor_alias: str) -> str:
    """
    Return the engineering unit used by the TM311 cyclic process data.

    The TM311 process-data temperature is defined in degrees Celsius.
    A process-data read is made first so a disconnected sensor reports offline.
    """
    url = (
        f"{HUB_URL}/iolink/v1/devices/{sensor_alias}"
        "/processdata/getdata/value?format=byteArray"
    )

    try:
        process_data = _get_byte_array(url)

        if len(process_data) != 4:
            raise ValueError(
                f"Expected 4 TM311 process-data bytes, got {len(process_data)}."
            )

        return "°C"

    except Exception as exc:
        print(f"Failed to read TM311 unit from {sensor_alias}: {exc}")
        return "offline"


def get_cold_temp_value():
    return _get_tm311_temperature(COLD_TEMP_ALIAS)


def get_cold_temp_unit():
    return _get_tm311_unit(COLD_TEMP_ALIAS)


def get_hot_temp_value():
    return _get_tm311_temperature(HOT_TEMP_ALIAS)


def get_hot_temp_unit():
    return _get_tm311_unit(HOT_TEMP_ALIAS)

def _get_ptouch_pressure_psig(sensor_alias: str):
    """
    Return pressure from a 0-200 psig MP Sensor P.Touch transmitter.

    The four-byte cyclic input begins with a signed, big-endian 16-bit
    pressure value in kPa. Convert kPa to psi using the manufacturer
    multiplier 0.14504.
    """
    url = (
        f"{HUB_URL}/iolink/v1/devices/{sensor_alias}"
        "/processdata/getdata/value?format=byteArray"
    )

    try:
        process_data = _get_byte_array(url)

        if len(process_data) != 4:
            raise ValueError(
                f"Expected 4 P.Touch process-data bytes, got {len(process_data)}."
            )

        raw_pressure_kpa = struct.unpack(">h", bytes(process_data[0:2]))[0]

        # Special process-data values defined by the P.Touch IO-Link interface.
        if raw_pressure_kpa == 32760:
            raise RuntimeError("P.Touch pressure is above the process-data range.")
        if raw_pressure_kpa == 32764:
            raise RuntimeError("P.Touch reports no measurement data.")

        pressure_psig = raw_pressure_kpa * 0.14504

        return round(pressure_psig, 2)

    except Exception as exc:
        print(f"Failed to read P.Touch pressure from {sensor_alias}: {exc}")
        return "UNKNOWN"


def _get_ptouch_pressure_unit(sensor_alias: str) -> str:
    """
    Return PSIG after confirming that the P.Touch sensor is communicating.
    """
    url = (
        f"{HUB_URL}/iolink/v1/devices/{sensor_alias}"
        "/processdata/getdata/value?format=byteArray"
    )

    try:
        process_data = _get_byte_array(url)

        if len(process_data) != 4:
            raise ValueError(
                f"Expected 4 P.Touch process-data bytes, got {len(process_data)}."
            )

        return "PSIG"

    except Exception as exc:
        print(f"Failed to read P.Touch unit from {sensor_alias}: {exc}")
        return "offline"


def get_cold_pres_value():
    return _get_ptouch_pressure_psig(COLD_PRESSURE_ALIAS)


def get_cold_pres_unit():
    return _get_ptouch_pressure_unit(COLD_PRESSURE_ALIAS)


def get_hot_pres_value():
    return _get_ptouch_pressure_psig(HOT_PRESSURE_ALIAS)


def get_hot_pres_unit():
    return _get_ptouch_pressure_unit(HOT_PRESSURE_ALIAS)

def _get_picomag_flow(sensor_alias: str):
    """
    Return the current Picomag volume flow rate.

    The Picomag cyclic process data contains 15 bytes. Bytes 8-11 are
    the volume-flow value encoded as a big-endian IEEE-754 float.
    """
    url = (
        f"{HUB_URL}/iolink/v1/devices/{sensor_alias}"
        "/processdata/getdata/value?format=byteArray"
    )

    try:
        process_data = _get_byte_array(url)

        if len(process_data) != 15:
            raise ValueError(
                f"Expected 15 Picomag process-data bytes, got {len(process_data)}."
            )

        flow_value = struct.unpack(">f", bytes(process_data[8:12]))[0]

        return round(flow_value, 3)

    except Exception as exc:
        print(f"Failed to read Picomag flow from {sensor_alias}: {exc}")
        return "UNKNOWN"


def _get_picomag_flow_unit(sensor_alias: str) -> str:
    """
    Return the volume-flow unit selected in the Picomag configuration.
    """
    url = (
        f"{HUB_URL}/iolink/v1/devices/{sensor_alias}"
        "/parameters/550/value/?format=byteArray"
    )

    units = {
        0: "L/s",
        1: "m³/h",
        2: "L/min",
        3: "gal/min",
        4: "fl oz/min",
        5: "L/h",
    }

    try:
        unit_bytes = _get_byte_array(url)

        if len(unit_bytes) != 2:
            raise ValueError(
                f"Expected 2 Picomag unit bytes, got {len(unit_bytes)}."
            )

        unit_number = int.from_bytes(unit_bytes, byteorder="big", signed=False)

        return units.get(unit_number, f"unknown unit ({unit_number})")

    except Exception as exc:
        print(f"Failed to read Picomag flow unit from {sensor_alias}: {exc}")
        return "offline"


def get_cold_flow_value():
    return _get_picomag_flow(COLD_FLOW_SENSOR_ALIAS)


def get_cold_flow_unit():
    return _get_picomag_flow_unit(COLD_FLOW_SENSOR_ALIAS)


def get_hot_flow_value():
    return _get_picomag_flow(HOT_FLOW_SENSOR_ALIAS)


def get_hot_flow_unit():
    return _get_picomag_flow_unit(HOT_FLOW_SENSOR_ALIAS)

def _get_ambient_temp_rh(sensor_alias: str) -> str:
    """
    Return ambient temperature and relative humidity as "temp : RH".

    The STEGO CSS 014 cyclic input is six bytes:
      bytes 0-1: signed 16-bit temperature, scaled by 0.1
      byte 2:    temperature status flags
      bytes 3-4: signed 16-bit humidity, scaled by 0.1
      byte 5:    humidity status flags

    Parameter index 66 selects the temperature encoding:
      0 = degrees Celsius
      1 = degrees Fahrenheit

    This function always returns temperature in degrees Fahrenheit.
    """
    process_url = (
        f"{HUB_URL}/iolink/v1/devices/{sensor_alias}"
        "/processdata/getdata/value?format=byteArray"
    )
    mode_url = (
        f"{HUB_URL}/iolink/v1/devices/{sensor_alias}"
        "/parameters/66/value/?format=byteArray"
    )

    try:
        process_data = _get_byte_array(process_url)

        if len(process_data) != 6:
            raise ValueError(
                f"Expected 6 CSS 014 process-data bytes, got {len(process_data)}."
            )

        raw_temperature = struct.unpack(">h", bytes(process_data[0:2]))[0]
        raw_humidity = struct.unpack(">h", bytes(process_data[3:5]))[0]

        temperature = raw_temperature / 10.0
        humidity = raw_humidity / 10.0

        mode_bytes = _get_byte_array(mode_url)
        if len(mode_bytes) != 1:
            raise ValueError(
                f"Expected 1 CSS 014 temperature-mode byte, got {len(mode_bytes)}."
            )

        temperature_mode = mode_bytes[0]

        if temperature_mode == 0:
            temperature_f = temperature * 9.0 / 5.0 + 32.0
        elif temperature_mode == 1:
            temperature_f = temperature
        else:
            raise ValueError(
                f"Unknown CSS 014 temperature mode: {temperature_mode}"
            )

        return f"{round(temperature_f, 1)} : {round(humidity, 1)}"

    except Exception as exc:
        print(f"Failed to read ambient temperature/RH from {sensor_alias}: {exc}")
        return "UNKNOWN"


def _get_ambient_temp_rh_unit(sensor_alias: str) -> str:
    """
    Return the stitched ambient-data units after confirming communication.
    """
    url = (
        f"{HUB_URL}/iolink/v1/devices/{sensor_alias}"
        "/processdata/getdata/value?format=byteArray"
    )

    try:
        process_data = _get_byte_array(url)

        if len(process_data) != 6:
            raise ValueError(
                f"Expected 6 CSS 014 process-data bytes, got {len(process_data)}."
            )

        return "°F : %RH"

    except Exception as exc:
        print(f"Failed to read ambient units from {sensor_alias}: {exc}")
        return "offline"


def get_temp_rh_near_value():
    return _get_ambient_temp_rh(NEAR_AMBIENT_ALIAS)


def get_temp_rh_near_unit():
    return _get_ambient_temp_rh_unit(NEAR_AMBIENT_ALIAS)


def get_temp_rh_far_value():
    return _get_ambient_temp_rh(FAR_AMBIENT_ALIAS)


def get_temp_rh_far_unit():
    return _get_ambient_temp_rh_unit(FAR_AMBIENT_ALIAS)

def _set_flow_unit_gpm(sensor_alias: str) -> bool:
    """Set one Picomag flow sensor to US gal/min."""

    url = (
        f"{HUB_URL}/iolink/v1/devices/{sensor_alias}"
        "/parameters/550/value"
    )

    gpm_value = 3
    payload = {
        "value": list(gpm_value.to_bytes(2, byteorder="big"))
    }

    try:
        response = requests.post(
            url,
            json=payload,
            auth=(HUB_USERNAME, HUB_PASSWORD),
            timeout=5,
        )

        if not response.ok:
            print(
                f"Failed to set {sensor_alias} to gal/min: "
                f"HTTP {response.status_code}"
            )
            print(f"Hub response: {response.text}")
            return False

        print(f"{sensor_alias} set to gal/min")
        return True

    except requests.RequestException as exc:
        print(f"Request failed for {sensor_alias}: {exc}")
        return False

def set_flow_units_gpm() -> bool:
    """
    Set both the cold and hot Picomag flow sensors to gal/min.

    Returns True only if both writes succeed.
    """

    cold_success = _set_flow_unit_gpm(COLD_FLOW_SENSOR_ALIAS)
    hot_success = _set_flow_unit_gpm(HOT_FLOW_SENSOR_ALIAS)

    return cold_success and hot_success

# example usage
#print(f"Cold water flow: {get_flow()} {get_flow_unit()}")