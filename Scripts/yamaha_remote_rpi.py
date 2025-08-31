#!/usr/bin/env python3
"""
Télécommande IR Yamaha pour Raspberry Pi 5 - Version optimisée
Yamaha RX-E600MK2
Protocole NEC avec Custom Code 0x78
Utilise lgpio avec timing amélioré pour compatibilité Arduino
"""

import lgpio
import time
import sys
import threading
from typing import Dict, Optional

class YamahaRemote:
    def __init__(self, ir_pin: int = 18):
        """
        Initialise la télécommande Yamaha
        
        Args:
            ir_pin: Pin GPIO pour la LED IR (défaut: 18)
        """
        self.ir_pin = ir_pin
        self.h = None
        self.YAMAHA_ADDRESS = 0x78
        
        # Dictionnaire des commandes
        self.commands = {
            'POWER': 0x0F,
            'DIGIT_0': 0x10,
            'DIGIT_1': 0x11,
            'DIGIT_2': 0x12,
            'DIGIT_3': 0x13,
            'DIGIT_4': 0x14,
            'DIGIT_5': 0x15,
            'DIGIT_6': 0x16,
            'DIGIT_7': 0x17,
            'DIGIT_8': 0x18,
            'DIGIT_9': 0x19,
            'MODE_10': 0x1A,
            'START_100': 0x1D,
            'REP_A': 0x0C,
            'RANDOM_B': 0x07,
            'PROG_C': 0x0B,
            'D_KEY': 0x09,
            'PAUSE': 0x0A,
            'TIME': 0x08,
            'PLAY': 0x02,
            'REW': 0x04,
            'STOP': 0x01,
            'FF': 0x03,
            'TAPE_DIR': 0x43,
            'PRESET_DN': 0x1C,
            'TUNER': 0x4B,
            'PRESET_UP': 0x1B,
            'MD': 0x57,
            'DVD': 0x4A,
            'TAPE': 0x41,
            'AUX': 0x49,
            'MD_REC': 0x58,
            'TAPE_REC': 0x46,
            'MODE': 0x05,
            'START': 0x06,
            'SLEEP': 0x4F,
            'VOL_UP': 0x1E,
            'DISPLAY': 0x4E,
            'VOL_DOWN': 0x1F
        }
        
        # Aliases pour faciliter l'utilisation
        self.aliases = {
            'PWR': 'POWER',
            'VOL+': 'VOL_UP',
            'VOLUP': 'VOL_UP',
            'VOL-': 'VOL_DOWN',
            'VOLDOWN': 'VOL_DOWN',
            'FORWARD': 'FF',
            'REWIND': 'REW',
            'RADIO': 'TUNER',
            'CD': 'MODE',
            'DISC': 'MODE',
            'RANDOM': 'RANDOM_B',
            'REPEAT': 'REP_A',
            '0': 'DIGIT_0',
            '1': 'DIGIT_1',
            '2': 'DIGIT_2',
            '3': 'DIGIT_3',
            '4': 'DIGIT_4',
            '5': 'DIGIT_5',
            '6': 'DIGIT_6',
            '7': 'DIGIT_7',
            '8': 'DIGIT_8',
            '9': 'DIGIT_9'
        }
        
        self.init_gpio()
        
        # Optimisations timing
        self.carrier_freq = 38000
        self.duty_cycle = 0.33  # 33% comme Arduino
        
    def init_gpio(self):
        """Initialise la connexion GPIO avec lgpio"""
        try:
            self.h = lgpio.gpiochip_open(0)  # Chip 0 pour Pi 5
            
            # Configure le pin en sortie avec priorité haute
            lgpio.gpio_claim_output(self.h, self.ir_pin, 0)
            
            print(f"GPIO initialisé avec lgpio - Pin IR: {self.ir_pin}")
            
        except Exception as e:
            print(f"Erreur d'initialisation GPIO: {e}")
            print("Assurez-vous que lgpio est installé:")
            print("sudo apt install python3-lgpio")
            sys.exit(1)
    
    def nec_encode(self, address: int, command: int) -> list:
        """
        Encode une commande au format NEC - Compatible Arduino
        
        Args:
            address: Adresse du périphérique  
            command: Code de la commande
            
        Returns:
            Liste des durées des impulsions [ON, OFF, ON, OFF, ...]
        """
        # Format NEC identique à Arduino
        data = []
        
        # AGC burst: 9ms ON, 4.5ms OFF
        data.extend([9000, 4500])
        
        # Address (8 bits, LSB first)
        for i in range(8):
            if (address >> i) & 1:
                data.extend([560, 1690])  # Bit 1
            else:
                data.extend([560, 560])   # Bit 0
        
        # ~Address (8 bits, LSB first)
        address_inv = (~address) & 0xFF
        for i in range(8):
            if (address_inv >> i) & 1:
                data.extend([560, 1690])  # Bit 1
            else:
                data.extend([560, 560])   # Bit 0
        
        # Command (8 bits, LSB first)
        for i in range(8):
            if (command >> i) & 1:
                data.extend([560, 1690])  # Bit 1
            else:
                data.extend([560, 560])   # Bit 0
        
        # ~Command (8 bits, LSB first)
        command_inv = (~command) & 0xFF
        for i in range(8):
            if (command_inv >> i) & 1:
                data.extend([560, 1690])  # Bit 1
            else:
                data.extend([560, 560])   # Bit 0
        
        # Stop bit
        data.append(560)
        
        return data
    
    def send_ir_burst(self, duration_us: int):
        """
        Génère une rafale IR modulée à 38kHz avec duty cycle correct
        Optimisé pour reproduire le comportement Arduino
        
        Args:
            duration_us: Durée en microsecondes
        """
        if duration_us <= 0:
            return
            
        # Calcul des timings pour 38kHz (26.3µs période)
        period_us = 26.3  # 1000000 / 38000
        on_time_us = period_us * self.duty_cycle  # ~8.7µs ON
        off_time_us = period_us - on_time_us      # ~17.6µs OFF
        
        cycles = int(duration_us / period_us)
        
        # Conversion en nanosecondes pour meilleure précision
        on_time_ns = int(on_time_us * 1000)
        off_time_ns = int(off_time_us * 1000)
        
        # Envoi optimisé avec nanosecondes
        start_time = time.time_ns()
        
        for cycle in range(cycles):
            lgpio.gpio_write(self.h, self.ir_pin, 1)
            # Délai précis avec busy wait pour les courtes durées
            target_time = start_time + (cycle * period_us * 1000) + on_time_ns
            while time.time_ns() < target_time:
                pass
                
            lgpio.gpio_write(self.h, self.ir_pin, 0)
            target_time = start_time + ((cycle + 1) * period_us * 1000)
            while time.time_ns() < target_time:
                pass
        
        # Assure que le pin est à 0
        lgpio.gpio_write(self.h, self.ir_pin, 0)
    
    def send_ir_signal(self, pulses: list):
        """
        Envoie le signal IR avec timing précis
        
        Args:
            pulses: Liste des durées des impulsions (microsecondes)
        """
        try:
            # Augmentation de priorité du processus
            import os
            try:
                os.nice(-10)  # Priorité plus haute (nécessite sudo)
            except:
                pass  # Ignore si pas de droits sudo
            
            start_time = time.time_ns()
            
            for i, duration in enumerate(pulses):
                if i % 2 == 0:  # Impulsion ON (modulée à 38kHz)
                    self.send_ir_burst(duration)
                else:  # Pause OFF (non modulée)
                    lgpio.gpio_write(self.h, self.ir_pin, 0)
                    # Délai précis
                    target_time = start_time + sum(pulses[:i+1]) * 1000
                    while time.time_ns() < target_time:
                        pass
            
            # Final OFF state
            lgpio.gpio_write(self.h, self.ir_pin, 0)
            
        except Exception as e:
            print(f"Erreur lors de l'envoi IR: {e}")
    
    def send_command(self, command_name: str, double_send: bool = False):
        """
        Envoie une commande IR
        
        Args:
            command_name: Nom de la commande
            double_send: Envoie deux fois la commande (pour POWER)
        """
        # Résout les aliases
        if command_name.upper() in self.aliases:
            command_name = self.aliases[command_name.upper()]
        else:
            command_name = command_name.upper()
        
        if command_name not in self.commands:
            print(f"Commande inconnue: {command_name}")
            return False
        
        command_code = self.commands[command_name]
        
        print(f"Envoi: {command_name} (Address=0x{self.YAMAHA_ADDRESS:02X}, Command=0x{command_code:02X})")
        
        # Encode et envoie
        pulses = self.nec_encode(self.YAMAHA_ADDRESS, command_code)
        
        # Debug: affiche le timing total
        total_time = sum(pulses) / 1000  # en millisecondes
        print(f"  Durée signal: {total_time:.1f}ms, {len(pulses)} impulsions")
        
        self.send_ir_signal(pulses)
        
        if double_send:
            time.sleep(0.108)  # Gap standard NEC entre répétitions
            self.send_ir_signal(pulses)
            print("  (double envoi)")
        
        return True
    
    def send_power(self):
        """Envoie la commande POWER avec double envoi"""
        return self.send_command('POWER', double_send=True)
    
    def send_nec_repeat(self, times: int = 1):
        """
        Envoie un signal de répétition NEC
        
        Args:
            times: Nombre de répétitions
        """
        repeat_pulses = [9000, 2250, 560]  # Repeat code NEC
        
        for _ in range(times):
            print("Envoi repeat code NEC")
            self.send_ir_signal(repeat_pulses)
            time.sleep(0.108)  # 108ms gap
    
    def test_sequence(self):
        """Séquence de test étendue"""
        print("=== SÉQUENCE DE TEST ÉTENDUE ===")
        
        print("\n1. Test simple VOLUME UP...")
        self.send_command('VOL_UP')
        time.sleep(2)
        
        print("\n2. Test VOLUME DOWN...")
        self.send_command('VOL_DOWN')
        time.sleep(2)
        
        print("\n3. Test POWER (double envoi)...")
        self.send_power()
        time.sleep(3)
        
        print("\n4. Test avec repeat code...")
        self.send_command('VOL_UP')
        self.send_nec_repeat(2)
        time.sleep(2)
        
        print("\nTest terminé.")
    
    def debug_signal(self, command_name: str):
        """
        Debug d'une commande spécifique
        
        Args:
            command_name: Commande à debugger
        """
        if command_name.upper() in self.aliases:
            command_name = self.aliases[command_name.upper()]
        else:
            command_name = command_name.upper()
        
        if command_name not in self.commands:
            print(f"Commande inconnue: {command_name}")
            return
        
        command_code = self.commands[command_name]
        pulses = self.nec_encode(self.YAMAHA_ADDRESS, command_code)
        
        print(f"\n=== DEBUG: {command_name} ===")
        print(f"Address: 0x{self.YAMAHA_ADDRESS:02X} ({self.YAMAHA_ADDRESS:08b})")
        print(f"Command: 0x{command_code:02X} ({command_code:08b})")
        print(f"~Address: 0x{(~self.YAMAHA_ADDRESS)&0xFF:02X}")
        print(f"~Command: 0x{(~command_code)&0xFF:02X}")
        print(f"Nombre d'impulsions: {len(pulses)}")
        print(f"Durée totale: {sum(pulses)/1000:.1f}ms")
        
        # Affiche le début du signal
        print("Début du signal (µs):")
        for i in range(min(20, len(pulses))):
            state = "ON " if i % 2 == 0 else "OFF"
            print(f"  {i:2d}: {state} {pulses[i]:4d}µs")
        if len(pulses) > 20:
            print("  ...")
    
    def print_help(self):
        """Affiche l'aide"""
        print("\n=== COMMANDES DISPONIBLES ===")
        print("POWER/PWR    - Marche/Arrêt")
        print("VOL+/VOLUP   - Volume +")
        print("VOL-/VOLDOWN - Volume -")
        print("PLAY         - Lecture")
        print("PAUSE        - Pause")
        print("STOP         - Arrêt")
        print("FF/FORWARD   - Avance rapide")
        print("REW/REWIND   - Retour rapide")
        print("TUNER/RADIO  - Tuner FM")
        print("TAPE         - Cassette")
        print("CD/DISC      - CD")
        print("AUX          - Entrée auxiliaire")
        print("MD           - MiniDisc")
        print("DVD          - DVD")
        print("RANDOM       - Lecture aléatoire")
        print("REPEAT       - Répétition")
        print("DISPLAY      - Affichage")
        print("SLEEP        - Minuterie")
        print("1-9, 0       - Chiffres")
        print("TEST         - Séquence de test")
        print("DEBUG <cmd>  - Debug d'une commande")
        print("HELP         - Cette aide")
        print("QUIT/EXIT    - Quitter")
        print("=============================\n")
    
    def interactive_mode(self):
        """Mode interactif"""
        print("Télécommande IR Yamaha - Mode interactif optimisé")
        print("Timing amélioré pour compatibilité Arduino")
        print("Tapez 'HELP' pour voir les commandes disponibles")
        print("Tapez 'QUIT' ou 'EXIT' pour quitter")
        
        while True:
            try:
                command = input("\n> ").strip()
                
                if not command:
                    continue
                
                cmd_parts = command.split()
                
                if cmd_parts[0].upper() in ['QUIT', 'EXIT', 'Q']:
                    break
                elif cmd_parts[0].upper() == 'HELP':
                    self.print_help()
                elif cmd_parts[0].upper() == 'TEST':
                    self.test_sequence()
                elif cmd_parts[0].upper() == 'DEBUG':
                    if len(cmd_parts) > 1:
                        self.debug_signal(cmd_parts[1])
                    else:
                        print("Usage: DEBUG <commande>")
                elif cmd_parts[0].upper() in ['POWER', 'PWR']:
                    self.send_power()
                else:
                    self.send_command(cmd_parts[0])
                    
            except KeyboardInterrupt:
                print("\nAu revoir!")
                break
            except Exception as e:
                print(f"Erreur: {e}")
    
    def cleanup(self):
        """Nettoie les ressources"""
        if self.h is not None:
            lgpio.gpio_write(self.h, self.ir_pin, 0)
            lgpio.gpiochip_close(self.h)

