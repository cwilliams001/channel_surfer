
# Channel Surfer

Channel Surfer is a Python script that allows you to manage multiple Kismet endpoints and control Wi-Fi adapters connected to those endpoints. It provides an interactive command-line interface for adding, removing, and interacting with Kismet endpoints.

## Features

- Manage multiple Kismet endpoints
- Add and remove endpoints dynamically
- Lock Wi-Fi adapters to specific channels
- Set Wi-Fi adapters to various hopping modes
- Supports 2.4GHz, 5GHz, and dual-band hopping
- Persistent storage of endpoint configurations

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

Run the script using Python:

```bash
python3 channel_surfer.py
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

The script stores endpoint configurations in a JSON file named `endpoints.json` in the `.channel_surfer` directory within the user's home folder. This file is automatically created and updated as you add or remove endpoints. The configuration file location is consistent regardless of where you run the script from.

## Notes

- Ensure that you have the necessary permissions to interact with the Kismet API on the specified endpoints.
- The script uses ANSI color codes for a more user-friendly interface. Make sure your terminal supports ANSI colors for the best experience.
