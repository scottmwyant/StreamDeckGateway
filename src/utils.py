import json
import socket
import subprocess

from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class HostInfo:
    ifname: str
    netAddress: str
    prefixlen: int
    phyAddress: Optional[str]
    hostname: str
    model: str

def _getHostname() -> str:
    return socket.gethostname()

def _getInterfaceNames() -> List[str]:
    result: subprocess.CompletedProcess = subprocess.run(
        ["ls /sys/class/net"],
        capture_output=True,
        text=True,
        shell=True
    )
    if result.stdout:
        return (result.stdout.strip()).split("\n")
    return list()
        
def _getPhysicalAddress(ifName) -> Dict | None:
    result: subprocess.CompletedProcess = subprocess.run(
        ["ip", "-4", "-br", "-j", "link", "show", ifName],
        capture_output=True,
        text=True
    )
    if result.stdout:
        return (json.loads(result.stdout))[0]["address"]
    
def _getNetAddress(ifName) -> Dict:
    result: subprocess.CompletedProcess = subprocess.run(
        ["ip", "-4", "-br", "-j", "address", "show", ifName],
        capture_output=True,
        text=True
    )
    if result.stdout:
        return (json.loads(result.stdout))[0]
    raise RuntimeError(f"Failed to get network address for interface {ifName}")

def _getHardwareModel() -> str:
    return  Path("/proc/device-tree/model") \
            .read_text().rstrip("\x00")

def _getSystemUptime() -> float:
    return int(float(Path("/proc/uptime").read_text().split()[0]))

def getHostInfo() -> HostInfo:
    names = _getInterfaceNames()
    try:
        i = names.index("lo")
        names.pop(i)
    except ValueError:
        pass
    _if = names[0]
    
    info = _getNetAddress(_if)
    info["hostname"] = _getHostname()
    info["model"] = _getHardwareModel()
    info["netAddress"] = info["addr_info"][0]["local"]
    info["prefixlen"] = info["addr_info"][0]["prefixlen"]
    del info["addr_info"]
    del info["operstate"]
    mac = _getPhysicalAddress(_if)
    if mac:
        info["phyAddress"] = mac
    return HostInfo(**info)
    
def shutdown():
    subprocess.run(["systemctl", "poweroff"])
