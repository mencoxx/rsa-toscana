import urllib.request
import json
import base64
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

API_BASE = "https://risorse.regione.toscana.it/api/rsa"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
# Centro Toscana + raggio massimo accettato dal portale (500 km): copre tutta la regione.
STREAM_BODY = {"lat": 43.45, "lon": 11.1, "radius": 500}


def _http(url, body=None, timeout=60):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json, text/event-stream"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def fetch_stream_structures():
    """Elenco base di tutte le strutture (endpoint SSE usato dalla mappa del portale)."""
    text = _http(API_BASE + "/structures/nearby/stream", STREAM_BODY)
    structures, event = [], None
    for line in text.splitlines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            payload = json.loads(line[5:].strip())
            if event == "structure":
                structures.append(payload)
            elif event == "error":
                raise RuntimeError("Errore dal server della Regione: %s" % payload.get("message", payload))
    return structures


def fetch_structure_detail(struct_id):
    for attempt in range(3):
        try:
            return json.loads(_http("%s/structures/%s" % (API_BASE, struct_id), timeout=20))
        except Exception:
            time.sleep(1 + attempt)
    return None


def _txt(value):
    return "" if value is None else str(value)


def to_legacy(base, det):
    """Converte i dati del nuovo portale nel formato storico usato da JSON e pagine HTML."""
    det = det or {}
    car = base.get("caratteristiche") or {}
    pl = det.get("postiLetto") or {}
    cont = det.get("contatti") or {}
    base_cont = base.get("contatti") or {}
    quote = det.get("quote") or {}
    comune = (det.get("comune") or {}).get("comune")
    telefono = cont.get("telefono") or base_cont.get("telefono_rsa")
    email = cont.get("email") or base_cont.get("email")
    sito = cont.get("sitoInternet") or base_cont.get("sito_internet")
    fax = cont.get("fax") or base_cont.get("fax_rsa")
    return {
        "id": _txt(base.get("id")),
        "nome": base.get("nome") or det.get("nome") or "",
        "gestione": base.get("gestione") or det.get("gestione") or "",
        "indirizzo": base.get("indirizzo") or det.get("indirizzo") or "",
        "comune": comune or "N.D.",
        "zona": det.get("zona") or "",
        "telefono": _txt(telefono),
        "rsa_posti_liberi": _txt(car.get("posti_liberi", pl.get("postiLiberi", 0))),
        "posti_liberi_m": _txt(car.get("posti_liberi_m", pl.get("postiLiberiM", 0))),
        "posti_liberi_f": _txt(car.get("posti_liberi_f", pl.get("postiLiberiF", 0))),
        "rsa_quota": _txt(quote.get("quotaSociale")),
        "rsa_quotasanitaria": _txt(quote.get("quotaSanitaria")),
        "rsa_attiva": "1" if base.get("attiva") == "si" else "0",
        "rsa_data_aggiornamento": "",  # il nuovo portale non espone piu' questa data
        "lat": _txt(base.get("lat")),
        "lon": _txt(base.get("lon")),
        "decoded_details": {"struttura": {
            "email": email, "sito_internet": sito,
            "telefono_rsa": telefono, "fax_rsa": fax,
        }},
    }


def _has_free_beds(base):
    car = base.get("caratteristiche") or {}
    return any((car.get(k) or 0) > 0 for k in ("posti_liberi", "posti_liberi_m", "posti_liberi_f"))


def fetch_all_structures(log=print):
    """Restituisce (totale_strutture, {id: struttura}) con solo le strutture che hanno posti liberi."""
    log("Recupero elenco strutture dal portale della Regione...")
    base_list = fetch_stream_structures()
    if not base_list:
        raise RuntimeError("Il portale non ha restituito alcuna struttura (formato cambiato?).")
    with_beds = [b for b in base_list if _has_free_beds(b)]
    log("Trovate %d strutture, %d con posti liberi. Scarico i dettagli..." % (len(base_list), len(with_beds)))
    result = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_structure_detail, b["id"]): b for b in with_beds}
        for fut in as_completed(futures):
            base = futures[fut]
            result[_txt(base["id"])] = to_legacy(base, fut.result())
    return len(base_list), result

