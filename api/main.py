from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse
import os
import subprocess
from starlette.status import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from typing import Dict

app = FastAPI()
security = HTTPBasic()

USERNAME = os.getenv("API_USERNAME", "admin")
PASSWORD = os.getenv("API_PASSWORD", "secret")

VPN_SERVICE_NAME = "openvpn@upv_vpn_aveiro"
VPN_STATUS_FILE = "/tmp/upv_vpn_aveiro_status"

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != USERNAME or credentials.password != PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

@app.post("/vpn/start")
def start_vpn(credentials: HTTPBasicCredentials = Depends(verify_credentials)):
    try:
        subprocess.run(["sudo", "systemctl", "start", VPN_SERVICE_NAME], check=True)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "VPN started successfully"})
    except subprocess.CalledProcessError:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"error": "Failed to start VPN"})

@app.post("/vpn/stop")
def stop_vpn(credentials: HTTPBasicCredentials = Depends(verify_credentials)):
    try:
        subprocess.run(["sudo", "systemctl", "stop", VPN_SERVICE_NAME], check=True)
        try:
            with open(VPN_STATUS_FILE, "w") as f:
                f.write("NOT_OK" + "\n")
        except Exception:
            pass
        
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "VPN stopped successfully"})
    except subprocess.CalledProcessError:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"error": "Failed to stop VPN"})

@app.get("/vpn/status")
def vpn_status():
    try:
        with open(VPN_STATUS_FILE, "r") as f:
            status_line = f.readline().strip()
            if status_line == "OK":
                return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "The VPN is active"})
            else:
                return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "The VPN is not active"})
    except Exception:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "The VPN is not active"})