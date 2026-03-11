"""
config.py — Application-wide configuration and constants.

All settings can be overridden via environment variables or a .env file.
The Config object is a singleton loaded once at import time.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DEFAULT_SESSION_DIR = Path.home() / ".sn_cmdb" / "sessions"
DEFAULT_DB_PATH = Path.cwd() / "cmdb.db"

# ---------------------------------------------------------------------------
# ServiceNow REST API defaults
# ---------------------------------------------------------------------------
SN_TABLE_API_PATH = "/api/now/table"
DEFAULT_PAGE_SIZE = 1000          # records per REST request (max 10 000 for most instances)
MAX_PAGE_SIZE = 10_000

# ---------------------------------------------------------------------------
# Core CMDB tables always included in an "all" download
# ---------------------------------------------------------------------------
CORE_CMDB_TABLES: list[str] = [
    # Base CI
    "cmdb_ci",
    # Infrastructure
    "cmdb_ci_server",
    "cmdb_ci_computer",
    "cmdb_ci_hardware",
    "cmdb_ci_storage_device",
    "cmdb_ci_disk",
    "cmdb_ci_memory",
    "cmdb_ci_processor",
    # Network
    "cmdb_ci_network_adapter",
    "cmdb_ci_ip_address",
    "cmdb_ci_netgear",
    "cmdb_ci_router",
    "cmdb_ci_switch",
    "cmdb_ci_firewall",
    "cmdb_ci_lb",
    # Application / Software
    "cmdb_ci_appl",
    "cmdb_ci_service",
    "cmdb_ci_business_service",
    "cmdb_ci_db_instance",
    "cmdb_ci_db_catalog",
    # Cloud
    "cmdb_ci_cloud_service_account",
    "cmdb_ci_vm_instance",
    # Relationships
    "cmdb_rel_ci",
    "cmdb_rel_type",
    # Metadata / schema
    "sys_db_object",
    "sys_dictionary",
]

# ---------------------------------------------------------------------------
# Pydantic settings model
# ---------------------------------------------------------------------------


class AppConfig(BaseModel):
    """
    Runtime configuration for sn-cmdb.

    Values are read from environment variables (case-insensitive, prefix SN_CMDB_).
    Alternatively supply a .env file in the working directory.

    Environment variables:
        SN_CMDB_INSTANCE_URL   — Base URL of the ServiceNow instance, e.g. https://dev12345.service-now.com
        SN_CMDB_SESSION_DIR    — Directory to store saved Playwright sessions (default: ~/.sn_cmdb/sessions)
        SN_CMDB_DB_PATH        — Path to the SQLite database file (default: ./cmdb.db)
        SN_CMDB_PAGE_SIZE      — Records per API page request (default: 1000, max 10000)
        SN_CMDB_USERNAME       — ServiceNow username for credential-based login fallback
        SN_CMDB_PASSWORD       — ServiceNow password for credential-based login fallback
        SN_CMDB_HEADLESS       — Run browser in headless mode (default: false for login, true for extract)
        SN_CMDB_LOG_LEVEL      — Logging level: DEBUG | INFO | WARNING | ERROR (default: INFO)
    """

    instance_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("SN_CMDB_INSTANCE_URL"),
        description="Base URL of the ServiceNow instance (e.g. https://dev12345.service-now.com)",
    )
    session_dir: Path = Field(
        default_factory=lambda: Path(
            os.getenv("SN_CMDB_SESSION_DIR", str(DEFAULT_SESSION_DIR))
        ),
        description="Directory where Playwright browser sessions are stored",
    )
    db_path: Path = Field(
        default_factory=lambda: Path(
            os.getenv("SN_CMDB_DB_PATH", str(DEFAULT_DB_PATH))
        ),
        description="Path to the SQLite database file",
    )
    page_size: int = Field(
        default_factory=lambda: int(os.getenv("SN_CMDB_PAGE_SIZE", str(DEFAULT_PAGE_SIZE))),
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Number of records fetched per API request",
    )
    username: Optional[str] = Field(
        default_factory=lambda: os.getenv("SN_CMDB_USERNAME"),
        description="ServiceNow username (credential-based login fallback)",
    )
    password: Optional[str] = Field(
        default_factory=lambda: os.getenv("SN_CMDB_PASSWORD"),
        description="ServiceNow password (credential-based login fallback)",
    )
    headless: bool = Field(
        default_factory=lambda: os.getenv("SN_CMDB_HEADLESS", "false").lower() == "true",
        description="Whether to run the browser in headless mode",
    )
    log_level: str = Field(
        default_factory=lambda: os.getenv("SN_CMDB_LOG_LEVEL", "INFO"),
        description="Log level: DEBUG | INFO | WARNING | ERROR",
    )


def load_config() -> AppConfig:
    """Load and return the application configuration singleton."""
    return AppConfig()
