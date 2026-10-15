#!/usr/bin/env python3
"""Pagine statiche per i motori di ricerca.

Legge i bandi pubblicati (vista open_calls_public, chiave pubblica) e scrive:
  bandi/<slug>/index.html      una pagina per bando, con dati strutturati schema.org (JSON-LD)
  bandi/<slug>/scadenza.ics    la scadenza da aggiungere al calendario
  citta/<slug>/index.html      una pagina per città ("Bandi per artisti a Milano")
  regioni/<slug>/index.html    una pagina per regione italiana, quando la città è nota
  citta/index.html             l'elenco di città e regioni
  segnala/index.html           il modulo "Segnala un bando" (testata presa da index.html)
  sitemap.xml                  tutte le pagine qui sopra

Gira da solo con la GitHub Action .github/workflows/pagine.yml (gratis).
Si può lanciare anche a mano:  python3 scripts/genera_pagine.py
Solo libreria standard di Python.
"""
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
import unicodedata
import urllib.parse
import urllib.request

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITO = "https://bohememag.it/opencalls/"
SUPABASE_URL = "https://aqgxgdpsjyidambwipqg.supabase.co"
CHIAVE = "sb_publishable_COi81UtfEAr0grmvCHqMMQ_pVJEWl4k"
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]

# Città italiane -> regione (capoluoghi e città dell'arte più frequenti).
REGIONI = {
    "Lombardia": "milano bergamo brescia como cremona lecco lodi mantova monza pavia sondrio varese",
    "Lazio": "roma frosinone latina rieti viterbo",
    "Piemonte": "torino alessandria asti biella cuneo novara verbania vercelli",
    "Veneto": "venezia verona padova vicenza treviso rovigo belluno",
    "Emilia-Romagna": "bologna modena parma reggio-emilia ferrara ravenna rimini forli cesena piacenza",
    "Toscana": "firenze pisa siena lucca livorno arezzo prato pistoia grosseto massa carrara",
    "Liguria": "genova la-spezia savona imperia",
    "Campania": "napoli salerno caserta avellino benevento",
    "Puglia": "bari lecce taranto foggia brindisi barletta andria trani",
    "Sicilia": "palermo catania messina siracusa ragusa trapani agrigento caltanissetta enna",
    "Sardegna": "cagliari sassari nuoro oristano",
    "Friuli-Venezia Giulia": "trieste udine pordenone gorizia",
    "Trentino-Alto Adige": "trento bolzano merano rovereto",
    "Marche": "ancona pesaro urbino macerata ascoli-piceno fermo",
    "Umbria": "perugia terni spoleto assisi",
    "Abruzzo": "l-aquila pescara chieti teramo",
    "Calabria": "reggio-calabria cosenza catanzaro crotone vibo-valentia",
    "Basilicata": "potenza matera",
    "Molise": "campobasso isernia",
    "Valle d'Aosta": "aosta",
}
CITTA_REGIONE = {c: r for r, cc in REGIONI.items() for c in cc.split()}
NON_LUOGHI = {"online", "on-line", "remoto", "remote", "virtuale", "virtual", "internazionale",
              "international", "worldwide", "ovunque", "tbd", "n-a", "na", "varie", "various"}


def slug(t, n=60):
    t = unicodedata.normalize("NFD", str(t or "")).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:n].strip("-") or "bando"


def e(t):
    return html.escape(str(t or ""), quote=True)


def con_schema(u):
    if not u:
        return None
    u = str(u).strip()
    u = u.replace(" ", "%20")
    return u if re.match(r"^https?://", u, re.I) else "https://" + u.lstrip("/")


def giorno(iso):
    try:
        return dt.date.fromisoformat(str(iso)[:10])
    except ValueError:
        return None


def data_lunga(iso):
    d = giorno(iso)
    return f"{d.day} {MESI[d.month - 1]} {d.year}" if d else None


def gratis(b):
    return bool(re.match(r"^\s*(free|gratis|gratuit[oa]?|nessun|no fee|0\s*(€|eur)?\s*$)", b.get("cost") or "", re.I))


def arte(b):
    return "Fotografia" if re.search(r"photo|fotogra", str(b.get("disciplines") or ""), re.I) else "Arte visiva"


def luogo_di(b):
    luogo, paese = str(b.get("location") or "").strip(), str(b.get("organization_country") or "").strip()
    return ", ".join(x for x in [luogo, paese] if x) if paese and paese.lower() not in luogo.lower() else luogo


