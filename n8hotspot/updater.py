"""
Version of N8-HotSpot, the hourly check for updates on GitHub and "Update now"
(same logic as HBlink4-FreeRadioID). Optional automatic mode: installs a new version
at night, when nobody is transmitting.

After an update:
  - changed requirements.txt   -> pip install into the own virtual environment
  - changed config generator   -> ini files written again, MMDVMHost and DMRGateway restarted
  - always                     -> the web interface restarts (sudo rule from install.sh, else systemd Restart=always)
"""
import json
import re
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = "dhartmann1979/N8-HotSpot"
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BRANCH_RE = re.compile(r"^[A-Za-z0-9_./-]{1,100}$")

_local: Optional[Dict[str, Any]] = None
_cache: Dict[str, Any] = {}


VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _package_version() -> str:
    """Version from the file VERSION (SemVer; N8-HotSpot 1.1.0 is the first one with an update check)."""
    try:
        v = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        return v if VERSION_RE.match(v) else ""
    except OSError:
        return ""


def _base_version() -> str:
    return ""


def vtuple(v: str) -> tuple:
    """'1.2.3' -> (1, 2, 3); anything else -> (0, 0, 0)."""
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", (v or "").strip())
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


CHANGELOG_HEAD = re.compile(r"^##\s*\[?v?(\d+\.\d+\.\d+)\]?\s*(?:[-–—]\s*(\S+))?.*$", re.M)


def changelog_sections(text: str) -> list:
    """CHANGELOG.md -> [{'version', 'date', 'body'}], newest first (as in the file)."""
    out = []
    heads = list(CHANGELOG_HEAD.finditer(text or ""))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        out.append({"version": h.group(1), "date": h.group(2) or "", "body": text[h.end():end].strip()[:6000]})
    return out


def changes_since(text: str, local: str) -> list:
    """Changelog sections newer than the installed version (max. 10)."""
    lv = vtuple(local)
    return [s for s in changelog_sections(text) if vtuple(s["version"]) > lv][:10]


def _git(*args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def local_version(refresh: bool = False) -> Dict[str, Any]:
    """{'version', 'commit', 'short', 'date', 'branch'} – commit/date empty without git."""
    global _local
    if _local is None or refresh:
        line = _git("log", "-1", "--format=%H|%cI")
        commit, _, date = line.partition("|")
        _local = {"version": _package_version(), "base": _base_version(), "commit": commit, "short": commit[:7],
                  "date": date, "branch": _git("rev-parse", "--abbrev-ref", "HEAD")}
    return dict(_local)


def _fetch_json(url: str, timeout: float = 6) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "N8-HotSpot",
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read(2_000_000).decode("utf-8", errors="replace"))


def _fetch_text(fetch, repo: str, path: str, ref: str) -> str:
    """A text file from GitHub (contents API, base64)."""
    import base64
    j = fetch(f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}")
    return base64.b64decode(j.get("content") or "").decode("utf-8", errors="replace")


def check(repo: str = DEFAULT_REPO, branch: str = "main", max_age: float = 6 * 3600,
          force: bool = False, fetch=_fetch_json) -> Dict[str, Any]:
    """Compare the local commit with the newest commit of repo/branch on GitHub."""
    repo = (repo or DEFAULT_REPO).strip()
    branch = (branch or "main").strip()
    key = f"{repo}@{branch}"
    hit = _cache.get(key)
    if hit and not force and time.time() - hit["checked_at"] < max_age:
        return hit
    loc = local_version(refresh=force)
    res: Dict[str, Any] = {"repo": repo, "branch": branch, "local": loc, "checked_at": time.time(),
                           "available": False, "behind": 0, "latest": None, "commits": [], "error": "",
                           "remote_version": "", "release_notes": [],
                           "url": f"https://github.com/{repo}"}
    if not _REPO_RE.match(repo) or not _BRANCH_RE.match(branch):
        res["error"] = "invalid repository or branch name"
    else:
        try:
            head = fetch(f"https://api.github.com/repos/{repo}/commits/{branch}")
            sha = head.get("sha", "")
            c = head.get("commit") or {}
            res["latest"] = {"commit": sha, "short": sha[:7], "date": (c.get("committer") or {}).get("date", ""),
                             "message": (c.get("message") or "").split("\n")[0][:140]}
            if loc["commit"] and sha and sha != loc["commit"]:
                cmp = fetch(f"https://api.github.com/repos/{repo}/compare/{loc['commit']}...{sha}")
                status = cmp.get("status")
                res["behind"] = int(cmp.get("ahead_by") or 0)
                res["available"] = status in ("ahead", "diverged") and res["behind"] > 0
                res["commits"] = [{"short": (x.get("sha") or "")[:7],
                                   "message": ((x.get("commit") or {}).get("message") or "").split("\n")[0][:140],
                                   "date": (((x.get("commit") or {}).get("committer")) or {}).get("date", "")}
                                  for x in reversed(cmp.get("commits") or [])][:10]
                res["url"] = f"https://github.com/{repo}/compare/{loc['short']}...{sha[:7]}"
            elif not loc["commit"]:
                res["error"] = "no git checkout here – cannot compare"
            if res["available"] or not loc["commit"]:
                # Version number and release notes of the new version (VERSION + CHANGELOG.md on GitHub)
                try:
                    rv = _fetch_text(fetch, repo, "VERSION", sha or branch).strip()
                    res["remote_version"] = rv if VERSION_RE.match(rv) else ""
                    res["release_notes"] = changes_since(_fetch_text(fetch, repo, "CHANGELOG.md", sha or branch),
                                                         loc.get("version", ""))
                except Exception:
                    pass
        except Exception as e:   # network, rate limit, unknown commit (local changes not pushed)
            res["error"] = str(e)[:200]
    _cache[key] = res
    return res


