#!/usr/bin/env python3
"""
Versions of N8-Hotspot (see docs/de/updates.md).

  python3 scripts/release.py 1.1.0          check CHANGELOG.md, write VERSION and commit
                                            (after git push, GitHub creates tag v1.1.0 and the release)
  python3 scripts/release.py 1.1.0 --tag    additionally create the annotated tag v1.1.0 here
  python3 scripts/release.py --check        VERSION and the newest CHANGELOG entry match?
  python3 scripts/release.py --notes 1.1.0  print the description of one version (used by the GitHub release)
  python3 scripts/release.py --date 1.1.0   print the date of one version

Nothing is pushed: afterwards  git push
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from n8hotspot.updater import changelog_sections, vtuple, VERSION_RE  # noqa: E402


def sections():
    return changelog_sections((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))


def section(version):
    return next((s for s in sections() if s["version"] == version), None)


def die(msg):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip()); return
    if argv[0] == "--notes":
        s = section(argv[1]) or die(f"no entry for {argv[1]} in CHANGELOG.md")
        print(s["body"]); return
    if argv[0] == "--date":
        s = section(argv[1]) or die(f"no entry for {argv[1]} in CHANGELOG.md")
        print(s["date"]); return
    current = (ROOT / "VERSION").read_text().strip()
    newest = (sections() or [{}])[0].get("version", "")
    if argv[0] == "--check":
        if current != newest:
            die(f"VERSION is {current}, newest CHANGELOG entry is {newest}")
        print(f"✓ v{current}"); return

    new = argv[0].lstrip("v")
    if not VERSION_RE.match(new):
        die("version must look like 1.2.3")
    if vtuple(new) <= vtuple(current) and new != current:
        die(f"{new} is not newer than {current}")
    s = section(new) or die(f"write the entry '## [{new}] – YYYY-MM-DD' in CHANGELOG.md first")
    if newest != new:
        die(f"the entry for {new} must be the first (newest) one in CHANGELOG.md")
    if len(s["body"]) < 40:
        die("describe the changes in more detail in CHANGELOG.md")
    (ROOT / "VERSION").write_text(new + "\n")
    subprocess.run(["git", "-C", str(ROOT), "add", "VERSION", "CHANGELOG.md"], check=True)
    if subprocess.run(["git", "-C", str(ROOT), "diff", "--cached", "--quiet"]).returncode != 0:
        subprocess.run(["git", "-C", str(ROOT), "commit", "-q", "-m", f"Release v{new}\n\n{s['body']}"], check=True)
    if "--tag" in argv:
        subprocess.run(["git", "-C", str(ROOT), "tag", "-a", f"v{new}", "-m", f"v{new} – {s['date']}\n\n{s['body']}"], check=True)
        print(f"✓ v{new} tagged. Publish with:  git push && git push origin v{new}")
    else:
        print(f"✓ v{new} ready. Publish with:  git push   (GitHub then creates tag v{new} and the release)")


if __name__ == "__main__":
    main(sys.argv[1:])
