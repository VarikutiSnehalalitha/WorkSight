"""ONVIF WS-Discovery LAN Camera Scanner.

Probes multicast 239.255.255.250:3702 for ONVIF Profile S / NetworkVideoTransmitter
cameras on the local network. When running in isolated/dev networks without
physical ONVIF cameras, clearly reports zero physical devices found (and optionally
lists labeled simulated discovery examples when ALLOW_SIMULATED_FEEDS=true).
"""

import re
import socket
import uuid
from typing import Dict, List
from urllib.parse import urlparse

from app.core.config import get_settings

WS_DISCOVERY_MULTICAST = "239.255.255.250"
WS_DISCOVERY_PORT = 3702

PROBE_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
            xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
            xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
            xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
  <e:Header>
    <w:MessageID>uuid:{msg_id}</w:MessageID>
    <w:To e:mustUnderstand="true">urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
    <w:Action a:mustUnderstand="true" xmlns:a="http://schemas.xmlsoap.org/ws/2004/08/addressing">
      http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe
    </w:Action>
  </e:Header>
  <e:Body>
    <d:Probe>
      <d:Types>dn:NetworkVideoTransmitter</d:Types>
    </d:Probe>
  </e:Body>
</e:Envelope>
"""


def discover_onvif_cameras(timeout_seconds: float = 1.5) -> List[Dict]:
    """Perform a non-blocking ONVIF WS-Discovery multicast scan on the local subnet."""
    discovered: List[Dict] = []
    seen_ips = set()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(timeout_seconds)
    try:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        payload = PROBE_TEMPLATE.format(msg_id=str(uuid.uuid4())).encode("utf-8")
        sock.sendto(payload, (WS_DISCOVERY_MULTICAST, WS_DISCOVERY_PORT))

        while True:
            try:
                data, addr = sock.recvfrom(65535)
                xml_text = data.decode("utf-8", errors="ignore")
                xaddrs_match = re.search(r"<[^:>]*XAddrs[^>]*>([^<]+)</", xml_text)
                service_url = (
                    xaddrs_match.group(1).strip().split()[0]
                    if xaddrs_match
                    else f"http://{addr[0]}:80/onvif/device_service"
                )
                parsed = urlparse(service_url)
                ip = parsed.hostname or addr[0]
                if ip in seen_ips:
                    continue
                seen_ips.add(ip)
                discovered.append(
                    {
                        "name": f"ONVIF Camera ({ip})",
                        "ip_address": ip,
                        "port": parsed.port or 80,
                        "manufacturer": "ONVIF Compatible",
                        "model": "Profile S NVT",
                        "onvif_service_url": service_url,
                        "is_simulated_discovery": False,
                    }
                )
            except socket.timeout:
                break
    except OSError:
        # Multicast may be unavailable in restricted sandboxes or cloud VPCs
        pass
    finally:
        sock.close()

    settings = get_settings()
    if not discovered and settings.ALLOW_SIMULATED_FEEDS:
        # Clearly labeled simulated discovery samples for development/demo testing
        return [
            {
                "name": "Simulated ONVIF Demo — North Lobby Dome",
                "ip_address": "192.168.100.21",
                "port": 554,
                "manufacturer": "WorkSight Dev Simulator",
                "model": "WS-SIM-ONVIF-S1 (SIMULATED)",
                "onvif_service_url": "simulated://onvif/192.168.100.21",
                "is_simulated_discovery": True,
            },
            {
                "name": "Simulated ONVIF Demo — East Wing Corridor",
                "ip_address": "192.168.100.22",
                "port": 554,
                "manufacturer": "WorkSight Dev Simulator",
                "model": "WS-SIM-ONVIF-S2 (SIMULATED)",
                "onvif_service_url": "simulated://onvif/192.168.100.22",
                "is_simulated_discovery": True,
            },
        ]

    return discovered
