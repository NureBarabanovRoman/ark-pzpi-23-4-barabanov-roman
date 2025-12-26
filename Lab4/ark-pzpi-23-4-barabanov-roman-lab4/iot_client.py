import json
import time
import math
import random
import requests
import sys
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class SmartPollingTerminal:
    def __init__(self, config_file="config.json"):
        self.load_config(config_file)
        self.battery = 100.0
        self.rssi = -60
        self.temperature = 36.6
        self.is_registered = False
        self.last_log = "System initialized..."
        self.start_time = time.time()

    def load_config(self, filename):
        try:
            with open(filename, "r") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            console.print("[bold red]Config file not found![/bold red]")
            sys.exit(1)

    def register(self):
        url = f"{self.config['server_url']}/iot/register"
        payload = {
            "device_id": self.config['device_id'],
            "device_type": self.config['device_type'],
            "room_id": self.config['room_id']
        }
        try:
            resp = requests.post(url, json=payload, timeout=2)
            if resp.status_code == 200:
                self.is_registered = True
                self.last_log = "[green]Connected to Server[/green]"
            else:
                self.last_log = f"[red]Registration Error: {resp.status_code}[/red]"
        except:
            self.last_log = "[bold red]Server Unreachable[/bold red]"

    def update_physics(self):
        uptime = time.time() - self.start_time
        self.battery = max(0, 100 - (uptime * 0.1))
        self.rssi = -60 + int(5 * math.sin(uptime)) + random.randint(-2, 2)
        self.temperature = 36.6 + math.sin(uptime * 0.5) * 2

    def send_click(self, btn_index):
        if not self.is_registered:
            self.last_log = "[yellow]Waiting for connection...[/yellow]"
            self.register()
            return

        url = f"{self.config['server_url']}/iot/click"
        payload = {"device_id": self.config['device_id'], "button_index": btn_index}
        try:
            resp = requests.post(url, json=payload, timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                self.last_log = f"[cyan]VOTED:[/cyan] {data.get('choice')} ({data.get('poll')})"
            else:
                self.last_log = f"[red]Server Error:[/red] {resp.text}"
        except Exception as e:
            self.last_log = f"[red]Network Error[/red]"

    def draw_ui(self):
        os.system('cls' if os.name == 'nt' else 'clear')

        table = Table(title=f"Smart Vote Terminal: {self.config['device_id']}", expand=True)
        table.add_column("Sensor", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_column("Status", style="green")

        bat_style = "green" if self.battery > 30 else "red blink"
        rssi_style = "green" if self.rssi > -70 else "yellow"
        temp_style = "green" if self.temperature < 40 else "red blink"

        table.add_row("Battery", f"[{bat_style}]{self.battery:.1f} %[/]", "OK" if self.battery > 0 else "DEAD")
        table.add_row("Signal", f"[{rssi_style}]{self.rssi} dBm[/]", "Strong" if self.rssi > -70 else "Weak")
        table.add_row("Temp", f"[{temp_style}]{self.temperature:.1f} °C[/]",
                      "Normal" if self.temperature < 40 else "OVERHEAT")
        table.add_row("Room", self.config['room_id'], "Active")

        console.print(table)
        console.print(Panel(self.last_log, title="Last Event", border_style="blue"))
        console.print("\n[bold]Controls:[/bold] [0/1] Vote | [r] Reconnect | [q] Quit")

    def run(self):
        self.register()
        while True:
            self.update_physics()
            self.draw_ui()

            choice = console.input("[bold yellow]Action > [/bold yellow]")

            if choice.lower() == 'q':
                break
            elif choice.lower() == 'r':
                self.register()
            elif choice.isdigit():
                self.send_click(int(choice))
            else:
                self.last_log = "[yellow]Invalid command[/yellow]"


if __name__ == "__main__":
    client = SmartPollingTerminal()
    client.run()