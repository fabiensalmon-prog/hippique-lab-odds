"""Hippique Lab — enregistrement des cotes et des masses PMU dans les 20 dernières minutes avant chaque départ (courses françaises).

Tourne dans GitHub Actions (dépôt public : minutes gratuites). Une boucle par minute :
  - départ dans 6 à 20 min  : un relevé toutes les 3 min
  - départ dans 0 à 6 min   : un relevé par minute
  - jusqu'à 3 min après l'heure prévue (les départs glissent) : un relevé par minute, tant que la course n'est pas arrivée
Relevé = masses par combinaison de tous les jeux (combinaisons), rapports directs gagnant / placé / couplé gagnant / 2sur4.
Sortie : data/AAAA-MM-JJ/R<r>C<c>.jsonl (une ligne JSON par relevé) + data/AAAA-MM-JJ/programme.json
Bibliothèque standard uniquement. Usage : python3 collect/capture.py [durée_max_minutes]
"""
import json, os, sys, time, subprocess, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

BASE = "https://online.turfinfo.api.pmu.fr/rest/client/1/programme"
UA = {"User-Agent": "HippiqueLab-research/0.1 (usage personnel)", "Accept": "application/json"}
ROOT = os.path.join(os.path.dirname(__file__), "..", "data")
PARIS = timezone(timedelta(hours=1))  # heure d'hiver ; l'API donne des horodatages UTC (ms), on n'utilise ce fuseau que pour la date
RAPPORTS = ("SIMPLE_GAGNANT", "SIMPLE_PLACE", "COUPLE_GAGNANT", "DEUX_SUR_QUATRE")


def get(url):
    for i in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                b = r.read()
                return json.loads(b) if b else None
        except urllib.error.HTTPError as e:
            if e.code in (204, 400, 404):
                return None
        except Exception:
            pass
        time.sleep(2)
    return None


def git_save(msg):
    subprocess.run("git add data && (git diff --cached --quiet || git commit -q -m \"%s\") && "
                   "for i in 1 2 3 4; do git pull --rebase -q && git push -q && break; sleep 5; done" % msg, shell=True)


def programme(ds):
    p = get(f"{BASE}/{ds}")
    races = []
    if not p:
        return races
    for reu in p.get("programme", {}).get("reunions", []):
        if (reu.get("pays") or {}).get("code") != "FRA":
            continue
        for c in reu.get("courses", []):
            races.append(dict(r=reu["numOfficiel"], c=c["numOrdre"], depart=c.get("heureDepart", 0) / 1000,
                              hippodrome=(reu.get("hippodrome") or {}).get("libelleCourt"), discipline=c.get("discipline"),
                              specialite=c.get("specialite"), prix=c.get("montantPrix"), partants=c.get("nombreDeclaresPartants"),
                              distance=c.get("distance"), statut=c.get("statut"), libelle=c.get("libelle")))
    return races


def snapshot(ds, r, c):
    snap = dict(t=round(time.time()), combinaisons=get(f"{BASE}/{ds}/R{r}/C{c}/combinaisons"))
    for t in RAPPORTS:
        snap[t] = get(f"{BASE}/{ds}/R{r}/C{c}/rapports/{t}")
        time.sleep(0.3)
    return snap


def main(max_min=345):
    t0 = time.time()
    day = datetime.now(PARIS).date(); ds = day.strftime("%d%m%Y")
    folder = os.path.join(ROOT, day.isoformat()); os.makedirs(folder, exist_ok=True)
    races, last_prog, last_save, last_snap = [], 0, time.time(), {}
    while time.time() - t0 < max_min * 60:
        now = time.time()
        if now - last_prog > 900 or not races:          # programme rafraîchi toutes les 15 min (horaires et statuts)
            races = programme(ds) or races; last_prog = now
            json.dump(races, open(os.path.join(folder, "programme.json"), "w"), ensure_ascii=False)
        todo = [x for x in races if x["depart"] and -180 <= x["depart"] - now <= 1200 and x.get("statut") not in ("FIN_COURSE", "ARRIVEE_DEFINITIVE", "COURSE_ANNULEE")]
        remaining = [x for x in races if x["depart"] and x["depart"] - now > -180]
        if not remaining:
            print("plus de course aujourd'hui"); break
        for x in todo:
            k = f"R{x['r']}C{x['c']}"; dt = x["depart"] - now
            every = 170 if dt > 360 else 50
            if now - last_snap.get(k, 0) < every:
                continue
            s = snapshot(ds, x["r"], x["c"]); s["avant_depart_s"] = round(dt); last_snap[k] = now
            with open(os.path.join(folder, k + ".jsonl"), "a") as f:
                f.write(json.dumps(s, ensure_ascii=False, separators=(",", ":")) + "\n")
            print(datetime.now(PARIS).strftime("%H:%M:%S"), k, x["hippodrome"], f"départ dans {dt/60:.1f} min", flush=True)
        if time.time() - last_save > 600:
            git_save(f"Cotes {day} {datetime.now(PARIS):%H:%M}"); last_save = time.time()
        time.sleep(max(5, 60 - (time.time() - now)))
    git_save(f"Cotes {day} fin de lot")
    # lot suivant si des courses restent (un job GitHub dure 6 h au plus)
    races = programme(ds) or races
    if any(x["depart"] - time.time() > -180 for x in races if x["depart"]):
        print("courses restantes : lot suivant")
        subprocess.run("gh workflow run capture.yml", shell=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 345)
