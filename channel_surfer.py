#!/usr/bin/env python3
import json
import time
from pathlib import Path
import requests
from requests.exceptions import RequestException

# ANSI color codes for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

def get_config_file_path() -> Path:
    """Get the configuration file path for endpoints."""
    config_dir = Path.home() / ".channel_surfer"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "endpoints.json"

def load_endpoints() -> list:
    """Load endpoints from the configuration file."""
    config_file = get_config_file_path()
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"{Colors.YELLOW}Endpoints configuration file not found. Starting with an empty list.{Colors.NC}")
        return []
    except json.JSONDecodeError:
        print(f"{Colors.RED}Error decoding the endpoints configuration file. Starting with an empty list.{Colors.NC}")
        return []

def save_endpoints(endpoints: list) -> None:
    """Save endpoints to the configuration file."""
    config_file = get_config_file_path()
    with open(config_file, 'w') as f:
        json.dump(endpoints, f, indent=2)

def add_endpoint() -> dict:
    """Prompt user to add a new endpoint."""
    name = input(f"{Colors.YELLOW}Enter endpoint name: {Colors.NC}")
    url = input(f"{Colors.YELLOW}Enter endpoint URL (http://<ip>:<port>): {Colors.NC}")
    endpoint_type = input(f"{Colors.YELLOW}Enter endpoint type (e.g., local, vpn): {Colors.NC}")
    user = input(f"{Colors.YELLOW}Enter Kismet username: {Colors.NC}")
    password = input(f"{Colors.YELLOW}Enter Kismet password: {Colors.NC}")

    return {
        "name": name,
        "url": url,
        "type": endpoint_type,
        "user": user,
        "pass": password
    }

def format_hop_channels(channels) -> str:
    """Format a list of hop channels for display."""
    return ' '.join(str(ch) for ch in channels)

def make_request(endpoint: dict, method: str, url: str, data: dict = None):
    """
    Make an HTTP request with basic authentication.
    
    Returns the response object on success, or None on failure.
    """
    try:
        response = requests.request(method, url, auth=(endpoint['user'], endpoint['pass']), data=data)
        response.raise_for_status()
        return response
    except RequestException as e:
        print(f"{Colors.RED}Error connecting to {endpoint['name']}: {e}{Colors.NC}")
        return None

def lock_channel(endpoint: dict, source_uuid: str, channel: str, interface: str) -> None:
    """Lock a specific channel on a device."""
    url = f"{endpoint['url']}/datasource/by-uuid/{source_uuid}/set_channel.cmd"
    payload = {"channel": channel}
    response = make_request(endpoint, 'POST', url, data={"json": json.dumps(payload)})
    if response:
        try:
            data = response.json()
            if data.get("kismet.datasource.channel") == channel:
                print(f"{Colors.GREEN}Successfully locked channel {channel} on device {interface}{Colors.NC}")
            else:
                print(f"{Colors.RED}Failed to lock channel {channel} on device {interface}{Colors.NC}")
        except json.JSONDecodeError:
            print(f"{Colors.RED}Failed to decode response when locking channel on device {interface}{Colors.NC}")
    else:
        print(f"{Colors.RED}Request failed for locking channel on device {interface}{Colors.NC}")

def set_hopping(endpoint: dict, source_uuid: str, hop_rate: int, channels, interface: str) -> None:
    """
    Set hopping mode on a device.
    
    The 'channels' parameter can be a comma-separated string or a list.
    """
    json_data = {"hop": True, "rate": hop_rate}
    if channels:
        if isinstance(channels, str):
            # Split by comma and remove any extra whitespace
            json_data["channels"] = [ch.strip() for ch in channels.split(',') if ch.strip()]
        else:
            json_data["channels"] = channels
    url = f"{endpoint['url']}/datasource/by-uuid/{source_uuid}/set_channel.cmd"
    response = make_request(endpoint, 'POST', url, data={"json": json.dumps(json_data)})
    if response:
        try:
            data = response.json()
            if data.get("kismet.datasource.hopping") == 1:
                print(f"{Colors.GREEN}Successfully set hopping mode on device {interface}{Colors.NC}")
                new_channels = data.get("kismet.datasource.hop_channels", [])
                formatted_channels = format_hop_channels(new_channels)
                print(f"{Colors.YELLOW}New hop channels: {formatted_channels}{Colors.NC}")
            else:
                print(f"{Colors.RED}Failed to set hopping mode on device {interface}{Colors.NC}")
        except json.JSONDecodeError:
            print(f"{Colors.RED}Failed to decode response when setting hopping mode on device {interface}{Colors.NC}")
    else:
        print(f"{Colors.RED}Request failed for setting hopping mode on device {interface}{Colors.NC}")

