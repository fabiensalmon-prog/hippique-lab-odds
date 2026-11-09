# hippique-lab-odds

Recherche personnelle (aucun pari réel) : enregistrement des cotes et des masses de paris PMU dans les 20 dernières minutes avant le départ des courses françaises, pour mesurer l'écart entre la cote disponible 2 à 5 minutes avant le départ et le rapport final.

- `collect/capture.py` : boucle d'enregistrement (bibliothèque standard Python), lancée par `.github/workflows/capture.yml`.
- `data/AAAA-MM-JJ/R<r>C<c>.jsonl` : un relevé JSON par ligne (masses par combinaison de tous les jeux, rapports directs gagnant, placé, couplé gagnant, 2sur4), avec `avant_depart_s` = secondes avant l'heure de départ prévue.
- Données : API publique du programme PMU, collecte lente (≈ 5 requêtes par course et par minute au plus, uniquement dans les 20 dernières minutes).
