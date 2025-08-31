// Télécommande IR Yamaha pour Arduino UNO
// Yamaha RX-E600MK2
// Protocole NEC avec Custom Code 0x78

#include <IRremote.h>

// Configuration matérielle
#define IR_SEND_PIN 3        // Pin de sortie IR (changez selon votre montage)
#define BUTTON_PIN 2         // Pin pour bouton test (optionnel)

// Protocole NEC - Yamaha
#define YAMAHA_ADDRESS 0x78  // Custom Code

// Codes des commandes
#define POWER      0x0F
#define DIGIT_0    0x10
#define DIGIT_1    0x11
#define DIGIT_2    0x12
#define DIGIT_3    0x13
#define DIGIT_4    0x14
#define DIGIT_5    0x15
#define DIGIT_6    0x16
#define DIGIT_7    0x17
#define DIGIT_8    0x18
#define DIGIT_9    0x19
#define MODE_10    0x1A
#define START_100  0x1D
#define REP_A      0x0C
#define RANDOM_B   0x07
#define PROG_C     0x0B
#define D_KEY      0x09
#define PAUSE      0x0A
#define TIME       0x08
#define PLAY       0x02
#define REW        0x04
#define STOP       0x01
#define FF         0x03
#define TAPE_DIR   0x43
#define PRESET_DN  0x1C
#define TUNER      0x4B
#define PRESET_UP  0x1B
#define MD         0x57
#define DVD        0x4A
#define TAPE       0x41
#define AUX        0x49
#define MD_REC     0x58
#define TAPE_REC   0x46
#define MODE       0x05
#define START      0x06
#define SLEEP      0x4F
#define VOL_UP     0x1E
#define DISPLAY    0x4E
#define VOL_DOWN   0x1F

void setup() {
  Serial.begin(9600);
  Serial.println("Télécommande IR Yamaha - Démarrage");
  
  // Initialisation IR
  IrSender.begin(IR_SEND_PIN);
  
  // Pin bouton (optionnel)
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  
  Serial.println("Prêt ! Commandes disponibles :");
  Serial.println("POWER, VOL+, VOL-, PLAY, PAUSE, STOP, etc.");
  Serial.println("Tapez une commande ou 'help' pour la liste complète");
}

void loop() {
  // Test avec bouton physique
  if (digitalRead(BUTTON_PIN) == LOW) {
    sendPowerCommand();
    delay(500);
  }
  
  // Interface série
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toUpperCase();
    
    processCommand(command);
  }
}

// Fonction principale d'envoi IR
void sendIRCommand(uint8_t command, String name) {
  Serial.print("Envoi: ");
  Serial.print(name);
  Serial.print(" (0x");
  Serial.print(command, HEX);
  Serial.println(")");
  
  // Envoi standard
  IrSender.sendNEC(YAMAHA_ADDRESS, command, 0);
  delay(100);
}

// Fonction spéciale pour POWER (double envoi)
void sendPowerCommand() {
  Serial.println("Envoi commande POWER (double)");
  
  // Premier envoi
  IrSender.sendNEC(YAMAHA_ADDRESS, POWER, 0);
  delay(100);
  
  // Deuxième envoi (requis par certains Yamaha)
  IrSender.sendNEC(YAMAHA_ADDRESS, POWER, 0);
  delay(500);
}