# Fonctions utilitaires
def send_single_command(command: str, ir_pin: int = 18):
    """
    Envoie une seule commande et quitte
    
    Args:
        command: Commande à envoyer
        ir_pin: Pin GPIO pour IR
    """
    remote = YamahaRemote(ir_pin)
    try:
        if command.upper() in ['POWER', 'PWR']:
            remote.send_power()
        else:
            remote.send_command(command)
    finally:
        remote.cleanup()

def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Télécommande IR Yamaha (lgpio optimisé)')
    parser.add_argument('--pin', type=int, default=18, 
                       help='Pin GPIO pour la LED IR (défaut: 18)')
    parser.add_argument('--command', type=str, 
                       help='Commande unique à envoyer')
    parser.add_argument('--test', action='store_true', 
                       help='Lance la séquence de test')
    parser.add_argument('--debug', type=str,
                       help='Debug une commande spécifique')
    
    args = parser.parse_args()
    
    if args.command:
        send_single_command(args.command, args.pin)
    elif args.test:
        remote = YamahaRemote(args.pin)
        try:
            remote.test_sequence()
        finally:
            remote.cleanup()
    elif args.debug:
        remote = YamahaRemote(args.pin)
        try:
            remote.debug_signal(args.debug)
        finally:
            remote.cleanup()
    else:
        remote = YamahaRemote(args.pin)
        try:
            remote.interactive_mode()
        finally:
            remote.cleanup()

if __name__ == "__main__":
    main()