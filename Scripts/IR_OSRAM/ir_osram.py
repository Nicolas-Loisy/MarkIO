#!/usr/bin/env python3
"""
Telecommande IR Osram RGBW pour Raspberry Pi 5 - Version optimisee
Protocole NEC avec Custom Code 0x00 (adresse ignoree par les ampoules Osram)
Utilise lgpio avec timing ameliore pour compatibilite Arduino
Base sur les codes IR reverse-engineered des ampoules Osram LED Star+ RGBW
"""

import lgpio
import time
import sys
import threading
from typing import Dict, Optional

class OsramRGBWRemote:
    def __init__(self, ir_pin: int = 18):
        """
        Initialise la telecommande Osram RGBW
        
        Args:
            ir_pin: Pin GPIO pour la LED IR (defaut: 18)
        """
        self.ir_pin = ir_pin
        self.h = None
        self.OSRAM_ADDRESS = 0x00  # L'adresse est ignoree par les ampoules Osram
        
        # Dictionnaire des commandes Osram RGBW (codes hexadecimaux)
        # Base sur l'analyse des telecommandes Osram RGBW 24 touches
        self.commands = {
            # Controles principaux
            'ON': 0x07,
            'OFF': 0x06,
            'BRIGHT_UP': 0x00,
            'BRIGHT_DOWN': 0x02,
            
            # Couleurs principales
            'RED': 0x08,
            'GREEN': 0x09,
            'BLUE': 0x0A,
            'WHITE': 0x03,
            
            # Couleurs etendues - Rangee 1
            'RED1': 0x0C,
            'GREEN1': 0x0D,
            'BLUE1': 0x0E,
            'FLASH': 0x0F,
            
            # Couleurs etendues - Rangee 2  
            'RED2': 0x10,
            'GREEN2': 0x11,
            'BLUE2': 0x12,
            'STROBE': 0x13,
            
            # Couleurs etendues - Rangee 3
            'RED3': 0x14,
            'GREEN3': 0x15,
            'BLUE3': 0x16,
            'SMOOTH': 0x17,
            
            # Couleurs etendues - Rangee 4
            'RED4': 0x18,
            'GREEN4': 0x19,
            'BLUE4': 0x1A,
            'MODE': 0x1B
        }
        
        # Aliases pour faciliter l'utilisation
        self.aliases = {
            'POWER_ON': 'ON',
            'POWER_OFF': 'OFF',
            'POWER': 'ON',  # Par defaut ON, utilisateur peut specifier OFF
            'BRIGHT+': 'BRIGHT_UP',
            'BRIGHT-': 'BRIGHT_DOWN',
            'BRIGHTER': 'BRIGHT_UP',
            'DIMMER': 'BRIGHT_DOWN',
            'LIGHT_UP': 'BRIGHT_UP',
            'LIGHT_DOWN': 'BRIGHT_DOWN',
            
            # Couleurs principales
            'R': 'RED',
            'G': 'GREEN',
            'B': 'BLUE',
            'W': 'WHITE',
            
            # Effets
            'BLINK': 'FLASH',
            'STROBOSCOPE': 'STROBE',
            'TRANSITION': 'FADE',
            'GRADUAL': 'SMOOTH',
            
            # Couleurs numerotees alternatives
            'ORANGE': 'RED1',
            'CYAN': 'BLUE1', 
            'PURPLE': 'RED2',
            'YELLOW': 'GREEN2',
            'PINK': 'RED3',
            'LIME': 'GREEN3',
            'VIOLET': 'BLUE3',
            'MAGENTA': 'RED4'
        }
        
        self.init_gpio()
        
        # Optimisations timing identiques au code Yamaha
        self.carrier_freq = 38000
        self.duty_cycle = 0.33  # 33% comme Arduino
        
    def init_gpio(self):
        """Initialise la connexion GPIO avec lgpio"""
        try:
            self.h = lgpio.gpiochip_open(0)  # Chip 0 pour Pi 5
            
            # Configure le pin en sortie avec priorite haute
            lgpio.gpio_claim_output(self.h, self.ir_pin, 0)
            
            print(f"GPIO initialise avec lgpio - Pin IR: {self.ir_pin}")
            
        except Exception as e:
            print(f"Erreur d'initialisation GPIO: {e}")
            print("Assurez-vous que lgpio est installe:")
            print("sudo apt install python3-lgpio")
            sys.exit(1)
    
    def nec_encode(self, address: int, command: int) -> list:
        """
        Encode une commande au format NEC - Compatible Arduino
        Identique au code Yamaha pour maintenir la compatibilite
        
        Args:
            address: Adresse du peripherique (0x00 pour Osram)
            command: Code de la commande
            
        Returns:
            Liste des durees des impulsions [ON, OFF, ON, OFF, ...]
        """
        # Format NEC identique a Arduino
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
        
        # Ajout d'impulsions OFF supplementaires pour atteindre 71 impulsions
        while len(data) < 71:
            data.append(560)  # OFF supplementaire
        return data
    
    def send_ir_burst(self, duration_us: int):
        """
        Genere une rafale IR modulee a 38kHz avec duty cycle correct
        Code identique au Yamaha pour maintenir la compatibilite
        
        Args:
            duration_us: Duree en microsecondes
        """
        if duration_us <= 0:
            return
            
        # Calcul des timings pour 38kHz (26.3us periode)
        period_us = 26.3  # 1000000 / 38000
        on_time_us = period_us * self.duty_cycle  # ~8.7us ON
        off_time_us = period_us - on_time_us      # ~17.6us OFF
        
        cycles = int(duration_us / period_us)
        
        # Conversion en nanosecondes pour meilleure precision
        on_time_ns = int(on_time_us * 1000)
        off_time_ns = int(off_time_us * 1000)
        
        # Envoi optimise avec nanosecondes
        start_time = time.time_ns()
        
        for cycle in range(cycles):
            lgpio.gpio_write(self.h, self.ir_pin, 1)
            # Delai precis avec busy wait pour les courtes durees
            target_time = start_time + (cycle * period_us * 1000) + on_time_ns
            while time.time_ns() < target_time:
                pass
                
            lgpio.gpio_write(self.h, self.ir_pin, 0)
            target_time = start_time + ((cycle + 1) * period_us * 1000)
            while time.time_ns() < target_time:
                pass
        
        # Assure que le pin est a 0
        lgpio.gpio_write(self.h, self.ir_pin, 0)
    
    def send_ir_signal(self, pulses: list):
        """
        Envoie le signal IR avec timing precis
        Code identique au Yamaha
        
        Args:
            pulses: Liste des durees des impulsions (microsecondes)
        """
        try:
            # Augmentation de priorite du processus
            import os
            try:
                os.nice(-10)  # Priorite plus haute (necessite sudo)
            except:
                pass  # Ignore si pas de droits sudo
            
            start_time = time.time_ns()
            
            for i, duration in enumerate(pulses):
                if i % 2 == 0:  # Impulsion ON (modulee a 38kHz)
                    self.send_ir_burst(duration)
                else:  # Pause OFF (non modulee)
                    lgpio.gpio_write(self.h, self.ir_pin, 0)
                    # Delai precis
                    target_time = start_time + sum(pulses[:i+1]) * 1000
                    while time.time_ns() < target_time:
                        pass
            
            # Final OFF state
            lgpio.gpio_write(self.h, self.ir_pin, 0)
            
        except Exception as e:
            print(f"Erreur lors de l'envoi IR: {e}")
    
    def send_command(self, command_name: str, repeat_count: int = 0):
        """
        Envoie une commande IR Osram
        
        Args:
            command_name: Nom de la commande
            repeat_count: Nombre de repetitions (pour maintenir une couleur)
        """
        # Resout les aliases
        if command_name.upper() in self.aliases:
            command_name = self.aliases[command_name.upper()]
        else:
            command_name = command_name.upper()
        
        if command_name not in self.commands:
            print(f"Commande inconnue: {command_name}")
            return False
        
        command_code = self.commands[command_name]
        
        print(f"Envoi: {command_name} (Address=0x{self.OSRAM_ADDRESS:02X}, Command=0x{command_code:02X})")
        
        # Encode et envoie
        pulses = self.nec_encode(self.OSRAM_ADDRESS, command_code)
        
        # Debug: affiche le timing total
        total_time = sum(pulses) / 1000  # en millisecondes
        print(f"  Duree signal: {total_time:.1f}ms, {len(pulses)} impulsions")
        
        self.send_ir_signal(pulses)
        
        # Repetitions si demandees (utile pour maintenir un effet)
        for i in range(repeat_count):
            time.sleep(0.108)  # Gap standard NEC entre repetitions
            self.send_ir_signal(pulses)
            print(f"  (repetition {i+1})")
        
        return True
    
    def send_nec_repeat(self, times: int = 1):
        """
        Envoie un signal de repetition NEC
        
        Args:
            times: Nombre de repetitions
        """
        repeat_pulses = [9000, 2250, 560]  # Repeat code NEC
        
        for _ in range(times):
            print("Envoi repeat code NEC")
            self.send_ir_signal(repeat_pulses)
            time.sleep(0.108)  # 108ms gap
    
    def demo_sequence(self):
        """Sequence de demonstration des couleurs Osram RGBW"""
        print("=== DEMONSTRATION OSRAM RGBW ===")
        
        print("\n1. Allumage de l'ampoule...")
        self.send_command('ON')
        time.sleep(2)
        
        print("\n2. Test des couleurs principales...")
        colors = ['RED', 'GREEN', 'BLUE', 'WHITE']
        for color in colors:
            print(f"   Couleur: {color}")
            self.send_command(color)
            time.sleep(1.5)
        
        print("\n3. Test luminosite...")
        self.send_command('BRIGHT_UP')
        time.sleep(1)
        self.send_command('BRIGHT_DOWN')
        time.sleep(1)
        
        print("\n4. Test des effets...")
        effects = ['FLASH', 'STROBE', 'FADE', 'SMOOTH']
        for effect in effects:
            print(f"   Effet: {effect}")
            self.send_command(effect)
            time.sleep(3)
        
        print("\n5. Retour au blanc...")
        self.send_command('WHITE')
        time.sleep(2)
        
        print("\n6. Extinction...")
        self.send_command('OFF')
        
        print("\nDemonstration terminee.")
    
    def color_cycle(self, duration: int = 30):
        """
        Cycle automatique de couleurs
        
        Args:
            duration: Duree du cycle en secondes
        """
        print(f"=== CYCLE DE COULEURS ({duration}s) ===")
        
        # Allume l'ampoule
        self.send_command('ON')
        time.sleep(1)
        
        # Liste des couleurs pour le cycle
        colors = ['RED', 'RED1', 'RED2', 'RED3', 'RED4',
                 'GREEN', 'GREEN1', 'GREEN2', 'GREEN3', 'GREEN4',
                 'BLUE', 'BLUE1', 'BLUE2', 'BLUE3', 'BLUE4',
                 'WHITE']
        
        start_time = time.time()
        color_index = 0
        
        while (time.time() - start_time) < duration:
            color = colors[color_index]
            print(f"Couleur: {color}")
            self.send_command(color)
            
            time.sleep(2)  # 2 secondes par couleur
            color_index = (color_index + 1) % len(colors)
        
        print("Cycle termine.")
    
    def debug_signal(self, command_name: str):
        """
        Debug d'une commande specifique
        
        Args:
            command_name: Commande a debugger
        """
        if command_name.upper() in self.aliases:
            command_name = self.aliases[command_name.upper()]
        else:
            command_name = command_name.upper()
        
        if command_name not in self.commands:
            print(f"Commande inconnue: {command_name}")
            return
        
        command_code = self.commands[command_name]
        pulses = self.nec_encode(self.OSRAM_ADDRESS, command_code)
        
        print(f"\n=== DEBUG: {command_name} ===")
        print(f"Address: 0x{self.OSRAM_ADDRESS:02X} ({self.OSRAM_ADDRESS:08b})")
        print(f"Command: 0x{command_code:02X} ({command_code:08b})")
        print(f"~Address: 0x{(~self.OSRAM_ADDRESS)&0xFF:02X}")
        print(f"~Command: 0x{(~command_code)&0xFF:02X}")
        print(f"Nombre d'impulsions: {len(pulses)}")
        print(f"Duree totale: {sum(pulses)/1000:.1f}ms")
        
        # Affiche le debut du signal
        print("Debut du signal (us):")
        for i in range(min(20, len(pulses))):
            state = "ON " if i % 2 == 0 else "OFF"
            print(f"  {i:2d}: {state} {pulses[i]:4d}us")
        if len(pulses) > 20:
            print("  ...")
        
        # Calcule et affiche le code NEC complet
        nec_code = (self.OSRAM_ADDRESS << 24) | ((~self.OSRAM_ADDRESS & 0xFF) << 16) | (command_code << 8) | (~command_code & 0xFF)
        print(f"Code NEC complet: 0x{nec_code:08X}")
    
    def print_help(self):
        """Affiche l'aide"""
        print("\n=== COMMANDES OSRAM RGBW DISPONIBLES ===")
        print("CONTROLES PRINCIPAUX:")
        print("  ON/POWER_ON    - Allumer l'ampoule")
        print("  OFF/POWER_OFF  - Eteindre l'ampoule")
        print("  BRIGHT+/UP     - Augmenter luminosite")
        print("  BRIGHT-/DOWN   - Diminuer luminosite")
        print("")
        print("COULEURS PRINCIPALES:")
        print("  RED/R          - Rouge")
        print("  GREEN/G        - Vert") 
        print("  BLUE/B         - Bleu")
        print("  WHITE/W        - Blanc")
        print("")
        print("COULEURS ETENDUES:")
        print("  RED1-4         - Nuances de rouge")
        print("  GREEN1-4       - Nuances de vert")
        print("  BLUE1-4        - Nuances de bleu")
        print("  ORANGE, CYAN, PURPLE, YELLOW, etc.")
        print("")
        print("EFFETS LUMINEUX:")
        print("  FLASH/BLINK    - Clignotement rapide")
        print("  STROBE         - Effet stroboscope")
        print("  FADE           - Transition douce")
        print("  SMOOTH         - Changement graduel")
        print("")
        print("COMMANDES SPECIALES:")
        print("  DEMO           - Demonstration complete")
        print("  CYCLE [duree]  - Cycle de couleurs")
        print("  DEBUG <cmd>    - Debug d'une commande")
        print("  HELP           - Cette aide")
        print("  QUIT/EXIT      - Quitter")
        print("=========================================\n")
    
    def interactive_mode(self):
        """Mode interactif"""
        print("Telecommande IR Osram RGBW - Mode interactif")
        print("Compatible avec ampoules Osram LED Star+ RGBW")
        print("Protocole NEC optimise pour Raspberry Pi 5")
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
                elif cmd_parts[0].upper() == 'DEMO':
                    self.demo_sequence()
                elif cmd_parts[0].upper() == 'CYCLE':
                    duration = 30  # duree par defaut
                    if len(cmd_parts) > 1:
                        try:
                            duration = int(cmd_parts[1])
                        except ValueError:
                            print("Duree invalide, utilisation de 30s par defaut")
                    self.color_cycle(duration)
                elif cmd_parts[0].upper() == 'DEBUG':
                    if len(cmd_parts) > 1:
                        self.debug_signal(cmd_parts[1])
                    else:
                        print("Usage: DEBUG <commande>")
                else:
                    # Gestion des repetitions
                    repeat_count = 0
                    if len(cmd_parts) > 1 and cmd_parts[1].isdigit():
                        repeat_count = int(cmd_parts[1])
                    
                    self.send_command(cmd_parts[0], repeat_count)
                    
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
def send_single_command(command: str, ir_pin: int = 18, repeat_count: int = 0):
    """
    Envoie une seule commande et quitte
    
    Args:
        command: Commande a envoyer
        ir_pin: Pin GPIO pour IR
        repeat_count: Nombre de repetitions
    """
    remote = OsramRGBWRemote(ir_pin)
    try:
        remote.send_command(command, repeat_count)
    finally:
        remote.cleanup()

