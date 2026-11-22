# SoundBoard ESP32

Une mini « soundboard » faite maison : 6 switchs mécaniques branchés sur un **ESP32**.
Chaque appui lance une action sur le PC Windows (ouvrir / fermer une appli).
Le PC et l'ESP32 communiquent par le câble USB, **sur n'importe quel port COM**.

| Switch | GPIO | Action sur le PC |
|:---:|:---:|---|
| 1 | 13 | PowerShell + agent IA `hermes.exe` — ouvre / ferme |
| 2 | 14 | Discord — ouvre / ferme |
| 3 | 25 | Claude (application) — ouvre |
| 4 | 26 | Google Chrome (fenêtre « appli ») — ouvre / ferme |
| 5 | 27 | Muet de Windows — coupe / rétablit le son |
| 6 | 32 | Capture d'écran — enregistre un PNG dans `Images` |

**Les switchs sont entièrement modifiables dans le code** : tu choisis ce que chacun ouvre ou ferme. Voir la section [Personnaliser les switchs](#personnaliser-les-switchs) ci-dessous.

## Personnaliser les switchs

Les 6 switchs ne sont pas figés : **tu peux modifier dans le code ce que chacun ouvre et ferme** sur le PC.

1. **L'action (ce qui s'ouvre / se ferme)** se règle dans `pc/soundboard.py`.
   Chaque appui envoie le numéro du switch (1 à 6) au PC. Le dictionnaire `ACTIONS` associe ce numéro à une fonction :

   ```python
   ACTIONS = {
       "1": hermes,
       "2": discord,
       "3": claude,
       "4": google,
       "5": muet,
       "6": capture,
   }
   ```

   Écris ta propre fonction (par exemple `ouvre_calculatrice()`) et remplace la fonction dans la ligne voulue. Pour un bouton « ouvre / ferme », la fonction vérifie si l'application tourne : premier appui = lancement, deuxième appui = fermeture (voir `discord()` ou `google()` comme exemples).

2. **Le texte affiché sur l'écran OLED** se règle dans `firmware/oled/oled.ino`, dans le tableau `noms` :

   ```cpp
   const char* noms[6] = {"Hermes", "Discord", "Claude", "Google", "Muet", "Capture"};
   ```

