"""Mock server for EnergyMe device API endpoints.

This server provides mock responses for development and testing of the EnergyMe Home Assistant integration.
"""
import time
from flask import Flask, jsonify, request

app = Flask(__name__)

# --- System Endpoints ---

@app.route('/api/v1/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "uptime": int(time.time()),
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    })

@app.route('/api/v1/system/info', methods=['GET'])
def system_info():
    """Get system information."""
    return jsonify({
        "static": {
            "product": {
                "companyName": "EnergyMe",
                "productName": "Home",
                "fullProductName": "EnergyMe - Home",
                "productDescription": "An open-source energy monitoring system for home use, capable of monitoring up to 17 circuits.",
                "githubUrl": "https://github.com/jibrilsharafi/EnergyMe-Home",
                "author": "Jibril Sharafi",
                "authorEmail": "jibril.sharafi@gmail.com"
            },
            "firmware": {
                "buildVersion": "00.12.36",
                "buildDate": "Aug 29 2025",
                "buildTime": "13:39:52",
                "sketchMD5": "184b3123456477a354b68aa8f527d766",
                "partitionAppName": "app0"
            },
            "hardware": {
                "chipModel": "ESP32-S3",
                "chipRevision": 2,
                "chipCores": 2,
                "chipId": 273206166522968,
                "cpuFrequencyMHz": 240,
                "flashChipSizeBytes": 16777216,
                "flashChipSpeedHz": 80000000,
                "psramSizeBytes": 2097152
            },
            "monitoring": {
                "crashCount": 19,
                "consecutiveCrashCount": 0,
                "resetCount": 21,
                "consecutiveResetCount": 0,
                "lastResetReason": 3,
                "lastResetReasonString": "Software",
                "lastResetWasCrash": False
            },
            "sdk": {
                "sdkVersion": "v5.4.2-25-g858a988d6e",
                "coreVersion": "3.2.1"
            },
            "device": {
                "id": "588c81c47af8"
            }
        },
        "dynamic": {
            "time": {
                "uptimeMilliseconds": int(time.time() * 1000),
                "uptimeSeconds": int(time.time()),
                "currentTimestampIso": int(time.time())
            },
            "memory": {
                "heap": {
                    "totalBytes": 343000,
                    "freeBytes": 126208,
                    "usedBytes": 216792,
                    "minFreeBytes": 90864,
                    "maxAllocBytes": 48116,
                    "freePercentage": 36.79534,
                    "usedPercentage": 63.20466
                },
                "psram": {
                    "totalBytes": 2097152,
                    "freeBytes": 1849000,
                    "usedBytes": 248152,
                    "minFreeBytes": 1699744,
                    "maxAllocBytes": 1834996,
                    "freePercentage": 88.16719,
                    "usedPercentage": 11.83281
                }
            },
            "storage": {
                "littlefs": {
                    "totalBytes": 7208960,
                    "usedBytes": 16384,
                    "freeBytes": 7192576,
                    "freePercentage": 99.77273,
                    "usedPercentage": 0.227272
                },
                "nvs": {
                    "totalUsableEntries": 1890,
                    "usedEntries": 839,
                    "availableEntries": 1051,
                    "usedEntriesPercentage": 44.39153,
                    "availableEntriesPercentage": 55.60846,
                    "namespaceCount": 19
                }
            },
            "performance": {
                "temperatureCelsius": 44
            },
            "network": {
                "wifiConnected": True,
                "wifiSsid": "Casasha",
                "wifiMacAddress": "58:8C:81:C4:7A:F8",
                "wifiLocalIp": "192.168.1.76",
                "wifiGatewayIp": "192.168.1.1",
                "wifiSubnetMask": "255.255.255.0",
                "wifiDnsIp": "192.168.1.1",
                "wifiBssid": "DC:15:C8:82:DF:2B",
                "wifiRssi": -90
            }
        }
    })

