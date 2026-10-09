#!/usr/bin/env python3
"""Variabili Figma -> admin/tokens.css (stile del pannello).

Uso:
    python3 scripts/figma_tokens.py /mnt/project-files/boheme/boheme-design/tokens/figma-tokens.json

Il JSON è l'elenco delle variabili della collezione "Bohème" del
file Figma del pannello (C4KJafSmGKjI2EohOGnITc), come lo restituisce
get_variable_defs del Figma MCP: {"colore/giallo": "#CCA40B", ...}.
Lo script scrive admin/tokens.json (copia leggibile) e admin/tokens.css.
Le variabili che mancano nel Figma restano col valore precedente, così
una variabile cancellata per sbaglio non rompe il pannello.

Regole per i nomi (concordate col thread design): minuscole, accenti tolti,
ogni carattere che non è a-z o 0-9 diventa "-" ("arti/Street Art" ->
--arti-street-art). Colori così come sono, numeri in px, font (gruppo
"font") tra virgolette e caricati da Google Fonts.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
JSON_TOKEN = RADICE / "admin" / "tokens.json"
CSS_TOKEN = RADICE / "admin" / "tokens.css"
GRUPPI = ("colore", "arti", "font", "testo", "angoli", "spazio", "layout")
PESI_FONT = {"titoli": "600;700", "testo": "400;500;600;700"}


def nome_css(nome):
    senza_accenti = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return "--" + re.sub(r"[^a-z0-9]+", "-", senza_accenti.lower()).strip("-")


def pulisci_valore(nome, valore):
    gruppo = nome.split("/")[0]
    testo = str(valore).strip()
    if gruppo in ("colore", "arti"):
        m = re.fullmatch(r"#?([0-9A-Fa-f]{6})([0-9A-Fa-f]{2})?", testo)
        if not m:
            raise ValueError(f"{nome}: colore non valido {testo!r}")
        return "#" + (m.group(1) + (m.group(2) or "")).upper()
    if gruppo == "font":
        # get_variable_defs può dare 'Font(family: "Inter", ...)': teniamo la famiglia
        m = re.search(r'family:\s*"?([^",)]+)', testo)
        famiglia = (m.group(1) if m else testo).strip().strip('"')
        if not re.fullmatch(r"[A-Za-z0-9 ]+", famiglia):
            raise ValueError(f"{nome}: font non valido {testo!r}")
        return famiglia
    numero = float(re.sub(r"px$", "", testo))
    if not 0 <= numero <= 4000:
        raise ValueError(f"{nome}: numero fuori scala {testo!r}")
    return int(numero) if numero.is_integer() else numero


def leggi(path):
    dati = json.loads(Path(path).read_text())
    if isinstance(dati, dict) and "variables" in dati:
        dati = dati["variables"]
    return {k: v for k, v in dati.items() if k.split("/")[0] in GRUPPI and "/" in k}


def css(token):
    righe = []
    font = [token[k] for k in ("font/titoli", "font/testo") if k in token]
    if font:
        famiglie = []
        for chiave in ("titoli", "testo"):
            f = token.get("font/" + chiave)
            if f and not any(f == x.split(":")[0].replace("+", " ") for x in famiglie):
                famiglie.append(f.replace(" ", "+") + ":wght@" + PESI_FONT[chiave])
        url = "https://fonts.googleapis.com/css2?" + "&".join("family=" + x for x in famiglie) + "&display=swap"
        righe.append(f'@import url("{url}");')
    righe.append("/* GENERATO da scripts/tokens_da_figma.py dalle variabili Figma: non modificare a mano. */")
    righe.append(":root {")
    for nome in sorted(token, key=lambda n: (GRUPPI.index(n.split("/")[0]), n)):
        valore = token[nome]
        var = nome_css(nome)
        if nome.startswith("font/"):
            valore = f'"{valore}", system-ui, -apple-system, "Segoe UI", sans-serif'
        elif isinstance(valore, (int, float)):
            valore = f"{valore}px"
        righe.append(f"  {var}: {valore};")
    righe.append("}")
    return "\n".join(righe) + "\n"


def main():
    precedenti = json.loads(JSON_TOKEN.read_text()) if JSON_TOKEN.exists() else {}
    nuovi = {}
    if len(sys.argv) > 1:
        for nome, valore in leggi(sys.argv[1]).items():
            nuovi[nome] = pulisci_valore(nome, valore)
    token = {**precedenti, **nuovi}
    cambiati = sorted(k for k in token if precedenti.get(k) != token[k])
    JSON_TOKEN.write_text(json.dumps(token, indent=2, ensure_ascii=False) + "\n")
    CSS_TOKEN.write_text(css(token))
    mancanti = sorted(set(precedenti) - set(nuovi)) if len(sys.argv) > 1 else []
    print("cambiati:", ", ".join(cambiati) or "nessuno")
    if mancanti:
        print("non trovati nel Figma (tengo il valore di prima):", ", ".join(mancanti))


if __name__ == "__main__":
    main()
