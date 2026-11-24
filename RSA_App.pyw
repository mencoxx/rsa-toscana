import urllib.request
import json
import base64
import time
import os
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed

API_BASE = "https://risorse.regione.toscana.it/api/rsa"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
# Centro Toscana + raggio massimo accettato dal portale (500 km): copre tutta la regione.
STREAM_BODY = {"lat": 43.45, "lon": 11.1, "radius": 500}

# Comuni toscani [nome, lat, lon] per il calcolo della distanza nella pagina HTML
COMUNI_TOSCANA = [
    ["Abbadia San Salvatore", 42.881, 11.6775],
    ["Abetone Cutigliano", 44.1004, 10.7564],
    ["Agliana", 43.9028, 11.0065],
    ["Altopascio", 43.815, 10.6747],
    ["Anghiari", 43.5405, 12.0568],
    ["Arcidosso", 42.8715, 11.5388],
    ["Arezzo", 43.4664, 11.8823],
    ["Asciano", 43.2349, 11.5594],
    ["Aulla", 44.2093, 9.9682],
    ["Badia Tedalda", 43.7064, 12.1856],
    ["Bagni di Lucca", 44.0105, 10.5912],
    ["Bagno a Ripoli", 43.7514, 11.3194],
    ["Bagnone", 44.3154, 9.9944],
    ["Barberino di Mugello", 44.0004, 11.2386],
    ["Barberino Tavarnelle", 43.5575, 11.1731],
    ["Barga", 44.073, 10.4848],
    ["Bibbiena", 43.6945, 11.8181],
    ["Bibbona", 43.2694, 10.5982],
    ["Bientina", 43.7101, 10.6198],
    ["Borgo a Mozzano", 43.9785, 10.5436],
    ["Borgo San Lorenzo", 43.9548, 11.3877],
    ["Bucine", 43.4791, 11.6169],
    ["Buggiano", 43.8799, 10.7275],
    ["Buonconvento", 43.1379, 11.4819],
    ["Buti", 43.7273, 10.5874],
    ["Calci", 43.7256, 10.5157],
    ["Calcinaia", 43.683, 10.6157],
    ["Calenzano", 43.8651, 11.1672],
    ["Camaiore", 43.9386, 10.3042],
    ["Campagnatico", 42.8828, 11.2749],
    ["Campi Bisenzio", 43.8206, 11.1378],
    ["Campiglia Marittima", 43.059, 10.6169],
    ["Campo nell'Elba", 42.7448, 10.2336],
    ["Camporgiano", 44.1586, 10.3338],
    ["Cantagallo", 44.0283, 11.1078],
    ["Capalbio", 42.4533, 11.422],
    ["Capannoli", 43.5839, 10.6786],
    ["Capannori", 43.8489, 10.5748],
    ["Capoliveri", 42.7431, 10.3803],
    ["Capolona", 43.5634, 11.8598],
    ["Capraia e Limite", 43.7425, 10.9764],
    ["Capraia Isola", 43.0499, 9.8423],
    ["Caprese Michelangelo", 43.644, 11.9858],
    ["Careggine", 44.1208, 10.3244],
    ["Carmignano", 43.8138, 11.0183],
    ["Carrara", 44.0773, 10.0968],
    ["Casale Marittimo", 43.2973, 10.6155],
    ["Casciana Terme Lari", 43.5663, 10.5935],
    ["Cascina", 43.6765, 10.5493],
    ["Casola in Lunigiana", 44.2012, 10.1757],
    ["Casole d'Elsa", 43.3405, 11.0431],
    ["Castagneto Carducci", 43.1607, 10.61],
    ["Castel del Piano", 42.8931, 11.5377],
    ["Castel Focognano", 43.6516, 11.8356],
    ["Castel San Niccolò", 43.741, 11.7046],
    ["Castelfiorentino", 43.6057, 10.9713],
    ["Castelfranco di Sotto", 43.6997, 10.7452],
    ["Castelfranco Piandiscò", 43.622, 11.5583],
    ["Castell'Azzara", 42.7735, 11.6978],
    ["Castellina in Chianti", 43.47, 11.2857],
    ["Castellina Marittima", 43.412, 10.5755],
    ["Castelnuovo Berardenga", 43.3455, 11.5031],
    ["Castelnuovo di Garfagnana", 44.1103, 10.4117],
    ["Castelnuovo di Val di Cecina", 43.2069, 10.906],
    ["Castiglion Fibocchi", 43.5276, 11.7632],
    ["Castiglion Fiorentino", 43.3416, 11.9239],
    ["Castiglione d'Orcia", 43.0044, 11.6164],
    ["Castiglione della Pescaia", 42.762, 10.8788],
    ["Castiglione di Garfagnana", 44.1491, 10.4113],
    ["Cavriglia", 43.5237, 11.4891],
    ["Cecina", 43.3122, 10.5194],
    ["Cerreto Guidi", 43.7597, 10.8776],
    ["Certaldo", 43.5478, 11.0408],
    ["Cetona", 42.9629, 11.9006],
    ["Chianciano Terme", 43.0588, 11.8318],
    ["Chianni", 43.4858, 10.6426],
    ["Chiesina Uzzanese", 43.8392, 10.7195],
    ["Chitignano", 43.6614, 11.8803],
    ["Chiusdino", 43.1551, 11.0881],
    ["Chiusi", 43.0167, 11.9476],
    ["Chiusi della Verna", 43.6997, 11.935],
    ["Cinigiano", 42.8911, 11.3942],
    ["Civitella in Val di Chiana", 43.4032, 11.7709],
    ["Civitella Paganico", 42.994, 11.2816],
    ["Colle di Val d'Elsa", 43.4212, 11.1178],
    ["Collesalvetti", 43.5892, 10.4761],
    ["Comano", 44.2972, 10.1349],
    ["Coreglia Antelminelli", 44.0645, 10.5253],
    ["Cortona", 43.2751, 11.9851],
    ["Crespina Lorenzana", 43.572, 10.561],
    ["Dicomano", 43.8915, 11.5236],
    ["Empoli", 43.7191, 10.9472],
    ["Fabbriche di Vergemoli", 43.9973, 10.4275],
    ["Fauglia", 43.567, 10.516],
    ["Fiesole", 43.8069, 11.2932],
    ["Figline e Incisa Valdarno", 43.6291, 11.4449],
    ["Filattiera", 44.3313, 9.9369],
    ["Firenze", 43.7692, 11.2559],
    ["Firenzuola", 44.1176, 11.3788],
    ["Fivizzano", 44.2371, 10.1228],
    ["Foiano della Chiana", 43.2525, 11.8185],
    ["Follonica", 42.9226, 10.7599],
    ["Forte dei Marmi", 43.9602, 10.1667],
    ["Fosciandora", 44.1152, 10.4554],
    ["Fosdinovo", 44.1344, 10.0191],
    ["Fucecchio", 43.7286, 10.8101],
    ["Gaiole in Chianti", 43.4688, 11.4335],
    ["Gallicano", 44.0605, 10.4357],
    ["Gambassi Terme", 43.5386, 10.9532],
    ["Gavorrano", 42.9252, 10.9057],
    ["Greve in Chianti", 43.5832, 11.3172],
    ["Grosseto", 42.7603, 11.1136],
    ["Guardistallo", 43.3133, 10.633],
    ["Impruneta", 43.6857, 11.2544],
    ["Isola del Giglio", 42.3657, 10.9009],
    ["Lajatico", 43.4751, 10.7285],
    ["Lamporecchio", 43.817, 10.8968],
    ["Larciano", 43.8247, 10.8772],
    ["Lastra a Signa", 43.7701, 11.1061],
    ["Laterina", 43.5077, 11.7093],
    ["Licciana Nardi", 44.265, 10.0385],
    ["Livorno", 43.5523, 10.3087],
    ["Londa", 43.8601, 11.5672],
    ["Loro Ciuffenna", 43.5933, 11.6315],
    ["Lucca", 43.8443, 10.5015],
    ["Lucignano", 43.2755, 11.7471],
    ["Magliano in Toscana", 42.5986, 11.2935],
    ["Manciano", 42.5873, 11.5155],
    ["Marciana", 42.79, 10.168],
    ["Marciana Marina", 42.8047, 10.1968],
    ["Marciano della Chiana", 43.3051, 11.7864],
    ["Marliana", 43.9341, 10.7701],
    ["Marradi", 44.0755, 11.6128],
    ["Massa", 44.0367, 10.1417],
    ["Massa e Cozzile", 43.9099, 10.7447],
    ["Massa Marittima", 43.0502, 10.8879],
    ["Massarosa", 43.8685, 10.3418],
    ["Minucciano", 44.1703, 10.2076],
    ["Molazzana", 44.0726, 10.4184],
    ["Monsummano Terme", 43.8716, 10.8144],
    ["Montaione", 43.5523, 10.9123],
    ["Montalcino", 43.0592, 11.4906],
    ["Montale", 43.9347, 11.0223],
    ["Monte Argentario", 42.4392, 11.1158],
    ["Monte San Savino", 43.3314, 11.7253],
    ["Montecarlo", 43.8504, 10.6686],
    ["Montecatini Val di Cecina", 43.392, 10.7482],
    ["Montecatini-Terme", 43.8841, 10.7728],
    ["Montelupo Fiorentino", 43.7295, 11.0208],
    ["Montemignaio", 43.7401, 11.6199],
    ["Montemurlo", 43.9269, 11.0371],
    ["Montepulciano", 43.0926, 11.7807],
    ["Monterchi", 43.4856, 12.1119],
    ["Monteriggioni", 43.3931, 11.2186],
    ["Monteroni d'Arbia", 43.2311, 11.4219],
    ["Monterotondo Marittimo", 43.1455, 10.8558],
    ["Montescudaio", 43.3264, 10.6278],
    ["Montespertoli", 43.6431, 11.0753],
    ["Montevarchi", 43.5236, 11.5675],
    ["Monteverdi Marittimo", 43.177, 10.7152],
    ["Monticiano", 43.1394, 11.1797],
    ["Montieri", 43.1305, 11.0162],
    ["Montignoso", 44.0181, 10.1765],
    ["Montopoli in Val d'Arno", 43.6686, 10.7604],
    ["Mulazzo", 44.3217, 9.9071],
    ["Murlo", 43.1685, 11.3911],
    ["Orbetello", 42.4374, 11.2094],
    ["Orciano Pisano", 43.4913, 10.5101],
    ["Ortignano Raggiolo", 43.6815, 11.7525],
    ["Palaia", 43.6048, 10.7731],
    ["Palazzuolo sul Senio", 44.1123, 11.5473],
    ["Peccioli", 43.548, 10.721],
    ["Pelago", 43.7702, 11.5064],
    ["Pergine Valdarno", 43.4706, 11.6859],
    ["Pescaglia", 43.9664, 10.4113],
    ["Pescia", 43.9032, 10.6886],
    ["Piancastagnaio", 42.8494, 11.6918],
    ["Piazza al Serchio", 44.1826, 10.3],
    ["Pienza", 43.0763, 11.68],
    ["Pietrasanta", 43.9596, 10.2277],
    ["Pieve a Nievole", 43.879, 10.7947],
    ["Pieve Fosciana", 44.1306, 10.4107],
    ["Pieve Santo Stefano", 43.6685, 12.0417],
    ["Piombino", 42.922, 10.5274],
    ["Pisa", 43.7155, 10.4013],
    ["Pistoia", 43.9335, 10.9173],
    ["Pitigliano", 42.6349, 11.6694],
    ["Podenzana", 44.2064, 9.9412],
    ["Poggibonsi", 43.4669, 11.1466],
    ["Poggio a Caiano", 43.8163, 11.0559],
    ["Pomarance", 43.3001, 10.8738],
    ["Ponsacco", 43.6202, 10.6336],
    ["Pontassieve", 43.7758, 11.4399],
    ["Ponte Buggianese", 43.8428, 10.7474],
    ["Pontedera", 43.6639, 10.636],
    ["Pontremoli", 44.3774, 9.8829],
    ["Poppi", 43.7245, 11.7653],
    ["Porcari", 43.8397, 10.6167],
    ["Porto Azzurro", 42.7646, 10.3987],
    ["Portoferraio", 42.8153, 10.3312],
    ["Prato", 43.8806, 11.097],
    ["Pratovecchio Stia", 43.7982, 11.7084],
    ["Quarrata", 43.8476, 10.9786],
    ["Radda in Chianti", 43.4865, 11.3744],
    ["Radicofani", 42.897, 11.7664],
    ["Radicondoli", 43.2611, 11.0413],
    ["Rapolano Terme", 43.2865, 11.6042],
    ["Reggello", 43.6825, 11.5364],
    ["Rignano sull'Arno", 43.7221, 11.4535],
    ["Rio Marina", 42.8146, 10.4252],
    ["Rio nell'Elba", 42.813, 10.3993],
    ["Riparbella", 43.3647, 10.5997],
    ["Roccalbegna", 42.7841, 11.5093],
    ["Roccastrada", 43.0112, 11.1674],
    ["Rosignano Marittimo", 43.4053, 10.4727],
    ["Rufina", 43.8266, 11.4879],
    ["Sambuca Pistoiese", 44.104, 10.999],
    ["San Casciano dei Bagni", 42.8713, 11.8754],
    ["San Casciano in Val di Pesa", 43.6566, 11.1844],
    ["San Gimignano", 43.4678, 11.0432],
    ["San Giovanni Valdarno", 43.5667, 11.5296],
    ["San Giuliano Terme", 43.7633, 10.4425],
    ["San Godenzo", 43.9263, 11.6196],
    ["San Marcello Piteglio", 44.0574, 10.7929],
    ["San Miniato", 43.6794, 10.8524],
    ["San Quirico d'Orcia", 43.0603, 11.6033],
    ["San Romano in Garfagnana", 44.169, 10.3454],
    ["San Vincenzo", 43.1008, 10.5382],
    ["Sansepolcro", 43.5701, 12.1413],
    ["Santa Croce sull'Arno", 43.7114, 10.7784],
    ["Santa Fiora", 42.8314, 11.5857],
    ["Santa Luce", 43.4725, 10.5648],
    ["Santa Maria a Monte", 43.6987, 10.6924],
    ["Sarteano", 42.9896, 11.8692],
    ["Sassetta", 43.1284, 10.644],
    ["Scandicci", 43.7582, 11.1813],
    ["Scansano", 42.6879, 11.3332],
    ["Scarlino", 42.9073, 10.8519],
    ["Scarperia e San Piero", 43.996, 11.356],
    ["Seggiano", 42.928, 11.5573],
    ["Semproniano", 42.7302, 11.5417],
    ["Seravezza", 43.9952, 10.2284],
    ["Serravalle Pistoiese", 43.9056, 10.832],
    ["Sestino", 43.7084, 12.297],
    ["Sesto Fiorentino", 43.8322, 11.1984],
    ["Siena", 43.3182, 11.3319],
    ["Signa", 43.7824, 11.0976],
    ["Sillano Giuncugnano", 44.225, 10.3024],
    ["Sinalunga", 43.2124, 11.7361],
    ["Sorano", 42.6817, 11.7138],
    ["Sovicille", 43.2802, 11.2283],
    ["Stazzema", 43.9971, 10.2956],
    ["Subbiano", 43.5756, 11.8703],
    ["Suvereto", 43.0793, 10.6791],
    ["Talla", 43.602, 11.7871],
    ["Terranuova Bracciolini", 43.5509, 11.5858],
    ["Terricciola", 43.5246, 10.676],
    ["Torrita di Siena", 43.1666, 11.7719],
    ["Trequanda", 43.1887, 11.6678],
    ["Tresana", 44.2382, 9.9516],
    ["Uzzano", 43.8817, 10.7091],
    ["Vagli Sotto", 44.1144, 10.2804],
    ["Vaglia", 43.9066, 11.2814],
    ["Vaiano", 43.9686, 11.1233],
    ["Vecchiano", 43.7816, 10.3866],
    ["Vernio", 44.0533, 11.1558],
    ["Viareggio", 43.8669, 10.2498],
    ["Vicchio", 43.9338, 11.4654],
    ["Vicopisano", 43.6998, 10.5844],
    ["Villa Basilica", 43.9278, 10.6451],
    ["Villa Collemandina", 44.1596, 10.3976],
    ["Villafranca in Lunigiana", 44.292, 9.951],
    ["Vinci", 43.7871, 10.9265],
    ["Volterra", 43.4017, 10.8594],
    ["Zeri", 44.3529, 9.7635],
]



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

class RSAApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RSA Toscana - Posti Liberi")
        self.root.geometry("550x420")
        self.root.resizable(False, False)
        
        # Color Palette (Dark Theme matching the HTML)
        self.bg_primary = "#0f172a"
        self.bg_secondary = "#1e293b"
        self.accent = "#3b82f6"
        self.accent_hover = "#2563eb"
        self.success = "#10b981"
        self.text_primary = "#f8fafc"
        self.text_secondary = "#94a3b8"
        self.text_muted = "#64748b"
        
        self.root.configure(bg=self.bg_primary)
        
        # Style configurations
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("TProgressbar", thickness=15, troughcolor=self.bg_secondary, background=self.accent)
        
        # Script directory path
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.json_path = os.path.join(self.script_dir, "rsa_posti_liberi.json")
        self.html_path = os.path.join(self.script_dir, "risultati_rsa.html")
        
        self.is_updating = False
        
        self.create_widgets()
        self.load_current_status()
        
    def create_widgets(self):
        # Header Frame
        header_frame = tk.Frame(self.root, bg=self.bg_primary, pady=20)
        header_frame.pack(fill="x")
        
        title_label = tk.Label(
            header_frame, 
            text="RSA Toscana", 
            font=("Segoe UI", 24, "bold"), 
            fg=self.accent, 
            bg=self.bg_primary
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            header_frame,
            text="Monitoraggio Posti Liberi in Tempo Reale",
            font=("Segoe UI", 11),
            fg=self.text_secondary,
            bg=self.bg_primary
        )
        subtitle_label.pack()

        author_label = tk.Label(
            header_frame,
            text="by Leonardo Cozzolino  •  Leonardo.cozzolino@gmail.com",
            font=("Segoe UI", 8),
            fg=self.text_muted,
            bg=self.bg_primary,
            cursor="hand2"
        )
        author_label.pack(pady=(2, 0))
        author_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/mencoxx/rsa-toscana"))

        # Status Card Frame
        self.status_card = tk.Frame(
            self.root, 
            bg=self.bg_secondary, 
            padx=20, 
            pady=20, 
            highlightbackground="#334155", 
            highlightthickness=1
        )
        self.status_card.pack(fill="x", padx=30, pady=10)
        
        # Status Labels
        self.lbl_status = tk.Label(
            self.status_card, 
            text="Stato: Caricamento...", 
            font=("Segoe UI", 12, "bold"), 
            fg=self.text_primary, 
            bg=self.bg_secondary,
            anchor="w"
        )
        self.lbl_status.pack(fill="x", pady=2)
        
        self.lbl_count = tk.Label(
            self.status_card, 
            text="Strutture con posti: --", 
            font=("Segoe UI", 10), 
            fg=self.text_secondary, 
            bg=self.bg_secondary,
            anchor="w"
        )
        self.lbl_count.pack(fill="x", pady=2)
        
        self.lbl_beds = tk.Label(
            self.status_card, 
            text="Posti liberi totali: --", 
            font=("Segoe UI", 10), 
            fg=self.text_secondary, 
            bg=self.bg_secondary,
            anchor="w"
        )
        self.lbl_beds.pack(fill="x", pady=2)
        
        self.lbl_date = tk.Label(
            self.status_card, 
            text="Ultimo aggiornamento: --", 
            font=("Segoe UI", 9, "italic"), 
            fg=self.text_muted, 
            bg=self.bg_secondary,
            anchor="w"
        )
        self.lbl_date.pack(fill="x", pady=5)
        
        # Progress Frame (hidden initially)
        self.progress_frame = tk.Frame(self.root, bg=self.bg_primary, padx=30)
        
        self.lbl_progress = tk.Label(
            self.progress_frame, 
            text="Download in corso...", 
            font=("Segoe UI", 9), 
            fg=self.text_secondary, 
            bg=self.bg_primary,
            anchor="w"
        )
        self.lbl_progress.pack(fill="x", pady=2)
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, 
            orient="horizontal", 
            mode="determinate", 
            style="TProgressbar"
        )
        self.progress_bar.pack(fill="x", pady=5)
        
        # Action Buttons Frame
        btn_frame = tk.Frame(self.root, bg=self.bg_primary, pady=20)
        btn_frame.pack(fill="x", padx=30, side="bottom")
        
        # Button Styles
        # Note: We simulate a premium hover effect
        self.btn_update = tk.Button(
            btn_frame, 
            text="🔄 Aggiorna Dati", 
            font=("Segoe UI", 11, "bold"),
            fg=self.bg_primary, 
            bg=self.success, 
            activebackground="#059669",
            activeforeground=self.bg_primary,
            bd=0, 
            padx=15, 
            pady=8,
            cursor="hand2",
            command=self.start_update_thread
        )
        self.btn_update.pack(side="left", expand=True, fill="x", padx=5)
        
        self.btn_view = tk.Button(
            btn_frame, 
            text="👁️ Apri Tabella", 
            font=("Segoe UI", 11, "bold"),
            fg="white", 
            bg=self.accent, 
            activebackground=self.accent_hover,
            activeforeground="white",
            bd=0, 
            padx=15, 
            pady=8,
            cursor="hand2",
            command=self.open_visualization
        )
        self.btn_view.pack(side="right", expand=True, fill="x", padx=5)
        
        # Hover effect bindings
        self.btn_update.bind("<Enter>", lambda e: self.btn_update.config(bg="#34d399"))
        self.btn_update.bind("<Leave>", lambda e: self.btn_update.config(bg=self.success))
        self.btn_view.bind("<Enter>", lambda e: self.btn_view.config(bg="#60a5fa"))
        self.btn_view.bind("<Leave>", lambda e: self.btn_view.config(bg=self.accent))
        
    def load_current_status(self):
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                struct_count = len(data)
                beds_count = sum(item.get("posti_liberi_int", 0) for item in data)
                
                dates = [item.get("rsa_data_aggiornamento") for item in data if item.get("rsa_data_aggiornamento")]
                latest_date = "N.D."
                if dates:
                    dates.sort()
                    latest_date = dates[-1]
                
                self.lbl_status.config(text="Stato: Dati Pronti", fg=self.success)
                self.lbl_count.config(text=f"Strutture con posti liberi: {struct_count}")
                self.lbl_beds.config(text=f"Posti liberi totali in Toscana: {beds_count}")
                self.lbl_date.config(text=f"Ultimo aggiornamento nei dati: {latest_date}")
                self.btn_view.config(state="normal")
            except Exception as e:
                self.lbl_status.config(text="Stato: Errore lettura file", fg="red")
                self.btn_view.config(state="disabled")
        else:
            self.lbl_status.config(text="Stato: Nessun dato scaricato", fg="#f59e0b")
            self.lbl_count.config(text="Avvia un aggiornamento per iniziare.")
            self.lbl_beds.config(text="")
            self.lbl_date.config(text="")
            self.btn_view.config(state="disabled")

    def open_visualization(self):
        if os.path.exists(self.html_path):
            webbrowser.open(f"file:///{self.html_path}")
        else:
            messagebox.showwarning("Errore", "La pagina web dei risultati non esiste ancora. Esegui prima un aggiornamento.")

    def start_update_thread(self):
        if self.is_updating:
            return
        
        self.is_updating = True
        self.btn_update.config(state="disabled")
        self.btn_view.config(state="disabled")
        
        self.progress_frame.pack(fill="x", padx=30, pady=10)
        self.progress_bar["value"] = 0
        
        # Start background scraping thread
        threading.Thread(target=self.run_update, daemon=True).start()

    def run_update(self):
        try:
            def log(msg):
                self.lbl_progress.config(text=msg)
                self.root.update_idletasks()

            _totale, all_structures = fetch_all_structures(log)
            self.progress_bar["value"] = 100

            # Process data
            self.lbl_progress.config(text="Filtrazione e salvataggio dei dati...")
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

            # Save files
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(structures_with_beds, f, ensure_ascii=False, indent=4)

            self.generate_html_table(structures_with_beds)
            
            # Caricamento automatico su GitHub
            try:
                self.lbl_progress.config(text="Caricamento dei dati su GitHub...")
                token = ""
                token_path = os.path.join(self.script_dir, "github_token.txt")
                if os.path.exists(token_path):
                    try:
                        with open(token_path, "r", encoding="utf-8") as f:
                            token = f.read().strip()
                    except Exception:
                        pass
                if not token:
                    token = os.environ.get("GITHUB_TOKEN", "")
                
                if token:
                    self.upload_to_github(self.json_path, "rsa_posti_liberi.json", "mencoxx", "rsa-toscana", token)
                    self.upload_to_github(self.html_path, "index.html", "mencoxx", "rsa-toscana", token)
                else:
                    print("Nessun token trovato. Upload saltato.")
            except Exception as e:
                print(f"Errore durante l'upload automatico su GitHub: {e}")
            
            # Update GUI on success
            self.root.after(0, self.update_complete, True)
            
        except Exception as e:
            self.root.after(0, self.update_complete, False, str(e))

    def update_complete(self, success, err_msg=""):
        self.is_updating = False
        self.btn_update.config(state="normal")
        self.btn_view.config(state="normal")
        self.progress_frame.pack_forget()
        
        if success:
            self.load_current_status()
            messagebox.showinfo("Successo", "Dati RSA aggiornati e caricati online con successo!")
        else:
            self.lbl_status.config(text="Stato: Errore aggiornamento", fg="red")
            messagebox.showerror("Errore", f"Si è verificato un errore durante l'aggiornamento:\n{err_msg}")

    def upload_to_github(self, file_path, github_path, repo_owner, repo_name, token):
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

    def generate_html_table(self, structures):
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
        html_content = html_content.replace("##COMUNI_DATA##", json.dumps(COMUNI_TOSCANA, ensure_ascii=False))
        with open(self.html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

if __name__ == "__main__":
    root = tk.Tk()
    app = RSAApp(root)
    root.mainloop()
