"""
SoundBoard ESP32 : programme du PC (Windows).

Il écoute la soundboard branchée en USB (sur n'importe quel port COM)
et lance une action à chaque appui sur un switch.
Il envoie aussi l'heure à la carte (utile pour le modèle « horloge »).

Pour changer ce qu'ouvre/ferme un switch, éditez le dictionnaire ACTIONS
plus bas : voir le commentaire « PERSONNALISATION DES SWITCHS ».
"""
import ctypes
import os
import subprocess
import time

import serial
import serial.tools.list_ports

user32 = ctypes.windll.user32
WM_CLOSE = 0x0010
CREATE_NEW_CONSOLE = 0x00000010
VK_VOLUME_MUTE = 0x00AD
KEYEVENTF_KEYUP = 0x0002
user32.keybd_event.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_uint, ctypes.c_size_t]
user32.keybd_event.restype = None

# Chemin de l'agent IA lancé par le switch 1 (modifie-le si besoin)
HERMES = os.path.expandvars(r"%LOCALAPPDATA%\hermes\bin\hermes.exe")

# Puces USB-série des cartes ESP32 : CP210x, CH340, FTDI, USB natif ESP32-S3
VID_ESP32 = {0x10C4, 0x1A86, 0x0403, 0x303A}

# Toutes les 30 s, le PC renvoie l'heure à la carte
INTERVALLE_HEURE = 30


# ---------- Outils Windows ----------

def processus_actif(nom):
    sortie = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {nom}"],
                            capture_output=True, text=True).stdout
    return nom.lower() in sortie.lower()


def trouver_fenetres(titre_exact):
    resultats = []
    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            longueur = user32.GetWindowTextLengthW(hwnd)
            if longueur:
                buf = ctypes.create_unicode_buffer(longueur + 1)
                user32.GetWindowTextW(hwnd, buf, longueur + 1)
                if buf.value == titre_exact:
                    resultats.append(hwnd)
        return True

    user32.EnumWindows(EnumProc(callback), 0)
    return resultats


# ---------- Actions des switchs ----------

proc_hermes = None


def hermes():
    """1er appui : ouvre PowerShell et lance l'agent. 2e appui : ferme."""
    global proc_hermes
    if proc_hermes is not None and proc_hermes.poll() is None:
        subprocess.run(["taskkill", "/PID", str(proc_hermes.pid), "/T", "/F"],
                       capture_output=True)
        proc_hermes = None
    else:
        proc_hermes = subprocess.Popen(
            ["powershell", "-NoExit", "-Command", f'& "{HERMES}"'],
            creationflags=CREATE_NEW_CONSOLE,
        )


def discord():
    if processus_actif("Discord.exe"):
        subprocess.run(["taskkill", "/IM", "Discord.exe", "/F"],
                       capture_output=True)
    else:
        chemin = os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe")
        subprocess.Popen([chemin, "--processStart", "Discord.exe"])


def claude():
    os.startfile("claude://")


def google():
    """Ouvre Google dans une fenêtre Chrome « appli ». 2e appui : ferme."""
    fenetres = trouver_fenetres("Google")
    if fenetres:
        for h in fenetres:
            user32.PostMessageW(h, WM_CLOSE, 0, 0)
        return
    chemins = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in chemins:
        if os.path.exists(c):
            subprocess.Popen([c, "--app=https://www.google.com"])
            return
    print("Chrome introuvable")


def muet():
    """1er appui : coupe le son de Windows ; 2e appui : le remet."""
    user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
    user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_KEYUP, 0)


def capture():
    """Enregistre une capture de l'écran dans le dossier Images."""
    dossier = os.path.join(os.path.expanduser("~"), "Pictures")
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, "capture_" + time.strftime("%Y%m%d_%H%M%S") + ".png")
    script = (
        "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
        "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
        "$bmp=New-Object System.Drawing.Bitmap($b.Width,$b.Height); "
        "$g=[System.Drawing.Graphics]::FromImage($bmp); "
        "$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size); "
        f"$bmp.Save('{chemin}'); $g.Dispose(); $bmp.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True)
    print("Capture enregistrée :", chemin)


# ---------- PERSONNALISATION DES SWITCHS ----------
# Chaque appui sur la carte envoie son numéro (1 à 6). Ce dictionnaire associe
# ce numéro à la fonction à lancer sur le PC. Pour changer ce qu'un switch
# ouvre ou ferme, modifie la fonction correspondante ci-dessus (ou remplace-la
# ici par une autre fonction). Les mêmes noms s'affichent sur l'écran OLED via
# le tableau "noms" dans firmware/oled/oled.ino.
# Switch 1 à 6 (même ordre que les GPIO du firmware)
ACTIONS = {
    "1": hermes,
    "2": discord,
    "3": claude,
    "4": google,
    "5": muet,
    "6": capture,
}


# ---------- Connexion automatique, sur n'importe quel port COM ----------

def trouver_ports():
    """Ports à essayer : d'abord les cartes ESP32 connues, puis les autres
    ports USB (jamais COM1, le port interne du PC)."""
    ports = list(serial.tools.list_ports.comports())
    esp = [p.device for p in ports if p.vid in VID_ESP32]
    autres = [p.device for p in ports
              if p.vid is not None and p.device not in esp]
    return esp + autres


def ouvrir_soundboard():
    for port in trouver_ports():
        try:
            return serial.Serial(port, 115200, timeout=1), port
        except (serial.SerialException, OSError):
            continue  # port occupé ou pas la bonne carte : on passe au suivant
    return None, None


def envoyer_heure(ser):
    ser.write(time.strftime("T%H%M%S\n").encode())


def traiter(ligne):
    print("Reçu :", ligne)
    action = ACTIONS.get(ligne)
    if action:
        action()


def main():
    attente_affichee = False
    while True:
        ser, port = ouvrir_soundboard()
        if ser is None:
            if not attente_affichee:
                print("Aucune soundboard trouvée : branche-la, je réessaie...")
                attente_affichee = True
            time.sleep(2)
            continue

        attente_affichee = False
        time.sleep(2)  # l'ESP32 redémarre quand le port s'ouvre
        try:
            ser.write(b"PC\n")  # dit à la soundboard que le PC est connecté
            envoyer_heure(ser)
            dernier_envoi = time.time()
            print("SoundBoard connectée sur", port)
            while True:
                ligne = ser.readline().decode(errors="ignore").strip()
                if ligne:
                    traiter(ligne)
                if time.time() - dernier_envoi >= INTERVALLE_HEURE:
                    envoyer_heure(ser)
                    dernier_envoi = time.time()
        except (serial.SerialException, OSError):
            print("SoundBoard débranchée : reconnexion automatique...")
        finally:
            try:
                ser.close()
            except Exception:
                pass
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Arrêt.")