def upload_to_github(file_path, github_path, repo_owner, repo_name, token):
    try:
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{github_path}"
        with open(file_path, "rb") as f:
            file_content = f.read()
        encoded_content = base64.b64encode(file_content).decode("utf-8")
        
        sha = None
        req_get = urllib.request.Request(
            url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Python-Urllib"
            }
        )
        try:
            with urllib.request.urlopen(req_get, timeout=10) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                sha = resp_data.get("sha")
        except Exception:
            pass
            
        data = {
            "message": f"Update {github_path} - {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "content": encoded_content
        }
        if sha:
            data["sha"] = sha
            
        req_put = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
                "User-Agent": "Python-Urllib"
            },
            method="PUT"
        )
        with urllib.request.urlopen(req_put, timeout=15) as resp:
            if resp.status in [200, 201]:
                print(f"File {github_path} caricato con successo su GitHub!")
                return True
    except Exception as e:
        print(f"Errore durante l'upload di {github_path} su GitHub: {e}")
    return False

def main():
    start_time = time.time()
    try:
        totale, all_structures = fetch_all_structures(print)
    except Exception as e:
        print("ERRORE: impossibile recuperare i dati: %s" % e)
        raise SystemExit(1)  # fallisce in modo visibile, senza sovrascrivere i dati esistenti

    print("Scaricamento completato in %.2f secondi." % (time.time() - start_time))
    print("Trovate %d strutture totali in Toscana." % totale)

    structures_with_beds = []
    for s_id, s in all_structures.items():
        try:
            posti_liberi = int(s.get("rsa_posti_liberi", 0))
        except ValueError:
            posti_liberi = 0

        s["posti_liberi_int"] = posti_liberi
        
        try:
            s["posti_liberi_m_int"] = int(s.get("posti_liberi_m", 0))
        except ValueError:
            s["posti_liberi_m_int"] = 0

        try:
            s["posti_liberi_f_int"] = int(s.get("posti_liberi_f", 0))
        except ValueError:
            s["posti_liberi_f_int"] = 0

        if posti_liberi > 0 or s["posti_liberi_m_int"] > 0 or s["posti_liberi_f_int"] > 0:
            s["decoded_details"] = s.get("decoded_details")
            json_data_b64 = s.get("json_data")
            if json_data_b64 and json_data_b64 != "NULL":
                try:
                    decoded = base64.b64decode(json_data_b64).decode('utf-8')
                    s["decoded_details"] = json.loads(decoded)
                except Exception:
                    pass
            structures_with_beds.append(s)

    structures_with_beds.sort(key=lambda x: (x.get("comune", ""), x.get("nome", "")))

    print(f"Trovate {len(structures_with_beds)} strutture con POSTI LIBERI in Toscana.")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_json_path = os.path.join(script_dir, "rsa_posti_liberi.json")
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(structures_with_beds, f, ensure_ascii=False, indent=4)
    print(f"Salvati dati grezzi in {output_json_path}")

    generate_html_table(structures_with_beds, script_dir)
    
    # Crea una copia chiamata index.html per la compatibilità con GitHub Pages
    try:
        import shutil
        shutil.copy2(os.path.join(script_dir, "risultati_rsa.html"), os.path.join(script_dir, "index.html"))
    except Exception as e:
        print(f"Errore nella creazione di index.html: {e}")
    
    # Caricamento automatico su GitHub (solo se non siamo su GitHub Actions)
    if "GITHUB_ACTIONS" not in os.environ:
        token = ""
        token_path = os.path.join(script_dir, "github_token.txt")
        if os.path.exists(token_path):
            try:
                with open(token_path, "r", encoding="utf-8") as f:
                    token = f.read().strip()
            except Exception:
                pass
        
        if not token:
            token = os.environ.get("GITHUB_TOKEN", "")

        if token:
            print("\nAvvio caricamento dei dati su GitHub...")
            output_html_path = os.path.join(script_dir, "risultati_rsa.html")
            upload_to_github(output_json_path, "rsa_posti_liberi.json", "mencoxx", "rsa-toscana", token)
            upload_to_github(output_html_path, "index.html", "mencoxx", "rsa-toscana", token)
        else:
            print("\nNessun token GitHub trovato. Saltato caricamento automatico.")
    
    print("\nGenerazione completata con successo!")
    if "GITHUB_ACTIONS" not in os.environ:
        input("\nPremi Invio per chiudere questa finestra...")

