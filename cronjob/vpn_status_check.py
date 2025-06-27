#!/usr/bin/env python3
import subprocess
from pathlib import Path

IP_FILE = "/home/ubuntu/vpn_check_ip"
STATUS_FILE = "/tmp/upv_vpn_aveiro_status"

PING_COUNT = 5
TIMEOUT_SEC = 3

def read_target_ip() -> str:
    try:
        with open(IP_FILE, "r") as f:
            return f.readline().strip()
    except Exception:
        print("No File with IP")
        return None

def check_vpn_status(ip: str) -> str:
    try:
        result = subprocess.run(
            ["ping", "-c", str(PING_COUNT), "-W", str(TIMEOUT_SEC), ip],
            capture_output=True,
            text=True
        )
        output = result.stdout
        print("Output:", output)
        # Find the summary line like: '5 packets transmitted, 5 received, 0% packet loss, time 4006ms'
        for line in output.splitlines():
            if "packets transmitted" in line:
                parts = line.split(",")
                transmitted = int(parts[0].split()[0])
                received = int(parts[1].split()[0])
                if received >= (PING_COUNT // 2 + 1):
                    return "OK"
                else:
                    return "NOT_OK"
        return "UNCLEAR_STATUS"
    except Exception:
        return "UNCLEAR_STATUS"

def write_status(status: str):
    try:
        with open(STATUS_FILE, "w") as f:
            f.write(status + "\n")
    except Exception:
        pass

def main():
    ip = read_target_ip()
    if not ip:
        write_status("UNCLEAR_STATUS")
        return
    status = check_vpn_status(ip)
    write_status(status)

if __name__ == "__main__":
    main()