# ------------------------------------------------------------------ installing
# "Update now" is deliberately narrow: it only fast-forwards the checkout to the
# branch of the git remote "origin" that is configured on disk (never a URL from
# the web UI), only to the exact commit the admin saw, never with local changes,
# with git hooks and the file/ext transports switched off and no shell involved.
_GIT_SAFE = ["-c", "core.hooksPath=/dev/null", "-c", "protocol.file.allow=never",
             "-c", "protocol.ext.allow=never", "-c", "credential.helper="]
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIREMENT_FILES = ("requirements.txt",)
CONFIG_FILES = ("n8hotspot/configgen.py", "n8hotspot/settings.py")


class UpdateError(Exception):
    pass


def _git_run(*args: str, timeout: float = 120) -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(Path.home()), "LC_ALL": "C",
           "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/true", "SSH_ASKPASS": "/bin/true",
           "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}
    try:
        return subprocess.run(["git", "-C", str(REPO_ROOT), *_GIT_SAFE, *args], capture_output=True,
                              text=True, timeout=timeout, env=env)
    except (OSError, subprocess.SubprocessError) as e:
        raise UpdateError(f"git could not be run: {e}")


def _git_ok(*args: str, timeout: float = 120) -> str:
    r = _git_run(*args, timeout=timeout)
    if r.returncode != 0:
        msg = (r.stderr or r.stdout or "").strip().splitlines()
        raise UpdateError(f"git {args[0]} failed: {msg[-1] if msg else r.returncode}")
    return r.stdout.strip()


def origin_url() -> str:
    url = _git("remote", "get-url", "origin")
    return re.sub(r"//[^/@]+@", "//", url)   # never show credentials


def install(branch: str, expected: str) -> Dict[str, Any]:
    """Fast-forward to origin/<branch> if that is exactly `expected`. Returns what changed."""
    branch = (branch or "main").strip()
    expected = (expected or "").strip().lower()
    if not _BRANCH_RE.match(branch) or branch.startswith("-") or ".." in branch:
        raise UpdateError("Invalid branch name.")
    if not _SHA_RE.match(expected):
        raise UpdateError("Please check for updates first.")
    if not (REPO_ROOT / ".git").exists():
        raise UpdateError("This installation is not a git checkout – update by hand.")
    head_branch = _git_ok("rev-parse", "--abbrev-ref", "HEAD")
    if head_branch != branch:
        raise UpdateError(f"The checkout is on branch '{head_branch}', not '{branch}'.")
    dirty = _git_ok("status", "--porcelain", "--untracked-files=no")
    if dirty:
        files = ", ".join(line.split(maxsplit=1)[-1] for line in dirty.splitlines()[:5])
        raise UpdateError(f"Files were changed by hand ({files}). Update on the console, "
                          "or undo the changes first (git stash).")
    old = _git_ok("rev-parse", "HEAD")
    _git_ok("fetch", "--no-tags", "--quiet", "origin", f"refs/heads/{branch}", timeout=180)
    new = _git_ok("rev-parse", "FETCH_HEAD")
    if new != expected:
        raise UpdateError("The version on the server's git remote is not the one that was shown "
                          f"({new[:7]} instead of {expected[:7]}). Check again.")
    if new == old:
        return {"old": old, "new": new, "files": [], "requirements_changed": False, "changed": False}
    if _git_run("merge-base", "--is-ancestor", old, new).returncode != 0:
        raise UpdateError("This installation has its own commits – it cannot simply be moved forward. Update by hand.")
    files = [f for f in _git_ok("diff", "--name-only", old, new).splitlines() if f]
    _git_ok("merge", "--ff-only", "--quiet", new)
    local_version(refresh=True)
    _cache.clear()
    return {"old": old, "new": new, "files": files[:200], "changed": True,
            "requirements_changed": any(f in REQUIREMENT_FILES for f in files),
            "config_changed": any(f in CONFIG_FILES for f in files)}


# ------------------------------------------------------------------- after the update
def pip_install() -> str:
    """Install changed Python packages into the running virtual environment ('' = ok)."""
    import sys
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(REPO_ROOT / "requirements.txt")],
                           capture_output=True, text=True, timeout=600)
        return "" if r.returncode == 0 else (r.stderr or r.stdout).strip().splitlines()[-1][:300]
    except (OSError, subprocess.SubprocessError) as e:
        return str(e)


def _sudo() -> list:
    import os
    return [] if os.geteuid() == 0 else ["sudo", "-n"]


def systemctl(action: str, service: str) -> bool:
    """Only the commands allowed by /etc/sudoers.d/n8hotspot (install.sh)."""
    import shutil
    sc = shutil.which("systemctl") or "/usr/bin/systemctl"
    try:
        return subprocess.run([*_sudo(), sc, action, f"{service}.service"], capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def in_window(hour: int, now: Optional[float] = None) -> bool:
    """True during the hour chosen for automatic updates (local time)."""
    import datetime as _dt
    return _dt.datetime.fromtimestamp(now or time.time()).hour == int(hour)
