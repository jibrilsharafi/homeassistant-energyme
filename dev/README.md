# Development Tools

This directory contains development and testing utilities for the EnergyMe Home Assistant integration.

## Files

### `run-ha-dev.ps1`

PowerShell script to run Home Assistant in a Docker container for development.

**Usage:**

```powershell
cd dev
.\run-ha-dev.ps1
```

**What it does:**

- Creates config directory if needed
- Sets up configuration.yaml with debug logging
- Runs Home Assistant in Docker with the integration mounted
- Accessible at <http://localhost:8123>

### `test-local.ps1`

PowerShell script for local testing and validation.

### `mock_server.py`

Flask-based mock server that simulates the EnergyMe device API.

**Usage:**

```bash
python mock_server.py
```

**Endpoints:**

- `/api/v1/system/info` - Device information
- `/api/v1/ade7953/channel` - Channel configuration
- `/api/v1/ade7953/meter-values` - Meter readings

### `requirements.txt`

Python dependencies for development tools (ruff, colorlog, etc.)

## Development Workflow

1. **Start mock server** (optional, for testing without hardware):

   ```bash
   cd dev
   python mock_server.py
   ```

2. **Run Home Assistant**:

   ```powershell
   cd dev
   .\run-ha-dev.ps1
   ```

3. **Configure integration**:
   - Navigate to <http://localhost:8123>
   - Add EnergyMe integration
   - Use mock server address (<http://host.docker.internal:5000>) or real device IP

4. **View logs**:
   - Logs are visible in the Docker container output
   - Or check Settings → System → Logs in HA UI

## Scripts (Root Directory)

Development scripts in the `/scripts` directory:

- `./scripts/develop` - Run HA directly (Linux/macOS)
- `./scripts/lint` - Run linting checks
- `./scripts/setup` - Setup development environment