# @app.route('/api/v1/system/statistics', methods=['GET'])
# def system_statistics():
#     """Get system statistics."""
#     return jsonify({
#         "ade7953TotalInterrupts": 1000,
#         "ade7953TotalHandledInterrupts": 999,
#         "ade7953ReadingCount": 500,
#         "ade7953ReadingCountFailure": 1,
#         "mqttMessagesPublished": 200,
#         "mqttMessagesPublishedError": 0,
#         "customMqttMessagesPublished": 50,
#         "customMqttMessagesPublishedError": 0,
#         "modbusRequests": 100,
#         "modbusRequestsError": 2,
#         "influxdbUploadCount": 50,
#         "influxdbUploadCountError": 0,
#         "wifiConnection": 1,
#         "wifiConnectionError": 0,
#         "webServerRequests": 1500,
#         "webServerRequestsError": 5,
#         "logVerbose": 200,
#         "logDebug": 500,
#         "logInfo": 1000,
#         "logWarning": 50,
#         "logError": 10,
#         "logFatal": 1,
#         "logDropped": 5
#     })

@app.route('/api/v1/system/restart', methods=['POST'])
def system_restart():
    """Restart the system."""
    return jsonify({"success": True, "message": "System is restarting."})

@app.route('/api/v1/system/factory-reset', methods=['POST'])
def factory_reset():
    """Perform factory reset of the system."""
    return jsonify({"success": True, "message": "Factory reset initiated."})

@app.route('/api/v1/system/secrets', methods=['GET'])
def check_secrets():
    """Check if the system has secrets available."""
    return jsonify({"hasSecrets": True})

@app.route('/api/v1/firmware/update-info', methods=['GET'])
def firmware_update_info():
    """Get firmware update information."""
    return jsonify({
        "currentVersion": "00.11.09",
        "buildDate": "Aug 03 2025",
        "buildTime": "14:30:25",
        "availableVersion": "00.11.10",
        "updateUrl": "https://github.com/jibrilsharafi/EnergyMe-Home/releases/download/v00.11.10/firmware.bin",
        "isLatest": False
    })

# --- ADE7953 Endpoints ---

@app.route('/api/v1/ade7953/config', methods=['GET', 'PUT', 'PATCH'])
def ade7953_config():
    """Get or update ADE7953 configuration."""
    if request.method == 'GET':
        return jsonify({
            "aVGain": 4194304,
            "aIGain": 4194304,
            "bIGain": 4194304,
            "aIRmsOs": 0,
            "bIRmsOs": 0,
            "aWGain": 4194304,
            "bWGain": 4194304,
            "aWattOs": 0,
            "bWattOs": 0,
            "aVarGain": 4194304,
            "bVarGain": 4194304,
            "aVarOs": 0,
            "bVarOs": 0,
            "aVaGain": 4194304,
            "bVaGain": 4194304,
            "aVaOs": 0,
            "bVaOs": 0,
            "phCalA": 0,
            "phCalB": 0
        })
    elif request.method in ['PUT', 'PATCH']:
        return jsonify({"success": True, "message": "Configuration updated successfully"})

@app.route('/api/v1/ade7953/config/reset', methods=['POST'])
def reset_ade7953_config():
    """Reset ADE7953 configuration."""
    return jsonify({"success": True, "message": "ADE7953 configuration reset to defaults."})


@app.route('/api/v1/ade7953/sample-time', methods=['GET', 'PUT'])
def ade7953_sample_time():
    """Get or set ADE7953 sample time."""
    if request.method == 'GET':
        return jsonify({"sampleTime": 1000})
    elif request.method == 'PUT':
        # In a real app, you'd save this value
        return jsonify({"success": True, "message": "Sample time updated."})


