# EnergyMe Custom Component for Home Assistant

This repository contains the EnergyMe custom component for Home Assistant. This component is designed to be a blueprint for other custom component developers to build upon.

## Structure

The main integration files are located in `custom_components/energyme/`. This is where the main functionality of the component is implemented.

- [`__init__.py`](custom_components/energyme/__init__.py): This is the main entry point for the integration.
- [`sensor.py`](custom_components/energyme/sensor.py): This file contains the implementation of the EnergyMe sensor.
- [`manifest.json`](custom_components/energyme/manifest.json): This file contains metadata about the integration.

## Development

Development and testing are done in a Visual Studio Code devcontainer, as defined in [`.devcontainer.json`](.devcontainer.json).

Python packages used for development, linting, and testing this integration are listed in [`requirements.txt`](requirements.txt).

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.