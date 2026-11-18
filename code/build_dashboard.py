"""Create a standalone dashboard and a GitHub-ready archive, aggregates only."""
import base64
import json
import runpy
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
runpy.run_path(str(root / "code" / "write_findings.py"), run_name="__main__")
docs = root / "docs"
output = root / "output"
output.mkdir(exist_ok=True)

results = {p.stem: json.loads(p.read_text()) for p in sorted((docs / "results").glob("*.json"))}
html = (docs / "index.html").read_text()
css = (docs / "assets" / "style.css").read_text()
js = (docs / "assets" / "app.js").read_text()
mark = "data:image/svg+xml;base64," + base64.b64encode((docs / "assets" / "mark.svg").read_bytes()).decode()
catalog = "data:application/json;base64," + base64.b64encode((docs / "results" / "catalog.json").read_bytes()).decode()
html = html.replace('<link rel="stylesheet" href="assets/style.css">', f"<style>{css}</style>")
html = html.replace('<script src="assets/app.js" defer></script>', "")
html = html.replace("assets/mark.svg", mark).replace('href="results/catalog.json" download', f'href="{catalog}" download="catalog.json"')
decisions = "data:text/plain;charset=utf-8;base64," + base64.b64encode((docs / "analysis-decisions.txt").read_bytes()).decode()
html = html.replace('href="analysis-decisions.txt" download', f'href="{decisions}" download="ANALYSIS_DECISIONS.txt"')
# The embedded copy keeps findings inside the same file, with no server needed.
html = html.replace('href="findings.html"', 'href="?tab=findings#explorer"')
html = html.replace('Open this summary as a separate page ↗', 'Link to this findings view ↗')
# Escape < to make data inert even if source labels ever contain HTML/script tags.
payload = json.dumps(results, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
html = html.replace("</body>", f'<script id="embedded-results" type="application/json">{payload}</script>\n<script>{js}</script>\n</body>')
(output / "trust-democracy.html").write_text(html)

with zipfile.ZipFile(output / "trust-democracy-github.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for folder in ("docs", "code", "tables", "figures"):
        for path in sorted((root / folder).rglob("*")):
            if path.is_file() and path.name != ".DS_Store" and "__pycache__" not in path.parts and "example" not in path.relative_to(root).parts:
                archive.write(path, path.relative_to(root))
    for name in ("README.md", ".gitignore", "ANALYSIS_DECISIONS.txt"):
        archive.write(root / name, name)
print("Built output/trust-democracy.html (open directly, no server required).")
print("Built output/trust-democracy-github.zip (site, code, tables, figure; no raw data).")
