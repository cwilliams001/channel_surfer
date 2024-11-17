# This is an austic TUI attempt for  github.com/cwilliams001 program channel_surfer that make it easy to change or lock the channel when using kismet - especially remote instances
# It probably will break in a million different ways, but I'm trying to learn. 

import urwid
import requests
import json
import os
from requests.exceptions import RequestException
from pathlib import Path
import pyfiglet  


def get_config_file_path():
    home_dir = Path.home()
    config_dir = home_dir / ".channel_surfer"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "endpoints.json"

def load_endpoints():
    config_file = get_config_file_path()
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

def save_endpoints(endpoints):
    config_file = get_config_file_path()
    with open(config_file, 'w') as f:
        json.dump(endpoints, f, indent=2)

def format_hop_channels(channels):
    return ' '.join(channels).replace('"', '').replace('[', '').replace(']', '')

def make_request(endpoint, method, url, data=None):
    try:
        response = requests.request(method, url, auth=(endpoint['user'], endpoint['pass']), data=data)
        response.raise_for_status()
        return response
    except RequestException:
        return None

def lock_channel(endpoint, source_uuid, channel, interface):
    url = f"{endpoint['url']}/datasource/by-uuid/{source_uuid}/set_channel.cmd"
    response = make_request(endpoint, 'POST', url, data={"json": json.dumps({"channel": channel})})
    if response and f'"kismet.datasource.channel": "{channel}"' in response.text:
        return True, f"Successfully locked channel {channel} on device {interface}"
    else:
        return False, f"Failed to lock channel {channel} on device {interface}"

def set_hopping_mode(endpoint, source_uuid, hop_rate, channels, interface):
    json_data = {"hop": True, "rate": hop_rate}
    if channels:
        json_data["channels"] = channels.split(',')

    url = f"{endpoint['url']}/datasource/by-uuid/{source_uuid}/set_channel.cmd"
    response = make_request(endpoint, 'POST', url, data={"json": json.dumps(json_data)})

    if response and '"kismet.datasource.hopping": 1' in response.text:
        new_channels = json.loads(response.text)["kismet.datasource.hop_channels"]
        formatted_channels = format_hop_channels(new_channels)
        return True, f"Successfully set hopping mode on device {interface}\nNew hop channels: {formatted_channels}"
    else:
        return False, f"Failed to set hopping mode on device {interface}"

def set_two_channel_hopping(endpoint, source_uuid, channels, interface):
    json_data = {"hop": True, "rate": 6, "channels": channels}

    url = f"{endpoint['url']}/datasource/by-uuid/{source_uuid}/set_channel.cmd"
    response = make_request(endpoint, 'POST', url, data={"json": json.dumps(json_data)})

    if response and '"kismet.datasource.hopping": 1' in response.text:
        new_channels = json.loads(response.text)["kismet.datasource.hop_channels"]
        formatted_channels = format_hop_channels(new_channels)
        return True, f"Successfully set hopping mode on device {interface}\nNew hop channels: {formatted_channels}"
    else:
        return False, f"Failed to set hopping mode on device {interface}"

def get_datasources(endpoint):
    response = make_request(endpoint, 'GET', f"{endpoint['url']}/datasource/all_sources.json")
    if not response:
        return []
    try:
        sources = response.json()
        return sources
    except json.JSONDecodeError:
        return []
    except KeyError:
        return []


class FocusLineBox(urwid.WidgetWrap):
    def __init__(self, widget):
        self.widget = widget
        self.linebox_with_lines = urwid.LineBox(widget)
        self.linebox_without_lines = urwid.LineBox(widget,
            tlcorner=' ', tline=' ', lline=' ', trcorner=' ', blcorner=' ', rline=' ', bline=' ', brcorner=' ')
        self._w = self.linebox_without_lines

    def selectable(self):
        return self.widget.selectable()

    def keypress(self, size, key):
        return self._w.keypress(size, key)

    def mouse_event(self, size, event, button, col, row, focus):
        return self._w.mouse_event(size, event, button, col, row, focus)

    def render(self, size, focus=False):
        if focus:
            self._w = self.linebox_with_lines
        else:
            self._w = self.linebox_without_lines
        return self._w.render(size, focus)

def create_menu_button(caption, callback, user_data=None):
    button = urwid.Button(caption)
    if user_data is not None:
        urwid.connect_signal(button, 'click', callback, user_data)
    else:
        urwid.connect_signal(button, 'click', callback)
    button = FocusLineBox(button)
    return urwid.Padding(button, align='center', width=('relative', 50))

