"""Build a deterministic PCM ZIP and standalone manual-install ZIP."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def archive(path, entries):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            out.writestr(info, data)


def main():
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    metadata = json.loads((ROOT / "metadata.json").read_text())
    version = metadata["versions"][0]["version"]
    source = {p.name: p.read_bytes() for p in (ROOT / "populateview").glob("*.py")}
    pcm = {"plugins/" + name: content for name, content in source.items()}
    pcm["plugins/LICENSE"] = (ROOT / "LICENSE").read_bytes()
    pcm["plugins/README.md"] = (ROOT / "README.md").read_bytes()
    pcm["metadata.json"] = (ROOT / "metadata.json").read_bytes()
    package = output / ("PopulateView-" + version + "-pcm.zip")
    archive(package, pcm)
    manual = {"populateview/" + name: content for name, content in source.items()}
    manual["populateview/LICENSE"] = (ROOT / "LICENSE").read_bytes()
    manual["README.md"] = (ROOT / "README.md").read_bytes()
    archive(output / ("PopulateView-" + version + "-manual.zip"), manual)
    published = metadata["versions"][0]
    published.update(download_sha256=hashlib.sha256(package.read_bytes()).hexdigest(),
                     download_size=package.stat().st_size,
                     install_size=sum(map(len, pcm.values())),
                     download_url="https://github.com/RealHaltewunsch/PopulateView/releases/download/v"
                     + version + "/" + package.name)
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    sums = "".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n"
                   for p in sorted(output.glob("*.zip")))
    (output / "SHA256SUMS").write_text(sums)
    print(sums, end="")


if __name__ == "__main__":
    main()