def get_datasources(endpoint: dict) -> list:
    """Retrieve and display datasources from an endpoint."""
    print(f"{Colors.CYAN}Fetching available datasources from {endpoint['name']}...{Colors.NC}")
    url = f"{endpoint['url']}/datasource/all_sources.json"
    response = make_request(endpoint, 'GET', url)
    if not response:
        return []
    try:
        sources = response.json()
        print(f"{Colors.YELLOW}Found datasources on {endpoint['name']}:{Colors.NC}")
        for i, source in enumerate(sources, 1):
            interface = source.get("kismet.datasource.interface", "N/A")
            name = source.get("kismet.datasource.name", "N/A")
            uuid = source.get("kismet.datasource.uuid", "N/A")
            hopping = source.get("kismet.datasource.hopping", 0)
            
            print(f"{Colors.MAGENTA}{i}. {Colors.BLUE}{interface}{Colors.NC} ({Colors.CYAN}{name}{Colors.NC})")
            if hopping:
                hop_channels = format_hop_channels(source.get("kismet.datasource.hop_channels", []))
                print(f"   Channel: {Colors.GREEN}Hopping{Colors.NC}")
                print(f"   Hopping: {Colors.CYAN}true{Colors.NC}")
                print(f"   Hop Channels: {Colors.YELLOW}{hop_channels}{Colors.NC}")
            else:
                channel = source.get("kismet.datasource.channel", "N/A")
                print(f"   Channel: {Colors.GREEN}{channel}{Colors.NC}")
                print(f"   Hopping: {Colors.RED}false{Colors.NC}")
            print(f"   UUID: {Colors.YELLOW}{uuid}{Colors.NC}")
        return sources
    except json.JSONDecodeError:
        print(f"{Colors.RED}Error: Invalid JSON response from {endpoint['name']}{Colors.NC}")
        return []
    except KeyError as e:
        print(f"{Colors.RED}Error: Unexpected data structure in response from {endpoint['name']}: {e}{Colors.NC}")
        return []

def select_device(sources: list) -> dict:
    """Allow the user to select a device from the list of datasources."""
    print(f"\n{Colors.YELLOW}Available devices:{Colors.NC}")
    for i, source in enumerate(sources, 1):
        interface = source.get("kismet.datasource.interface", "N/A")
        name = source.get("kismet.datasource.name", "N/A")
        print(f"{Colors.MAGENTA}{i}. {Colors.BLUE}{interface}{Colors.NC} ({Colors.CYAN}{name}{Colors.NC})")
    while True:
        try:
            device_choice = int(input(f"{Colors.YELLOW}Enter the device number: {Colors.NC}")) - 1
            if 0 <= device_choice < len(sources):
                selected = sources[device_choice]
                print(f"{Colors.GREEN}Selected device: {Colors.BLUE}{selected.get('kismet.datasource.interface', 'N/A')}{Colors.NC} ({Colors.CYAN}{selected.get('kismet.datasource.name', 'N/A')}{Colors.NC})")
                return selected
            else:
                print(f"{Colors.RED}Invalid device number. Please try again.{Colors.NC}")
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number.{Colors.NC}")

def handle_endpoint_actions(selected_endpoint: dict) -> None:
    """Handle actions for the selected endpoint."""
    while True:
        sources = get_datasources(selected_endpoint)
        if not sources:
            print(f"{Colors.RED}No datasources found or an error occurred. Returning to endpoint selection.{Colors.NC}")
            break

        print(f"{Colors.CYAN}======================================{Colors.NC}")
        print(f"\n{Colors.YELLOW}Choose an action:{Colors.NC}")
        print(f"{Colors.MAGENTA}1. {Colors.NC}Lock channel for a device")
        print(f"{Colors.MAGENTA}2. {Colors.NC}Set device to hopping mode")
        print(f"{Colors.MAGENTA}3. {Colors.NC}Set device to hop between two channels")
        print(f"{Colors.MAGENTA}4. {Colors.NC}Back to endpoint selection")
        choice = input(f"{Colors.YELLOW}Enter your choice (1-4): {Colors.NC}")

        if choice in ['1', '2', '3']:
            selected_device = select_device(sources)
            uuid = selected_device.get("kismet.datasource.uuid")
            interface = selected_device.get("kismet.datasource.interface", "N/A")
            if choice == '1':
                channel = input(f"{Colors.YELLOW}Enter the channel to lock for {interface}: {Colors.NC}")
                lock_channel(selected_endpoint, uuid, channel, interface)
            elif choice == '2':
                print(f"{Colors.YELLOW}Choose hopping mode:{Colors.NC}")
                print(f"{Colors.MAGENTA}1. {Colors.NC}2.4GHz")
                print(f"{Colors.MAGENTA}2. {Colors.NC}5GHz")
                print(f"{Colors.MAGENTA}3. {Colors.NC}Both 2.4GHz and 5GHz")
                hop_choice = input(f"{Colors.YELLOW}Enter your choice (1-3): {Colors.NC}")
                channels = {
                    '1': "1,2,3,4,5,6,7,8,9,10,11,14",
                    '2': "36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,128,132,136,140,144,149,153,157,161,165,169,173,177",
                    '3': "1,2,3,4,5,6,7,8,9,10,11,14,36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,128,132,136,140,144,149,153,157,161,165,169,173,177"
                }.get(hop_choice, "")
                # Using a hop rate of 5 for hopping mode
                set_hopping(selected_endpoint, uuid, 5, channels, interface)
            elif choice == '3':
                channel1 = input(f"{Colors.YELLOW}Enter the first channel to hop: {Colors.NC}")
                channel2 = input(f"{Colors.YELLOW}Enter the second channel to hop: {Colors.NC}")
                channels = [channel1, channel2]
                # Using a fixed hop rate (6) for two-channel hopping
                set_hopping(selected_endpoint, uuid, 6, channels, interface)
        elif choice == '4':
            break
        else:
            print(f"{Colors.RED}Invalid choice. Please enter a number between 1 and 4.{Colors.NC}")
        input(f"{Colors.CYAN}Press Enter to continue...{Colors.NC}")