@app.route('/api/v1/ade7953/channel', methods=['GET', 'PUT', 'PATCH'])
def ade7953_channel():
    """Get or update channel configuration."""
    if request.method == 'GET':
        index = request.args.get('index')
        if index:
            return jsonify({
                "index": int(index),
                "active": True,
                "reverse": False,
                "label": f"Channel {index}",
                "phase": 1,
                "ctSpecification": {
                    "currentRating": 100.0,
                    "voltageOutput": 1.0,
                    "scalingFraction": 0.0
                }
            })
        else:
            return jsonify([
                    {
                        "index": i,
                        "active": True,
                        "reverse": False,
                        "label": f"Channel {i}",
                        "phase": 1,
                        "ctSpecification": {
                            "currentRating": 100.0,
                            "voltageOutput": 1.0,
                            "scalingFraction": 0.0
                        }
                    } for i in range(3) # Maximum is 17, but 3 for testing
                ])
    elif request.method in ['PUT', 'PATCH']:
        return jsonify({"success": True, "message": "Channel configuration updated."})


@app.route('/api/v1/ade7953/channel/reset', methods=['POST'])
def reset_channel_config():
    """Reset channel configuration."""
    return jsonify({"success": True, "message": "Channel configuration reset."})


@app.route('/api/v1/ade7953/register', methods=['GET', 'PUT'])
def ade7953_register():
    """Read or write to an ADE7953 register."""
    if request.method == 'GET':
        return jsonify({
            "address": request.args.get('address'),
            "bits": request.args.get('bits'),
            "signed": request.args.get('signed', 'false').lower() in ['true', '1'],
            "value": 12345678
        })
    elif request.method == 'PUT':
        return jsonify({"success": True, "message": "Register written successfully."})


@app.route('/api/v1/ade7953/meter-values', methods=['GET'])
def get_meter_values():
    """Get real-time meter values."""
    index = request.args.get('index')

    def get_single_meter_values(channel_index):
        """Generate meter values for a single channel."""
        return {
            "voltage": 230.5 + (channel_index * 0.1),  # Slight variation per channel
            "current": 5.2 + (channel_index * 0.2),
            "activePower": 1198.6 + (channel_index * 10),
            "reactivePower": 120.3 + (channel_index * 2),
            "apparentPower": 1204.8 + (channel_index * 10.1),
            "powerFactor": 0.99 - (channel_index * 0.001),
            "activeEnergyImported": 1234.56 + (channel_index * 100),
            "activeEnergyExported": 12.34 + (channel_index * 1),
            "reactiveEnergyImported": 567.89 + (channel_index * 50),
            "reactiveEnergyExported": 5.67 + (channel_index * 0.5),
            "apparentEnergy": 1235.67 + (channel_index * 100.1)
        }

    if index is not None:
        # Return data for a specific channel
        channel_index = int(index)
        return jsonify(get_single_meter_values(channel_index))
    else:
        # Return data for all active channels, following the C++ structure
        result = []
        CHANNEL_COUNT = 17  # Maximum number of channels

        for i in range(CHANNEL_COUNT):
            # Simulate some channels being active and having valid measurements
            # For testing, let's make channels 0-2 active
            if i < 3:  # Only first 3 channels are active for testing
                channel_data = {
                    "index": i,
                    "label": f"Channel {i}",
                    "phase": 1,
                    "data": get_single_meter_values(i)
                }
                result.append(channel_data)

        return jsonify(result)


@app.route('/api/v1/ade7953/grid-frequency', methods=['GET'])
def get_grid_frequency():
    """Get the current grid frequency."""
    return jsonify({"gridFrequency": 50.01})


@app.route('/api/v1/ade7953/energy/reset', methods=['POST'])
def reset_energy_values():
    """Reset all energy values."""
    return jsonify({"success": True, "message": "Energy values have been reset."})


@app.route('/api/v1/ade7953/energy', methods=['PUT'])
def set_energy_values():
    """Set energy values for a specific channel."""
    return jsonify({"success": True, "message": "Energy values updated."})

if __name__ == '__main__':
    app.run(debug=True)
