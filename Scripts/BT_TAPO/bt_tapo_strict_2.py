
from typing import Dict, Any, List, Optional, Union
import asyncio
import sys
import yaml
from tapo import ApiClient
from pydantic import BaseModel, EmailStr, ValidationError, field_validator

# Modèles Pydantic
class CredentialsModel(BaseModel):
    email: EmailStr
    password: str

class DeviceBaseModel(BaseModel):
    type: str
    ip: str

class DeviceP110Model(DeviceBaseModel):
    type: str = "P110"

class DeviceP110MModel(DeviceBaseModel):
    type: str = "P110M"

class DeviceL530Model(DeviceBaseModel):
    type: str = "L530"

class DeviceL510Model(DeviceBaseModel):
    type: str = "L510"

class DeviceL520Model(DeviceBaseModel):
    type: str = "L520"

DeviceModel = Union[DeviceP110Model, DeviceP110MModel, DeviceL530Model, DeviceL510Model, DeviceL520Model]

class ConfigModel(BaseModel):
    credentials: CredentialsModel
    devices: Dict[str, DeviceBaseModel]

    @field_validator('devices', mode='before')
    def validate_devices(cls, v):
        out = {}
        for name, dev in v.items():
            dtype = dev.get('type')
            if dtype == "P110":
                out[name] = DeviceP110Model(**dev)
            elif dtype == "P110M":
                out[name] = DeviceP110MModel(**dev)
            elif dtype == "L530":
                out[name] = DeviceL530Model(**dev)
            elif dtype == "L510":
                out[name] = DeviceL510Model(**dev)
            elif dtype == "L520":
                out[name] = DeviceL520Model(**dev)
            else:
                raise ValueError(f"Type de device inconnu: {dtype}")
        return out

# Modèles d'action
class ActionOnOffModel(BaseModel):
    action: str
    @field_validator('action')
    def validate_action(cls, v):
        if v not in ["on", "off"]:
            raise ValueError("Action doit être 'on' ou 'off'")
        return v

class ActionBrightnessModel(BaseModel):
    action: str
    value: int
    @field_validator('action')
    def validate_action(cls, v):
        if v != "set_brightness":
            raise ValueError("Action doit être 'set_brightness'")
        return v
    @field_validator('value')
    def validate_value(cls, v):
        if not (0 <= v <= 100):
            raise ValueError("Brightness doit être entre 0 et 100")
        return v

class ActionColorModel(BaseModel):
    action: str
    r: int
    g: int
    b: int
    @field_validator('action')
    def validate_action(cls, v):
        if v != "set_color":
            raise ValueError("Action doit être 'set_color'")
        return v
    @field_validator('r','g','b')
    def validate_rgb(cls, v):
        if not (0 <= v <= 255):
            raise ValueError("RGB doit être entre 0 et 255")
        return v

def load_config(path: str = "config.yaml") -> ConfigModel:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ConfigModel(**data)

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

    try:
        config = load_config(path="E:/Nicolas/Workspace/MarkIO/Scripts/BT_TAPO/config.yaml")
    except ValidationError as e:
        print("Erreur de validation de la configuration:", e)
        sys.exit(1)

    email = config.credentials.email
    password = config.credentials.password

    if device_name not in config.devices:
        print(f"Appareil {device_name} introuvable dans config.yaml")
        sys.exit(1)

    device = config.devices[device_name]
    device_type = device.type
    ip = device.ip

    # Validation stricte des commandes et paramètres
    action_model = None
    if device_type in ["P110", "P110M"]:
        try:
            action_model = ActionOnOffModel(action=command)
        except ValidationError as e:
            print("Commande non valide:", e)
            sys.exit(1)
    elif device_type in ["L510", "L520"]:
        if command in ["on", "off"]:
            try:
                action_model = ActionOnOffModel(action=command)
            except ValidationError as e:
                print("Commande non valide:", e)
                sys.exit(1)
        elif command == "set_brightness":
            if len(args) != 1:
                print("set_brightness requiert 1 argument (valeur)")
                sys.exit(1)
            try:
                action_model = ActionBrightnessModel(action=command, value=int(args[0]))
            except ValidationError as e:
                print("Paramètre brightness non valide:", e)
                sys.exit(1)
        else:
            print(f"Commande {command} non autorisée pour {device_type}")
            sys.exit(1)
    elif device_type == "L530":
        if command in ["on", "off"]:
            try:
                action_model = ActionOnOffModel(action=command)
            except ValidationError as e:
                print("Commande non valide:", e)
                sys.exit(1)
        elif command == "set_brightness":
            if len(args) != 1:
                print("set_brightness requiert 1 argument (valeur)")
                sys.exit(1)
            try:
                action_model = ActionBrightnessModel(action=command, value=int(args[0]))
            except ValidationError as e:
                print("Paramètre brightness non valide:", e)
                sys.exit(1)
        elif command == "set_color":
            if len(args) != 3:
                print("set_color requiert 3 arguments (r g b)")
                sys.exit(1)
            try:
                action_model = ActionColorModel(action=command, r=int(args[0]), g=int(args[1]), b=int(args[2]))
            except ValidationError as e:
                print("Paramètres couleur non valides:", e)
                sys.exit(1)
        else:
            print(f"Commande {command} non autorisée pour {device_type}")
            sys.exit(1)
    else:
        print(f"Type de device {device_type} non géré")
        sys.exit(1)

    client = ApiClient(email, password)
    tapo_device = await getattr(client, device_type.lower())(ip)

    # Exécution de la commande
    if isinstance(action_model, ActionOnOffModel):
        func = getattr(tapo_device, action_model.action)
        result = await func()
    elif isinstance(action_model, ActionBrightnessModel):
        func = getattr(tapo_device, action_model.action)
        result = await func(action_model.value)
    elif isinstance(action_model, ActionColorModel):
        func = getattr(tapo_device, action_model.action)
        result = await func(action_model.r, action_model.g, action_model.b)
    else:
        print("Action non reconnue")
        sys.exit(1)
    print("Commande exécutée:", result)

if __name__ == "__main__":
    asyncio.run(main())
