# 🏥 RSA Toscana — Monitoraggio Posti Liberi

Applicazione desktop e pagina web per monitorare in **tempo reale** i posti letto disponibili nelle Residenze Sanitarie Assistenziali (RSA) della Regione Toscana.

I dati vengono recuperati direttamente dal portale ufficiale della Regione Toscana e aggiornati su richiesta.

---

## 🌐 Consulta la pagina web

Puoi vedere i dati aggiornati direttamente dal browser, senza installare nulla:

👉 **[mencoxx.github.io/rsa-toscana](https://mencoxx.github.io/rsa-toscana)**

La pagina include:
- Ricerca per nome struttura, comune o indirizzo
- Filtro per comune e per genere del posto letto
- Ordinamento per colonna
- Retta giornaliera, contatti e data di aggiornamento per ogni struttura

---

## 💻 App Desktop (Windows)

Se preferisci usare l'applicazione locale, puoi scaricarla direttamente:

### ⬇️ [Scarica RSA_App.exe](https://github.com/mencoxx/rsa-toscana/releases/download/v1.0/RSA_App.exe)

> Dimensione: ~11 MB — Nessuna installazione richiesta, basta avviare il file.

### Come si usa

1. **Scarica** `RSA_App.exe` dal link sopra
2. **Avvia** il file (potresti vedere un avviso di Windows SmartScreen — clicca su *Ulteriori informazioni* → *Esegui comunque*)
3. Clicca **🔄 Aggiorna Dati** per scaricare le ultime disponibilità dalla Regione
4. Al termine, clicca **👁️ Apri Tabella** per aprire la pagina HTML nel tuo browser

### Nota sull'avviso di Windows

Il file `.exe` non è firmato digitalmente (firma costosa), quindi Windows potrebbe mostrare un avviso. Il codice sorgente è completamente visibile in questo repository: puoi verificarlo prima di eseguirlo.

---

## ⚙️ Come funziona

```
Regione Toscana API
        │
        ▼
RSA_App (scarica tutti i comuni in parallelo)
        │
        ├─► rsa_posti_liberi.json   (dati grezzi)
        ├─► risultati_rsa.html      (tabella interattiva)
        └─► GitHub Pages            (pubblicazione automatica)
```

- Recupera la lista dei comuni dalla Regione Toscana
- Per ogni comune scarica le strutture RSA in parallelo (fino a 25 connessioni simultanee)
- Filtra solo le strutture con almeno un posto libero
- Genera una pagina HTML interattiva con ricerca e filtri
- Carica i dati aggiornati su GitHub Pages

---

## 🛠️ Esecuzione da sorgente

Requisiti: **Python 3.10+**

```bash
# Clona il repository
git clone https://github.com/mencoxx/rsa-toscana.git
cd rsa-toscana

# Avvia l'app (nessuna dipendenza esterna, usa solo la libreria standard)
python RSA_App.pyw
```

Per ricompilare l'eseguibile:

```bash
pip install pyinstaller
pyinstaller --noconfirm RSA_App.spec
# L'exe viene generato in dist/RSA_App.exe
```

---

## 📁 Struttura del repository

| File | Descrizione |
|---|---|
| `RSA_App.pyw` | Sorgente principale dell'app (Python + tkinter) |
| `RSA_App.spec` | Configurazione PyInstaller |
| `rsa_posti_liberi.json` | Dati aggiornati (generato dall'app) |
| `index.html` | Pagina web interattiva (generata dall'app) |
| `.github/workflows/scrape.yml` | Workflow GitHub Actions per aggiornamento automatico |

---

## 📬 Contatti

Sviluppato da **Leonardo Cozzolino**

- 📧 [Leonardo.cozzolino@gmail.com](mailto:Leonardo.cozzolino@gmail.com)
- 🐙 [github.com/mencoxx](https://github.com/mencoxx)

Per segnalazioni, suggerimenti o domande apri una [Issue](https://github.com/mencoxx/rsa-toscana/issues).

---

*Dati forniti dal portale ufficiale della Regione Toscana — aggiornati dalle strutture stesse.*