def citta_di(b):
    """Prima parte del luogo ("Milano, Italia" -> "Milano"), se è un posto vero."""
    luogo = str(b.get("location") or "").strip()
    if not luogo:
        return None
    nome = re.split(r"[,;/(|·–-]\s*", luogo)[0].strip()
    if not nome or slug(nome) in NON_LUOGHI or len(nome) > 40:
        return None
    return nome[:1].upper() + nome[1:]


def leggi_bandi():
    url = SUPABASE_URL + "/rest/v1/open_calls_public?select=*&order=deadline.asc.nullslast"
    req = urllib.request.Request(url, headers={"apikey": CHIAVE, "Authorization": "Bearer " + CHIAVE})
    with urllib.request.urlopen(req, timeout=30) as r:
        righe = json.load(r)
    oggi = dt.date.today()
    tenuti = []
    for b in righe:
        if b.get("status") == "expired":
            continue
        d = giorno(b.get("deadline")) if b.get("deadline") else None
        if d and d < oggi:
            continue
        tenuti.append(b)
    return tenuti


# ---------------------------------------------------------------- html

STILE = """
* { box-sizing: border-box; }
body { margin: 0; background: var(--colore-fondo-crema); color: var(--colore-nero-caldo); font-family: var(--font-testo);
  font-size: var(--testo-testo); line-height: 1.5; -webkit-font-smoothing: antialiased; }
a { color: inherit; }
.giallo { background: var(--colore-giallo); color: var(--colore-bianco); }
.testata { display: flex; align-items: center; justify-content: space-between; gap: var(--spazio-medio);
  padding: var(--spazio-testata-verticale) var(--spazio-testata-lati); position: relative; }
.marchio { display: flex; align-items: center; text-decoration: none; color: var(--colore-bianco); }
.marchio svg { display: block; flex: none; }
.menu { display: flex; gap: var(--spazio-grande); }
.menu a { font-weight: 500; text-decoration: none; color: var(--colore-bianco); }
.menu a:hover { text-decoration: underline; }
.apri-menu { display: none; }
.apertura, main { max-width: calc(760px + 2 * var(--spazio-pagina-lati)); margin: 0 auto; padding-left: var(--spazio-pagina-lati); padding-right: var(--spazio-pagina-lati); }
.apertura { padding-top: var(--spazio-blocchi); padding-bottom: var(--spazio-blocchi); display: flex; flex-direction: column; gap: var(--spazio-medio); }
.apertura h1 { margin: 0; font-family: var(--font-titoli); font-weight: 700; font-size: 40px; letter-spacing: -0.02em; line-height: 1.15; }
.apertura p { margin: 0; font-weight: 500; font-size: var(--testo-sezione); }
.briciole { font-size: var(--testo-dettagli); font-weight: 500; }
.briciole a { text-decoration: none; }
main { padding-top: var(--spazio-blocchi); padding-bottom: var(--spazio-pagina-alto); display: flex; flex-direction: column; gap: var(--spazio-grande); }
.etichetta { font-weight: 500; font-size: var(--testo-tag); letter-spacing: 0.1em; }
.voci { margin: 0; display: grid; grid-template-columns: max-content 1fr; gap: var(--spazio-piccolo) var(--spazio-medio);
  background: var(--colore-card-beige); border-radius: var(--angoli-card); padding: var(--spazio-grande); }
.voci dt { font-weight: 600; font-size: var(--testo-dettagli); color: var(--colore-grigio-testo); padding-top: 1px; }
.voci dd { margin: 0; overflow-wrap: anywhere; }
.voci ul { margin: 0; padding-left: 18px; }
.voci a, .testo a { color: var(--colore-giallo-scuro-testo); }
.verificato { margin: 0; font-size: var(--testo-dettagli); color: var(--colore-grigio-testo); }
.azioni { display: flex; flex-wrap: wrap; gap: var(--spazio-piccolo); }
.bottone { font-weight: 600; text-decoration: none; padding: var(--spazio-pillola-verticale) var(--spazio-pillola-orizzontale);
  border-radius: var(--angoli-pillola); background: var(--colore-bianco); border: 1px solid var(--colore-linee); }
.bottone.pieno { background: var(--colore-nero-caldo); color: var(--colore-bianco); border-color: var(--colore-nero-caldo); }
.elenco { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--spazio-medio); }
.elenco li { background: var(--colore-card-beige); border-radius: var(--angoli-card); padding: var(--spazio-card) var(--spazio-grande); }
.elenco h2 { margin: 4px 0; font-family: var(--font-titoli); font-weight: 700; font-size: 19px; line-height: 1.25; }
.elenco h2 a { text-decoration: none; }
.elenco h2 a:hover { text-decoration: underline; }
.elenco .sotto { color: var(--colore-grigio-testo); font-weight: 500; }
.luoghi { display: flex; flex-wrap: wrap; gap: var(--spazio-piccolo); list-style: none; padding: 0; margin: 0; }
.luoghi a { display: inline-block; font-weight: 500; text-decoration: none; padding: var(--spazio-pillola-verticale) var(--spazio-pillola-orizzontale);
  border-radius: var(--angoli-pillola); background: var(--colore-bianco); border: 1px solid var(--colore-linee); }
h2.sezione { margin: 0; font-family: var(--font-titoli); font-weight: 700; font-size: 24px; }
@media (max-width: 720px) {
  .testata { padding: var(--spazio-medio); }
  .menu { display: none; }
  .apri-menu { display: block; font: inherit; font-weight: 500; background: none; border: 0; color: var(--colore-bianco); cursor: pointer; padding: var(--spazio-minimo) 0; }
  .testata.aperto .menu { display: flex; flex-direction: column; gap: var(--spazio-medio); position: absolute; right: var(--spazio-medio); top: 100%; z-index: 2;
    background: var(--colore-nero-caldo); padding: var(--spazio-medio) var(--spazio-grande); border-radius: var(--angoli-avviso); }
  .apertura, main { padding-left: var(--spazio-medio); padding-right: var(--spazio-medio); }
  .apertura { padding-top: var(--spazio-piccolo); padding-bottom: var(--spazio-grande); }
  .apertura h1 { font-size: var(--testo-titolo-pagina); }
  main { padding-top: var(--spazio-grande); }
  .voci { grid-template-columns: 1fr; gap: 2px; padding: var(--spazio-card); }
  .voci dd { margin-bottom: var(--spazio-piccolo); }
  .elenco li { padding: var(--spazio-card); }
}
"""

