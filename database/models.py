"""
Dataclass models matching the SQLite schema.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Account:
    id: Optional[int] = None
    username: str = ""
    cookies_json: str = ""
    proxy: Optional[str] = None
    status: str = "idle"
    schedule_id: int = 1
    start_date: str = ""
    current_day: int = 1
    notes: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Schedule:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    schedule_json: str = ""
    created_at: Optional[str] = None


@dataclass
class Target:
    id: Optional[int] = None
    username: str = ""
    url: str = ""
    priority: int = 1
    active: int = 1
    created_at: Optional[str] = None


@dataclass
class ActivityLog:
    id: Optional[int] = None
    account_id: int = 0
    action_type: str = ""
    target_username: Optional[str] = None
    target_url: Optional[str] = None
    status: str = ""
    error_message: Optional[str] = None
    executed_at: Optional[str] = None


@dataclass
class Setting:
    key: str = ""
    value: str = ""
