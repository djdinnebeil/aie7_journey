import json
import glob

for nb_path in glob.glob("*.ipynb"):
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)
    if "widgets" in nb.get("metadata", {}):
        del nb["metadata"]["widgets"]
        with open(nb_path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1)
        print(f"Fixed: {nb_path}")
    else:
        print(f"No widgets metadata in: {nb_path}") 