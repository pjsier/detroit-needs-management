import json
from pathlib import Path
from collections import Counter
import csv

BASE_DIR = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    with Path.open(BASE_DIR / "src" / "assets" / "resources.geojson", "r") as f:
        resources = json.load(f)
    counter = Counter()
    for resource in resources["features"]:
        counter.update(resource["properties"]["attributes"].keys())
    with Path.open(BASE_DIR / "attribute-counts.csv", "w") as f:
        writer = csv.DictWriter(f, fieldnames=["attribute", "count"])
        writer.writeheader()
        for item, count in counter.most_common():
            writer.writerow({"attribute": item, "count": count})
