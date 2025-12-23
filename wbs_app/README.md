# WBS Project Dashboard (Streamlit)

Dashboard Streamlit moderne qui **extrait automatiquement** la structure WBS et les métriques (Planned / Forecast / Schedule / Earned / Écart / Impact / Glissement) depuis un fichier **Excel** puis génère une vue hiérarchique **pro** (Niveau 1 → sections N2 alignées → tableau N3 + bar chart).

https://wbs-dashboard-app-265wfosvya6ebzja5uokf9.streamlit.app/

---

## ✨ Points clés
- **Upload Excel** → extraction instantanée du WBS (zéro config)
- **Header N2 aligné** aux colonnes du tableau (grid)
- **Mode large** sans scroll horizontal
- **Graphiques** Plotly (Schedule vs Units)

---

## 🚀 Utilisation la plus simple (Windows)
1. Télécharge le ZIP du repo, dézippe.
2. Double-clique `start.bat`.
3. Ton navigateur s’ouvre sur `http://localhost:8501`.
4. Clique **Upload Excel** et charge ton fichier (ex: `examples/Exemple_WBS.xlsx`).

> Le script crée un environnement virtuel tout seul et installe ce qu’il faut.

### macOS / Linux
```bash
chmod +x start_mac.sh
./start_mac.sh