def select_endpoint(endpoints: list) -> None:
    """Allow the user to select an endpoint and perform actions."""
    while True:
        print(f"\n{Colors.CYAN}======================================{Colors.NC}")
        print(f"{Colors.YELLOW}Available endpoints:{Colors.NC}")
        for i, endpoint in enumerate(endpoints, 1):
            print(f"{Colors.MAGENTA}{i}. {Colors.BLUE}{endpoint['name']}{Colors.NC} ({endpoint['type']})")
        print(f"{Colors.MAGENTA}{len(endpoints) + 1}. {Colors.NC}Back to main menu")
        
        endpoint_choice = input(f"{Colors.YELLOW}Select an endpoint (1-{len(endpoints) + 1}): {Colors.NC}")
        try:
            endpoint_index = int(endpoint_choice) - 1
            if 0 <= endpoint_index < len(endpoints):
                selected_endpoint = endpoints[endpoint_index]
                print(f"{Colors.GREEN}Selected endpoint: {Colors.BLUE}{selected_endpoint['name']}{Colors.NC}")
                handle_endpoint_actions(selected_endpoint)
            elif endpoint_index == len(endpoints):
                break
            else:
                print(f"{Colors.RED}Invalid endpoint number. Please try again.{Colors.NC}")
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number.{Colors.NC}")

def remove_endpoint(endpoints: list) -> None:
    """Allow the user to remove an endpoint from the list."""
    while True:
        print(f"\n{Colors.CYAN}======================================{Colors.NC}")
        print(f"{Colors.YELLOW}Available endpoints:{Colors.NC}")
        for i, endpoint in enumerate(endpoints, 1):
            print(f"{Colors.MAGENTA}{i}. {Colors.BLUE}{endpoint['name']}{Colors.NC} ({endpoint['type']})")
        print(f"{Colors.MAGENTA}{len(endpoints) + 1}. {Colors.NC}Cancel")
        
        endpoint_choice = input(f"{Colors.YELLOW}Select an endpoint to remove (1-{len(endpoints) + 1}): {Colors.NC}")
        try:
            endpoint_index = int(endpoint_choice) - 1
            if 0 <= endpoint_index < len(endpoints):
                removed_endpoint = endpoints.pop(endpoint_index)
                print(f"{Colors.GREEN}Removed endpoint: {Colors.BLUE}{removed_endpoint['name']}{Colors.NC}")
                break
            elif endpoint_index == len(endpoints):
                print(f"{Colors.YELLOW}Cancelled endpoint removal.{Colors.NC}")
                break
            else:
                print(f"{Colors.RED}Invalid endpoint number. Please try again.{Colors.NC}")
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number.{Colors.NC}")

def main() -> None:
    """Main menu loop."""
    endpoints = load_endpoints()

    while True:
        print(f"\n{Colors.CYAN}======================================{Colors.NC}")
        print(f"{Colors.YELLOW}Main Menu:{Colors.NC}")
        print(f"{Colors.MAGENTA}1. {Colors.NC}Select an endpoint")
        print(f"{Colors.MAGENTA}2. {Colors.NC}Add a new endpoint")
        print(f"{Colors.MAGENTA}3. {Colors.NC}Remove an endpoint")
        print(f"{Colors.MAGENTA}4. {Colors.NC}Exit")
        
        choice = input(f"{Colors.YELLOW}Enter your choice (1-4): {Colors.NC}")
        if choice == '1':
            if endpoints:
                select_endpoint(endpoints)
            else:
                print(f"{Colors.RED}No endpoints available. Please add one first.{Colors.NC}")
        elif choice == '2':
            new_endpoint = add_endpoint()
            endpoints.append(new_endpoint)
            save_endpoints(endpoints)
            print(f"{Colors.GREEN}New endpoint added successfully.{Colors.NC}")
        elif choice == '3':
            if endpoints:
                remove_endpoint(endpoints)
                save_endpoints(endpoints)
            else:
                print(f"{Colors.RED}No endpoints available to remove.{Colors.NC}")
        elif choice == '4':
            print(f"{Colors.GREEN}Exiting...{Colors.NC}")
            break
        else:
            print(f"{Colors.RED}Invalid choice. Please enter a number between 1 and 4.{Colors.NC}")

if __name__ == "__main__":
    main()
