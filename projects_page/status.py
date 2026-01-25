from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from excel_cache import load_headers_cache, save_headers_cache
from projects import project_mapping_key
from wbs_app.extract_wbs_json_calamine import (
    ASSIGN_REQUIRED_FIELDS,
    SUMMARY_REQUIRED_FIELDS,
    get_table_headers,
    suggest_column_mapping,
)


def file_cache_key(path: str | None) -> tuple[float, int] | None:
    if not path:
        return None
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return (stat.st_mtime, stat.st_size)


def mapping_cache_key(mapping: dict | None) -> str:
    if not mapping:
        return ""
    try:
        import json

        return json.dumps(mapping, sort_keys=True, separators=(",", ":"))
    except Exception:
        return str(mapping)


@st.cache_data(show_spinner=False)
def cached_table_headers(
    file_path: str,
    file_key: tuple[float, int] | None,
    table_type: str,
    mapping_key: str,
    mapping: dict[str, dict[str, str]] | None,
):
    _ = file_key
    _ = mapping_key
    return get_table_headers(
        file_path,
        table_type,
        column_mapping=mapping,
    )


def file_exists(path_value: str | None) -> bool:
    if not path_value:
        return False
    try:
        return Path(path_value).exists()
    except OSError:
        return False


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def format_updated(value: str | None) -> str:
    parsed = parse_dt(value)
    if parsed is None:
        return value or "--"
    return parsed.strftime("%b %d, %Y")


def missing_required_fields(
    headers: list[object] | None,
    table_type: str,
    mapping: dict[str, dict[str, str]],
) -> list[str]:
    required_fields = SUMMARY_REQUIRED_FIELDS if table_type == "activity_summary" else ASSIGN_REQUIRED_FIELDS
    if not headers:
        return list(required_fields)

    header_list = [str(h).strip() for h in headers if str(h or "").strip()]
    suggested = suggest_column_mapping(headers, table_type)
    table_mapping = mapping.get(table_type, {})
    missing: list[str] = []

    for field in required_fields:
        mapped = table_mapping.get(field)
        if mapped and mapped in header_list:
            continue
        if field in suggested:
            continue
        missing.append(field)

    return missing


def project_status(project: dict) -> tuple[str, str, str | None]:
    file_path = project.get("file_path")
    if not file_exists(file_path):
        return "Needs upload", "warn", None

    project_id = project.get("id")
    file_key = project.get("file_key")
    mapping_key = project.get("mapping_key")
    expected_key = project_mapping_key(project_id, file_key)
    if expected_key and mapping_key and mapping_key != expected_key:
        return "Needs mapping (Stale)", "warn", "Mapping is for a different upload."

    mapping = project.get("mapping")
    mapping = mapping if isinstance(mapping, dict) else {}

    try:
        persisted = load_headers_cache(file_path, mapping)
        if persisted:
            summary_headers = persisted.get("summary_headers")
            assign_headers = persisted.get("assign_headers")
        else:
            fk = file_cache_key(file_path)
            mk = mapping_cache_key(mapping)

            summary_headers = cached_table_headers(
                file_path,
                fk,
                "activity_summary",
                mk,
                mapping,
            )
            assign_headers = cached_table_headers(
                file_path,
                fk,
                "resource_assignments",
                mk,
                mapping,
            )

            try:
                save_headers_cache(
                    file_path,
                    mapping,
                    summary_headers=summary_headers,
                    assign_headers=assign_headers,
                )
            except Exception:
                pass
    except Exception:
        return "File error", "warn", "Unreadable Excel file."

    summary_missing = missing_required_fields(
        summary_headers[0] if summary_headers else None,
        "activity_summary",
        mapping,
    )
    if summary_missing:
        return "Needs mapping (Summary)", "warn", None

    assign_missing = missing_required_fields(
        assign_headers[0] if assign_headers else None,
        "resource_assignments",
        mapping,
    )
    if assign_missing:
        return "Ready (Dashboard)", "ok", "Schedule needs assignments."

    return "Ready (Schedule)", "ok", None


def project_action(status_label: str) -> str:
    if status_label == "Needs upload":
        return "Upload data"
    if status_label.startswith("Needs mapping"):
        return "Finish mapping"
    if status_label == "Ready (Dashboard)":
        return "Open dashboard"
    if status_label == "File error":
        return "Re-upload file"
    return "Open project"


def sort_projects(items: list[dict], sort_mode: str) -> list[dict]:
    if sort_mode == "Name A-Z":
        return sorted(items, key=lambda p: (p.get("name") or "").lower())
    if sort_mode == "Created (newest)":
        return sorted(
            items,
            key=lambda p: parse_dt(p.get("created_at")) or datetime.min,
            reverse=True,
        )
    return sorted(
        items,
        key=lambda p: parse_dt(p.get("updated_at")) or datetime.min,
        reverse=True,
    )
