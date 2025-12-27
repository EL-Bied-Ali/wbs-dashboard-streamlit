# charts.py – figures Plotly
import plotly.graph_objects as go

def s_curve(
    x,
    weekly_actual,
    actual_curve,
    planned_curve,
    forecast_curve,
    planned_hover=None,
    actual_hover=None,
    forecast_hover=None,
):
    fig = go.Figure()
    fig.add_bar(
        x=x,
        y=weekly_actual,
        name="Weekly Actual %",
        opacity=0.55,
        marker_color="#2fc192",
        hovertemplate="%{x|%d %b %Y}<br>Weekly: %{y:.1f}%<extra></extra>",
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
            hovertemplate=(
                "%{x|%d %b %Y}<br>Actual: %{customdata}<extra></extra>"
                if actual_hover is not None
                else "%{x|%d %b %Y}<br>Actual: %{y:.1f}%<extra></extra>"
            ),
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
            hovertemplate=(
                "%{x|%d %b %Y}<br>Planned: %{customdata}<extra></extra>"
                if planned_hover is not None
                else "%{x|%d %b %Y}<br>Planned: %{y:.1f}%<extra></extra>"
            ),
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
            hovertemplate=(
                "%{x|%d %b %Y}<br>Forecast: %{customdata}<extra></extra>"
                if forecast_hover is not None
                else "%{x|%d %b %Y}<br>Forecast: %{y:.1f}%<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        height=520,
        barmode="overlay",
        hovermode="x unified",
        margin=dict(l=12, r=40, t=10, b=34),
        paper_bgcolor="#11162d",
        plot_bgcolor="#11162d",
        font=dict(color="#e8eefc", size=13, family="Inter, 'Segoe UI', sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0),
        transition=dict(duration=850, easing="cubic-in-out"),
    )
    fig.update_yaxes(
        title="%",
        rangemode="tozero",
        range=[0, 100],
        gridcolor="rgba(255,255,255,0.08)",
        tickfont=dict(size=12),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.08)",
        tickfont=dict(size=12),
        tickformat="%d %b",
    )
    return fig
