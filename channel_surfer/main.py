#!/usr/bin/env python3
import json
from pathlib import Path
import requests
from requests.exceptions import RequestException

from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.table import Table

console = Console()

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
        console.print("[yellow]Endpoints configuration file not found. Starting with an empty list.[/yellow]")
        return []
    except json.JSONDecodeError:
        console.print("[red]Error decoding the endpoints configuration file. Starting with an empty list.[/red]")
        return []

def save_endpoints(endpoints: list) -> None:
    """Save endpoints to the configuration file."""
    config_file = get_config_file_path()
    with open(config_file, 'w') as f:
        json.dump(endpoints, f, indent=2)

def add_endpoint() -> dict:
    """Prompt user to add a new endpoint."""
    name = Prompt.ask("[yellow]Enter endpoint name[/yellow]")
    url = Prompt.ask("[yellow]Enter endpoint URL (http://<ip>:<port>)[/yellow]")
    endpoint_type = Prompt.ask("[yellow]Enter endpoint type (e.g., local, vpn)[/yellow]")
    user = Prompt.ask("[yellow]Enter Kismet username[/yellow]")
    password = Prompt.ask("[yellow]Enter Kismet password[/yellow]", password=True)
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
        console.print(f"[red]Error connecting to {endpoint['name']}: {e}[/red]")
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
                console.print(f"[green]Successfully locked channel {channel} on device {interface}[/green]")
            else:
                console.print(f"[red]Failed to lock channel {channel} on device {interface}[/red]")
        except json.JSONDecodeError:
            console.print(f"[red]Failed to decode response when locking channel on device {interface}[/red]")
    else:
        console.print(f"[red]Request failed for locking channel on device {interface}[/red]")

def set_hopping(endpoint: dict, source_uuid: str, hop_rate: int, channels, interface: str) -> None:
    """
    Set hopping mode on a device.
    The 'channels' parameter can be a comma-separated string or a list.
    """
    json_data = {"hop": True, "rate": hop_rate}
    if channels:
        if isinstance(channels, str):
            json_data["channels"] = [ch.strip() for ch in channels.split(',') if ch.strip()]
        else:
            json_data["channels"] = channels
    url = f"{endpoint['url']}/datasource/by-uuid/{source_uuid}/set_channel.cmd"
    response = make_request(endpoint, 'POST', url, data={"json": json.dumps(json_data)})
    if response:
        try:
            data = response.json()
            if data.get("kismet.datasource.hopping") == 1:
                console.print(f"[green]Successfully set hopping mode on device {interface}[/green]")
                new_channels = data.get("kismet.datasource.hop_channels", [])
                formatted_channels = format_hop_channels(new_channels)
                console.print(f"[yellow]New hop channels: {formatted_channels}[/yellow]")
            else:
                console.print(f"[red]Failed to set hopping mode on device {interface}[/red]")
        except json.JSONDecodeError:
            console.print(f"[red]Failed to decode response when setting hopping mode on device {interface}[/red]")
    else:
        console.print(f"[red]Request failed for setting hopping mode on device {interface}[/red]")

