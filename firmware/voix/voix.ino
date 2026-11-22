// SoundBoard ESP32 - modèle « voix » (haut-parleur)
// Dit une phrase au branchement et le nom de l'appli à chaque appui.
//
// Switchs (l'autre patte sur GND) : 13, 14, 25, 26, 27, 32
// Haut-parleur : GPIO 33 -> résistance 100 ohm -> condensateur (+ côté GPIO)
//                -> fil 1 du haut-parleur ; fil 2 -> GND
//                (ou GPIO 33 -> condensateur -> entrée d'un module ampli)
//
// Avant de compiler : python tools/make_sons.py  (crée sons.h dans ce dossier)
// Carte : ESP32 Dev Module, paquet esp32 version 2.0.17

#include "sons.h"

#define SPK_PIN 33

const int pins[6] = {13, 14, 25, 26, 27, 32};
bool prev[6] = {HIGH, HIGH, HIGH, HIGH, HIGH, HIGH};

void jouer(const uint8_t* data, unsigned int len) {
  ledcSetup(0, 78125, 8);          // porteuse PWM 78 kHz, 8 bits
  ledcAttachPin(SPK_PIN, 0);
  unsigned long periode = 1000000UL / SON_RATE;
  unsigned long t = micros();
  for (unsigned int i = 0; i < len; i++) {
    ledcWrite(0, pgm_read_byte(&data[i]));
    t += periode;
    while ((long)(micros() - t) < 0) {}
  }
  ledcWrite(0, 0);
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 6; i++) pinMode(pins[i], INPUT_PULLUP);
  delay(300);
  jouer(son_hello, son_hello_len);   // phrase au branchement
}

void loop() {
  while (Serial.available()) Serial.read();   // ignore les messages du PC

  for (int i = 0; i < 6; i++) {
    bool etat = digitalRead(pins[i]);
    if (etat == LOW && prev[i] == HIGH) {
      Serial.println(i + 1);                  // le PC réagit tout de suite
      jouer(sons[i].data, sons[i].len);       // puis le nom est dit
    }
    prev[i] = etat;
  }
  delay(30);
}
