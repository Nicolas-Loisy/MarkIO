import lgpio
import time

# === Configuration ===
IR_GPIO = 11  # Numéro BCM du GPIO connecté au récepteur IR
MAX_IDLE = 0.1  # Temps max (s) sans impulsion  fin du signal

# === Fonction de décodage NEC ===
def decode_nec(pulses):
    if len(pulses) < 66:
        print(" Signal trop court pour du NEC.")
        return None

    # Vérifie le préambule (approximatif)
    if not (8500 <= pulses[0] <= 9500 and 4000 <= pulses[1] <= 5000):
        print(" Préambule invalide : pas un signal NEC.")
        return None

    bits = []
    for i in range(2, 66, 2):  # Paires de LOW-HIGH
        low = pulses[i]
        high = pulses[i + 1]

        if not (400 <= low <= 700):
            print(f" Durée LOW invalide : {low}")
            return None

        if 400 <= high <= 700:
            bits.append(0)
        elif 1500 <= high <= 1800:
            bits.append(1)
        else:
            print(f" Durée HIGH invalide : {high}")
            return None

    # Reconstruction des octets
    def bits_to_byte(b):
        return sum([bit << i for i, bit in enumerate(b)])

    addr = bits_to_byte(bits[0:8])
    addr_inv = bits_to_byte(bits[8:16])
    cmd = bits_to_byte(bits[16:24])
    cmd_inv = bits_to_byte(bits[24:32])

    if addr ^ addr_inv != 0xFF or cmd ^ cmd_inv != 0xFF:
        print(" Incohérence entre données et inversion.")
        return None

    full_code = (addr << 24) | (addr_inv << 16) | (cmd << 8) | cmd_inv
    return {
        "adresse": addr,
        "commande": cmd,
        "raw_bits": bits,
        "code_hex": f"0x{full_code:08X}"
    }

# === Initialisation GPIO ===
h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_input(h, IR_GPIO)

print(" Prêt. Appuie sur un bouton de la télécommande... (Ctrl+C pour quitter)")

try:
    while True:
        # Attente du premier changement d'état
        last_level = lgpio.gpio_read(h, IR_GPIO)
        while True:
            level = lgpio.gpio_read(h, IR_GPIO)
            if level != last_level:
                break
            time.sleep(0.00001)  # 10 Âµs

        # Capture des impulsions
        timings = []
        last_time = time.time()
        last_level = level

        while True:
            level = lgpio.gpio_read(h, IR_GPIO)
            if level != last_level:
                now = time.time()
                delta = now - last_time
                timings.append(round(delta * 1_000_000))  # Âµs
                last_time = now
                last_level = level

            if time.time() - last_time > MAX_IDLE:
                break

        # Affichage brut
        print(f"\n Signal capté ({len(timings)} impulsions) :")
        print(timings)

        # Décodage NEC
        decoded = decode_nec(timings)
        if decoded:
            print(" Signal NEC décodé :")
            print(f"    Adresse  : 0x{decoded['adresse']:02X}")
            print(f"    Commande : 0x{decoded['commande']:02X}")
            print(f"    Code HEX : {decoded['code_hex']}")
        else:
            print("Echec du décodage.")

        print("----\n")

except KeyboardInterrupt:
    print("\n Interruption par l'utilisateur.")

finally:
    lgpio.gpiochip_close(h)