MENU_JS = """<script>
(function () {
  var t = document.getElementById("testata"), a = document.getElementById("apri-menu");
  a.addEventListener("click", function () { var o = t.classList.toggle("aperto"); a.setAttribute("aria-expanded", o ? "true" : "false"); });
})();
</script>"""


def testata():
    with open(os.path.join(RADICE, "index.html"), encoding="utf-8") as f:
        m = re.search(r'\s*<header class="testata".*?</header>', f.read(), re.S)
    return m.group(0)


def pagina(percorso, titolo, descrizione, apertura, corpo, json_ld=None, profondita=2):
    su = "../" * profondita
    ld = "".join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
                 for x in (json_ld or []))
    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<title>{e(titolo)}</title>
<meta name="description" content="{e(descrizione)}">
<link rel="canonical" href="{SITO}{percorso}">
<meta property="og:type" content="website">
<meta property="og:title" content="{e(titolo)}">
<meta property="og:description" content="{e(descrizione)}">
<meta property="og:url" content="{SITO}{percorso}">
<meta property="og:site_name" content="Bohème Vedetta">
<meta name="theme-color" content="#CCA40B">
<link rel="stylesheet" href="{su}admin/tokens.css">
<style>{STILE}</style>
{ld}</head>
<body>
<!-- Pagina generata da scripts/genera_pagine.py: non modificarla a mano. -->
<div class="giallo">
{testata()}
  <section class="apertura">
{apertura}
  </section>
