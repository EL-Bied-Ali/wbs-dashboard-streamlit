# charts.py – figures Plotly
import plotly.graph_objects as go
from datetime import datetime, date

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
    meet_tolerance=0.05,
):
    fig = go.Figure()
    def _max_numeric(*series):
        max_val = None
        for values in series:
            if values is None:
                continue
            for v in values:
                if isinstance(v, (int, float)):
                    if max_val is None or v > max_val:
                        max_val = v
        return max_val
    def _add_pin(x_val, y_val, text, color, y_offset=-34, x_offset=0):
        arrow_color = color
        fig.add_trace(
            go.Scatter(
                x=[x_val],
                y=[y_val],
                mode="markers",
                marker=dict(size=18, color=color, opacity=0.22, line=dict(width=0)),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[x_val],
                y=[y_val],
                mode="markers",
                marker=dict(size=9, color=color, line=dict(width=2, color="#0b1026")),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_annotation(
            x=x_val,
            y=y_val,
            text=f"<b>{text}</b>",
            showarrow=True,
            arrowhead=4,
            arrowwidth=2,
            arrowsize=1.2,
            arrowcolor=arrow_color,
            ax=x_offset,
            ay=y_offset,
            bgcolor="rgba(12, 18, 40, 0.92)",
            bordercolor=color,
            borderwidth=2,
            borderpad=8,
            font=dict(size=13, color="#eef3ff"),
            align="center",
        )
    def _has_values(series):
        return series is not None and any(isinstance(v, (int, float)) for v in series)
    def _week_value(val):
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        try:
            return datetime.fromisoformat(str(val)).date()
        except Exception:
            return None
    def _colorize(base_color, *, future_color=None):
        cur = _week_value(current_week)
        colors = []
        for xi in x:
            xi_week = _week_value(xi)
            if cur is not None and xi_week is not None:
                if xi_week == cur:
                    colors.append("#e9c75f")
                    continue
                if future_color and xi_week > cur:
                    colors.append(future_color)
                    continue
            colors.append(base_color)
        return colors
    def _bar_colors(base_color):
        if current_week is None or not x:
            return base_color
        return ["#e9c75f" if xi == current_week else base_color for xi in x]

    planned_colors = _colorize("#4b6ff4")
    actual_colors = _colorize("#2fc192")
    forecast_colors = _colorize("#e9c75f", future_color="#b47cff")
    if _has_values(weekly_planned):
        fig.add_bar(
            x=x,
            y=weekly_planned,
            name="Weekly Planned %",
            opacity=0.45,
            marker_color=planned_colors,
            customdata=weekly_planned_hover,
            offsetgroup="planned",
            yaxis="y2",
            hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>",
        )
    if _has_values(weekly_actual):
        fig.add_bar(
            x=x,
            y=weekly_actual,
            name="Weekly Actual %",
            opacity=0.45,
            marker_color=actual_colors,
            customdata=weekly_actual_hover,
            offsetgroup="actual",
            yaxis="y2",
            hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>",
        )
    if _has_values(weekly_forecast):
        fig.add_bar(
            x=x,
            y=weekly_forecast,
            name="Weekly Forecast %",
            opacity=0.45,
            marker_color=forecast_colors,
            customdata=weekly_forecast_hover,
            offsetgroup="actual",
            yaxis="y2",
            hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>",
        )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=actual_curve,
            name="Actual Progress %",
            mode="lines+markers",
            line=dict(width=3, color="#2fc192"),
            marker=dict(size=6),
            customdata=actual_hover,
            hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=planned_curve,
            name="Planned Progress %",
            mode="lines",
            line=dict(width=3, color="#4b6ff4"),
            customdata=planned_hover,
            hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=forecast_curve,
            name="Forecast Progress %",
            mode="lines",
            line=dict(width=3, dash="dot", color="#e9c75f"),
            customdata=forecast_hover,
            hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>",
        )
    )
    if current_week is not None:
        planned_idx = None
        for idx, x_val in enumerate(x):
            if x_val == current_week:
                planned_idx = idx
                break
        if planned_idx is not None:
            planned_val = planned_curve[planned_idx] if planned_curve and planned_idx < len(planned_curve) else None
            if isinstance(planned_val, (int, float)):
                _add_pin(x[planned_idx], planned_val, f"{planned_val:.1f}%", "#4b6ff4", y_offset=-46, x_offset=-42)
    if actual_curve and forecast_curve:
        for idx, x_val in enumerate(x):
            if idx >= len(actual_curve) or idx >= len(forecast_curve):
                continue
            a_val = actual_curve[idx]
            f_val = forecast_curve[idx]
            if not isinstance(a_val, (int, float)) or not isinstance(f_val, (int, float)):
                continue
            if abs(a_val - f_val) <= meet_tolerance:
                _add_pin(x_val, a_val, f"{a_val:.1f}%", "#2fc192", y_offset=44, x_offset=48)
    fig.update_layout(
        height=520,
        barmode="group",
        bargap=0.22,
        bargroupgap=0.08,
        hovermode="x unified",
        margin=dict(l=12, r=40, t=10, b=34),
        paper_bgcolor="#11162d",
        plot_bgcolor="#11162d",
        font=dict(color="#e8eefc", size=13, family="Inter, 'Segoe UI', sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0),
        transition=dict(duration=850, easing="cubic-in-out"),
    )
    max_bar = _max_numeric(weekly_planned, weekly_actual, weekly_forecast)
    yaxis2 = dict(
        title="Weekly %",
        overlaying="y",
        side="right",
        rangemode="tozero",
        showgrid=False,
        tickfont=dict(size=12),
    )
    if isinstance(max_bar, (int, float)) and max_bar > 0:
        yaxis2["range"] = [0, max_bar * 2.5]
    fig.update_layout(yaxis2=yaxis2)
    fig.update_layout(
        yaxis=dict(
            title="Cumulative %",
            rangemode="tozero",
            range=[0, 100],
            gridcolor="rgba(255,255,255,0.08)",
            tickfont=dict(size=12),
        )
    )
    tickvals = list(x[::2])
    if tickvals and current_week is not None and current_week not in tickvals:
        tickvals.append(current_week)
    ordered_tickvals = []
    for xi in x:
        if xi in tickvals and xi not in ordered_tickvals:
            ordered_tickvals.append(xi)
    tickvals = ordered_tickvals
    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.08)",
        tickfont=dict(size=12),
        tickformat="%d %b",
        tickmode="array" if tickvals else None,
        tickvals=tickvals if tickvals else None,
    )
    return fig
