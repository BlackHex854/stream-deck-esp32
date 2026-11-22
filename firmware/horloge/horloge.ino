// SoundBoard ESP32 - modèle « horloge »
// Module 4 chiffres TM1637 qui affiche l'heure envoyée par le PC
// (le script Python envoie l'heure à la connexion, puis toutes les 30 s).
//
// Switchs (l'autre patte sur GND) : 13, 14, 25, 26, 27, 32
// Module TM1637 : CLK -> GPIO 22, DIO -> GPIO 21, VCC -> 3V3, GND -> GND
//
// Bibliothèque (Library Manager) : "TM1637" de Avishay Orpaz
// Carte : ESP32 Dev Module, paquet esp32 version 2.0.17

#include <TM1637Display.h>

#define CLK 22
#define DIO 21

TM1637Display afficheur(CLK, DIO);

const int pins[6] = {13, 14, 25, 26, 27, 32};
bool prev[6] = {HIGH, HIGH, HIGH, HIGH, HIGH, HIGH};

String ligne = "";
bool heureRecue = false;
unsigned long baseSecondes = 0;   // secondes depuis minuit à la dernière synchro
unsigned long tSynchro = 0;       // millis() à ce moment
int derniereSec = -1;

void afficherHeure() {
  unsigned long ecoule = (millis() - tSynchro) / 1000;
  unsigned long s = (baseSecondes + ecoule) % 86400UL;
  int h = s / 3600;
  int m = (s % 3600) / 60;
  int sec = s % 60;
  if (sec == derniereSec) return;      // on ne redessine qu'une fois par seconde
  derniereSec = sec;
  // les deux points clignotent chaque seconde
  afficheur.showNumberDecEx(h * 100 + m, (sec % 2 == 0) ? 0b01000000 : 0, true);
}

void traiterLigne() {
  // Format envoyé par le PC : T + HHMMSS, par exemple T152342
  if (ligne.length() == 7 && ligne[0] == 'T') {
    int h = ligne.substring(1, 3).toInt();
    int m = ligne.substring(3, 5).toInt();
    int s = ligne.substring(5, 7).toInt();
    if (h < 24 && m < 60 && s < 60) {
      baseSecondes = h * 3600UL + m * 60UL + s;
      tSynchro = millis();
      heureRecue = true;
      derniereSec = -1;
    }
  }
}

void lireSerie() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      traiterLigne();
      ligne = "";
    } else if (c != '\r' && ligne.length() < 16) {
      ligne += c;
    }
  }
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 6; i++) pinMode(pins[i], INPUT_PULLUP);
  afficheur.setBrightness(5);          // 0 (faible) à 7 (fort)
  const uint8_t tirets[] = {0x40, 0x40, 0x40, 0x40};
  afficheur.setSegments(tirets);       // "----" en attendant l'heure du PC
}

void loop() {
  lireSerie();
  if (heureRecue) afficherHeure();

  for (int i = 0; i < 6; i++) {
    bool etat = digitalRead(pins[i]);
    if (etat == LOW && prev[i] == HIGH) {
      Serial.println(i + 1);
    }
    prev[i] = etat;
  }
  delay(30);
}