</div>
<main>
{corpo}
</main>
{MENU_JS}
</body>
</html>
"""


def briciole(*voci):
    parti = [f'<a href="{e(h)}">{e(t)}</a>' if h else e(t) for t, h in voci]
    return '    <nav class="briciole" aria-label="Percorso">' + " › ".join(parti) + "</nav>"


def briciole_ld(*voci):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": t, "item": u} for i, (t, u) in enumerate(voci)]}


def ics(b):
    d = giorno(b["deadline"])
    dopo = d + dt.timedelta(days=1)
    esc = lambda t: str(t or "").replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")
    url = con_schema(b.get("opportunity_url") or b.get("organization_website")) or ""
    righe = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Bohème//Vedetta//IT", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             "BEGIN:VEVENT", f"UID:{b['id']}@bohememag.it",
             "DTSTAMP:" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
             "DTSTART;VALUE=DATE:" + d.strftime("%Y%m%d"), "DTEND;VALUE=DATE:" + dopo.strftime("%Y%m%d"),
             "SUMMARY:" + esc("Scadenza: " + (b.get("title") or "bando")),
             "DESCRIPTION:" + esc("\n".join(x for x in [b.get("organization_name"), url, SITO + "#bando-" + b["id"]] if x))]
    if url:
        righe.append("URL:" + url)
    righe += ["BEGIN:VALARM", "TRIGGER:-P7D", "ACTION:DISPLAY", "DESCRIPTION:" + esc("Tra 7 giorni scade: " + (b.get("title") or "bando")),
              "END:VALARM", "END:VEVENT", "END:VCALENDAR"]
    piegate = []
    for r in righe:
        while len(r.encode()) > 74:
            taglio = 74
            while len(r[:taglio].encode()) > 74:
                taglio -= 1
            piegate.append(r[:taglio])
            r = " " + r[taglio:]
        piegate.append(r)
    return "\r\n".join(piegate) + "\r\n"


def pagina_bando(b, percorso, luogo):
    titolo = b.get("title") or "Bando senza titolo"
    ente = b.get("organization_name")
    tipo = arte(b)
    scad = data_lunga(b.get("deadline")) if b.get("deadline") else None
    sito = con_schema(b.get("organization_website"))
    ufficiale = con_schema(b.get("opportunity_url"))
    descr = " ".join(x for x in [
        f"Open call di {tipo.lower()}" + (f" di {ente}" if ente else "") + ".",
        f"Scadenza {scad}." if scad else "",
        "Iscrizione gratuita." if gratis(b) else "",
        (b.get("description") or "")[:110]] if x).strip()[:160]

    voci = []
    def voce(nome, valore):
        if valore:
            voci.append(f"    <dt>{e(nome)}</dt><dd>{valore}</dd>")
    voce("Scadenza", e(scad or "Non indicata"))
    voce("Iscrizione", e("Gratis" if gratis(b) else b.get("cost")))
    voce("Premio", e(b.get("prizes")))
    voce("Mostra", e(b.get("exhibition")))
    voce("Luogo", e(luogo_di(b)))
    voce("Discipline", e(b.get("disciplines")))
    if b.get("eligibility"):
        parti = [x.strip() for x in re.split(r";\s+|\n+", b["eligibility"]) if x.strip()]
        voce("Requisiti", "<ul>" + "".join(f"<li>{e(x)}</li>" for x in parti) + "</ul>" if len(parti) > 1 else e(parti[0]))
    if sito:
        voce("Organizzatore", f'<a href="{e(sito)}" rel="noopener nofollow" target="_blank">{e(ente or sito)}</a>')
    else:
        voce("Organizzatore", e(ente))
    if ufficiale:
        voce("Bando ufficiale", f'<a href="{e(ufficiale)}" rel="noopener nofollow" target="_blank">{e(re.sub(r"^https?://(www\.)?", "", urllib.parse.unquote(ufficiale)).rstrip("/"))}</a>')

    verificato = b.get("link_verified_at") or b.get("updated_at")
    azioni = []
    if ufficiale or sito:
        azioni.append(f'<a class="bottone pieno" href="{e(ufficiale or sito)}" rel="noopener nofollow" target="_blank">Vai al bando</a>')
    if b.get("deadline") and giorno(b["deadline"]):
        azioni.append('<a class="bottone" href="scadenza.ics" download>Aggiungi al calendario</a>')
    azioni.append(f'<a class="bottone" href="../../#bando-{e(b["id"])}">Tutti i bandi</a>')

    corpo = []
    if b.get("description"):
        corpo.append(f'  <p class="testo" style="margin:0">{e(b["description"])}</p>')
    corpo.append('  <dl class="voci">\n' + "\n".join(voci) + "\n  </dl>")
    if verificato and data_lunga(verificato):
        corpo.append(f'  <p class="verificato">Verificato il {e(data_lunga(verificato))} dalla redazione di Bohème.</p>')
    corpo.append('  <div class="azioni">' + "".join(azioni) + "</div>")
    if luogo:
        corpo.append(f'  <p class="verificato">Altri bandi a <a href="../../{e(luogo[1])}">{e(luogo[0])}</a>.</p>')

    briciole_voci = [("Bandi", "../../")]
    if luogo:
        briciole_voci.append((luogo[0], "../../" + luogo[1]))
    apertura = "\n".join([
        briciole(*briciole_voci, (titolo, None)),
        f'    <span class="etichetta">OPEN CALL · {e(tipo.upper())}</span>',
        f"    <h1>{e(titolo)}</h1>",
        f"    <p>{e(ente + (' · ' + b['organization_country'] if b.get('organization_country') else ''))}</p>" if ente else "",
    ])

    evento = {
        "@context": "https://schema.org", "@type": "Event", "name": titolo,
        "description": (b.get("description") or descr)[:500],
        "url": SITO + percorso,
        "eventStatus": "https://schema.org/EventScheduled",
        "startDate": str(b.get("created_at") or dt.date.today())[:10],
        "about": tipo,
    }
    if b.get("deadline"):
        evento["endDate"] = str(b["deadline"])[:10]
    if b.get("location"):
        evento["eventAttendanceMode"] = "https://schema.org/OfflineEventAttendanceMode"
        evento["location"] = {"@type": "Place", "name": b["location"],
                              "address": luogo_di(b)}
    else:
        evento["eventAttendanceMode"] = "https://schema.org/OnlineEventAttendanceMode"
        evento["location"] = {"@type": "VirtualLocation", "url": ufficiale or sito or SITO + percorso}
    if ente:
        evento["organizer"] = {"@type": "Organization", "name": ente, **({"url": sito} if sito else {})}
    if gratis(b):
        evento["isAccessibleForFree"] = True
        evento["offers"] = {"@type": "Offer", "price": "0", "priceCurrency": "EUR", "url": ufficiale or sito or SITO + percorso,
                            "availability": "https://schema.org/InStock"}
    elif ufficiale:
        evento["offers"] = {"@type": "Offer", "url": ufficiale, "description": b.get("cost") or "Vedi bando"}
    ld = [evento, briciole_ld(("Bandi", SITO), *([(luogo[0], SITO + luogo[1])] if luogo else []), (titolo, SITO + percorso))]
    return pagina(percorso, f"{titolo} — scadenza {scad} | Bohème Vedetta" if scad else f"{titolo} | Bohème Vedetta",
                  descr, apertura, "\n".join(corpo), ld)


def scheda_elenco(b, su):
    tipo = arte(b)
    scad = data_lunga(b.get("deadline")) if b.get("deadline") else "scadenza non indicata"
    sotto = " · ".join(x for x in [b.get("organization_name"), "scade il " + scad if b.get("deadline") else scad,
                                   "gratis" if gratis(b) else None] if x)
    return (f'    <li><span class="etichetta">OPEN CALL · {e(tipo.upper())}</span>'
            f'<h2><a href="{su}{e(b["_percorso"])}">{e(b.get("title") or "Senza titolo")}</a></h2>'
            f'<div class="sotto">{e(sotto)}</div></li>')


def pagina_luogo(nome, percorso, qui, tipo_luogo, altri):
    foto = sum(1 for b in qui if arte(b) == "Fotografia")
    titolo = f"Bandi per artisti {'in' if tipo_luogo == 'regione' else 'a'} {nome}: open call di fotografia e arte visiva"
    descr = (f"{len(qui)} {'bando aperto' if len(qui) == 1 else 'bandi aperti'} {'in' if tipo_luogo == 'regione' else 'a'} {nome}"
             f"{f', di cui {foto} di fotografia' if foto else ''}. Open call, premi e residenze controllati a mano dalla redazione di Bohème.")
    apertura = "\n".join([
        briciole(("Bandi", "../../"), ("Città", "../"), (nome, None)),
        f"    <h1>Bandi per artisti {'in' if tipo_luogo == 'regione' else 'a'} {e(nome)}.</h1>",
        f"    <p>{e(descr)}</p>",
    ])
    corpo = ['  <ul class="elenco">'] + [scheda_elenco(b, "../../") for b in qui] + ["  </ul>"]
    if altri:
        corpo += ['  <h2 class="sezione">Anche qui</h2>', '  <ul class="luoghi">'] + \
                 [f'    <li><a href="../../{e(p)}">{e(n)}</a></li>' for n, p in altri] + ["  </ul>"]
    lista = {"@context": "https://schema.org", "@type": "ItemList", "name": titolo,
             "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": SITO + b["_percorso"], "name": b.get("title")}
                                 for i, b in enumerate(qui)]}
    return pagina(percorso, titolo[:70] + " | Bohème Vedetta" if len(titolo) < 70 else titolo, descr, apertura, "\n".join(corpo),
                  [lista, briciole_ld(("Bandi", SITO), ("Città", SITO + "citta/"), (nome, SITO + percorso))])


def scrivi(rel, testo, binario=False):
    p = os.path.join(RADICE, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="" if binario else None) as f:
        f.write(testo)


def main():
    bandi = leggi_bandi()
    for cartella in ("bandi", "citta", "regioni"):
        shutil.rmtree(os.path.join(RADICE, cartella), ignore_errors=True)

    usati = set()
    for b in bandi:
        s = slug(b.get("title"))
        if s in usati:
            s = s + "-" + str(b["id"])[:6]
        usati.add(s)
        b["_percorso"] = f"bandi/{s}/"

    citta, regioni = {}, {}
    for b in bandi:
        c = citta_di(b)
        if not c:
            continue
        citta.setdefault(slug(c), [c, []])[1].append(b)
        r = CITTA_REGIONE.get(slug(c))
        if r:
            regioni.setdefault(slug(r), [r, []])[1].append(b)

    luoghi = [(n, f"citta/{s}/") for s, (n, _) in sorted(citta.items())] + \
             [(n, f"regioni/{s}/") for s, (n, _) in sorted(regioni.items())]

    for b in bandi:
        c = citta_di(b)
        luogo = (c, f"citta/{slug(c)}/") if c else None
        scrivi(b["_percorso"] + "index.html", pagina_bando(b, b["_percorso"], luogo))
        if b.get("deadline") and giorno(b["deadline"]):
            scrivi(b["_percorso"] + "scadenza.ics", ics(b), binario=True)
    for s, (n, qui) in citta.items():
        scrivi(f"citta/{s}/index.html", pagina_luogo(n, f"citta/{s}/", qui, "citta", [x for x in luoghi if x[1] != f"citta/{s}/"]))
    for s, (n, qui) in regioni.items():
        scrivi(f"regioni/{s}/index.html", pagina_luogo(n, f"regioni/{s}/", qui, "regione", [x for x in luoghi if x[1] != f"regioni/{s}/"]))

    # Indice delle città (sempre presente, anche vuoto).
    corpo = (['  <ul class="luoghi">'] + [f'    <li><a href="../{e(p)}">{e(n)}</a></li>' for n, p in luoghi] + ["  </ul>"]) if luoghi \
        else ['  <p class="testo" style="margin:0">Per ora nessun bando ha una città indicata. Li trovi tutti nella <a href="../">pagina dei bandi</a>.</p>']
    scrivi("citta/index.html", pagina("citta/", "Bandi per artisti per città e regione | Bohème Vedetta",
                                      "Open call, premi e residenze per artisti divisi per città e regione, controllati a mano dalla redazione di Bohème.",
                                      briciole(("Bandi", "../"), ("Città", None)) + "\n    <h1>Bandi per città e regione.</h1>",
                                      "\n".join(corpo), profondita=1))

    # Modulo "Segnala un bando": stessa testata della pagina principale.
    with open(os.path.join(RADICE, "scripts", "modelli", "segnala.html"), encoding="utf-8") as f:
        scrivi("segnala/index.html", f.read().replace("{{TESTATA}}", testata().strip("\n")))

    oggi = dt.date.today().isoformat()
    def agg(b):
        return str(b.get("updated_at") or b.get("link_verified_at") or b.get("created_at") or oggi)[:10]
    indirizzi = [(SITO, oggi), (SITO + "segnala/", oggi), (SITO + "citta/", oggi)]
    indirizzi += [(SITO + b["_percorso"], agg(b)) for b in bandi]
    indirizzi += [(SITO + p, oggi) for _, p in luoghi]
    scrivi("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "".join(f"  <url><loc>{e(u)}</loc><lastmod>{d}</lastmod></url>\n" for u, d in indirizzi) + "</urlset>\n")
    print(f"{len(bandi)} bandi, {len(citta)} città, {len(regioni)} regioni, {len(indirizzi)} indirizzi nella sitemap")


if __name__ == "__main__":
    sys.exit(main())