class ChannelSurferApp:
    def __init__(self):
        self.endpoints = load_endpoints()
        self.loop = None
        self.selected_endpoint = None
        self.selected_device = None
        self.sources = []
        self.previous_menu = []
        self.form_pile = None  
        self.list_box = None  

        self.ascii_art = pyfiglet.figlet_format("Channel Surfer", font="small")

    def run(self):
        palette = [
            ('header', 'dark green', 'black'),
            ('reversed', 'standout', ''),
            ('background', '', 'black'),
        ]

        self.main_widget = urwid.AttrMap(urwid.WidgetPlaceholder(self.main_menu()), 'background')
        self.loop = urwid.MainLoop(
            self.main_widget,
            palette=palette,
            unhandled_input=self.handle_input,
            handle_mouse=True  
        )
        self.loop.run()

    def handle_input(self, key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()
        elif key == 'tab':
            if self.form_pile is not None:
                self.move_focus_in_pile(self.form_pile, 1)
            elif self.list_box is not None:
                self.move_focus_in_listbox(self.list_box, 1)
        elif key == 'shift tab':
            if self.form_pile is not None:
                self.move_focus_in_pile(self.form_pile, -1)
            elif self.list_box is not None:
                self.move_focus_in_listbox(self.list_box, -1)

    def move_focus_in_pile(self, pile, direction):
        num_items = len(pile.contents)
        focus_position = pile.focus_position
        for i in range(1, num_items):
            next_position = (focus_position + direction * i) % num_items
            widget, options = pile.contents[next_position]
            if widget.selectable():
                pile.focus_position = next_position
                break

    def move_focus_in_listbox(self, listbox, direction):
        walker = listbox.body
        num_items = len(walker)
        focus_position = walker.focus
        for i in range(1, num_items):
            next_position = (focus_position + direction * i) % num_items
            if walker[next_position].selectable():
                walker.set_focus(next_position)
                break

    def main_menu(self):
        self.form_pile = None  
        self.list_box = None   
        body = [
            urwid.Text(('header', self.ascii_art), align='center'),
            urwid.Divider(),
            create_menu_button("Select an Endpoint", self.select_endpoint),
            create_menu_button("Add a New Endpoint", self.add_endpoint),
            create_menu_button("Remove an Endpoint", self.remove_endpoint),
            create_menu_button("Exit", self.exit_program),
        ]
        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(body))
        self.list_box = listbox  
        return urwid.Padding(listbox, align='center', width=('relative', 60))

    def select_endpoint(self, button):
        self.previous_menu.append(self.main_widget.original_widget)
        self.main_widget.original_widget = self.show_select_endpoint()

    def show_select_endpoint(self):
        self.form_pile = None
        body = [urwid.Text("Select an Endpoint", align='center'), urwid.Divider()]
        if not self.endpoints:
            body.append(urwid.Text("No endpoints available."))
            body.append(create_menu_button("Back", self.go_back))
        else:
            for idx, ep in enumerate(self.endpoints):
                button = create_menu_button(f"{ep['name']} ({ep['type']})", self.endpoint_selected, idx)
                body.append(button)
            body.append(create_menu_button("Back", self.go_back))
        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(body))
        self.list_box = listbox  
        return urwid.Padding(listbox, align='center', width=('relative', 60))

    def endpoint_selected(self, button, idx):
        self.selected_endpoint = self.endpoints[idx]
        self.previous_menu.append(self.main_widget.original_widget)
        self.main_widget.original_widget = self.show_endpoint_menu()

    def show_endpoint_menu(self):
        self.form_pile = None
        ep_name = self.selected_endpoint['name']
        body = [
            urwid.Text(f"Endpoint: {ep_name}", align='center'),
            urwid.Divider(),
            create_menu_button("Lock Channel for a Device", self.lock_channel),
            create_menu_button("Set Device to Hopping Mode", self.set_hopping_mode),
            create_menu_button("Set Device to Hop Between Two Channels", self.set_two_channel_hopping),
            create_menu_button("Back", self.go_back),
        ]
        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(body))
        self.list_box = listbox  
        return urwid.Padding(listbox, align='center', width=('relative', 60))

    def lock_channel(self, button):
        self.select_device("lock_channel")

    def set_hopping_mode(self, button):
        self.select_device("set_hopping_mode")

    def set_two_channel_hopping(self, button):
        self.select_device("set_two_channel_hopping")

    def select_device(self, action):
        self.previous_menu.append(self.main_widget.original_widget)
        self.sources = get_datasources(self.selected_endpoint)
        body = [urwid.Text("Select a Device", align='center'), urwid.Divider()]
        if not self.sources:
            body.append(urwid.Text("No devices available."))
            body.append(create_menu_button("Back", self.go_back))
        else:
            for idx, source in enumerate(self.sources):
                interface = source.get("kismet.datasource.interface", "")
                name = source.get("kismet.datasource.name", "")
                button = create_menu_button(f"{interface} ({name})", self.device_selected, (idx, action))
                body.append(button)
            body.append(create_menu_button("Back", self.go_back))
        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(body))
        self.list_box = listbox  
        self.main_widget.original_widget = urwid.Padding(listbox, align='center', width=('relative', 60))

    def device_selected(self, button, data):
        idx, action = data
        self.selected_device = self.sources[idx]
        if action == "lock_channel":
            self.lock_channel_prompt()
        elif action == "set_hopping_mode":
            self.set_hopping_mode_prompt()
        elif action == "set_two_channel_hopping":
            self.set_two_channel_hopping_prompt()

    def lock_channel_prompt(self):
        self.previous_menu.append(self.main_widget.original_widget)
        channel_edit = urwid.Edit("Enter the Channel to Lock: ")
        submit_button = create_menu_button("Submit", self.perform_lock_channel, channel_edit)
        back_button = create_menu_button("Back", self.go_back)
        body = [
            urwid.Text("Lock Channel", align='center'),
            urwid.Divider(),
            urwid.Padding(channel_edit, align='center', width=('relative', 50)),
            urwid.Divider(),
            submit_button,
            back_button
        ]
        pile = urwid.Pile(body)
        self.form_pile = pile  
        fill = urwid.Filler(pile, valign='top')
        self.main_widget.original_widget = urwid.Padding(fill, align='center', width=('relative', 60))

    def perform_lock_channel(self, button, channel_edit):
        channel = channel_edit.edit_text.strip()
        success, message = lock_channel(
            self.selected_endpoint,
            self.selected_device["kismet.datasource.uuid"],
            channel,
            self.selected_device["kismet.datasource.interface"]
        )
        self.previous_menu = []  
        self.show_message(message)

    def set_hopping_mode_prompt(self):
        self.previous_menu.append(self.main_widget.original_widget)
        options = [
            ("2.4GHz", "hop_2_4ghz"),
            ("5GHz", "hop_5ghz"),
            ("Both 2.4GHz and 5GHz", "hop_both"),
        ]
        body = [urwid.Text("Select Hopping Mode", align='center'), urwid.Divider()]
        for label, action in options:
            button = create_menu_button(label, self.perform_set_hopping_mode, action)
            body.append(button)
        body.append(create_menu_button("Back", self.go_back))
        pile = urwid.Pile(body)
        self.form_pile = pile  
        fill = urwid.Filler(pile, valign='top')
        self.main_widget.original_widget = urwid.Padding(fill, align='center', width=('relative', 60))

    def perform_set_hopping_mode(self, button, action):
        if action == "hop_2_4ghz":
            channels = "1,2,3,4,5,6,7,8,9,10,11,14"
        elif action == "hop_5ghz":
            channels = "36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,128,132,136,140,144,149,153,157,161,165,169,173,177"
        elif action == "hop_both":
            channels = "1,2,3,4,5,6,7,8,9,10,11,14," \
                       "36,40,44,48,52,56,60,64,100,104,108,112," \
                       "116,120,124,128,132,136,140,144,149,153," \
                       "157,161,165,169,173,177"
        else:
            channels = ""
        success, message = set_hopping_mode(
            self.selected_endpoint,
            self.selected_device["kismet.datasource.uuid"],
            5,  
            channels,
            self.selected_device["kismet.datasource.interface"]
        )
        self.previous_menu = []  
        self.show_message(message)

    def set_two_channel_hopping_prompt(self):
        self.previous_menu.append(self.main_widget.original_widget)
        channels_edit = urwid.Edit("Enter the Two Channels to Hop Between (comma-separated): ")
        submit_button = create_menu_button("Submit", self.perform_set_two_channel_hopping, channels_edit)
        back_button = create_menu_button("Back", self.go_back)
        body = [
            urwid.Text("Set Two Channel Hopping", align='center'),
            urwid.Divider(),
            urwid.Padding(channels_edit, align='center', width=('relative', 50)),
            urwid.Divider(),
            submit_button,
            back_button
        ]
        pile = urwid.Pile(body)
        self.form_pile = pile  
        fill = urwid.Filler(pile, valign='top')
        self.main_widget.original_widget = urwid.Padding(fill, align='center', width=('relative', 60))

    def perform_set_two_channel_hopping(self, button, channels_edit):
        channels = channels_edit.edit_text.strip().split(",")
        success, message = set_two_channel_hopping(
            self.selected_endpoint,
            self.selected_device["kismet.datasource.uuid"],
            channels,
            self.selected_device["kismet.datasource.interface"]
        )
        self.previous_menu = []  
        self.show_message(message)

    def add_endpoint(self, button):
        self.previous_menu.append(self.main_widget.original_widget)
        self.name_edit = urwid.Edit("Endpoint Name: ")
        self.url_edit = urwid.Edit("Endpoint URL: ")
        self.type_edit = urwid.Edit("Endpoint Type: ")
        self.user_edit = urwid.Edit("Kismet Username: ")
        self.pass_edit = urwid.Edit("Kismet Password: ", mask='*')
        submit_button = create_menu_button("Submit", self.perform_add_endpoint)
        back_button = create_menu_button("Back", self.go_back)
        body = [
            urwid.Text("Add a New Endpoint", align='center'),
            urwid.Divider(),
            urwid.Padding(self.name_edit, align='center', width=('relative', 50)),
            urwid.Padding(self.url_edit, align='center', width=('relative', 50)),
            urwid.Padding(self.type_edit, align='center', width=('relative', 50)),
            urwid.Padding(self.user_edit, align='center', width=('relative', 50)),
            urwid.Padding(self.pass_edit, align='center', width=('relative', 50)),
            urwid.Divider(),
            submit_button,
            back_button
        ]
        pile = urwid.Pile(body)
        self.form_pile = pile  
        fill = urwid.Filler(pile, valign='top')
        self.main_widget.original_widget = urwid.Padding(fill, align='center', width=('relative', 60))

    def perform_add_endpoint(self, button):
        new_endpoint = {
            "name": self.name_edit.edit_text.strip(),
            "url": self.url_edit.edit_text.strip(),
            "type": self.type_edit.edit_text.strip(),
            "user": self.user_edit.edit_text.strip(),
            "pass": self.pass_edit.edit_text.strip()
        }
        self.endpoints.append(new_endpoint)
        save_endpoints(self.endpoints)
        self.previous_menu = []
        self.show_message("New endpoint added successfully.")

    def remove_endpoint(self, button):
        self.previous_menu.append(self.main_widget.original_widget)
        body = [urwid.Text("Remove an Endpoint", align='center'), urwid.Divider()]
        if not self.endpoints:
            body.append(urwid.Text("No endpoints to remove."))
            body.append(create_menu_button("Back", self.go_back))
        else:
            for idx, ep in enumerate(self.endpoints):
                button = create_menu_button(f"{ep['name']} ({ep['type']})", self.perform_remove_endpoint, idx)
                body.append(button)
            body.append(create_menu_button("Back", self.go_back))
        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(body))
        self.list_box = listbox  
        self.main_widget.original_widget = urwid.Padding(listbox, align='center', width=('relative', 60))

    def perform_remove_endpoint(self, button, idx):
        removed_endpoint = self.endpoints.pop(idx)
        save_endpoints(self.endpoints)
        self.previous_menu = []  
        self.show_message(f"Removed endpoint: {removed_endpoint['name']}")

    def show_message(self, message):
        self.form_pile = None  
        self.list_box = None  
        self.previous_menu.append(self.main_widget.original_widget)
        text = urwid.Text(message, align='center')
        ok_button = create_menu_button("OK", self.go_back)
        body = [
            text,
            urwid.Divider(),
            ok_button
        ]
        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(body))
        self.list_box = listbox  
        self.main_widget.original_widget = urwid.Padding(listbox, align='center', width=('relative', 60))

    def go_back(self, button):
        self.form_pile = None 
        self.list_box = None 
        if self.previous_menu:
            self.main_widget.original_widget = self.previous_menu.pop()
        else:
            self.main_widget.original_widget = self.main_menu()

    def exit_program(self, button):
        raise urwid.ExitMainLoop()

if __name__ == "__main__":
    app = ChannelSurferApp()
    app.run()