def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Telecommande IR Osram RGBW (lgpio optimise)')
    parser.add_argument('--pin', type=int, default=18, 
                       help='Pin GPIO pour la LED IR (defaut: 18)')
    parser.add_argument('--command', type=str, 
                       help='Commande unique a envoyer')
    parser.add_argument('--repeat', type=int, default=0,
                       help='Nombre de repetitions de la commande')
    parser.add_argument('--demo', action='store_true', 
                       help='Lance la demonstration complete')
    parser.add_argument('--cycle', type=int, default=0,
                       help='Lance un cycle de couleurs (duree en secondes)')
    parser.add_argument('--debug', type=str,
                       help='Debug une commande specifique')
    
    args = parser.parse_args()
    
    if args.command:
        send_single_command(args.command, args.pin, args.repeat)
    elif args.demo:
        remote = OsramRGBWRemote(args.pin)
        try:
            remote.demo_sequence()
        finally:
            remote.cleanup()
    elif args.cycle > 0:
        remote = OsramRGBWRemote(args.pin)
        try:
            remote.color_cycle(args.cycle)
        finally:
            remote.cleanup()
    elif args.debug:
        remote = OsramRGBWRemote(args.pin)
        try:
            remote.debug_signal(args.debug)
        finally:
            remote.cleanup()
    else:
        remote = OsramRGBWRemote(args.pin)
        try:
            remote.interactive_mode()
        finally:
            remote.cleanup()

if __name__ == "__main__":
    main()