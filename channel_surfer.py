#!/bin/python3
import requests
import json
import time
import os
from requests.exceptions import RequestException

# Kismet API credentials
KISMET_USER = "a"
KISMET_PASS = "a"

# List of endpoints
ENDPOINTS = [
    {"name": "Local Connection", "url": "http://127.0.0.1:2501", "type": "local"},
    {"name": "mint-rad (VPN)", "url": "http://11.0.0.4:2501", "type": "vpn"},
    {"name": "vz-rad (VPN)", "url": "http://10.0.0.5:2501", "type": "vpn"},
    # Add more endpoints as needed
]

# ANSI color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

def format_hop_channels(channels):
    return ' '.join(channels).replace('"', '').replace('[', '').replace(']', '')

def make_request(endpoint, method, url, data=None):
    try:
        response = requests.request(method, url, auth=(KISMET_USER, KISMET_PASS), data=data)
        response.raise_for_status()
        return response
    except RequestException as e:
        print(f"{Colors.RED}Error connecting to {endpoint['name']}: {str(e)}{Colors.NC}")
        return None

def lock_channel(endpoint, source_uuid, channel, interface):
    url = f"{endpoint['url']}/datasource/by-uuid/{source_uuid}/set_channel.cmd"
    response = make_request(endpoint, 'POST', url, data={"json": json.dumps({"channel": channel})})
    if response and f'"kismet.datasource.channel": "{channel}"' in response.text:
        print(f"{Colors.GREEN}Successfully locked channel {channel} on device {interface}{Colors.NC}")
    else:
        print(f"{Colors.RED}Failed to lock channel {channel} on device {interface}{Colors.NC}")

def set_hopping_mode(endpoint, source_uuid, hop_rate, channels, interface):
    json_data = {"hop": True, "rate": hop_rate}
    if channels:
        json_data["channels"] = channels.split(',')
    
    url = f"{endpoint['url']}/datasource/by-uuid/{source_uuid}/set_channel.cmd"
    response = make_request(endpoint, 'POST', url, data={"json": json.dumps(json_data)})
    
    if response and '"kismet.datasource.hopping": 1' in response.text:
        print(f"{Colors.GREEN}Successfully set hopping mode on device {interface}{Colors.NC}")
        new_channels = json.loads(response.text)["kismet.datasource.hop_channels"]
        formatted_channels = format_hop_channels(new_channels)
        print(f"{Colors.YELLOW}New hop channels: {formatted_channels}{Colors.NC}")
    else:
        print(f"{Colors.RED}Failed to set hopping mode on device {interface}{Colors.NC}")

def set_two_channel_hopping(endpoint, source_uuid, channels, interface):
    json_data = {"hop": True, "rate": 6, "channels": channels}
    
    url = f"{endpoint['url']}/datasource/by-uuid/{source_uuid}/set_channel.cmd"
    response = make_request(endpoint, 'POST', url, data={"json": json.dumps(json_data)})
    
    if response and '"kismet.datasource.hopping": 1' in response.text:
        print(f"{Colors.GREEN}Successfully set hopping mode on device {interface}{Colors.NC}")
        new_channels = json.loads(response.text)["kismet.datasource.hop_channels"]
        formatted_channels = format_hop_channels(new_channels)
        print(f"{Colors.YELLOW}New hop channels: {formatted_channels}{Colors.NC}")
    else:
        print(f"{Colors.RED}Failed to set hopping mode on device {interface}{Colors.NC}")

def get_datasources(endpoint):
    print(f"{Colors.CYAN}Fetching available datasources from {endpoint['name']}...{Colors.NC}")
    response = make_request(endpoint, 'GET', f"{endpoint['url']}/datasource/all_sources.json")
    if not response:
        return []

    try:
        sources = response.json()
        print(f"{Colors.YELLOW}Found datasources on {endpoint['name']}:{Colors.NC}")
        for i, source in enumerate(sources, 1):
            interface = source["kismet.datasource.interface"]
            name = source["kismet.datasource.name"]
            uuid = source["kismet.datasource.uuid"]
            hopping = source["kismet.datasource.hopping"]
            
            print(f"{Colors.MAGENTA}{i}. {Colors.BLUE}{interface}{Colors.NC} ({Colors.CYAN}{name}{Colors.NC})")
            
            if hopping:
                print(f"   Channel: {Colors.GREEN}Hopping{Colors.NC}")
                print(f"   Hopping: {Colors.CYAN}true{Colors.NC}")
                hop_channels = format_hop_channels(source["kismet.datasource.hop_channels"])
                print(f"   Hop Channels: {Colors.YELLOW}{hop_channels}{Colors.NC}")
            else:
                channel = source["kismet.datasource.channel"]
                print(f"   Channel: {Colors.GREEN}{channel}{Colors.NC}")
                print(f"   Hopping: {Colors.RED}false{Colors.NC}")
            
            print(f"   UUID: {Colors.YELLOW}{uuid}{Colors.NC}")
        
        return sources
    except json.JSONDecodeError:
        print(f"{Colors.RED}Error: Invalid JSON response from {endpoint['name']}{Colors.NC}")
        return []
    except KeyError as e:
        print(f"{Colors.RED}Error: Unexpected data structure in response from {endpoint['name']}: {str(e)}{Colors.NC}")
        return []

