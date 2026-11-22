// SoundBoard ESP32 - modèle « écran OLED »
// Écran OLED SSD1306 128x64 en SPI (7 broches) qui affiche le nom des 6 boutons,
// plus un buzzer pour les bips.
//
// Switchs (l'autre patte sur GND) : 13, 14, 25, 26, 27, 32
// Écran : VCC 3V3, GND, SCL(SCK) 18, SDA(MOSI) 23, RST 17, DC 16, CS 5
// Buzzer passif : GPIO 33 et GND
//
// Bibliothèques (Library Manager) : "Adafruit SSD1306" et "Adafruit GFX Library"
// Carte : ESP32 Dev Module, paquet esp32 version 2.0.17

#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define OLED_DC  16
#define OLED_CS  5
#define OLED_RST 17
#define BUZZER   33

Adafruit_SSD1306 display(128, 64, &SPI, OLED_DC, OLED_RST, OLED_CS);

const int pins[6] = {13, 14, 25, 26, 27, 32};
const char* noms[6] = {"Hermes", "Discord", "Claude", "Google", "Epic", "Roblox"};
bool prev[6] = {HIGH, HIGH, HIGH, HIGH, HIGH, HIGH};

void bip(int freq, int ms) {
  ledcWriteTone(0, freq);
  delay(ms);
  ledcWriteTone(0, 0);
}

void dessineCase(int i, bool actif) {
  int x = (i % 2) * 64;
  int y = (i / 2) * 21;
  display.fillRect(x, y, 64, 21, actif ? SSD1306_WHITE : SSD1306_BLACK);
  display.drawRect(x, y, 64, 21, SSD1306_WHITE);
  display.setTextColor(actif ? SSD1306_BLACK : SSD1306_WHITE);
  int16_t x1, y1; uint16_t w, h;
  display.getTextBounds(noms[i], 0, 0, &x1, &y1, &w, &h);
  display.setCursor(x + (64 - w) / 2, y + (21 - h) / 2);
  display.print(noms[i]);
  display.display();
}

void dessineTout() {
  display.clearDisplay();
  for (int i = 0; i < 6; i++) dessineCase(i, false);
}

void message(const char* l1, const char* l2) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(10, 8);  display.print(l1);
  display.setCursor(10, 36); display.print(l2);
  display.display();
  display.setTextSize(1);
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(20);
  for (int i = 0; i < 6; i++) pinMode(pins[i], INPUT_PULLUP);

  ledcSetup(0, 2000, 8);
  ledcAttachPin(BUZZER, 0);

  display.begin(SSD1306_SWITCHCAPVCC);
  display.setTextSize(1);

  message("SoundBoard", "Connectee");
  bip(1000, 100); bip(1500, 150);
  delay(1200);
  dessineTout();
}

void loop() {
  // Messages du PC : "PC" = le script Python est connecté ("T..." = heure, ignorée ici)
  if (Serial.available()) {
    String s = Serial.readStringUntil('\n');
    s.trim();
    if (s == "PC") {
      message("PC", "Connecte");
      bip(1200, 100); bip(1800, 150);
      delay(1200);
      dessineTout();
    }
  }

  for (int i = 0; i < 6; i++) {
    bool etat = digitalRead(pins[i]);
    if (etat == LOW && prev[i] == HIGH) {
      Serial.println(i + 1);
      dessineCase(i, true);
      bip(2000, 30);
      delay(150);
      dessineCase(i, false);
    }
    prev[i] = etat;
  }
  delay(30);
}
