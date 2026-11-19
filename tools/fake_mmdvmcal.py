#!/usr/bin/env python3
"""
Stand-in for MMDVMCal without hardware (demo mode and tests).

Prints the same lines as MMDVMCal on an MMDVM_HS board. In "BER Test Mode
(FEC) for DMR Simplex" it pretends a radio is transmitting in bursts; the BER
gets lower the closer the frequency is to nominal + TRUE_OFFSET.
Usage: fake_mmdvmcal.py <speed> <port>
"""
import os
import select
import sys
import termios
import time
import tty

TRUE_OFFSET = int(os.environ.get("FAKE_CAL_OFFSET", "-350"))


def out(s=""):
    sys.stdout.write(s + "\r\n")
    sys.stdout.flush()


def help_():
    for line in ["The commands are:", "    H/h      Display help", "    Q/q      Quit",
                 "    E/e      Enter frequency (current: %u Hz)" % state["freq"], "    F        Increase frequency",
                 "    f        Decrease frequency", "    Z/z      Enter frequency step", "    T        Increase deviation",
                 "    t        Decrease deviation", "    P        Increase RF power", "    p        Decrease RF power",
                 "    D/d      DMR Deviation Mode (Adjust for 2.75Khz Deviation)",
                 "    b        BER Test Mode (FEC) for DMR Simplex (CC1)", "    S/s      RSSI Mode",
                 "    <space>  Toggle transmit"]:
        out(line)


state = {"freq": 433000000, "step": 50, "mode": "", "tx": False, "level": 50.0, "power": 100.0, "nominal": None}


def readline(fd):
    buf = b""
    while True:
        c = os.read(fd, 1)
        if c in (b"\n", b"\r"):
            return buf.decode()
        buf += c


def main():
    if len(sys.argv) < 3:
        print("Usage: MMDVMCal <speed> <port>", file=sys.stderr)
        return 1
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd) if os.isatty(fd) else None
    if old:
        tty.setcbreak(fd)
    time.sleep(1.5)
    out("Version: 1, description: MMDVM_HS_Hat-v1.6.1 20230805 14.7456MHz ADF7021 FW by CA6JAU GitID #f3bd9ab")
    help_()
    burst_start, seq, frames, errs = time.time(), 0, 0, 0
    in_burst = False
    try:
        while True:
            r, _, _ = select.select([fd], [], [], 0.36)
            if r:
                c = os.read(fd, 1).decode(errors="ignore")
                if c in "qQ":
                    break
                elif c in "eE":
                    out("Enter frequency (current %u Hz):" % state["freq"])
                    v = readline(fd)
                    if v.isdigit():
                        state["freq"] = int(v)
                        if state["nominal"] is None:
                            state["nominal"] = int(v)
                        out("New frequency: %u Hz" % state["freq"])
                    else:
                        out("Not valid frequency")
                elif c == "F":
                    state["freq"] += state["step"]
                    out("TX frequency: %u" % state["freq"])
                elif c == "f":
                    state["freq"] -= state["step"]
                    out("TX frequency: %u" % state["freq"])
                elif c in "zZ":
                    out("Enter frequency step (current %u Hz):" % state["step"])
                    v = readline(fd)
                    if v.isdigit():
                        state["step"] = int(v)
                        out("New frequency step: %u Hz" % state["step"])
                elif c == "b":
                    state["mode"] = "ber"
                    out("BER Test Mode (FEC) for DMR Simplex")
                elif c in "dD":
                    state["mode"] = "dev"
                    out("DMR Deviation Mode (Set to 2.75Khz Deviation)")
                elif c in "sS":
                    state["mode"] = "rssi"
                    out("RSSI Mode")
                elif c == " ":
                    state["tx"] = not state["tx"]
                    out("Set transmitter %s" % ("ON" if state["tx"] else "OFF"))
                elif c in "tT":
                    state["level"] = max(0, min(100, state["level"] + (0.5 if c == "T" else -0.5)))
                    out("TX Level: %.1f%%" % state["level"])
                elif c in "pP":
                    state["power"] = max(0, min(100, state["power"] + (1 if c == "P" else -1)))
                    out("RF power: %.1f%%" % state["power"])
                elif c in "hH":
                    help_()
                elif c in "vV":
                    out("MMDVMCal 20240101 (fake for demo)")
                continue
            if state["mode"] == "ber" and state["nominal"]:
                t = (time.time() - burst_start) % 9.0
                if t < 6.0:
                    if not in_burst:
                        in_burst, seq, frames, errs = True, 0, 0, 0
                        out("DMR voice header received")
                    dev = abs(state["freq"] - (state["nominal"] + TRUE_OFFSET))
                    ber = max(0.0, min(18.0, (dev / 120.0) ** 2 * 0.8 + 0.15 + (seq % 3) * 0.08))
                    e = int(round(ber * 1.41))
                    frames += 1
                    errs += e
                    out("DMR audio seq. %d, FEC BER %% (errs): %.3f%% (%u/141)" % (seq % 6, e / 1.41, e))
                    seq += 1
                elif in_burst:
                    in_burst = False
                    bits = frames * 141
                    out("DMR voice end received, total frames: %d, bits: %d, errors: %d, BER: %.4f%%"
                        % (frames, bits, errs, errs * 100.0 / max(1, bits)))
            elif state["mode"] == "rssi" and int(time.time() * 3) % 3 == 0:
                out("RSSI: max: 812, min: 788, ave: 801")
    finally:
        if old:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return 0


if __name__ == "__main__":
    sys.exit(main())
