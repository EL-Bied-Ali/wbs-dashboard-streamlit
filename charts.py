# charts.py – figures Plotly
from __future__ import annotations

from datetime import datetime, date
from typing import Any, Optional

import plotly.graph_objects as go


def s_curve(
    x,
    actual_curve,
    planned_curve,
    forecast_curve,
    *,
    weekly_planned=None,
    weekly_actual=None,
    weekly_forecast=None,
    planned_hover=None,
    actual_hover=None,
    forecast_hover=None,
    weekly_planned_hover=None,
    weekly_actual_hover=None,
    weekly_forecast_hover=None,
    current_week=None,
    meet_tolerance: float = 0.05,
    selected_x=None,
):
    fig = go.Figure()

    def _as_dt(v):
        if isinstance(v, datetime):
            return v
        if isinstance(v, date):
            return datetime(v.year, v.month, v.day)
        return datetime.fromisoformat(str(v))

    x_dt = [_as_dt(v) for v in x]

    # -------------------------
    # Helpers
    # -------------------------
    def _is_num(v: Any) -> bool:
        return isinstance(v, (int, float))

    def _week_value(val: Any) -> Optional[date]:
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        try:
            return datetime.fromisoformat(str(val)).date()
        except Exception:
            return None

    def _has_values(series) -> bool:
        return series is not None and any(_is_num(v) for v in series)

    def _max_numeric(*series):
        m = None
        for s in series:
            if s is None:
                continue
            for v in s:
                if _is_num(v):
                    m = v if m is None else max(m, v)
        return m

    def _find_index(x_vals, target) -> Optional[int]:
        t = _week_value(target)
        if t is None:
            return None
        for i, xv in enumerate(x_vals):
            if _week_value(xv) == t:
                return i
        return None

    split_idx = None
    if selected_x is not None:
        split_idx = _find_index(x, selected_x)

    def _colorize(base_color, *, future_color=None):
        cur = _week_value(current_week)
        out = []
        for xi in x:
            d = _week_value(xi)
            if cur and d:
                if d == cur:
                    out.append("#e9c75f")
                    continue
                if future_color and d > cur:
                    out.append(future_color)
                    continue
            out.append(base_color)
        return out

    def add_premium_callout(
        fig,
        *,
        x,
        y,
        text,
        color,
        style: str = "glass",  # "glass" | "pill" | "badge"
        symbol: str = "",
        ax: int = 40,
        ay: int = -40,
        xref: str = "x",
        yref: str = "y2",
    ):
        BG = "rgba(20, 28, 60, 0.86)"
        FONT_COLOR = "#eef3ff"
        BORDER_W = 1.5
        PAD_GLASS = 9
        PAD_PILL = 8
        FONT_SIZE = 12
        text_html = f"<b>{symbol}{text}</b>" if symbol else f"<b>{text}</b>"

        if style == "glass":
            fig.add_annotation(
                x=x,
                y=y,
                xref=xref,
                yref=yref,
                text=text_html,
                showarrow=True,
                arrowhead=2,
                arrowwidth=1.5,
                arrowcolor=color,
                ax=ax,
                ay=ay,
                bgcolor=BG,
                bordercolor=color,
                borderwidth=BORDER_W,
                borderpad=PAD_GLASS,
                font=dict(size=FONT_SIZE, color=FONT_COLOR),
            )

        elif style == "pill":
            fig.add_annotation(
                x=x,
                y=y,
                xref=xref,
                yref=yref,
                text=text_html,
                showarrow=True,
                arrowhead=2,
                arrowwidth=1.5,
                arrowcolor=color,
                ax=ax,
                ay=ay,
                bgcolor=BG,
                bordercolor=color,
                borderwidth=BORDER_W,
                borderpad=PAD_PILL,
                font=dict(size=FONT_SIZE, color=FONT_COLOR),
                align="center",
            )

        elif style == "badge":
            fig.add_annotation(
                x=x,
                y=y,
                xref=xref,
                yref=yref,
                text=text,
                showarrow=False,
                bgcolor="rgba(233,199,95,0.85)",
                bordercolor="#e9c75f",
                borderpad=4,
                font=dict(size=11, color="#0b1026"),
            )

    # -------------------------
    # Colors
    # -------------------------
    planned_colors = _colorize("#4b6ff4")
    actual_colors = _colorize("#2fc192")
    forecast_colors = _colorize("#e9c75f", future_color="#b47cff")

    # -------------------------
    # Weekly bars
    # -------------------------
    if _has_values(weekly_planned):
        fig.add_bar(
            x=x_dt,
            y=weekly_planned,
            name="Weekly Planned %",
            opacity=0.38,
            marker_color=planned_colors,
            offsetgroup="planned",
            yaxis="y",
            hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>",
        )

    if _has_values(weekly_actual):
        fig.add_bar(
            x=x_dt,
            y=weekly_actual,
            name="Weekly Actual %",
            opacity=0.38,
            marker_color=actual_colors,
            offsetgroup="actual",
            yaxis="y",
            hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>",
        )

    # Intention conservée: même colonne que actual
    if _has_values(weekly_forecast):
        fig.add_bar(
            x=x_dt,
            y=weekly_forecast,
            name="Weekly Forecast %",
            opacity=0.38,
            marker_color=forecast_colors,
            offsetgroup="actual",
            yaxis="y",
            hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>",
        )

    # -------------------------
    # Cumulative curves (y)
    # -------------------------
    if planned_curve and forecast_curve:
        fig.add_trace(
            go.Scatter(
                x=x_dt + x_dt[::-1],
                y=planned_curve + forecast_curve[::-1],
                fill="toself",
                fillcolor="rgba(75, 111, 244, 0.10)",
                line=dict(color="rgba(255,255,255,0)"),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=x_dt,
            y=planned_curve,
            name="Planned Progress %",
            mode="lines",
            line=dict(width=3.2, color="#4b6ff4", shape="spline"),
            hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>",
        )
    )

    # --- Green before split (robust) ---
    if split_idx is None:
        green_before = actual_curve
    else:
        green_before = []
        for i in range(len(x_dt)):
            if i > split_idx:
                green_before.append(None)
                continue

            v = actual_curve[i] if i < len(actual_curve) else None
            if not _is_num(v):
                v = forecast_curve[i] if i < len(forecast_curve) else None
            if not _is_num(v):
                v = planned_curve[i] if i < len(planned_curve) else None

            green_before.append(v if _is_num(v) else None)

    fig.add_trace(
        go.Scatter(
            x=x_dt,
            y=green_before,
            name="Actual Progress %",
            mode="lines+markers",
            line=dict(width=3.2, color="#2fc192", shape="spline"),
            marker=dict(size=6),
            hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>",
        )
    )

    # Forecast after split (yellow dotted) with fallback to actual if forecast missing
    if split_idx is None:
        forecast_after = forecast_curve
    else:
        forecast_after = []
        for i in range(len(x_dt)):
            if i < split_idx:
                forecast_after.append(None)
                continue
            v = forecast_curve[i] if i < len(forecast_curve) else None
            if not _is_num(v):
                v = actual_curve[i] if i < len(actual_curve) else None
            forecast_after.append(v)

    fig.add_trace(
        go.Scatter(
            x=x_dt,
            y=forecast_after,
            name="Forecast Progress %",
            mode="lines",
            line=dict(width=2.4, dash="dot", color="#e9c75f", shape="spline"),
            hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>",
        )
    )

    if current_week is not None:
        idx = _find_index(x, current_week)
        if idx is not None:
            fig.add_shape(
                type="line",
                x0=x_dt[idx],
                x1=x_dt[idx],
                y0=0,
                y1=100,
                line=dict(
                    color="rgba(233,199,95,0.45)",
                    width=1.5,
                    dash="dot",
                ),
            )

    if split_idx is not None and 0 <= split_idx < len(x_dt):
        fig.add_shape(
            type="line",
            x0=x_dt[split_idx],
            x1=x_dt[split_idx],
            y0=0,
            y1=100,
            line=dict(
                color="rgba(233,199,95,0.35)",
                width=1,
                dash="dot",
            ),
        )

    # -------------------------
    # Pins
    # -------------------------
    if current_week is not None:
        idx = _find_index(x, current_week)
        if idx is not None and idx < len(planned_curve):
            v = planned_curve[idx]
            if _is_num(v):
                add_premium_callout(
                    fig,
                    x=x_dt[idx],
                    y=v,
                    text=f"{v:.1f}%",
                    color="#4b6ff4",
                    style="glass",
                    symbol="● ",
                    ax=-42,
                    ay=-46,
                )

    if actual_curve and forecast_curve:
        n = min(len(x), len(actual_curve), len(forecast_curve))
        for i in range(n):
            a, f = actual_curve[i], forecast_curve[i]
            if _is_num(a) and _is_num(f) and abs(a - f) <= meet_tolerance:
                add_premium_callout(
                    fig,
                    x=x_dt[i],
                    y=a,
                    text=f"{a:.1f}%",
                    color="#2fc192",
                    style="pill",
                    symbol="✓ ",
                )
                break

    if selected_x is not None:
        idx2 = _find_index(x, selected_x)
        if idx2 is not None:
            if idx2 < len(planned_curve):
                pv = planned_curve[idx2]
                if _is_num(pv):
                    add_premium_callout(
                        fig,
                        x=x_dt[idx2],
                        y=pv,
                        text=f"{pv:.1f}%",
                        color="#4b6ff4",
                        style="glass",
                        symbol="● ",
                        ax=42,
                        ay=-46,
                    )
            av = actual_curve[idx2] if idx2 < len(actual_curve) else None
            ay_val = 46
            sym = "✓ "
            col = "#2fc192"

            if not _is_num(av):
                fv = forecast_curve[idx2] if idx2 < len(forecast_curve) else None
                if _is_num(fv):
                    av = fv
                    sym = "≈ "
                    col = "#e9c75f"
                else:
                    for j in range(min(idx2, len(actual_curve) - 1), -1, -1):
                        v = actual_curve[j]
                        if _is_num(v):
                            av = v
                            break

            if _is_num(av):
                add_premium_callout(
                    fig,
                    x=x_dt[idx2],
                    y=av,
                    text=f"{av:.1f}%",
                    color=col,
                    style="pill",
                    symbol=sym,
                    ax=42,
                    ay=ay_val,
                )

    # -------------------------
    # Layout
    # -------------------------
    fig.update_layout(
        height=520,
        autosize=True,
        barmode="group",
        bargap=0.22,
        bargroupgap=0.08,
        hovermode="x unified",
        uirevision="s_curve_v1",
        margin=dict(l=64, r=40, t=10, b=34),
        paper_bgcolor="#0e1328",
        plot_bgcolor="#0e1328",
        font=dict(color="#e8eefc", size=13),
        legend=dict(orientation="h", y=1.05, x=0),
        title=dict(
            text="Project Progress (S-Curve)",
            x=0,
            font=dict(size=14, color="#cfd6ff"),
        ),
    )

    # Swap axes: weekly % on the left (y), cumulative % on the right (y2).
    fig.update_traces(yaxis="y", selector=dict(type="bar"))
    fig.update_traces(yaxis="y2", selector=dict(type="scatter"))

    max_bar = _max_numeric(weekly_planned, weekly_actual, weekly_forecast)
    fig.update_layout(
        yaxis=dict(
            title="Weekly %",
            rangemode="tozero",
            range=[0, max_bar * 1.6] if max_bar else None,
            showgrid=False,
            tickfont=dict(size=12),
            ticks="outside",
            ticklen=6,
        ),
        yaxis2=dict(
            title=dict(text="Cumulative %", standoff=32),
            overlaying="y",
            side="right",
            range=[0, 100],
            rangemode="tozero",
            gridcolor="rgba(255,255,255,0.08)",
            showgrid=True,
            automargin=True,
            tickfont=dict(size=12),
            ticks="outside",
            ticklen=6,
        ),
    )

    # -------------------------
    # X ticks
    # -------------------------
    tickvals = list(x_dt[::2])
    idx = _find_index(x, current_week) if current_week else None
    if idx is not None and x_dt[idx] not in tickvals:
        tickvals.append(x_dt[idx])

    fig.update_xaxes(
        tickmode="array" if tickvals else None,
        tickvals=tickvals,
        tickformat="%d %b",
        gridcolor="rgba(255,255,255,0.08)",
    )

    return fig
