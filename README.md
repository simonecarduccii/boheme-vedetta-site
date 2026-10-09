# boheme-vedetta-site

> Il sito pubblico di Bohème Vedetta: repository pubblico dedicato,
> pubblicato gratis con GitHub Pages su
> `https://simonecarduccii.github.io/boheme-vedetta-site/`.
>
> Pubblico apposta — dentro non c'è nessun segreto, l'accesso al
> pannello è protetto dal login (Supabase), non dal fatto che il
> codice sia nascosto. `boheme-vedetta` e `boheme-intelligence`
> (il codice vero, il database, le chiavi) restano privati altrove.
>
> Aggiornato e confermato: 2026-10-09.

---

## Cosa contiene

- `index.html` — la pagina pubblica con l'elenco dei bandi, oggi un
  prototipo minimale. Il design vero arriverà da `boheme-design`
  (agente 02), non ancora fatto.
- `admin/index.html` — il pannello di revisione interno (login
  richiesto), usato ogni giorno: è lo strumento di lavoro vero. Qui
  Simone:
  - rivede i bandi trovati dal Motore dei bandi;
  - in "Tutte le fonti" vede sito, pagina bandi e mail di ogni fonte,
    mette una fonte in pausa o la riattiva con un interruttore, e scrive
    a mano la mail che manca con il link di dove l'ha trovata (da quelle
    Scout impara dove cercare);
  - in "Fonti candidate" apre una finestrella con il riassunto del sito
    scritto da Scout e approva o scarta, con una nota facoltativa. Una
    candidata approvata entra da sola in "Tutte le fonti".

Il database e le sue regole stanno in `boheme-vedetta`
(`supabase/migrations/`, decisioni DEC-V23, V25, V26, V27).

## Come cambiare un testo da solo (nessun codice, nessun terminale)

1. Apri il file da cambiare su github.com (`index.html` o
   `admin/index.html`, sopra in questa pagina).
2. In alto a destra del file c'è una matita (icona "modifica").
   Premila.
3. Cambia la frase che ti interessa — è scritta tra virgolette o tra
   tag come `<h1>...</h1>`. Cambia solo il testo, non i simboli `<`,
   `>` o le virgolette intorno.
4. Scorri in fondo alla pagina, scrivi una riga di descrizione (anche
   solo "cambio testo") e premi il bottone verde **"Commit changes"**.
5. Aspetta un minuto, poi ricarica il sito: la modifica è online.

Se qualcosa va storto (pagina che non carica più), dimmelo: con la
cronologia del file ("History", in alto) si torna indietro in un
secondo, niente è mai perso.

## Dove trovare il resto

- Il servizio che scopre/verifica i bandi: `boheme-vedetta` (privato,
  altro repository, cartella affianco a questa).
- Le linee guida di stile e il design vero del sito pubblico:
  `boheme-design` (agente 02, ancora da fare).
