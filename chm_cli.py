#!/usr/bin/env python3
import os
import sys
import time
import random
import platform
import cmd
from typing import Optional
from urllib.parse import urlparse

import requests
import tempfile
from pathlib import Path
import ssdeep
import json  # for pretty-printing full metadata

# ==============================
# CONFIG
# ==============================
API_BASE = "http://127.0.0.1:8000/api"
VERSION = "CHM-X v1.1"

# ==============================
# COLORS
# ==============================
RED = "\033[91m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RESET = "\033[0m"
BOLD = "\033[1m"

# ==============================
# BANNER (CHM-X)
# ==============================
BANNER = r"""
 ██████╗  ██╗  ██╗  ███╗   ███╗   ██╗  ██╗
██╔════╝  ██║  ██║  ████╗ ████║   ╚██╗██╔╝
██║       ███████║  ██╔████╔██║    ╚███╔╝ 
██║       ██╔══██║  ██║╚██╔╝██║    ██╔██╗ 
╚██████╗  ██║  ██║  ██║ ╚═╝ ██║   ██╔╝ ██╗
 ╚═════╝  ╚═╝  ╚═╝  ╚═╝     ╚═╝   ╚═╝  ╚═╝

        ⚡  C H M  –  X  ⚡
     > Cyber • Hack • Modify <

"""

# ==============================
# VISUAL EFFECTS
# ==============================
def clear():
    os.system("clear" if os.name == "posix" else "cls")


def slow(text: str, delay: float = 0.002):
    if delay <= 0:
        sys.stdout.write(text)
        sys.stdout.flush()
        return
    for c in text:
        sys.stdout.write(c)
        sys.stdout.flush()
        time.sleep(delay)


def matrix_effect(lines=10):
    chars = "01█▓▒░"
    for _ in range(lines):
        print(f"{GREEN}{''.join(random.choice(chars) for _ in range(70))}{RESET}")
        time.sleep(0.05)


def loading_bar():
    sys.stdout.write(f"{CYAN}[+] Initializing CHM-X ")
    sys.stdout.flush()
    for _ in range(30):
        sys.stdout.write("█")
        sys.stdout.flush()
        time.sleep(0.04)
    print(" ✔")


def detect_os():
    os_name = platform.system()
    if "Linux" in os_name:
        return "Kali / Linux"
    elif "Windows" in os_name:
        return "Windows"
    return "Unknown"


def print_banner():
    clear()
    matrix_effect()

    print(f"{GREEN}[✓] Booting CHM-X Framework...{RESET}")
    time.sleep(0.3)
    print(f"{GREEN}[✓] Detecting OS...{RESET}")
    time.sleep(0.3)
    print(f"{CYAN}    → {detect_os()}{RESET}")
    time.sleep(0.3)

    loading_bar()
    time.sleep(0.4)

    clear()
    slow(f"{CYAN}{BANNER}{RESET}", 0.0015)

    print(f"{YELLOW}{BOLD}{VERSION}  |  Enterprise Security Framework{RESET}")
    print(f"{MAGENTA}Author : Devadharshini{RESET}")
    print(f"{GREEN}Mode   : Red Team / Forensics / Monitoring{RESET}")
    print(f"{CYAN}Type 'help' or '?' to list commands\n{RESET}")


# ==============================
# HELPER FUNCTIONS
# ==============================
def is_url(target: str) -> bool:
    parsed = urlparse(target)
    return parsed.scheme in ("http", "https")


# ==============================
# MAIN CLI
# ==============================
class ChmxShell(cmd.Cmd):
    prompt = "chmx> "

    def __init__(self):
        super().__init__()
        self.target: Optional[str] = None
        self.case_id: Optional[str] = None
        self.assessed_by: str = "cli-user"
        self.mode: str = "monitor"
        self.scan_type: str = "full_evidence"
        self.last_scan_id: Optional[str] = None

        # folders for sequence compare
        self.real_folder: Optional[str] = None
        self.tampered_folder: Optional[str] = None

    def preloop(self):
        print_banner()

    def cmdloop_with_ctrlc(self):
        """
        Keep shell open on Ctrl+C: abort current command, show prompt again.
        """
        while True:
            try:
                super().cmdloop()
                break
            except KeyboardInterrupt:
                print("^C")

    @staticmethod
    def _print_kv(title: str, value: str, width: int = 18):
        print(f"{title:<{width}}: {value}")

    # ------------ commands ------------

    def do_set(self, arg):
        """
        set <option> <value>
        Options:
          target         - folder path
          case           - case id
          user           - assessed_by name
          mode           - monitor (default)
          scan_type      - integrity | metadata | ai_detection | full_evidence
          real_folder    - real/original folder for sequence compare
          tampered_folder- tampered folder for sequence compare
        """
        parts = arg.split()
        if len(parts) < 2:
            print("Usage: set <option> <value>")
            return
        opt, value = parts[0], " ".join(parts[1:])
        if opt == "target":
            self.target = value
        elif opt == "case":
            self.case_id = value
        elif opt == "user":
            self.assessed_by = value
        elif opt == "mode":
            self.mode = value
        elif opt == "scan_type":
            self.scan_type = value
        elif opt == "real_folder":
            self.real_folder = value
        elif opt == "tampered_folder":
            self.tampered_folder = value
        else:
            print(f"Unknown option: {opt}")
            return
        print(f"[+] {opt} set to {value}")

    def do_show(self, arg):
        """
        show config
        show last
        """
        arg = arg.strip()
        if arg == "config":
            print("\n=== CONFIG ===")
            self._print_kv("Target", self.target or "-")
            self._print_kv("Case ID", self.case_id or "-")
            self._print_kv("User", self.assessed_by or "-")
            self._print_kv("Mode", self.mode)
            self._print_kv("Scan type", self.scan_type)
            self._print_kv("Real folder", self.real_folder or "-")
            self._print_kv("Tampered folder", self.tampered_folder or "-")
            print()
        elif arg == "last":
            print(f"Last scan_id: {self.last_scan_id or '-'}")
        else:
            print("Usage: show config | show last")

    # ====== FILE / FOLDER SCAN ======

    def do_run(self, arg):
        """
        run
        Run filesystem scan on target folder.
        """
        if not self.target:
            print("Set target first using: set target <path>")
            return

        if is_url(self.target):
            print("Target is a URL. URL scanning is disabled in this build.")
            return

        payload = {
            "root_path": self.target,
            "case_id": self.case_id,
            "assessed_by": self.assessed_by,
            "mode": self.mode,
            "scan_type": self.scan_type,
        }
        print(f"\n[+] Running filesystem scan on {self.target}...")
        resp = requests.post(f"{API_BASE}/scan", json=payload)
        if resp.status_code != 200:
            print(f"[!] Scan failed: {resp.status_code} {resp.text}")
            return

        data = resp.json()
        summary = data["summary"]
        self.last_scan_id = summary["scan_id"]

        print("\n=== SCAN SUMMARY ===")
        self._print_kv("Scan ID", summary["scan_id"])
        self._print_kv("Started", summary["started_at"])
        self._print_kv("Finished", summary["finished_at"])
        self._print_kv("Total files", str(summary["total_files"]))
        self._print_kv("Total matches", str(summary["total_matches"]))
        self._print_kv("Scan time (ms)", str(summary["scan_time_ms"]))
        print("\nFile types:")
        for k, v in summary["file_types"].items():
            print(f"  - {k:<10} {v}")
        print("\nScore buckets:")
        for k, v in summary["score_buckets"].items():
            print(f"  - {k:<10} {v}")
        print()

    def do_show_results(self, arg):
        """
        show_results [status]
        Show per-file hashes and integrity info (new / modified / intact).
        Optional status filter: new | modified | intact
        """
        if not self.target:
            print("Set target first: set target /path/to/folder")
            return

        parts = arg.split()
        status = parts[0] if parts else None

        payload = {
            "root_path": self.target,
            "case_id": self.case_id,
            "assessed_by": self.assessed_by,
            "mode": self.mode,
            "scan_type": self.scan_type,
        }
        params = {}
        if status:
            params["status"] = status

        resp = requests.post(f"{API_BASE}/scan/filter", params=params, json=payload)
        if resp.status_code != 200:
            print(f"[!] Filter scan failed: {resp.status_code} {resp.text}")
            return

        items = resp.json()
        print(f"\n=== RESULTS (status={status or 'all'}) ===")
        header = f"{'STATUS':<8} {'RISK':<18} {'SCORE':>6}  PATH"
        print(header)
        print("-" * len(header))
        for m in items:
            print(f"{m['status']:<8} {m['risk_level']:<18} {m['score']:>6.1f}  {m['file_path']}")
        print()

    # ====== REAL vs TAMPERED FOLDER COMPARE (by rel path) ======

    def do_compare(self, arg):
        """
        compare <real_folder> <tampered_folder>
        Compare two folders as evidence: real vs tampered (by relative path).
        Uses SHA256 + ssdeep + pHash (where available) to find:
          - only_in_real
          - only_in_tampered
          - modified_in_tampered
        Also shows camera + editor side-by-side for modified pairs.
        """
        parts = arg.split()
        if len(parts) != 2:
            print("Usage: compare <real_folder> <tampered_folder>")
            return

        real_root, tamp_root = parts[0], parts[1]

        def scan_folder(root_path: str):
            payload = {
                "root_path": root_path,
                "case_id": self.case_id,
                "assessed_by": self.assessed_by,
                "mode": self.mode,
                "scan_type": self.scan_type,
            }
            resp = requests.post(f"{API_BASE}/scan/filter", json=payload)
            if resp.status_code != 200:
                print(f"[!] Scan failed for {root_path}: {resp.status_code} {resp.text}")
                return []
            return resp.json()

        print(f"\n[+] Scanning REAL folder    : {real_root}")
        real_items = scan_folder(real_root)
        if not real_items:
            print("[!] No results for REAL folder (or scan failed).")
            return

        print(f"[+] Scanning TAMPERED folder: {tamp_root}")
        tamp_items = scan_folder(tamp_root)
        if not tamp_items:
            print("[!] No results for TAMPERED folder (or scan failed).")
            return

        def rel(path, root):
            try:
                return os.path.relpath(path, root)
            except ValueError:
                return path

        real_by_rel = {}
        tamp_by_rel = {}

        for m in real_items:
            p = m.get("file_path") or ""
            r = rel(p, real_root)
            real_by_rel[r] = m

        for m in tamp_items:
            p = m.get("file_path") or ""
            r = rel(p, tamp_root)
            tamp_by_rel[r] = m

        all_rel = sorted(set(real_by_rel.keys()) | set(tamp_by_rel.keys()))

        only_real = []
        only_tamp = []
        modified = []

        for r in all_rel:
            a = real_by_rel.get(r)
            b = tamp_by_rel.get(r)
            if a and not b:
                only_real.append(a)
            elif b and not a:
                only_tamp.append(b)
            else:
                sha_a = a.get("sha_new")
                sha_b = b.get("sha_new")
                if sha_a != sha_b:
                    fuzz_a = a.get("fuzzy_new")
                    fuzz_b = b.get("fuzzy_new")
                    ph_a = a.get("phash")
                    ph_b = b.get("phash")

                    sim = 0.0
                    dist = None
                    for tm in a.get("top_matches") or []:
                        if tm.get("path") == b.get("file_path"):
                            sim = max(sim, tm.get("similarity", 0.0))
                            if tm.get("type") == "phash":
                                dist = tm.get("phash_distance")
                    for tm in b.get("top_matches") or []:
                        if tm.get("path") == a.get("file_path"):
                            sim = max(sim, tm.get("similarity", 0.0))
                            if tm.get("type") == "phash":
                                dist = tm.get("phash_distance")

                    modified.append(
                        {
                            "rel": r,
                            "real": a,
                            "tamp": b,
                            "sim": sim,
                            "phash_dist": dist,
                            "fuzzy_real": fuzz_a,
                            "fuzzy_tamp": fuzz_b,
                            "phash_real": ph_a,
                            "phash_tamp": ph_b,
                        }
                    )

        print("\n=== ONLY IN REAL (likely removed / missing in tampered) ===")
        for m in only_real:
            print(f"  {rel(m['file_path'], real_root)}")

        print("\n=== ONLY IN TAMPERED (likely newly injected) ===")
        for m in only_tamp:
            print(f"  {rel(m['file_path'], tamp_root)}")

        print("\n=== MODIFIED IN TAMPERED (same rel path, different hash) ===")
        if not modified:
            print("  None")
        else:
            for entry in modified:
                r = entry["rel"]
                sim = entry["sim"]
                d = entry["phash_dist"]
                fr = entry["fuzzy_real"] or "-"
                ft = entry["fuzzy_tamp"] or "-"
                phr = entry["phash_real"] or "-"
                pht = entry["phash_tamp"] or "-"

                md_real = entry["real"].get("clean_metadata") or {}
                md_tamp = entry["tamp"].get("clean_metadata") or {}

                make_r = md_real.get("make") or ""
                model_r = md_real.get("model") or ""
                camera_r = (make_r + " " + model_r).strip() or "-"

                make_t = md_tamp.get("make") or ""
                model_t = md_tamp.get("model") or ""
                camera_t = (make_t + " " + model_t).strip() or "-"

                editor_r = md_real.get("edited_with") or "-"
                editor_t = md_tamp.get("edited_with") or "-"

                if d is not None:
                    extra = f" [phash d={d}]"
                else:
                    extra = ""

                print(f"\n[FILE] {r}")
                print(f"  REAL     : {entry['real']['file_path']}")
                print(f"  TAMPERED : {entry['tamp']['file_path']}")
                print(f"  SHA256   : {entry['real'].get('sha_new')}  vs  {entry['tamp'].get('sha_new')}")
                print(f"  SSDEEP   :")
                print(f"    real   : {fr}")
                print(f"    tamper : {ft}")
                print(f"  PHASH    :")
                print(f"    real   : {phr}")
                print(f"    tamper : {pht}")
                print(f"  CAMERA   : {camera_r}  |  {camera_t}")
                print(f"  EDITOR   : {editor_r}  |  {editor_t}")
                print(f"  SIMILARITY (from API top_matches): {sim:5.1f}%{extra}")

        print("\n[+] Compare complete.\n")

    # ====== SEQUENCE FOLDER COMPARE (by position) ======

    def _fetch_hash_block(self, path: str):
        root = str(Path(path).parent)
        payload = {
            "root_path": root,
            "case_id": self.case_id,
            "assessed_by": self.assessed_by,
            "mode": self.mode,
            "scan_type": self.scan_type,
        }
        resp = requests.post(f"{API_BASE}/scan/filter", json=payload)
        if resp.status_code != 200:
            return None

        items = resp.json()
        for m in items:
            if m.get("file_path") == path:
                return m
        return None

    def _print_pair_block(self, real_m: dict, tamp_m: dict):
        real_path = real_m.get("file_path") or ""
        tamp_path = tamp_m.get("file_path") or ""
        fname = os.path.basename(real_path) or os.path.basename(tamp_path) or "-"

        sha_real = real_m.get("sha_new") or "-"
        sha_tamp = tamp_m.get("sha_new") or "-"

        fuzzy_real = real_m.get("fuzzy_new") or "-"
        fuzzy_tamp = tamp_m.get("fuzzy_new") or "-"

        phash_real = real_m.get("phash") or "-"
        phash_tamp = tamp_m.get("phash") or "-"

        real_status = (real_m.get("status") or "intact").upper()
        tamp_status = (tamp_m.get("status") or "intact").upper()

        # similarity from ssdeep directly
        sim = 0.0
        if fuzzy_real != "-" and fuzzy_tamp != "-":
            try:
                sim = float(ssdeep.compare(fuzzy_real, fuzzy_tamp))
            except Exception:
                sim = 0.0

        md_real = real_m.get("clean_metadata") or {}
        md_tamp = tamp_m.get("clean_metadata") or {}

        origin_real = real_m.get("origin_guess") or "unknown"
        origin_tamp = tamp_m.get("origin_guess") or "unknown"

        make_r = md_real.get("make") or ""
        model_r = md_real.get("model") or ""
        camera_r = (make_r + " " + model_r).strip() or "-"

        make_t = md_tamp.get("make") or ""
        model_t = md_tamp.get("model") or ""
        camera_t = (make_t + " " + model_t).strip() or "-"

        editor_r = md_real.get("edited_with") or "-"
        editor_t = md_tamp.get("edited_with") or "-"

        # metadata ssdeep signatures
        meta_real = md_real.get("meta_ssdeep") or "-"
        meta_tamp = md_tamp.get("meta_ssdeep") or "-"

        print(f"[FILE] {fname}")
        print(f"  REAL     : {real_path}")
        print(f"  TAMPERED : {tamp_path}")
        print(f"  STATUS   : REAL={real_status}  |  TAMPERED={tamp_status}")
        print()
        print("  --- HASHES (CONTENT) ---")
        print("  SHA256   :")
        print(f"    real   : {sha_real}")
        print(f"    tamper : {sha_tamp}")
        print("  SSDEEP   :")
        print(f"    real   : {fuzzy_real}")
        print(f"    tamper : {fuzzy_tamp}")
        print(f"    similarity (ssdeep):   {sim:.1f}%")
        print("  PHASH    :")
        print(f"    real   : {phash_real}")
        print(f"    tamper : {phash_tamp}")
        print()
        print("  --- HASHES (METADATA) ---")
        print(f"    META_SSDEEP real   : {meta_real}")
        print(f"    META_SSDEEP tamper : {meta_tamp}")
        print()
        print("  --- METADATA ---")
        print(f"  ORIGIN   : {origin_real}  |  {origin_tamp}")
        print(f"  CAMERA   : {camera_r}  |  {camera_t}")
        print(f"  EDITOR   : {editor_r}  |  {editor_t}")
        print()
        print("...")

    def do_compare_seq(self, arg):
        """
        compare_seq
        Compare everything in real_folder with tampered_folder by position
        (sorted by filename) and print full hash+metadata block per pair.
        """
        if not self.real_folder or not self.tampered_folder:
            print("Set real_folder and tampered_folder first using 'set'.")
            return

        real_dir = Path(self.real_folder)
        tamp_dir = Path(self.tampered_folder)

        if not real_dir.is_dir():
            print(f"real_folder is not a directory: {real_dir}")
            return
        if not tamp_dir.is_dir():
            print(f"tampered_folder is not a directory: {tamp_dir}")
            return

        real_files = sorted([p for p in real_dir.iterdir() if p.is_file()], key=lambda p: p.name)
        tamp_files = sorted([p for p in tamp_dir.iterdir() if p.is_file()], key=lambda p: p.name)

        if not real_files or not tamp_files:
            print("One of the folders is empty.")
            return

        count = min(len(real_files), len(tamp_files))
        print(f"Comparing {count} pairs (by position).\n")

        for idx in range(count):
            real_path = str(real_files[idx])
            tamp_path = str(tamp_files[idx])

            real_m = self._fetch_hash_block(real_path)
            tamp_m = self._fetch_hash_block(tamp_path)

            if not real_m or not tamp_m:
                print(f"[SKIP] Could not fetch record for pair:\n  {real_path}\n  {tamp_path}\n")
                continue

            self._print_pair_block(real_m, tamp_m)

        if len(real_files) != len(tamp_files):
            print(
                f"Note: different file counts (real={len(real_files)}, "
                f"tampered={len(tamp_files)}); extra files not compared."
            )

    # ====== HASH / SIMILAR / METADATA ======

    def do_show_hash(self, arg):
        """
        show_hash [status]
        Show SHA256 + ssdeep + pHash (new/old/initial if available) for files.
        Optional status filter: new | modified | intact
        """
        if not self.target:
            print("Set target first: set target /path/to/folder")
            return

        parts = arg.split()
        status = parts[0] if parts else None

        payload = {
            "root_path": self.target,
            "case_id": self.case_id,
            "assessed_by": self.assessed_by,
            "mode": self.mode,
            "scan_type": self.scan_type,
        }
        params = {}
        if status:
            params["status"] = status

        resp = requests.post(f"{API_BASE}/scan/filter", params=params, json=payload)
        if resp.status_code != 200:
            print(f"[!] Filter scan failed: {resp.status_code} {resp.text}")
            return

        items = resp.json()

        global_pairs = []
        for m in items:
            src = m.get("file_path") or ""
            for tm in m.get("top_matches") or []:
                dst = tm.get("path", "")
                sim = tm.get("similarity", 0.0)
                if not src or not dst:
                    continue
                key = tuple(sorted([src, dst]))
                global_pairs.append((sim, key))

        pair_best = {}
        for sim, key in global_pairs:
            if key not in pair_best or sim > pair_best[key]:
                pair_best[key] = sim

        sorted_pairs = sorted(
            [(sim, a, b) for (a, b), sim in pair_best.items()],
            key=lambda x: x[0],
            reverse=True,
        )

        print(f"\n=== HASHES (status={status or 'all'}) ===")

        if sorted_pairs:
            print("\nTOP MATCHES:")
            for sim, a, b in sorted_pairs[:10]:
                print(f"  {sim:5.1f}%  {a}  <->  {b}")
            print("-" * 60)

        for m in items:
            st = (m.get("status") or "").upper()
            path = m.get("file_path") or ""
            print(f"\n[{st}] {path}")

            fuzzy_new = m.get("fuzzy_new") or "-"
            fuzzy_old = m.get("fuzzy_old")
            fuzzy_initial = m.get("fuzzy_initial")

            print(f"  SSDEEP (new)    : {fuzzy_new}")
            if fuzzy_old:
                print(f"  SSDEEP (old)    : {fuzzy_old}")
            if fuzzy_initial:
                print(f"  SSDEEP (initial): {fuzzy_initial}")

            sha_new = m.get("sha_new") or "-"
            sha_old = m.get("sha_old")
            sha_initial = m.get("sha_initial")

            print(f"  SHA256 (new)    : {sha_new}")
            if sha_old:
                print(f"  SHA256 (old)    : {sha_old}")
            if sha_initial:
                print(f"  SHA256 (initial): {sha_initial}")

            phash = m.get("phash")
            phash_old = m.get("phash_old")
            phash_initial = m.get("phash_initial")

            if phash or phash_old or phash_initial:
                print(f"  PHASH  (new)    : {phash or '-'}")
                if phash_old:
                    print(f"  PHASH  (old)    : {phash_old}")
                if phash_initial:
                    print(f"  PHASH  (initial): {phash_initial}")

        print()

    def do_show_similar(self, arg):
        """
        show_similar
        Show only top similar file pairs (ssdeep + pHash), without full hash dump.
        """
        if not self.target:
            print("Set target first: set target /path/to/folder")
            return

        payload = {
            "root_path": self.target,
            "case_id": self.case_id,
            "assessed_by": self.assessed_by,
            "mode": self.mode,
            "scan_type": self.scan_type,
        }

        resp = requests.post(f"{API_BASE}/scan/filter", json=payload)
        if resp.status_code != 200:
            print(f"[!] Filter scan failed: {resp.status_code} {resp.text}")
            return

        items = resp.json()

        pair_best = {}
        for m in items:
            src = m.get("file_path") or ""
            for tm in m.get("top_matches") or []:
                dst = tm.get("path", "")
                sim = tm.get("similarity", 0.0)
                t = tm.get("type", "ssdeep")
                d = tm.get("phash_distance")

                if not src or not dst:
                    continue
                key = tuple(sorted([src, dst]))
                if key not in pair_best or sim > pair_best[key]["similarity"]:
                    pair_best[key] = {
                        "similarity": sim,
                        "type": t,
                        "distance": d,
                    }

        if not pair_best:
            print("\nNo similar pairs found in this scan.\n")
            return

        rows = sorted(
            [(info["similarity"], a, b, info) for (a, b), info in pair_best.items()],
            key=lambda x: x[0],
            reverse=True,
        )

        print("\n=== SIMILAR FILE PAIRS ===")
        for sim, a, b, info in rows[:20]:
            t = info["type"]
            d = info["distance"]
            if t == "phash" and d is not None:
                extra = f" [phash d={d}]"
            else:
                extra = " [ssdeep]"
            print(f"  {sim:5.1f}%{extra}  {a}  <->  {b}")
        print()

    def do_show_metadata(self, arg):
        """
        show_metadata
        Show metadata + origin_guess for the last filesystem scan.
        """
        if not self.last_scan_id:
            print("No last scan_id. Run a scan first with: run")
            return

        resp = requests.get(f"{API_BASE}/scan/{self.last_scan_id}/metadata-files")
        if resp.status_code != 200:
            print(f"[!] Failed to fetch metadata: {resp.status_code} {resp.text}")
            return

        files = resp.json()

        for f in files:
            cg = f.get("origin_guess") or "-"
            md = f.get("clean_metadata") or {}

            make = md.get("make") or ""
            model = md.get("model") or ""
            camera = (make + " " + model).strip() or "-"

            software = md.get("software") or "-"
            dt = md.get("datetime") or "-"

            if md and md.get("width") and md.get("height"):
                size = f"{md.get('width')}x{md.get('height')}"
            else:
                size = "-"

            gps_place = f.get("gps_place")
            lat = f.get("gps_lat")
            lon = f.get("gps_lon")
            has_gps = f.get("has_gps")

            if gps_place:
                place = gps_place
            elif lat is not None and lon is not None:
                place = f"{lat:.6f},{lon:.6f}"
            else:
                place = "Y" if has_gps else "N"

            status = f.get("status") or "ok"
            editor = (md.get("edited_with") or "-")
            ai_tool = (md.get("ai_tool") or "-")

            meta_sig = md.get("meta_ssdeep") or "-"

            print("=== METADATA ===")
            print(f"STATUS     : {status}")
            print(f"ORIGIN     : {cg}")
            print(f"CAMERA     : {camera}")
            print(f"DATE & TIME: {dt}")
            print(f"PLACE      : {place}")
            print(f"SOFTWARE   : {software}")
            print(f"EDITOR     : {editor}")
            print(f"AI TOOL    : {ai_tool}")
            print(f"SIZE       : {size}")
            print(f"META_SSDEEP: {meta_sig}")
            print(f"PATH       : {f['file_path']}")
            print()

    def do_show_full_metadata(self, arg):
        """
        show_full_metadata
        Dump full EXIF/XMP/IPTC metadata (raw ExifTool JSON) for the last filesystem scan,
        if the API exposes a 'meta_full' field; otherwise just warn.
        """
        if not self.last_scan_id:
            print("No last scan_id. Run a scan first with: run")
            return

        resp = requests.get(f"{API_BASE}/scan/{self.last_scan_id}/metadata-files")
        if resp.status_code != 200:
            print(f"[!] Failed to fetch metadata: {resp.status_code} {resp.text}")
            return

        files = resp.json()

        found_any = False
        for f in files:
            path = f.get("file_path") or "-"
            meta_full = f.get("meta_full")

            if not meta_full:
                continue

            found_any = True
            print("========================================")
            print(f"FILE: {path}")
            print("---- FULL METADATA (EXIF/XMP/IPTC/etc) ----")
            try:
                print(json.dumps(meta_full, indent=2, sort_keys=True))
            except Exception:
                print(str(meta_full))
            print()

        if not found_any:
            print("No 'meta_full' field in API response; backend is not exposing full metadata yet.")

    # ====== EXIT ======

    def do_exit(self, arg):
        print("Bye.")
        return True

    def do_EOF(self, arg):
        print()
        return True


if __name__ == "__main__":
    shell = ChmxShell()
    shell.cmdloop_with_ctrlc()
