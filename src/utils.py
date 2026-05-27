import json
import socket
import subprocess

from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class HostInfo:
    ifname: str
    netAddress: str
    prefixlen: int
    phyAddress: Optional[str]
    hostname: str

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

def getHostInfo() -> HostInfo:
    names = _getInterfaceNames()
    try:
        i = names.index("lo")
        names.pop(i)
    except ValueError:
        pass
    _if = names[0]
    
    netInfo = _getNetAddress(_if)
    netInfo["hostname"] = _getHostname()
    netInfo["netAddress"] = netInfo["addr_info"][0]["local"]
    netInfo["prefixlen"] = netInfo["addr_info"][0]["prefixlen"]
    del netInfo["addr_info"]
    del netInfo["operstate"]
    mac = _getPhysicalAddress(_if)
    if mac:
        netInfo["phyAddress"] = mac
    return HostInfo(**netInfo)
    
def shutdown():
    subprocess.run(["systemctl", "poweroff"])