// Traitement des commandes série
void processCommand(String cmd) {
  
  if (cmd == "HELP") {
    printHelp();
  }
  else if (cmd == "POWER" || cmd == "PWR") {
    sendPowerCommand();
  }
  else if (cmd == "VOL+" || cmd == "VOLUP") {
    sendIRCommand(VOL_UP, "VOLUME UP");
  }
  else if (cmd == "VOL-" || cmd == "VOLDOWN") {
    sendIRCommand(VOL_DOWN, "VOLUME DOWN");
  }
  else if (cmd == "PLAY") {
    sendIRCommand(PLAY, "PLAY");
  }
  else if (cmd == "PAUSE") {
    sendIRCommand(PAUSE, "PAUSE");
  }
  else if (cmd == "STOP") {
    sendIRCommand(STOP, "STOP");
  }
  else if (cmd == "FF" || cmd == "FORWARD") {
    sendIRCommand(FF, "FAST FORWARD");
  }
  else if (cmd == "REW" || cmd == "REWIND") {
    sendIRCommand(REW, "REWIND");
  }
  else if (cmd == "CD" || cmd == "DISC") {
    sendIRCommand(MODE, "CD/DISC");
  }
  else if (cmd == "TUNER" || cmd == "RADIO") {
    sendIRCommand(TUNER, "TUNER");
  }
  else if (cmd == "TAPE") {
    sendIRCommand(TAPE, "TAPE");
  }
  else if (cmd == "AUX") {
    sendIRCommand(AUX, "AUX");
  }
  else if (cmd == "MD") {
    sendIRCommand(MD, "MD");
  }
  else if (cmd == "DVD") {
    sendIRCommand(DVD, "DVD");
  }
  else if (cmd == "DISPLAY") {
    sendIRCommand(DISPLAY, "DISPLAY");
  }
  else if (cmd == "SLEEP") {
    sendIRCommand(SLEEP, "SLEEP");
  }
  else if (cmd == "RANDOM") {
    sendIRCommand(RANDOM_B, "RANDOM");
  }
  else if (cmd == "REPEAT") {
    sendIRCommand(REP_A, "REPEAT");
  }
  // Chiffres
  else if (cmd == "1") sendIRCommand(DIGIT_1, "1");
  else if (cmd == "2") sendIRCommand(DIGIT_2, "2");
  else if (cmd == "3") sendIRCommand(DIGIT_3, "3");
  else if (cmd == "4") sendIRCommand(DIGIT_4, "4");
  else if (cmd == "5") sendIRCommand(DIGIT_5, "5");
  else if (cmd == "6") sendIRCommand(DIGIT_6, "6");
  else if (cmd == "7") sendIRCommand(DIGIT_7, "7");
  else if (cmd == "8") sendIRCommand(DIGIT_8, "8");
  else if (cmd == "9") sendIRCommand(DIGIT_9, "9");
  else if (cmd == "0") sendIRCommand(DIGIT_0, "0");
  // Test de diagnostic
  else if (cmd == "TEST") {
    testSequence();
  }
  else {
    Serial.println("Commande inconnue. Tapez 'HELP' pour voir les commandes.");
  }
}

// Séquence de test
void testSequence() {
  Serial.println("=== SÉQUENCE DE TEST ===");
  
  Serial.println("Test VOLUME...");
  sendIRCommand(VOL_UP, "VOL UP");
  delay(1000);
  sendIRCommand(VOL_DOWN, "VOL DOWN");
  delay(1000);
  
  Serial.println("Test POWER...");
  sendPowerCommand();
  delay(2000);
  
  Serial.println("Test terminé.");
}

// Aide
void printHelp() {
  Serial.println("\n=== COMMANDES DISPONIBLES ===");
  Serial.println("POWER/PWR    - Marche/Arrêt");
  Serial.println("VOL+/VOLUP   - Volume +");
  Serial.println("VOL-/VOLDOWN - Volume -");
  Serial.println("PLAY         - Lecture");
  Serial.println("PAUSE        - Pause");
  Serial.println("STOP         - Arrêt");
  Serial.println("FF/FORWARD   - Avance rapide");
  Serial.println("REW/REWIND   - Retour rapide");
  Serial.println("TUNER/RADIO  - Tuner FM");
  Serial.println("TAPE         - Cassette");
  Serial.println("CD/DISC      - CD");
  Serial.println("AUX          - Entrée auxiliaire");
  Serial.println("MD           - MiniDisc");
  Serial.println("DVD          - DVD");
  Serial.println("RANDOM       - Lecture aléatoire");
  Serial.println("REPEAT       - Répétition");
  Serial.println("DISPLAY      - Affichage");
  Serial.println("SLEEP        - Minuterie");
  Serial.println("1-9, 0       - Chiffres");
  Serial.println("TEST         - Séquence de test");
  Serial.println("HELP         - Cette aide");
  Serial.println("=============================\n");
}