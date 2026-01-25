from __future__ import annotations

from typing import Any

import streamlit as st

ROOT_ACTIVITY_ALL = "__all__"


def _truncate_label(text: str, max_len: int = 44) -> str:
    if not text:
        return ""
    text = str(text)
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3] + "..."


def build_activity_filter_sidebar(
    activity_rows: list[dict],
    *,
    sidebar: Any | None = None,
    root_key: str = "activity_root_id",
    start_depth_key: str = "activity_start_depth",
    max_depth_key: str = "activity_depth_filter",
    fallback_max_depth_key: str | None = None,
    label_max_len: int = 44,
) -> dict | None:
    if not activity_rows:
        return None
    sidebar = sidebar or st.sidebar

    if fallback_max_depth_key and max_depth_key not in st.session_state:
        if fallback_max_depth_key in st.session_state:
            st.session_state[max_depth_key] = st.session_state[fallback_max_depth_key]

    activity_id_options: list[str] = []
    activity_id_meta: dict[str, dict[str, Any]] = {}
    for idx, row in enumerate(activity_rows):
        row["_idx"] = idx
        activity_id = str(row.get("activity_id") or "").strip()
        if not activity_id or activity_id in activity_id_meta:
            continue
        level = int(row.get("level", 0))
        label = row.get("display_label") or row.get("label", "") or activity_id
        label = _truncate_label(label, label_max_len)
        activity_id_options.append(activity_id)
        activity_id_meta[activity_id] = {"idx": idx, "level": level, "label": label}

    root_options = [ROOT_ACTIVITY_ALL] + activity_id_options
    root_choice = st.session_state.get(root_key, ROOT_ACTIVITY_ALL)
    if root_choice not in root_options:
        root_choice = ROOT_ACTIVITY_ALL
        st.session_state[root_key] = root_choice

    def _root_label(value: str) -> str:
        if value == ROOT_ACTIVITY_ALL:
            return "All WBS"
        meta = activity_id_meta.get(value)
        if not meta:
            return value
        prefix = "|--" * max(0, meta["level"])
        label = meta.get("label") or value
        return f"{prefix} {label}".strip()

    sidebar.selectbox(
        "Root activity",
        root_options,
        index=root_options.index(root_choice),
        format_func=_root_label,
        key=root_key,
    )

    if root_choice != ROOT_ACTIVITY_ALL and root_choice in activity_id_meta:
        root_meta = activity_id_meta[root_choice]
        root_idx = root_meta["idx"]
        root_level = root_meta["level"]
        end_idx = len(activity_rows)
        for i in range(root_idx + 1, len(activity_rows)):
            if int(activity_rows[i].get("level", 0)) <= root_level:
                end_idx = i
                break
        scoped_rows = activity_rows[root_idx:end_idx]
        base_level = root_level
    else:
        scoped_rows = activity_rows
        base_level = 0

    max_level = 0
    for row in scoped_rows:
        level = int(row.get("level", 0)) - base_level
        if level > max_level:
            max_level = level

    start_choices = [str(i) for i in range(0, max_level + 1)]
    start_choice = st.session_state.get(start_depth_key, "0")
    if start_choice not in start_choices:
        start_choice = "0"
        st.session_state[start_depth_key] = start_choice
    sidebar.selectbox(
        "Start depth",
        start_choices,
        index=start_choices.index(start_choice),
        key=start_depth_key,
    )
    start_depth_level = st.session_state.get(start_depth_key, "0")
    if isinstance(start_depth_level, str) and start_depth_level.isdigit():
        start_depth_level = int(start_depth_level)
    else:
        start_depth_level = 0

    depth_choices = ["All levels"] + [str(i) for i in range(1, max_level + 2)]
    depth_choice = st.session_state.get(max_depth_key, "All levels")
    if depth_choice not in depth_choices:
        depth_choice = "All levels"
        st.session_state[max_depth_key] = depth_choice
    if depth_choice != "All levels":
        if int(depth_choice) - 1 < start_depth_level:
            depth_choice = str(start_depth_level + 1)
            st.session_state[max_depth_key] = depth_choice
    sidebar.selectbox(
        "Max depth",
        depth_choices,
        index=depth_choices.index(depth_choice) if depth_choice in depth_choices else 0,
        key=max_depth_key,
    )
    depth_choice = st.session_state.get(max_depth_key, "All levels")
    if depth_choice == "All levels":
        depth_limit = None
    else:
        depth_limit = int(depth_choice) - 1

    activity_options: list[str] = []
    activity_display: dict[str, str] = {}
    activity_rows_map: dict[str, dict] = {}
    activity_levels: dict[str, int] = {}
    activity_labels: dict[str, str] = {}
    for row in scoped_rows:
        key = f"act_{row['_idx']}"
        level = max(0, int(row.get("level", 0)) - base_level)
        label = row.get("display_label") or row.get("label", "")
        label = _truncate_label(label, label_max_len)
        activity_options.append(key)
        activity_levels[key] = level
        activity_labels[key] = label
        activity_rows_map[key] = row

    for key in activity_options:
        level = activity_levels.get(key, 0)
        prefix = "|--" * max(0, level - start_depth_level)
        label = activity_labels.get(key, "")
        activity_display[key] = f"{prefix} {label}".strip()

    def _level_in_range(level: int) -> bool:
        if level < start_depth_level:
            return False
        if depth_limit is not None and level > depth_limit:
            return False
        return True

    filtered_options = [
        k for k in activity_options
        if _level_in_range(activity_levels.get(k, 0))
    ]

    if not filtered_options:
        filtered_options = activity_options[:1]

    default_key = st.session_state.get("active_activity_key")
    if default_key not in filtered_options:
        default_key = filtered_options[0] if filtered_options else None

    return {
        "root_choice": root_choice,
        "scoped_rows": scoped_rows,
        "base_level": base_level,
        "start_depth_level": start_depth_level,
        "depth_limit": depth_limit,
        "activity_options": activity_options,
        "activity_display": activity_display,
        "activity_rows_map": activity_rows_map,
        "activity_levels": activity_levels,
        "filtered_options": filtered_options,
        "default_key": default_key,
        "activity_rows": activity_rows,
        "activity_id_meta": activity_id_meta,
    }
