import asyncio
import sys
import yaml
from tapo import ApiClient

async def load_config(path="config.yaml"):
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

    device_name = sys.argv[1]
    command = sys.argv[2]
    args = sys.argv[3:]

    config = await load_config(path="E:/Nicolas/Workspace/MarkIO/Scripts/BT_TAPO/config.yaml")
    email = config["credentials"]["email"]
    password = config["credentials"]["password"]

    if device_name not in config["devices"]:
        print(f"Appareil {device_name} introuvable dans config.yaml")
        sys.exit(1)

    device_info = config["devices"][device_name]

    client = ApiClient(email, password)

    # Ici on suppose que le type correspond à une méthode du client
    device_type = device_info["type"].lower()
    ip = device_info["ip"]

    # Exemple : client.p110(ip) pour une prise P110
    device = await getattr(client, device_type)(ip)

    # Exécution dynamique de la commande
    if not hasattr(device, command):
        print(f"La commande {command} n'existe pas pour ce type d'appareil.")
        sys.exit(1)

    func = getattr(device, command)

    # Convertir les arguments en int si possible
    parsed_args = [int(a) if a.isdigit() else a for a in args]

    result = await func(*parsed_args)
    print("Commande exécutée:", result)

if __name__ == "__main__":
    asyncio.run(main())
