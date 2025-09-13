from typing import Literal, TypedDict, Dict, Any, List
import asyncio
import sys
import yaml
from tapo import ApiClient

# Types stricts pour les devices et commandes
DeviceType = Literal["P110", "P110M", "L530", "L510", "L520"]
DeviceActionP110 = Literal["on", "off"]
DeviceActionP110M = Literal["on", "off"]
DeviceActionL530 = Literal["on", "off", "set_brightness", "set_color"]
DeviceActionL510 = Literal["on", "off", "set_brightness"]
DeviceActionL520 = Literal["on", "off", "set_brightness"]

class DeviceConfig(TypedDict):
    type: DeviceType
    ip: str

class Credentials(TypedDict):
    email: str
    password: str

class Config(TypedDict):
    credentials: Credentials
    devices: Dict[str, DeviceConfig]

async def load_config(path: str = "config.yaml") -> Config:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

async def main():
    if len(sys.argv) < 3:
        print("Usage: python tapo_remote.py <nom_appareil> <commande> [options]")
        print("Exemples:")
        print("  python tapo_remote.py salon_lampe on")
        print("  python tapo_remote.py salon_lampe set_brightness 50")
        print("  python tapo_remote.py salon_lampe set_color 255 0 0")
        sys.exit(1)

    device_name: str = sys.argv[1]
    command: str = sys.argv[2]
    args: List[str] = sys.argv[3:]

    config: Config = await load_config(path="E:/Nicolas/Workspace/MarkIO/Scripts/BT_TAPO/config.yaml")
    email: str = config["credentials"]["email"]
    password: str = config["credentials"]["password"]

    if device_name not in config["devices"]:
        print(f"Appareil {device_name} introuvable dans config.yaml")
        sys.exit(1)

    device_info: DeviceConfig = config["devices"][device_name]
    device_type: DeviceType = device_info["type"]
    ip: str = device_info["ip"]

    client = ApiClient(email, password)
    device = await getattr(client, device_type.lower())(ip)

    # Validation stricte des commandes
    allowed_actions = {
        "P110": ["on", "off"],
        "P110M": ["on", "off"],
        "L530": ["on", "off", "set_brightness", "set_color"],
        "L510": ["on", "off", "set_brightness"],
        "L520": ["on", "off", "set_brightness"],
    }
    if command not in allowed_actions[device_type]:
        print(f"La commande {command} n'est pas autorisée pour le type {device_type}.")
        sys.exit(1)

    func = getattr(device, command)
    parsed_args: List[Any] = [int(a) if a.isdigit() else a for a in args]
    result = await func(*parsed_args)
    print("Commande exécutée:", result)

if __name__ == "__main__":
    asyncio.run(main())
