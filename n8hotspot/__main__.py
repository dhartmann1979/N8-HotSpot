"""
Start:            python -m n8hotspot
New password:     python -m n8hotspot reset-password [username]
Write ini files:  python -m n8hotspot write-config
"""
import getpass
import logging
import os
import sys


def main(argv):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if len(argv) > 1 and argv[1] == "reset-password":
        from .app import Ctx
        user = argv[2] if len(argv) > 2 else "n8schicht"
        pw = os.environ.get("N8HS_PASSWORD") or getpass.getpass(f"New password for {user}: ")
        Ctx().auth.reset(user, pw)
        print(f"Password for {user} set. All of {user}'s sessions were ended.")
        return 0
    if len(argv) > 1 and argv[1] == "write-config":
        from . import app as a
        a.ctx = a.Ctx()
        print(a.write_config())
        return 0
    import uvicorn
    uvicorn.run("n8hotspot.app:app", host=os.environ.get("N8HS_BIND", "0.0.0.0"),
                port=int(os.environ.get("N8HS_PORT", "80")), log_level="warning", proxy_headers=False)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