def main():
    while True:
        print(f"\n{Colors.CYAN}======================================{Colors.NC}")
        print(f"{Colors.YELLOW}Available endpoints:{Colors.NC}")
        for i, endpoint in enumerate(ENDPOINTS, 1):
            print(f"{Colors.MAGENTA}{i}. {Colors.BLUE}{endpoint['name']}{Colors.NC} ({endpoint['type']})")
        
        endpoint_choice = input(f"{Colors.YELLOW}Select an endpoint (1-{len(ENDPOINTS)}), or 'q' to quit: {Colors.NC}")
        
        if endpoint_choice.lower() == 'q':
            print(f"{Colors.GREEN}Exiting...{Colors.NC}")
            break
        
        try:
            endpoint_index = int(endpoint_choice) - 1
            if 0 <= endpoint_index < len(ENDPOINTS):
                selected_endpoint = ENDPOINTS[endpoint_index]
                print(f"{Colors.GREEN}Selected endpoint: {Colors.BLUE}{selected_endpoint['name']}{Colors.NC}")
            else:
                print(f"{Colors.RED}Invalid endpoint number. Please try again.{Colors.NC}")
                continue
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number or 'q' to quit.{Colors.NC}")
            continue

        while True:
            sources = get_datasources(selected_endpoint)
            if not sources:
                print(f"{Colors.RED}No datasources found or error occurred. Returning to endpoint selection.{Colors.NC}")
                break

            print(f"{Colors.CYAN}======================================{Colors.NC}")
            print(f"\n{Colors.YELLOW}Choose an action:{Colors.NC}")
            print(f"{Colors.MAGENTA}1. {Colors.NC}Lock channel for a device")
            print(f"{Colors.MAGENTA}2. {Colors.NC}Set device to hopping mode")
            print(f"{Colors.MAGENTA}3. {Colors.NC}Set device to hop between two channels")
            print(f"{Colors.MAGENTA}4. {Colors.NC}Back to endpoint selection")
            choice = input(f"{Colors.YELLOW}Enter your choice (1-3): {Colors.NC}")

            if choice in ['1', '2', '3']:
                print(f"\n{Colors.YELLOW}Available devices:{Colors.NC}")
                for i, source in enumerate(sources, 1):
                    interface = source["kismet.datasource.interface"]
                    name = source["kismet.datasource.name"]
                    print(f"{Colors.MAGENTA}{i}. {Colors.BLUE}{interface}{Colors.NC} ({Colors.CYAN}{name}{Colors.NC})")
                
                while True:
                    try:
                        device_num = int(input(f"{Colors.YELLOW}Enter the device number: {Colors.NC}")) - 1
                        if 0 <= device_num < len(sources):
                            selected_device = sources[device_num]
                            print(f"{Colors.GREEN}Selected device: {Colors.BLUE}{selected_device['kismet.datasource.interface']}{Colors.NC} ({Colors.CYAN}{selected_device['kismet.datasource.name']}{Colors.NC})")
                            break
                        else:
                            print(f"{Colors.RED}Invalid device number. Please try again.{Colors.NC}")
                    except ValueError:
                        print(f"{Colors.RED}Please enter a valid number.{Colors.NC}")

                if choice == '1':
                    channel = input(f"{Colors.YELLOW}Enter the channel to lock for {selected_device['kismet.datasource.interface']}: {Colors.NC}")
                    lock_channel(selected_endpoint, selected_device["kismet.datasource.uuid"], channel, selected_device["kismet.datasource.interface"])
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
                    
                    set_hopping_mode(selected_endpoint, selected_device["kismet.datasource.uuid"], 5, channels, selected_device["kismet.datasource.interface"])
                elif choice == '3':
                    channel1 = input(f"{Colors.YELLOW}Enter the first channel to hop: {Colors.NC}")
                    channel2 = input(f"{Colors.YELLOW}Enter the second channel to hop: {Colors.NC}")
                    channels = [channel1, channel2]
                    set_two_channel_hopping(selected_endpoint, selected_device["kismet.datasource.uuid"], channels, selected_device["kismet.datasource.interface"])
            elif choice == '4':
                break
            else:
                print(f"{Colors.RED}Invalid choice. Please enter a number between 1 and 4.{Colors.NC}")
            time.sleep(2)

if __name__ == "__main__":
    main()