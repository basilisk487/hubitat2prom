import json
import os
import requests
import time
import re

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI()

useful_metrics = [
    "battery",
    "humidity",
    "illuminance",
    "level",
    "switch",
    "temperature",
    "power",
    "energy",
    "smoke",
    "carbonMonoxide",
    "batteryVoltage",
    "water",
    "motion",
    "presence",
    "contact",
    "pressure",
    "rate",
    "thermostatSetpoint",
    # Hub Information metrics
    "cpu15Min",
    "cpu15Pct",
    "cpu5Min",
    "cpuPct",
    "dbSize",
    "freeMem15",
    "freeMemory",
    "uptime",
]

# Load the configuration values from environment variables - HE_URI and HE_TOKEN
# are mandatory, however a default collection of metrics is provided if the
# HE_METRICS env is missing.
try:
    base_uri = os.environ["HE_URI"]
    access_token = os.environ["HE_TOKEN"]
    collected_metrics = os.getenv("HE_METRICS").split(",") if os.getenv("HE_METRICS") else useful_metrics
    metric_prefix = os.environ.get("HE_METRIC_PREFIX", "hubitat")
except KeyError as e:
    print(f"Could not read the environment variable - {e}")

def get_all_devices():
    return requests.get(f"{base_uri}/all?access_token={access_token}", timeout=30)

def get_devices():
    return requests.get(f"{base_uri}?access_token={access_token}", timeout=30)

@app.get("/info")
def info():
    result = get_devices()
    return {
        "status": {
            "CONNECTION": "ONLINE" if result.status_code == 200 else "OFFLINE",
            "CODE": result.status_code
        },
        "config": {
            "HE_URI": base_uri,
            "HE_TOKEN": access_token,
            "HE_METRICS": collected_metrics
        }
    }

@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    devices = get_all_devices()
    if devices.status_code == 200:
        lines = []

        for device in devices.json():
            for attrib in device['attributes']:
                # Is this a metric we should be collecting?
                if attrib in collected_metrics:
                    value = device['attributes'][attrib]
                    # Does it have a "proper" value?
                    if value is not None:
                        # If it's a switch, then change from text to binary values
                        if attrib == "switch":
                            if value == "on":
                                value = 1
                            else:
                                value = 0
                        if attrib == "water":
                            if value == "dry":
                                value = 1
                            else:
                                value = 0
                        if attrib == "power":
                            if value == "on":
                                value = 1
                            elif value == "off":
                                value = 0
                        if attrib == "contact":
                            match value:
                                case "open":
                                    value = 1
                                case "closed":
                                    value = 0
                        if attrib == "smoke" or attrib == "carbonMonoxide":
                            match value:
                                case "clear":
                                    value = 0
                                case "detected":
                                    value = 1
                                case "tested":
                                    value = -1
                        if attrib == "presence":
                            match value:
                                case "present":
                                    value = 1
                                case "not present":
                                    value = 0
                        if attrib == "motion":
                            match value:
                                case "active":
                                    value = 1
                                case "inactive":
                                    value = 0

                        tags = [
                            f"name=\"{device['name']}\"",
                            f"label=\"{device['label']}\"",
                            f"type=\"{device['type']}\"",
                            f"id=\"{sanitize(device['id'])}\""
                        ]
                        if device.get("room"):
                            tags.append(f"room=\"{device['room']}\"")
                        metric_name = f"{metric_prefix}_{sanitize(attrib)}"
                        if attrib == "temperature":  # report temperature twice
                            unit_f = f"unit=\"F\""
                            lines.append(f"{metric_name}{{{','.join(tags + [unit_f])}}} {value}")
                            value_c = (float(value) - 32) / 1.8
                            unit_c = f"unit=\"C\""
                            lines.append(f"{metric_name}{{{','.join(tags + [unit_c])}}} {value_c}")
                        else:
                            lines.append(f"{metric_name}{{{','.join(tags)}}} {value}")


        # Create the response
        response = "\n".join(lines)
    else:
        response = devices
    return response

def sanitize(inputValue):
    return re.sub('[^a-z0-9]+', '_', inputValue.lower())
