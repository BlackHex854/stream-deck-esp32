"""
make_sons.py : fabrique firmware/voix/sons.h (les voix pour l'ESP32).

Utilisation (sur un PC Windows) :
    python tools/make_sons.py

Windows dit chaque phrase, puis le script convertit les sons en tableaux
8 bits / 8000 Hz que l'ESP32 sait jouer.
Pour changer ce qui est dit, modifie les listes HELLO et SONS ci-dessous.

Option (pour utiliser tes propres fichiers WAV 16 bits : hello.wav, hermes.wav...) :
    python tools/make_sons.py --wavdir mon_dossier
"""
import argparse
import os
import struct
import subprocess
import sys
import tempfile
import wave

RATE = 8000  # fréquence de lecture sur l'ESP32

# (nom du son, phrase dite). L'ordre de SONS = switch 1 à 6.
HELLO = ("hello", "Hello there, how are you?")
SONS = [
    ("hermes", "Hermes"),
    ("discord", "Discord"),
    ("claude", "Claude"),
    ("google", "Google"),
    ("epic", "Epic Games"),
    ("roblox", "Roblox"),
]

SORTIE_PAR_DEFAUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "firmware", "voix", "sons.h"
)


def faire_wav_windows(chemin_wav, phrase):
    chemin_wav = os.path.abspath(chemin_wav)
    ps = (
        "Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$v = $s.GetInstalledVoices() | Where-Object "
        "{ $_.VoiceInfo.Culture.Name -like 'en-*' } | Select-Object -First 1;"
        "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) };"
        f"$s.SetOutputToWaveFile('{chemin_wav}');"
        f"$s.Speak('{phrase}');"
        "$s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)


def lire_wav(chemin):
    with wave.open(chemin, "rb") as w:
        canaux = w.getnchannels()
        largeur = w.getsampwidth()
        freq = w.getframerate()
        brut = w.readframes(w.getnframes())
    if largeur != 2:
        sys.exit(f"{chemin} : il faut un WAV 16 bits (PCM).")
    vals = struct.unpack("<%dh" % (len(brut) // 2), brut)
    if canaux > 1:
        vals = [sum(vals[i:i + canaux]) // canaux for i in range(0, len(vals), canaux)]
    return list(vals), freq


def reechantillonner(s, freq, cible):
    ratio = freq / cible
    sortie = []
    for k in range(int(len(s) / ratio)):
        a = int(k * ratio)
        b = max(a + 1, int((k + 1) * ratio))
        fenetre = s[a:b]
        sortie.append(sum(fenetre) / len(fenetre))
    return sortie


def couper_silences(s):
    pic = max(abs(x) for x in s) or 1
    seuil = pic * 0.02
    debut = next(i for i, x in enumerate(s) if abs(x) > seuil)
    fin = len(s) - next(i for i, x in enumerate(reversed(s)) if abs(x) > seuil)
    marge = RATE // 50  # 20 ms
    return s[max(0, debut - marge):min(len(s), fin + marge)]


def vers_8bits(s):
    pic = max(abs(x) for x in s) or 1
    out = []
    for x in s:
        v = 128 + int(round(x / pic * 0.95 * 127))
        out.append(min(255, max(0, v)))
    return out


def convertir(chemin_wav):
    s, freq = lire_wav(chemin_wav)
    s = reechantillonner(s, freq, RATE)
    s = couper_silences(s)
    return vers_8bits(s)


def tableau(nom, octets):
    lignes = []
    for i in range(0, len(octets), 16):
        lignes.append("  " + ", ".join(str(b) for b in octets[i:i + 16]) + ",")
    return (
        f"const unsigned int son_{nom}_len = {len(octets)};\n"
        f"const uint8_t son_{nom}[] PROGMEM = {{\n" + "\n".join(lignes) + "\n};\n\n"
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wavdir", help="dossier de WAV existants au lieu de la voix Windows")
    p.add_argument("--out", default=SORTIE_PAR_DEFAUT)
    args = p.parse_args()

    tous = [HELLO] + SONS
    donnees = {}
    with tempfile.TemporaryDirectory() as tmp:
        for nom, phrase in tous:
            if args.wavdir:
                wav = os.path.join(args.wavdir, nom + ".wav")
            else:
                wav = os.path.join(tmp, nom + ".wav")
                print(f"Voix : {phrase}")
                faire_wav_windows(wav, phrase)
            donnees[nom] = convertir(wav)

    sortie = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    with open(sortie, "w", encoding="utf-8") as f:
        f.write("// Genere par make_sons.py : ne pas modifier a la main\n")
        f.write("#pragma once\n#include <pgmspace.h>\n\n")
        f.write(f"#define SON_RATE {RATE}\n\n")
        for nom, _ in tous:
            f.write(tableau(nom, donnees[nom]))
        f.write("struct Son { const uint8_t* data; unsigned int len; };\n")
        f.write("// Un son par switch (switch 1 = case 0, ...)\n")
        f.write("const Son sons[6] = {\n")
        for nom, _ in SONS:
            f.write(f"  {{ son_{nom}, son_{nom}_len }},\n")
        f.write("};\n")

    total = sum(len(v) for v in donnees.values())
    for nom, _ in tous:
        print(f"  {nom}: {len(donnees[nom]) / RATE:.1f} s")
    print(f"OK : {sortie} ecrit ({total} octets au total)")


if __name__ == "__main__":
    main()
