"""Performance and benchmark measurement script for Spotify Local FLAC."""

import os
import sys
import time
import urllib.request
import json
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def get_process_metrics(pid: int):
    """Read CPU and RSS memory usage from /proc/[pid]/status and /proc/[pid]/stat."""
    with open(f"/proc/{pid}/status", "r") as f:
        status_text = f.read()

    rss_kb = 0
    for line in status_text.splitlines():
        if line.startswith("VmRSS:"):
            rss_kb = int(line.split()[1])
            break

    with open(f"/proc/{pid}/stat", "r") as f:
        stat_parts = f.read().split()
        utime = int(stat_parts[13])
        stime = int(stat_parts[14])

    return rss_kb / 1024.0, (utime + stime)


def measure():
    print("==========================================================")
    print("  Spotify Local FLAC - Performance Benchmarks")
    print("==========================================================")

    token_file = os.path.expanduser("~/.config/spotify-local-flac/token")
    with open(token_file, "r") as f:
        token = f.read().strip()

    # 1. Measure Startup Time
    print("\n[1] Measuring Startup Time...")
    start_t = time.perf_counter()
    proc = subprocess.Popen(
        [sys.executable, "-c", "from server.config import Config; from server.db import Database; c = Config(); d = Database(c.database_path)"],
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    )
    proc.wait()
    startup_ms = (time.perf_counter() - start_t) * 1000.0
    print(f"  Startup & DB Connection Time: {startup_ms:.2f} ms")

    # 2. Get Service PID
    output = subprocess.check_output(["systemctl", "--user", "show", "--property", "MainPID", "spotify-local-flac.service"]).decode().strip()
    pid = int(output.split("=")[1])
    print(f"\n[2] Found running companion service PID: {pid}")

    # 3. Measure Idle Memory & CPU
    print("\n[3] Measuring Idle Resource Usage (5s window)...")
    rss_idle, t1 = get_process_metrics(pid)
    time_start = time.perf_counter()
    time.sleep(5.0)
    rss_idle_2, t2 = get_process_metrics(pid)
    time_elapsed = time.perf_counter() - time_start

    clock_ticks = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
    cpu_idle_pct = ((t2 - t1) / clock_ticks) / time_elapsed * 100.0

    print(f"  Idle Memory (RSS): {rss_idle_2:.2f} MB")
    print(f"  Idle CPU Usage:    {cpu_idle_pct:.2f}%")

    # 4. Measure Scan Speed
    print("\n[4] Measuring Library Scan Speed (Incremental on 1,879 tracks)...")
    req = urllib.request.Request("http://127.0.0.1:18492/api/scan", method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        pass

    scan_start = time.perf_counter()
    while True:
        req = urllib.request.Request("http://127.0.0.1:18492/api/status")
        req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not data["scanner"]["is_scanning"]:
                break
        time.sleep(0.2)
    scan_elapsed = time.perf_counter() - scan_start
    total_tracks = data["stats"]["total_tracks"]
    rate = total_tracks / max(0.01, scan_elapsed)
    print(f"  Scanned {total_tracks} tracks in {scan_elapsed:.2f}s ({rate:.0f} tracks/sec)")

    # 5. Measure Playback CPU & Throughput during FLAC streaming
    print("\n[5] Measuring Resource Usage during FLAC Streaming...")
    req = urllib.request.Request("http://127.0.0.1:18492/api/tracks?limit=50")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        tracks = json.loads(resp.read().decode("utf-8"))["tracks"]

    flac_track = next((t for t in tracks if t["codec"] == "FLAC"), None)
    if not flac_track:
        print("  No FLAC track found for streaming benchmark.")
        return

    print(f"  Selected FLAC: {flac_track['title']} ({flac_track['sample_rate']}Hz, {flac_track['bit_depth']}-bit, {flac_track['file_size'] / (1024*1024):.2f} MB)")

    rss_before_play, pt1 = get_process_metrics(pid)
    stream_url = f"http://127.0.0.1:18492/api/stream/{flac_track['id']}"
    play_start = time.perf_counter()
    bytes_streamed = 0

    # Simulate realistic audio streaming: read in 64KB chunks
    stream_req = urllib.request.Request(stream_url)
    stream_req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(stream_req) as resp:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            bytes_streamed += len(chunk)
            time.sleep(0.005)  # Simulate network consumption
            if time.perf_counter() - play_start >= 5.0:
                break

    play_elapsed = time.perf_counter() - play_start
    rss_play, pt2 = get_process_metrics(pid)
    cpu_play_pct = ((pt2 - pt1) / clock_ticks) / play_elapsed * 100.0

    print(f"  Active Streaming Memory (RSS): {rss_play:.2f} MB")
    print(f"  Streaming CPU Usage:           {cpu_play_pct:.2f}%")
    print(f"  Stream Throughput:             {(bytes_streamed / (1024*1024)) / play_elapsed:.2f} MB/s")

    print("\n==========================================================")
    print("  Benchmark Completed Successfully")
    print("==========================================================")


if __name__ == "__main__":
    measure()