def get_datasources(endpoint: dict) -> list:
    """Retrieve and display datasources from an endpoint."""
    console.print(f"[cyan]Fetching available datasources from {endpoint['name']}...[/cyan]")
    url = f"{endpoint['url']}/datasource/all_sources.json"
    response = make_request(endpoint, 'GET', url)
    if not response:
        return []
    try:
        sources = response.json()
        console.print(f"[yellow]Found datasources on {endpoint['name']}:[/yellow]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("No.", style="dim", width=6)
        table.add_column("Interface", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Channel/Hopping", style="yellow")
        table.add_column("UUID", style="white")
        for i, source in enumerate(sources, 1):
            interface = source.get("kismet.datasource.interface", "N/A")
            name = source.get("kismet.datasource.name", "N/A")
            uuid = source.get("kismet.datasource.uuid", "N/A")
            hopping = source.get("kismet.datasource.hopping", 0)
            if hopping:
                hop_channels = format_hop_channels(source.get("kismet.datasource.hop_channels", []))
                channel_info = f"Hopping ({hop_channels})"
            else:
                channel_info = f"{source.get('kismet.datasource.channel', 'N/A')}"
            table.add_row(str(i), interface, name, channel_info, uuid)
        console.print(table)
        return sources
    except json.JSONDecodeError:
        console.print(f"[red]Error: Invalid JSON response from {endpoint['name']}[/red]")
        return []
    except KeyError as e:
        console.print(f"[red]Error: Unexpected data structure in response from {endpoint['name']}: {e}[/red]")
        return []

def select_device(sources: list) -> dict:
    """Allow the user to select a device from the list of datasources."""
    console.print("\n[yellow]Select a device by its number:[/yellow]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("No.", style="dim", width=6)
    table.add_column("Interface", style="cyan")
    table.add_column("Name", style="green")
    for i, source in enumerate(sources, 1):
        interface = source.get("kismet.datasource.interface", "N/A")
        name = source.get("kismet.datasource.name", "N/A")
        table.add_row(str(i), interface, name)
    console.print(table)
    while True:
        try:
            device_choice = IntPrompt.ask("[yellow]Enter the device number[/yellow]", default=1) - 1
            if 0 <= device_choice < len(sources):
                selected = sources[device_choice]
                console.print(f"[green]Selected device: {selected.get('kismet.datasource.interface', 'N/A')} "
                              f"({selected.get('kismet.datasource.name', 'N/A')})[/green]")
                return selected
            else:
                console.print("[red]Invalid device number. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")

def handle_endpoint_actions(selected_endpoint: dict) -> None:
    """Handle actions for the selected endpoint."""
    while True:
        sources = get_datasources(selected_endpoint)
        if not sources:
            console.print("[red]No datasources found or an error occurred. Returning to endpoint selection.[/red]")
            break
        console.rule("[cyan]Device Actions[/cyan]")
        console.print("[yellow]Choose an action:[/yellow]")
        console.print("[magenta]1.[/magenta] Lock channel for a device")
        console.print("[magenta]2.[/magenta] Set device to hopping mode")
        console.print("[magenta]3.[/magenta] Set device to hop between two channels")
        console.print("[magenta]4.[/magenta] Set device to efficient channels hopping")
        console.print("[magenta]5.[/magenta] Back to endpoint selection")
        choice = Prompt.ask("[yellow]Enter your choice (1-5)[/yellow]")
        if choice in ['1', '2', '3', '4']:
            selected_device = select_device(sources)
            uuid = selected_device.get("kismet.datasource.uuid")
            interface = selected_device.get("kismet.datasource.interface", "N/A")
            if choice == '1':
                channel = Prompt.ask(f"[yellow]Enter the channel to lock for {interface}[/yellow]")
                lock_channel(selected_endpoint, uuid, channel, interface)
            elif choice == '2':
                console.print("[yellow]Choose hopping mode:[/yellow]")
                console.print("[magenta]1.[/magenta] 2.4GHz")
                console.print("[magenta]2.[/magenta] 5GHz")
                console.print("[magenta]3.[/magenta] Both 2.4GHz and 5GHz")
                hop_choice = Prompt.ask("[yellow]Enter your choice (1-3)[/yellow]")
                channels = {
                    '1': "1,2,3,4,5,6,7,8,9,10,11,14",
                    '2': "36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,128,132,136,140,144,149,153,157,161,165,169,173,177",
                    '3': "1,2,3,4,5,6,7,8,9,10,11,14,36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,128,132,136,140,144,149,153,157,161,165,169,173,177"
                }.get(hop_choice, "")
                set_hopping(selected_endpoint, uuid, 5, channels, interface)
            elif choice == '3':
                channel1 = Prompt.ask(f"[yellow]Enter the first channel to hop for {interface}[/yellow]")
                channel2 = Prompt.ask(f"[yellow]Enter the second channel to hop for {interface}[/yellow]")
                channels = [channel1, channel2]
                set_hopping(selected_endpoint, uuid, 6, channels, interface)
            elif choice == '4':
                console.print("[yellow]Choose efficient channel option:[/yellow]")
                console.print("[magenta]1.[/magenta] 2.4GHz (channels 1,6,11)")
                console.print("[magenta]2.[/magenta] 5GHz (channels 36,40,44,48,149,153,157,161)")
                console.print("[magenta]3.[/magenta] Both 2.4GHz and 5GHz (all efficient channels)")
                eff_choice = Prompt.ask("[yellow]Enter your choice (1-3)[/yellow]")
                channels = {
                    '1': "1,6,11",
                    '2': "36,40,44,48,149,153,157,161",
                    '3': "1,6,11,36,40,44,48,149,153,157,161"
                }.get(eff_choice, "")
                if channels:
                    set_hopping(selected_endpoint, uuid, 5, channels, interface)
                else:
                    console.print("[red]Invalid choice for efficient channels. Returning to device selection.[/red]")
        elif choice == '5':
            break
        else:
            console.print("[red]Invalid choice. Please enter a number between 1 and 5.[/red]")
        Prompt.ask("[cyan]Press Enter to continue...[/cyan]", default="")

def select_endpoint(endpoints: list) -> None:
    """Allow the user to select an endpoint and perform actions."""
    while True:
        console.rule("[cyan]Endpoint Selection[/cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("No.", style="dim", width=6)
        table.add_column("Name", style="blue")
        table.add_column("Type", style="green")
        for i, endpoint in enumerate(endpoints, 1):
            table.add_row(str(i), endpoint['name'], endpoint['type'])
        table.add_row(str(len(endpoints) + 1), "Back to main menu", "")
        console.print(table)
        endpoint_choice = Prompt.ask(f"[yellow]Select an endpoint (1-{len(endpoints) + 1})[/yellow]")
        try:
            endpoint_index = int(endpoint_choice) - 1
            if 0 <= endpoint_index < len(endpoints):
                selected_endpoint = endpoints[endpoint_index]
                console.print(f"[green]Selected endpoint: {selected_endpoint['name']}[/green]")
                handle_endpoint_actions(selected_endpoint)
            elif endpoint_index == len(endpoints):
                break
            else:
                console.print("[red]Invalid endpoint number. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")

def remove_endpoint(endpoints: list) -> None:
    """Allow the user to remove an endpoint from the list."""
    while True:
        console.rule("[cyan]Remove Endpoint[/cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("No.", style="dim", width=6)
        table.add_column("Name", style="blue")
        table.add_column("Type", style="green")
        for i, endpoint in enumerate(endpoints, 1):
            table.add_row(str(i), endpoint['name'], endpoint['type'])
        table.add_row(str(len(endpoints) + 1), "Cancel", "")
        console.print(table)
        endpoint_choice = Prompt.ask(f"[yellow]Select an endpoint to remove (1-{len(endpoints) + 1})[/yellow]")
        try:
            endpoint_index = int(endpoint_choice) - 1
            if 0 <= endpoint_index < len(endpoints):
                removed_endpoint = endpoints.pop(endpoint_index)
                console.print(f"[green]Removed endpoint: {removed_endpoint['name']}[/green]")
                break
            elif endpoint_index == len(endpoints):
                console.print("[yellow]Cancelled endpoint removal.[/yellow]")
                break
            else:
                console.print("[red]Invalid endpoint number. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")

def main() -> None:
    """Main menu loop."""
    endpoints = load_endpoints()
    while True:
        console.rule("[cyan]Main Menu[/cyan]")
        console.print("[magenta]1.[/magenta] Select an endpoint")
        console.print("[magenta]2.[/magenta] Add a new endpoint")
        console.print("[magenta]3.[/magenta] Remove an endpoint")
        console.print("[magenta]4.[/magenta] Exit")
        choice = Prompt.ask("[yellow]Enter your choice (1-4)[/yellow]")
        if choice == '1':
            if endpoints:
                select_endpoint(endpoints)
            else:
                console.print("[red]No endpoints available. Please add one first.[/red]")
        elif choice == '2':
            new_endpoint = add_endpoint()
            endpoints.append(new_endpoint)
            save_endpoints(endpoints)
            console.print("[green]New endpoint added successfully.[/green]")
        elif choice == '3':
            if endpoints:
                remove_endpoint(endpoints)
                save_endpoints(endpoints)
            else:
                console.print("[red]No endpoints available to remove.[/red]")
        elif choice == '4':
            console.print("[green]Exiting...[/green]")
            break
        else:
            console.print("[red]Invalid choice. Please enter a number between 1 and 4.[/red]")

if __name__ == "__main__":
    main()
