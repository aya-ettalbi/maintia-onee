from pathlib import Path
import re
import shutil
from datetime import datetime


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MAIN_FILE = BACKEND_ROOT / "app" / "main.py"


def main() -> None:
    if not MAIN_FILE.exists():
        raise FileNotFoundError(f"Fichier introuvable : {MAIN_FILE}")

    text = MAIN_FILE.read_text(encoding="utf-8")

    if "historical_router" in text or "routes.historical" in text:
        print("La route historique est déjà enregistrée.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = MAIN_FILE.with_name(f"main.py.backup_{timestamp}")
    shutil.copy2(MAIN_FILE, backup)

    import_line = "from app.api.routes.historical import router as historical_router\n"

    # Insère l'import juste avant la création de l'application.
    match = re.search(r"(?m)^app\s*=\s*FastAPI\(", text)
    if not match:
        raise RuntimeError(
            "Impossible de trouver 'app = FastAPI(' dans app/main.py. "
            "Aucune modification n'a été effectuée."
        )

    text = text[:match.start()] + import_line + "\n" + text[match.start():]

    # Récupère le préfixe déjà utilisé par les autres routes.
    prefix_match = re.search(
        r"app\.include_router\([^,\n]+,\s*prefix\s*=\s*([^)]+)\)",
        text,
    )
    prefix_expr = prefix_match.group(1).strip() if prefix_match else '"/api/v1"'

    include_line = f"\napp.include_router(historical_router, prefix={prefix_expr})\n"

    # Ajoute après la dernière route enregistrée.
    matches = list(re.finditer(r"(?m)^app\.include_router\(.*$", text))
    if matches:
        pos = matches[-1].end()
        text = text[:pos] + include_line + text[pos:]
    else:
        text += include_line

    MAIN_FILE.write_text(text, encoding="utf-8")

    print("Route historique enregistrée dans app/main.py")
    print("Sauvegarde :", backup)
    print("Préfixe utilisé :", prefix_expr)


if __name__ == "__main__":
    main()
