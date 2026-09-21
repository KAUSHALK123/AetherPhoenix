import os
import platform
import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ResolvedCommand:
    command: str
    display_name: str
    description: str
    category: str
    risk_level: str
    platform: str
    is_safe: bool = True
    explanation: Optional[str] = None
    confidence: float = 1.0


class CommandResolverEngine:
    """
    Natural Language to Shell Command Resolver and MCP Service Engine.
    Maps conversational user instructions (e.g. 'chk my ipaddress', 'list processes', 'check disk space')
    to exact, valid, platform-tailored executable commands.
    """

    PROHIBITED_PATTERNS = [
        r"\bformat\s+[a-z]:",
        r"\brm\s+-rf\s+/",
        r"\bdel\s+/[fsq]\s+[a-z]:\\",
        r"\bdrop\s+database\b",
        r"\bwipe\s+disk\b",
        r":(){ :|:& };:",
        r"\bshutdown\s+/[sft]",
    ]

    def __init__(self, target_os: Optional[str] = None):
        self.os_name = target_os or ("windows" if platform.system().lower() == "windows" or os.name == "nt" else "linux")

    @classmethod
    def is_destructive(cls, command: str) -> bool:
        cmd_lower = command.lower()
        for pattern in cls.PROHIBITED_PATTERNS:
            if re.search(pattern, cmd_lower):
                return True
        return False

    @classmethod
    def resolve(cls, query: str, target_os: Optional[str] = None, os_type: Optional[str] = None) -> ResolvedCommand:
        """
        Translates a natural language user query into a safe, valid shell command.
        """
        effective_os = target_os or os_type or ("windows" if platform.system().lower() == "windows" or os.name == "nt" else "linux")
        q = query.strip()
        q_lower = q.lower()
        is_windows = effective_os == "windows"

        # Check for harmful/destructive intentions
        if cls.is_destructive(q):
            return ResolvedCommand(
                command="echo 'Blocked potentially harmful command by security policy'",
                display_name="Security Blocked Action",
                description="Operation blocked due to dangerous command pattern",
                category="SECURITY",
                risk_level="HIGH",
                platform=effective_os,
                is_safe=False,
                explanation="Blocked unsafe or destructive command.",
            )

        # 1. Network & IP Resolution
        if any(w in q_lower for w in ["public ip", "external ip", "wan ip", "ip address", "ipaddress", "my ip", "chk ip", "check ip", "what is my ip", "show ip", "get ip", "network config", "ipconfig", "ifconfig"]) or re.search(r"\bip\b", q_lower):
            if any(w in q_lower for w in ["public", "external", "wan"]):
                cmd = "curl.exe -s https://api.ipify.org" if is_windows else "curl -s https://api.ipify.org"
                return ResolvedCommand(
                    command=cmd,
                    display_name="Check Public IP",
                    description="Retrieve public/WAN IP address from external API",
                    category="NETWORK",
                    risk_level="LOW",
                    platform=effective_os,
                )
            cmd = "ipconfig /all" if is_windows else "ip a"
            return ResolvedCommand(
                command=cmd,
                display_name="Check Network IP Configuration",
                description="Display local network adapter IPv4/IPv6 addresses and configuration",
                category="NETWORK",
                risk_level="LOW",
                platform=effective_os,
            )

        # 2. Ping / Connectivity
        ping_match = re.search(r"(?:ping|test connection to|check reachability of)\s+([a-zA-Z0-9.-]+)", q, re.IGNORECASE)
        if ping_match or "ping" in q_lower:
            host = ping_match.group(1) if ping_match else "8.8.8.8"
            cmd = f"ping -n 4 {host}" if is_windows else f"ping -c 4 {host}"
            return ResolvedCommand(
                command=cmd,
                display_name=f"Ping {host}",
                description=f"Send ICMP echo test packets to {host}",
                category="NETWORK",
                risk_level="LOW",
                platform=effective_os,
            )

        # 3. Active Ports & Listening Sockets
        if any(w in q_lower for w in ["open port", "ports", "listening port", "netstat", "active socket", "network connection"]):
            cmd = "Get-NetTCPConnection -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess" if is_windows else "netstat -tuln"
            return ResolvedCommand(
                command=cmd,
                display_name="Check Open / Listening Ports",
                description="List active network TCP listening connections and bound ports",
                category="NETWORK",
                risk_level="LOW",
                platform=effective_os,
            )

        # 4. Running Processes
        if any(w in q_lower for w in ["running process", "process list", "tasklist", "list process", "what is running", "top process", "cpu usage"]):
            cmd = "Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Id, ProcessName, CPU, WorkingSet" if is_windows else "ps aux --sort=-%cpu | head -n 15"
            return ResolvedCommand(
                command=cmd,
                display_name="List Running Processes",
                description="List active processes sorted by CPU and memory consumption",
                category="PROCESS",
                risk_level="LOW",
                platform=effective_os,
            )

        # 5. Memory / RAM Usage
        if any(w in q_lower for w in ["memory usage", "ram usage", "free memory", "total ram", "check memory", "check ram"]):
            cmd = "Get-CimInstance Win32_OperatingSystem | Select-Object @{Name='TotalGB';Expression={[math]::round($_.TotalVisibleMemorySize/1MB,2)}}, @{Name='FreeGB';Expression={[math]::round($_.FreePhysicalMemory/1MB,2)}}" if is_windows else "free -h"
            return ResolvedCommand(
                command=cmd,
                display_name="Check Memory / RAM Usage",
                description="Inspect total available and free physical RAM capacity",
                category="SYSTEM",
                risk_level="LOW",
                platform=effective_os,
            )

        # 6. Disk Space & Drives
        if any(w in q_lower for w in ["disk space", "free disk", "storage", "drive space", "check disk", "disk usage", "hdd space", "ssd space"]):
            cmd = "Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{Name='UsedGB';Expression={[math]::round($_.Used/1GB,2)}}, @{Name='FreeGB';Expression={[math]::round($_.Free/1GB,2)}}" if is_windows else "df -h"
            return ResolvedCommand(
                command=cmd,
                display_name="Check Disk Storage & Drive Space",
                description="Display all filesystem drives with total used and free space in GB",
                category="DISK",
                risk_level="LOW",
                platform=effective_os,
            )

        # 7. System Info & Uptime
        if any(w in q_lower for w in ["system info", "systeminfo", "os version", "specs", "hardware info", "computer info"]):
            cmd = "Get-ComputerInfo | Select-Object CsName, WindowsProductName, WindowsVersion, CsProcessors, OsTotalVisibleMemorySize" if is_windows else "uname -a"
            return ResolvedCommand(
                command=cmd,
                display_name="Display System Information",
                description="Retrieve hardware and OS version details",
                category="SYSTEM",
                risk_level="LOW",
                platform=effective_os,
            )

        if any(w in q_lower for w in ["uptime", "boot time", "when was pc started", "restart time"]):
            cmd = "(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime" if is_windows else "uptime -p"
            return ResolvedCommand(
                command=cmd,
                display_name="Check System Uptime",
                description="Calculate time elapsed since last operating system boot",
                category="SYSTEM",
                risk_level="LOW",
                platform=effective_os,
            )

        # 8. Environment Variables
        if any(w in q_lower for w in ["env var", "environment variable", "show path", "check path", "printenv", "get-childitem env"]):
            cmd = "Get-ChildItem Env:" if is_windows else "printenv"
            return ResolvedCommand(
                command=cmd,
                display_name="List Environment Variables",
                description="List active environment variables and execution paths",
                category="SYSTEM",
                risk_level="LOW",
                platform=effective_os,
            )

        # 9. Find Large Files
        if any(w in q_lower for w in ["large file", "biggest file", "find large", "huge file"]):
            cmd = "Get-ChildItem -File -Recurse -ErrorAction SilentlyContinue | Sort-Object Length -Descending | Select-Object -First 10 Name, @{Name='SizeMB';Expression={[math]::round($_.Length/1MB,2)}}, FullName" if is_windows else "find . -type f -exec ls -s {} + | sort -n -r | head -10"
            return ResolvedCommand(
                command=cmd,
                display_name="Find Top 10 Largest Files",
                description="Recursively scan current directory and list top 10 largest files",
                category="DISK",
                risk_level="LOW",
                platform=effective_os,
            )

        # 10. Direct / explicit command fallback
        cleaned_cmd = q
        for prefix in ["run command", "execute command", "run", "execute", "exec", "cmd"]:
            if cleaned_cmd.lower().startswith(prefix):
                cleaned_cmd = cleaned_cmd[len(prefix):].strip(" :")
                break

        return ResolvedCommand(
            command=cleaned_cmd if cleaned_cmd else "Get-Location",
            display_name=f"Execute: {cleaned_cmd or 'Get-Location'}",
            description=f"Execute terminal command '{cleaned_cmd}'",
            category="SHELL",
            risk_level="LOW",
            platform=effective_os,
        )

    @classmethod
    def get_catalog(cls) -> List[Dict[str, str]]:
        """Returns standard MCP Command Catalog for AI capability registration."""
        return [
            {"intent": "check_network_ip", "sample_prompt": "chk my ipaddress", "windows_cmd": "ipconfig /all", "linux_cmd": "ip a", "category": "NETWORK"},
            {"intent": "check_public_ip", "sample_prompt": "what is my public ip", "windows_cmd": "curl.exe -s https://api.ipify.org", "linux_cmd": "curl -s https://api.ipify.org", "category": "NETWORK"},
            {"intent": "check_disk_space", "sample_prompt": "check disk space", "windows_cmd": "Get-PSDrive -PSProvider FileSystem", "linux_cmd": "df -h", "category": "DISK"},
            {"intent": "list_processes", "sample_prompt": "list running processes", "windows_cmd": "Get-Process | Sort-Object CPU -Descending", "linux_cmd": "ps aux", "category": "PROCESS"},
            {"intent": "check_memory", "sample_prompt": "check ram usage", "windows_cmd": "Get-CimInstance Win32_OperatingSystem", "linux_cmd": "free -h", "category": "SYSTEM"},
            {"intent": "check_open_ports", "sample_prompt": "show listening ports", "windows_cmd": "Get-NetTCPConnection -State Listen", "linux_cmd": "netstat -tuln", "category": "NETWORK"},
            {"intent": "system_uptime", "sample_prompt": "system uptime", "windows_cmd": "(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime", "linux_cmd": "uptime -p", "category": "SYSTEM"},
            {"intent": "find_large_files", "sample_prompt": "find large files", "windows_cmd": "Get-ChildItem -File -Recurse | Sort-Object Length -Descending", "linux_cmd": "find . -type f -exec ls -s {} +", "category": "DISK"},
        ]
