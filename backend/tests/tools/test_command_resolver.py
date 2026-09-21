import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.tools.terminal.command_resolver import CommandResolverEngine, ResolvedCommand


class TestCommandResolverEngine:
    """Test suite for Natural Language Shell Command Resolver Engine."""

    def test_resolve_ip_address_windows(self):
        result = CommandResolverEngine.resolve("chk my ipaddress", os_type="windows")
        assert isinstance(result, ResolvedCommand)
        assert result.category == "NETWORK"
        assert result.command == "ipconfig /all"
        assert result.is_safe is True
        assert result.confidence >= 0.9

    def test_resolve_ip_address_linux(self):
        result = CommandResolverEngine.resolve("check my ip address", os_type="linux")
        assert result.category == "NETWORK"
        assert "ip a" in result.command or "ifconfig" in result.command
        assert result.is_safe is True

    def test_resolve_public_ip(self):
        result = CommandResolverEngine.resolve("what is my public ip", os_type="windows")
        assert result.category == "NETWORK"
        assert "ipify.org" in result.command or "icanhazip.com" in result.command
        assert result.is_safe is True

    def test_resolve_disk_space(self):
        result = CommandResolverEngine.resolve("check available disk space", os_type="windows")
        assert result.category == "DISK"
        assert "Get-PSDrive" in result.command or "wmic" in result.command
        assert result.is_safe is True

    def test_resolve_processes(self):
        result = CommandResolverEngine.resolve("list top running processes", os_type="windows")
        assert result.category == "PROCESS"
        assert "Get-Process" in result.command or "tasklist" in result.command
        assert result.is_safe is True

    def test_resolve_memory(self):
        result = CommandResolverEngine.resolve("check memory usage and ram", os_type="windows")
        assert result.category == "SYSTEM"
        assert "Win32_OperatingSystem" in result.command
        assert result.is_safe is True

    def test_resolve_ports(self):
        result = CommandResolverEngine.resolve("show listening ports", os_type="windows")
        assert result.category in ["NETWORK", "PORTS"]
        assert "Get-NetTCPConnection" in result.command or "netstat" in result.command
        assert result.is_safe is True

    def test_resolve_ping_target(self):
        result = CommandResolverEngine.resolve("ping 8.8.8.8", os_type="windows")
        assert result.category == "NETWORK"
        assert "ping" in result.command
        assert "8.8.8.8" in result.command

    def test_blocked_dangerous_command(self):
        result = CommandResolverEngine.resolve("rm -rf / --no-preserve-root", os_type="linux")
        assert result.is_safe is False
        assert "Blocked" in result.display_name or "Security" in result.display_name


class TestMCPCommandEndpoints:
    """Test suite for MCP Command Resolver Endpoints."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_mcp_catalog_endpoint(self, client):
        response = client.get("/api/v1/mcp/commands/catalog")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "NETWORK" in data["categories"]
        assert "PROCESS" in data["categories"]
        assert "DISK" in data["categories"]

    def test_mcp_resolve_endpoint(self, client):
        response = client.post(
            "/api/v1/mcp/commands/resolve",
            json={"prompt": "chk my ipaddress", "os_type": "windows"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "NETWORK"
        assert data["command"] == "ipconfig /all"
        assert data["is_safe"] is True
