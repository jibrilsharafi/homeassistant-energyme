# EnergyMe Home Assistant Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

_A Home Assistant custom integration for EnergyMe energy monitoring devices._

This integration allows you to monitor electrical energy consumption and production data from EnergyMe devices directly in Home Assistant. It provides real-time access to electrical measurements including voltage, current, power, energy consumption, and power factor across multiple monitored channels.

## Features

- **Real-time Energy Monitoring**: Track electrical consumption and production
- **Multi-channel Support**: Monitor up to 17 different electrical circuits or devices
- **Comprehensive Metrics**: Access voltage, current, active/reactive/apparent power, energy totals, and power factor
- **Configurable Update Intervals**: Customize how frequently data is fetched from your device
- **Easy Configuration**: Simple setup through Home Assistant's UI with automatic device discovery

## Supported Sensors

For each active channel configured on your EnergyMe device, the integration creates sensors for:

- **Voltage** (V) - Line voltage measurements
- **Current** (A) - Current draw measurements  
- **Active Power** (W) - Real power consumption/generation
- **Reactive Power** (var) - Reactive power measurements
- **Apparent Power** (VA) - Total power measurements
- **Power Factor** - Efficiency ratio (dimensionless)
- **Active Energy Imported** (Wh) - Total energy consumed
- **Active Energy Exported** (Wh) - Total energy produced/exported
- **Reactive Energy Imported/Exported** (varh) - Reactive energy totals
- **Apparent Energy** (VAh) - Total apparent energy

## Installation

### Manual Installation

1. Download the latest release from the [releases page][releases]
2. Extract the `energyme` folder from the zip file
3. Copy the `energyme` folder to your `custom_components` directory in your Home Assistant configuration folder
4. Restart Home Assistant
5. Go to **Settings** → **Devices & Services** → **Add Integration**
6. Search for "EnergyMe" and follow the setup wizard

### HACS Installation

1. Add this repository as a custom repository in HACS:
   - Go to HACS → Integrations → ⋮ → Custom repositories
   - Add `https://github.com/jibrilsharafi/homeassistant-energyme` as an Integration
2. Install the "EnergyMe" integration from HACS
3. Restart Home Assistant
4. Add the integration through **Settings** → **Devices & Services**

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "EnergyMe" 
3. Enter the IP address or hostname of your EnergyMe device
4. The integration will automatically discover active channels and create appropriate sensors

### Configuration Options

- **Host**: IP address or hostname of your EnergyMe device
- **Update Interval**: How often to fetch data from the device (default: 10 seconds, minimum: 5 seconds)

## Device Requirements

Your EnergyMe device must:
- Be connected to the same network as your Home Assistant instance
- Have REST API endpoints enabled (default configuration)
- Respond to the following endpoints:
  - `/rest/is-alive` - Device health check
  - `/rest/get-channel` - Channel configuration
  - `/rest/meter` - Real-time energy data

## Troubleshooting

### Connection Issues
- Verify your EnergyMe device is powered on and connected to the network
- Check that the IP address/hostname is correct
- Ensure there are no firewall rules blocking communication
- Try accessing `http://[device-ip]/rest/is-alive` in a web browser

### Missing Sensors
- Check that channels are properly configured and marked as "active" on your EnergyMe device
- Verify the device is returning data at `/rest/meter` endpoint
- Check Home Assistant logs for any error messages

### Performance
- If you experience performance issues, try increasing the update interval in the integration options
- The default 10-second interval provides good real-time monitoring while minimizing network traffic

## Development

Development and testing are done in a Visual Studio Code devcontainer, as defined in [`.devcontainer.json`](.devcontainer.json).

Python packages used for development, linting, and testing this integration are listed in [`requirements.txt`](requirements.txt).

### Local Testing

Use the provided PowerShell script to test the integration locally:

```powershell
.\test-local.ps1
```

This will run hassfest validation using Docker containers.

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines.

If you encounter issues or have feature requests, please open an issue on the [GitHub repository][issues].

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

[releases-shield]: https://img.shields.io/github/release/jibrilsharafi/homeassistant-energyme.svg?style=for-the-badge
[releases]: https://github.com/jibrilsharafi/homeassistant-energyme/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/jibrilsharafi/homeassistant-energyme.svg?style=for-the-badge
[commits]: https://github.com/jibrilsharafi/homeassistant-energyme/commits/main
[license-shield]: https://img.shields.io/github/license/jibrilsharafi/homeassistant-energyme.svg?style=for-the-badge
[issues]: https://github.com/jibrilsharafi/homeassistant-energyme/issues