def generate_html_table(structures, output_dir):
    html_content = """<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RSA Toscana - Elenco Strutture con Posti Liberi</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --success: #10b981;
            --success-bg: rgba(16, 185, 129, 0.1);
            --male-color: #3b82f6;
            --male-bg: rgba(59, 130, 246, 0.15);
            --female-color: #ec4899;
            --female-bg: rgba(236, 72, 153, 0.15);
            --border-radius: 16px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem 1rem;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        header {
            margin-bottom: 2.5rem;
            text-align: center;
        }

        h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #60a5fa, #3b82f6, #1d4ed8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        header p {
            color: var(--text-secondary);
            font-size: 1.1rem;
        }

        /* Controls Section */
        .controls-card {
            background-color: var(--bg-secondary);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .search-filter-grid {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr;
            gap: 1rem;
        }

        @media (max-width: 768px) {
            .search-filter-grid {
                grid-template-columns: 1fr;
            }
        }

        .distance-row {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr;
            gap: 1rem;
            margin-top: 1rem;
        }

        @media (max-width: 768px) {
            .distance-row {
                grid-template-columns: 1fr;
            }
        }

        .btn-geo {
            cursor: pointer;
            text-align: center;
        }

        .geo-status {
            grid-column: 1 / -1;
            font-size: 0.8rem;
            color: var(--text-muted);
            min-height: 1.1em;
        }

        .dist-value {
            font-weight: 600;
            white-space: nowrap;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .form-group label {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .input-control {
            background-color: var(--bg-tertiary);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            color: var(--text-primary);
            padding: 0.75rem 1rem;
            font-size: 1rem;
            transition: all 0.2s ease;
            outline: none;
            width: 100%;
        }

        .input-control:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3);
        }

        select.input-control {
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 1rem center;
            background-size: 1.25rem;
            padding-right: 2.5rem;
        }

        /* Stats Bar */
        .stats-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            color: var(--text-secondary);
            font-size: 0.95rem;
            background-color: rgba(30, 41, 59, 0.5);
            padding: 0.75rem 1.5rem;
            border-radius: 9999px;
            border: 1px solid rgba(255, 255, 255, 0.03);
        }

        .stats-bar span strong {
            color: var(--accent);
        }

        footer {
            margin-top: 2.5rem;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.85rem;
            padding: 1.5rem;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
        }

        footer a {
            color: var(--accent);
            text-decoration: none;
            font-weight: 500;
        }

        footer a:hover {
            text-decoration: underline;
        }

        .footer-download {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            background-color: var(--bg-secondary);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 0.5rem 1rem;
            margin-top: 0.75rem;
            color: var(--text-primary);
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            transition: background-color 0.2s ease;
        }

        .footer-download:hover {
            background-color: var(--bg-tertiary);
            text-decoration: none;
        }

        /* Table Container */
        .table-responsive {
            background-color: var(--bg-secondary);
            border-radius: var(--border-radius);
            overflow: hidden;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }

        th {
            background-color: rgba(15, 23, 42, 0.6);
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
            padding: 1.2rem 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            cursor: pointer;
            user-select: none;
            position: relative;
        }

        th.sort-asc::after {
            content: " ▲";
            font-size: 0.65rem;
            color: var(--accent);
        }

        th.sort-desc::after {
            content: " ▼";
            font-size: 0.65rem;
            color: var(--accent);
        }

        td {
            padding: 1.2rem 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            vertical-align: middle;
            font-size: 0.95rem;
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover td {
            background-color: rgba(255, 255, 255, 0.015);
        }

        /* Text styling */
        .struct-name {
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            color: var(--text-primary);
            font-size: 1.05rem;
        }

        .struct-address {
            font-size: 0.82rem;
            color: var(--text-secondary);
            margin-top: 0.15rem;
        }

        .badge-total-beds {
            background-color: var(--success);
            color: var(--bg-primary);
            font-weight: 700;
            padding: 0.35rem 0.75rem;
            border-radius: 6px;
            font-size: 0.85rem;
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
        }

        .gender-pills {
            display: flex;
            gap: 0.4rem;
            margin-top: 0.35rem;
        }

        .badge-gender {
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
        }

        .badge-gender.m {
            color: var(--male-color);
            background-color: var(--male-bg);
        }

        .badge-gender.f {
            color: var(--female-color);
            background-color: var(--female-bg);
        }

        .price-value {
            font-weight: 700;
            color: var(--accent);
            font-size: 1.05rem;
        }

        .price-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            display: block;
        }

        .tel-link {
            color: var(--text-primary);
            text-decoration: none;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            transition: color 0.15s;
        }

        .tel-link:hover {
            color: var(--accent);
        }

        .email-link {
            color: var(--accent);
            text-decoration: none;
            font-size: 0.82rem;
            display: block;
            margin-top: 0.15rem;
        }

        .email-link:hover {
            text-decoration: underline;
        }

        .update-date-val {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        .no-results {
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-secondary);
        }

        .no-results h3 {
            color: var(--text-primary);
            margin-bottom: 0.5rem;
        }

        @media (max-width: 768px) {
            .stats-bar {
                flex-direction: column;
                gap: 0.5rem;
                text-align: center;
                border-radius: var(--border-radius);
                padding: 1rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>RSA Toscana - Posti Liberi</h1>
            <p>Tutte le strutture con posti letto disponibili in tempo reale, senza selezione geografica manuale</p>
        </header>

        <div class="controls-card">
            <div class="search-filter-grid">
                <div class="form-group">
                    <label for="search">Cerca Struttura, Comune o Indirizzo</label>
                    <input type="text" id="search" class="input-control" placeholder="Scrivi es. 'Massa', 'Sanatrix', 'via Roma'...">
                </div>
                <div class="form-group">
                    <label for="filter-comune">Filtra per Comune</label>
                    <select id="filter-comune" class="input-control">
                        <option value="all">Tutti i Comuni</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="filter-gender">Genere Posto Letto</label>
                    <select id="filter-gender" class="input-control">
                        <option value="all">Tutti i Posti</option>
                        <option value="male">Solo Uomini</option>
                        <option value="female">Solo Donne</option>
                    </select>
                </div>
            </div>
            <div class="distance-row">
                <div class="form-group">
                    <label for="origin-city">Distanza da (città di partenza)</label>
                    <select id="origin-city" class="input-control">
                        <option value="">Nessuna</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>&nbsp;</label>
                    <button type="button" id="btn-geo" class="input-control btn-geo">📍 Usa la mia posizione</button>
                </div>
                <div class="form-group">
                    <label for="filter-distance">Entro</label>
                    <select id="filter-distance" class="input-control">
                        <option value="0">Qualsiasi distanza</option>
                        <option value="10">10 km</option>
                        <option value="20">20 km</option>
                        <option value="30">30 km</option>
                        <option value="50">50 km</option>
                        <option value="75">75 km</option>
                        <option value="100">100 km</option>
                    </select>
                </div>
                <div id="geo-status" class="geo-status"></div>
            </div>
        </div>

        <div class="stats-bar">
            <span>Trovate <strong id="count-structures">0</strong> strutture con disponibilità per un totale di <strong id="count-beds">0</strong> posti liberi</span>
            <span id="update-date" style="font-size: 0.8rem; color: var(--text-muted)"></span>
        </div>

        <div class="table-responsive">
            <table id="rsa-table">
                <thead>
                    <tr>
                        <th id="col-nome" onclick="sortBy('nome')">Nome Struttura</th>
                        <th id="col-comune" onclick="sortBy('comune')">Comune / Zona</th>
                        <th id="col-posti" onclick="sortBy('posti_liberi_int')">Posti Liberi</th>
                        <th id="col-quota" onclick="sortBy('rsa_quota_float')">Retta Sociale</th>
                        <th>Contatti</th>
                        <th id="col-dist_km" onclick="sortBy('dist_km')">Distanza</th>
                    </tr>
                </thead>
                <tbody id="rsa-tbody">
                    <!-- Rows will be dynamically rendered here -->
                </tbody>
            </table>
            <div id="no-results-view" class="no-results" style="display: none;">
                <h3>Nessuna struttura trovata</h3>
                <p>Modifica la ricerca o rimuovi i filtri per vedere più risultati.</p>
            </div>
        </div>
    </div>

    <footer>
        <div>Sviluppato da <strong>Leonardo Cozzolino</strong> &mdash;
            <a href="mailto:Leonardo.cozzolino@gmail.com">Leonardo.cozzolino@gmail.com</a>
        </div>
        <div style="margin-top: 0.4rem; color: var(--text-secondary)">
            Sorgente e app scaricabile su GitHub:
        </div>
        <a class="footer-download" href="https://github.com/mencoxx/rsa-toscana/releases/download/v1.0/RSA_App.exe" target="_blank" rel="noopener">
            ⬇️ Scarica RSA_App.exe (Windows)
        </a>
        &nbsp;
        <a class="footer-download" href="https://github.com/mencoxx/rsa-toscana" target="_blank" rel="noopener" style="background:transparent; border-color: rgba(255,255,255,0.15);">
            GitHub
        </a>
    </footer>

    <script>
        // Data injected from Python (embedded fallback)
        const localRsaData = ##RSA_DATA##;
        // Comuni toscani [nome, lat, lon] per il calcolo della distanza
        const COMUNI = ##COMUNI_DATA##;
        let rsaData = [];

        // Initialize DOM elements
        const filterComune = document.getElementById('filter-comune');
        const searchInput = document.getElementById('search');
        const filterGender = document.getElementById('filter-gender');
        const tbody = document.getElementById('rsa-tbody');
        const table = document.getElementById('rsa-table');
        const noResultsView = document.getElementById('no-results-view');
        const countStructures = document.getElementById('count-structures');
        const countBeds = document.getElementById('count-beds');

        const originCity = document.getElementById('origin-city');
        const filterDistance = document.getElementById('filter-distance');
        const btnGeo = document.getElementById('btn-geo');
        const geoStatus = document.getElementById('geo-status');
        let origin = null; // { lat, lon, label }

        function haversineKm(lat1, lon1, lat2, lon2) {
            const rad = Math.PI / 180;
            const dLat = (lat2 - lat1) * rad;
            const dLon = (lon2 - lon1) * rad;
            const a = Math.sin(dLat / 2) ** 2 +
                Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
            return 6371 * 2 * Math.asin(Math.sqrt(a));
        }

        function updateDistances() {
            rsaData.forEach(item => {
                const la = parseFloat(item.lat);
                const lo = parseFloat(item.lon);
                item.dist_km = (origin && isFinite(la) && isFinite(lo))
                    ? haversineKm(origin.lat, origin.lon, la, lo)
                    : Infinity;
            });
        }

        function setOrigin(o, message) {
            origin = o;
            updateDistances();
            geoStatus.textContent = o
                ? (message || `Distanze in linea d'aria da: ${o.label}`)
                : '';
            // Con una partenza scelta ordina dalla più vicina, altrimenti per comune
            currentSortColumn = null;
            sortBy(o ? 'dist_km' : 'comune');
        }

        originCity.addEventListener('change', () => {
            const idx = originCity.value === '' ? -1 : parseInt(originCity.value, 10);
            const c = idx >= 0 ? COMUNI[idx] : null;
            try { localStorage.setItem('rsa_origin_city', c ? c[0] : ''); } catch (e) {}
            setOrigin(c ? { lat: c[1], lon: c[2], label: c[0] } : null);
        });

        btnGeo.addEventListener('click', () => {
            if (!navigator.geolocation) {
                geoStatus.textContent = 'La geolocalizzazione non è supportata da questo browser: scegli una città.';
                return;
            }
            geoStatus.textContent = 'Rilevamento della posizione in corso...';
            navigator.geolocation.getCurrentPosition(
                pos => {
                    originCity.value = '';
                    try { localStorage.setItem('rsa_origin_city', ''); } catch (e) {}
                    setOrigin(
                        { lat: pos.coords.latitude, lon: pos.coords.longitude, label: 'la tua posizione' },
                        "Distanze in linea d'aria dalla tua posizione (non viene salvata né inviata)"
                    );
                },
                err => {
                    geoStatus.textContent = err.code === 1
                        ? 'Permesso negato: scegli una città dall’elenco.'
                        : 'Posizione non disponibile: scegli una città dall’elenco.';
                },
                { timeout: 10000, maximumAge: 300000 }
            );
        });

        // Sorting state
        let currentSortColumn = 'comune';
        let currentSortOrder = 'asc'; // 'asc' or 'desc'

        async function init() {
            // Try to load latest data from GitHub Pages
            const githubUrl = "https://mencoxx.github.io/rsa-toscana/rsa_posti_liberi.json";
            try {
                const response = await fetch(githubUrl, { cache: "no-store" });
                if (response.ok) {
                    rsaData = await response.json();
                    console.log("Dati aggiornati caricati da GitHub!");
                } else {
                    throw new Error("Server error");
                }
            } catch (e) {
                console.log("Errore caricamento online, uso i dati locali:", e);
                rsaData = localRsaData;
            }

            // Parse rates for sorting
            rsaData.forEach(item => {
                item.rsa_quota_float = parseFloat(item.rsa_quota || 0);
            });

            // Extract unique comuni
            const comuni = [...new Set(rsaData.map(item => item.comune))].sort();
            filterComune.innerHTML = '<option value="all">Tutti i Comuni</option>';
            comuni.forEach(comune => {
                const option = document.createElement('option');
                option.value = comune;
                option.textContent = comune;
                filterComune.appendChild(option);
            });

            // Show last update based on most recent date in dataset
            const dates = rsaData.map(item => item.rsa_data_aggiornamento).filter(Boolean);
            if (dates.length > 0) {
                dates.sort();
                const latest = dates[dates.length - 1];
                document.getElementById('update-date').textContent = `Ultimo aggiornamento rilevato nei dati: ${latest}`;
            }

            // Distanza: popola la lista città e ripristina l'ultima scelta
            COMUNI.forEach((c, i) => {
                const option = document.createElement('option');
                option.value = String(i);
                option.textContent = c[0];
                originCity.appendChild(option);
            });
            updateDistances();
            let savedCity = '';
            try { savedCity = localStorage.getItem('rsa_origin_city') || ''; } catch (e) {}
            const savedIdx = COMUNI.findIndex(c => c[0] === savedCity);

            // Initial Sort & Render
            if (savedIdx >= 0) {
                originCity.value = String(savedIdx);
                setOrigin({ lat: COMUNI[savedIdx][1], lon: COMUNI[savedIdx][2], label: COMUNI[savedIdx][0] });
            } else {
                sortBy('comune');
            }
        }

        function sortBy(column) {
            if (currentSortColumn === column) {
                currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortColumn = column;
                currentSortOrder = 'asc';
            }
            
            // Update table headers class
            const headers = table.querySelectorAll('th');
            headers.forEach(th => {
                th.classList.remove('sort-asc', 'sort-desc');
            });
            const activeHeader = document.getElementById(`col-${column === 'rsa_quota_float' ? 'quota' : column === 'posti_liberi_int' ? 'posti' : column}`);
            if (activeHeader) {
                activeHeader.classList.add(currentSortOrder === 'asc' ? 'sort-asc' : 'sort-desc');
            }

            renderTable();
        }

        // Render table rows
        function renderTable() {
            const searchTerm = searchInput.value.toLowerCase().trim();
            const selectedComune = filterComune.value;
            const selectedGender = filterGender.value;

            // 1. Filter
            let filtered = rsaData.filter(item => {
                const matchSearch = !searchTerm || 
                    item.nome.toLowerCase().includes(searchTerm) || 
                    item.comune.toLowerCase().includes(searchTerm) || 
                    item.indirizzo.toLowerCase().includes(searchTerm) ||
                    (item.zona && item.zona.toLowerCase().includes(searchTerm));

                const matchComune = selectedComune === 'all' || item.comune === selectedComune;

                let matchGender = true;
                if (selectedGender === 'male') {
                    matchGender = item.posti_liberi_m_int > 0;
                } else if (selectedGender === 'female') {
                    matchGender = item.posti_liberi_f_int > 0;
                }

                const maxKm = parseFloat(filterDistance.value) || 0;
                const matchDistance = !origin || !maxKm || item.dist_km <= maxKm;

                return matchSearch && matchComune && matchGender && matchDistance;
            });

            // 2. Sort
            filtered.sort((a, b) => {
                let valA = a[currentSortColumn];
                let valB = b[currentSortColumn];

                // Handles strings vs numbers
                if (typeof valA === 'string') {
                    valA = valA.toLowerCase();
                    valB = valB.toLowerCase();
                }

                if (valA < valB) return currentSortOrder === 'asc' ? -1 : 1;
                if (valA > valB) return currentSortOrder === 'asc' ? 1 : -1;
                return 0;
            });

            // 3. Update stats
            countStructures.textContent = filtered.length;
            const totalBeds = filtered.reduce((sum, item) => sum + item.posti_liberi_int, 0);
            countBeds.textContent = totalBeds;

            // 4. Populate table rows
            tbody.innerHTML = '';
            
            if (filtered.length === 0) {
                table.style.display = 'none';
                noResultsView.style.display = 'block';
                return;
            }

            table.style.display = 'table';
            noResultsView.style.display = 'none';

            filtered.forEach(item => {
                const row = document.createElement('tr');

                // Extract structure details (email, site)
                let email = '';
                if (item.decoded_details && item.decoded_details.struttura) {
                    email = item.decoded_details.struttura.email || '';
                }

                // Gender pills
                let genderHtml = '';
                if (item.posti_liberi_m_int > 0) {
                    genderHtml += `<span class="badge-gender m">👨 M: ${item.posti_liberi_m_int}</span>`;
                }
                if (item.posti_liberi_f_int > 0) {
                    genderHtml += `<span class="badge-gender f">👩 F: ${item.posti_liberi_f_int}</span>`;
                }

                // Format price
                const formattedPrice = item.rsa_quota_float > 0 
                    ? `${item.rsa_quota_float.toFixed(2)} €` 
                    : 'N.D.';

                row.innerHTML = `
                    <td>
                        <div class="struct-name">${item.nome}</div>
                        <div class="struct-address">${item.indirizzo}</div>
                    </td>
                    <td>
                        <div style="font-weight: 500">${item.comune}</div>
                        <div style="font-size: 0.78rem; color: var(--text-secondary)">${item.zona}</div>
                    </td>
                    <td>
                        <div class="badge-total-beds">
                            🛏️ ${item.posti_liberi_int}
                        </div>
                        <div class="gender-pills">
                            ${genderHtml}
                        </div>
                    </td>
                    <td>
                        <span class="price-value">${formattedPrice}</span>
                        <span class="price-label">giorno IVA incl.</span>
                    </td>
                    <td>
                        ${item.telefono ? `<a href="tel:${item.telefono.split(' ')[0]}" class="tel-link">📞 ${item.telefono}</a>` : '<span style="color: var(--text-muted)">N.D.</span>'}
                        ${email ? `<a href="mailto:${email}" class="email-link">${email}</a>` : ''}
                    </td>
                    <td>
                        ${isFinite(item.dist_km)
                            ? `<span class="dist-value">${item.dist_km.toFixed(1)} km</span>`
                            : '<span style="color: var(--text-muted)">&mdash;</span>'}
                    </td>
                `;
                tbody.appendChild(row);
            });
        }

        // Attach listeners
        searchInput.addEventListener('input', renderTable);
        filterComune.addEventListener('change', renderTable);
        filterGender.addEventListener('change', renderTable);
        filterDistance.addEventListener('change', () => {
            if (!origin && parseFloat(filterDistance.value)) {
                geoStatus.textContent = 'Per filtrare per distanza scegli una città o usa la tua posizione.';
            }
            renderTable();
        });

        // Run Init on Page Load
        init();
    </script>
</body>
</html>
"""
    html_content = html_content.replace("##RSA_DATA##", json.dumps(structures, ensure_ascii=False))
    try:
        with open(os.path.join(output_dir, "comuni_toscana.json"), encoding="utf-8") as f:
            comuni = json.load(f)
    except Exception as e:
        print(f"Attenzione: comuni_toscana.json non leggibile ({e}): niente menu città.")
        comuni = []
    html_content = html_content.replace("##COMUNI_DATA##", json.dumps(comuni, ensure_ascii=False))

    output_html_path = os.path.join(output_dir, "risultati_rsa.html")
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Salvata tabella interattiva in {output_html_path}")

if __name__ == "__main__":
    main()
