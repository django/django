from pathlib import Path

EXTERNAL_CRS_FIXTURES = {
    path.stem: path.read_text()
    for path in sorted(Path(__file__).parent.glob("*.geojson"))
}