3. **Les GPIO utilisés** se règlent dans le tableau `pins` du même fichier (l'autre patte du switch va au GND).

Après modification du firmware, retéléverse le croquis ; après modification du Python, relance `python pc/soundboard.py`. Pense à garder le même ordre des 6 numéros des deux côtés.

## Les 3 modèles

Le programme du PC est le même pour tous. Seul le programme de l'ESP32 change :

| Modèle | Dossier | Ce qu'il ajoute | État |
|---|---|---|---|
| **Voix** | `firmware/voix` | Mini haut-parleur : dit une phrase au branchement et le nom de l'appli à chaque appui | testé |
| **OLED** | `firmware/oled` | Écran OLED SPI 128x64 qui affiche le nom des boutons, plus un buzzer | compile, pas testé sur un écran en état de marche |
| **Horloge** | `firmware/horloge` | Module 4 chiffres TM1637 qui affiche l'heure envoyée par le PC | pas testé |

## Contenu du dépôt

```
soundboard-esp32/
├── pc/
│   ├── soundboard.py          Programme du PC (Windows)
│   ├── requirements.txt       Dépendance Python : pyserial
│   └── lancer_soundboard.bat  Double-clic pour le lancer
├── tools/
│   └── make_sons.py           Fabrique les voix (sons.h) pour le modèle Voix
└── firmware/
    ├── voix/voix.ino
    ├── oled/oled.ino
    └── horloge/horloge.ino
```

## Matériel

- 1 ESP32 « DevKit » classique (ESP32-VROOM / ESP32-D0WD), avec un câble USB **de données**
- 6 switchs mécaniques (type MX)
- Selon le modèle :
  - **Voix** : mini haut-parleur, 1 résistance 100 Ω, 1 condensateur 100 à 220 µF (ou un module ampli PAM8403 pour plus de volume)
  - **OLED** : écran SSD1306 128x64 SPI (7 broches), 1 buzzer passif
  - **Horloge** : module 4 chiffres TM1637 (4 broches)

## Câblage

### Les 6 switchs (tous les modèles)

Une patte du switch sur le GPIO, l'autre sur **GND**. Pas de résistance : le programme active la résistance interne (`INPUT_PULLUP`). Les GND des switchs peuvent être reliés entre eux.

```
Switch 1 : GPIO 13 ── switch ── GND
Switch 2 : GPIO 14 ── switch ── GND
Switch 3 : GPIO 25 ── switch ── GND
Switch 4 : GPIO 26 ── switch ── GND
Switch 5 : GPIO 27 ── switch ── GND
Switch 6 : GPIO 32 ── switch ── GND
```

### Modèle Voix : haut-parleur

Un haut-parleur ne se branche **jamais sans résistance** sur une broche de l'ESP32.

```
GPIO 33 ──[ résistance 100 Ω ]──(+) condensateur (−)── fil 1 du haut-parleur
                                                       fil 2 du haut-parleur ── GND
```

- Le condensateur (électrolytique) est polarisé : la patte la plus **longue** (+) côté GPIO, la patte avec la **bande grise** (−) côté haut-parleur.
- Le son est faible avec ce montage. Pour plus de volume, utilise un module ampli :

```
GPIO 33 ──(+) condensateur 100 µF (−)── entrée de l'ampli
GND ESP32 ───────────────────────────── GND de l'ampli
VIN (5 V) ───────────────────────────── VCC de l'ampli
Sortie de l'ampli ───────────────────── haut-parleur
```

### Modèle OLED : écran SPI SSD1306 + buzzer

| Écran | ESP32 |
|---|---|
| VCC | 3V3 |
| GND | GND |
| SCL (SCK) | GPIO 18 |
| SDA (MOSI) | GPIO 23 |
| RST | GPIO 17 |
| DC | GPIO 16 |
| CS | GPIO 5 |

Buzzer passif : GPIO 33 et GND.

### Modèle Horloge : module TM1637

| TM1637 | ESP32 |
|---|---|
| CLK | GPIO 22 |
| DIO | GPIO 21 |
| VCC | 3V3 |
| GND | GND |

> Un afficheur 4 chiffres « nu » à 12 broches (6 de chaque côté) ne marche pas directement : il faut un module TM1637 ou une puce driver (MAX7219, 74HC595).

Broches à éviter sur l'ESP32 : 6 à 11 (mémoire flash), 0, 2, 12, 15 (démarrage), 34 à 39 (entrées seulement).

## Installation

### 1. Programme du PC (Windows)

1. Installe Python depuis [python.org](https://www.python.org) en cochant **Add python.exe to PATH**.
2. Dans une invite de commandes :
   ```
   pip install -r pc/requirements.txt
   ```
3. Si besoin, modifie dans `pc/soundboard.py` le chemin de `hermes.exe` (variable `HERMES`).

### 2. Programme de l'ESP32 (Arduino IDE)

1. Installe **Arduino IDE**.
2. **File → Preferences → Additional boards manager URLs** :
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
3. **Tools → Board → Boards Manager** : installe **esp32 (Espressif Systems) en version 2.0.17**. La version 3.x change l'API du son (`ledc`) et le code ne compilera pas.
4. Installe les bibliothèques du modèle choisi (**Sketch → Include Library → Manage Libraries**) :
   - Voix : aucune
   - OLED : *Adafruit SSD1306* et *Adafruit GFX Library*
   - Horloge : *TM1637* (Avishay Orpaz)
5. **Tools → Board → ESP32 Dev Module** et **Tools → Port** (le port de ton ESP32).

### 3. Modèle Voix : fabriquer les voix

```
python tools/make_sons.py
```

Windows dit les phrases et le script crée `firmware/voix/sons.h` (ignoré par Git). Pour changer les phrases, modifie `HELLO` et `SONS` en haut de `tools/make_sons.py`. Utilise une voix anglaise de Windows si possible, sinon l'accent sera celui de la voix française.

### 4. Téléverser

Ouvre le `.ino` du modèle choisi et clique sur **Upload**. Si l'upload reste bloqué sur `Connecting...`, maintiens le bouton **BOOT** de l'ESP32 jusqu'à ce que l'envoi démarre.

### 5. Lancer le programme du PC

```
python pc/soundboard.py
```

ou double-clique sur `pc/lancer_soundboard.bat`. Le script :

- trouve tout seul le port COM de la soundboard (CP210x, CH340, FTDI) ;
- se reconnecte tout seul si tu débranches puis rebranches la carte ;
- envoie l'heure à la carte toutes les 30 secondes (modèle Horloge).

Pour qu'il démarre avec Windows sans fenêtre noire : crée un raccourci vers `pythonw pc\soundboard.py` dans le dossier `shell:startup` (touche Windows + R).

## Dépannage

| Problème | Solution |
|---|---|
| Aucun port COM dans Arduino IDE | Câble USB de données, autre port USB du PC, installer le driver CP210x ou CH340 |
| `Wrong boot mode detected` | Maintenir **BOOT** pendant le « Connecting... » |
| `could not open port` | Fermer le Serial Monitor d'Arduino IDE et le script Python avant de téléverser |
| `sons.h: No such file` | Lancer `python tools/make_sons.py` (modèle Voix) |
| Rien ne se passe à l'appui | Regarder si le script affiche `Reçu : 1` : si non, c'est le câblage du switch |
| Pas de son | Vérifier le sens du condensateur, la résistance, le GND commun |

## Remarques

- Les actions utilisent les emplacements d'installation habituels de Windows. Si une appli ne se lance pas, ajuste son chemin dans `pc/soundboard.py` — c'est aussi là que tu modifies ce que les switchs ouvrent et ferment (voir [Personnaliser les switchs](#personnaliser-les-switchs)).
- Un exécutable lancé par ce script a les droits de ton compte : ne laisse pas d'inconnus brancher une autre carte sur ton PC avec ce script lancé.

## Licence

MIT — voir le fichier [LICENSE](LICENSE).
