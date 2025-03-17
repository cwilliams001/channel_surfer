# Channel Surfer

Channel Surfer is a Python tool that allows you to manage multiple Kismet endpoints and control Wi-Fi adapters connected to those endpoints. It provides an interactive command-line interface for adding, removing, and interacting with Kismet's API to control wireless adapter settings.

## Features

- Manage multiple Kismet endpoints
- Add and remove endpoints dynamically
- Lock Wi-Fi adapters to specific channels
- Set Wi-Fi adapters to various hopping modes
- Supports 2.4GHz, 5GHz, and dual-band hopping
- Persistent storage of endpoint configurations
- Efficient channel hopping for optimized scanning

## Requirements

- Python 3.6 or higher
- Kismet server(s) with API access

## Installation

You can install Channel Surfer in several ways:

### Via PyPI
Install directly using pip:

```bash
pip install channel-surfer
```

### Using pipx (Recommended)

For an isolated installation that avoids conflicts with your system Python, use pipx:

```bash
pipx install channel-surfer
```

## Usage

After installation, simply run:

```bash
channel-surfer
```

If installing directly from the repository:

```bash
python -m channel_surfer.main
```

### Main Menu

1. **Select an endpoint**: Choose an existing endpoint to interact with.
2. **Add a new endpoint**: Add a new Kismet endpoint to the configuration.
3. **Remove an endpoint**: Remove an existing endpoint from the configuration.
4. **Exit**: Quit the application.

### Endpoint Actions

After selecting an endpoint, you can perform the following actions:

1. **Lock channel for a device**: Set a Wi-Fi adapter to a specific channel.
2. **Set device to hopping mode**: Configure a Wi-Fi adapter to hop between channels.
   - 2.4GHz
   - 5GHz
   - Both 2.4GHz and 5GHz
3. **Set device to hop between two channels**: Configure a Wi-Fi adapter to hop between two specific channels.
4. **Set device to efficient channels hopping**: Configure a Wi-Fi adapter to hop between non-overlapping channels.
   - 2.4GHz efficient channels (1,6,11)
   - 5GHz efficient channels (36,40,44,48,149,153,157,161)
   - Both 2.4GHz and 5GHz efficient channels
5. **Back to endpoint selection**: Return to the endpoint selection menu.

## Configuration

The tool stores endpoint configurations in a JSON file named `endpoints.json` in the `.channel_surfer` directory within the user's home folder. This file is automatically created and updated as you add or remove endpoints. The configuration file location is consistent regardless of where you run the tool from.

## Troubleshooting

- **Connection issues**: Ensure your Kismet server is running and accessible from your network.
- **Authentication failures**: Verify your Kismet username and password are correct.
- **No devices shown**: Make sure your Wi-Fi adapters are properly connected and recognized by Kismet.
- **Permission issues**: The tool requires appropriate permissions to interact with the Kismet API.

## Developer Setup

To set up a development environment:

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the environment: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -e .`

## License

This project is licensed under the MIT License - see the project repository for details.

## Notes

- Ensure that you have the necessary permissions to interact with the Kismet API on the specified endpoints.
- The tool uses ANSI color codes through the Rich library for a more user-friendly interface.