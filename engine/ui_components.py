"""
PureRoute v2 — Professional Light-Theme Industrial Visualizers & Components
Clean, functional, minimal data-first interface conforming to Linear/Stripe/Vercel and modern industrial SCADA standards.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go

def clean_html(s: str) -> str:
    """Strips all leading/trailing whitespace per line to prevent markdown parsers from treating HTML as code blocks."""
    return "".join(line.strip() for line in s.strip().splitlines() if line.strip())

# Restrained Enterprise Status Color Palette (Muted only)
STATUS_PALETTE = {
    "UF_UV": {"bg": "#EBF5F0", "text": "#235E3F", "border": "#C6E7D4", "label": "UF+UV", "desc": "Ultrafiltration + Dual UV-C Disinfection"},
    "RO": {"bg": "#EDF4FA", "text": "#2B5880", "border": "#CBE0F1", "label": "RO+UV", "desc": "Reverse Osmosis + Dual UV-C (High Dissolved Solids)"},
    "RO_UV": {"bg": "#EDF4FA", "text": "#2B5880", "border": "#CBE0F1", "label": "RO+UV", "desc": "Reverse Osmosis + Dual UV-C (High Dissolved Solids)"},
    "LOCKED_RO": {"bg": "#EDF4FA", "text": "#2B5880", "border": "#93C5FD", "label": "LOCKED-RO", "desc": "Regional Groundwater Hazard Lock (CGWB 2024)"},
    "FLUSH": {"bg": "#FDF6EB", "text": "#8C5E1B", "border": "#F6DFB8", "label": "FLUSH", "desc": "Membrane Purge & High Turbidity Silt Flush"},
    "REPLACE": {"bg": "#FDF6EB", "text": "#8C5E1B", "border": "#F6DFB8", "label": "REPLACE", "desc": "Cartridge Replacement Required (FHI < 40%)"},
    "FAULT": {"bg": "#FDF0ED", "text": "#93302E", "border": "#F7CECA", "label": "FAULT", "desc": "Safety Interlock Tripped • Actuator Cutoff"}
}

def render_status_badge(state: str) -> str:
    """Renders a restrained status badge with accessible contrast and clean typography."""
    clean_state = state.replace("+", "_").replace(" ", "_").replace("-", "_")
    cfg = STATUS_PALETTE.get(clean_state, {"bg": "#F3F4F6", "text": "#374151", "border": "#E5E7EB", "label": state, "desc": ""})
    return clean_html(f"""
    <span style="display: inline-flex; align-items: center; gap: 6px; background-color: {cfg["bg"]}; color: {cfg["text"]}; border: 1px solid {cfg["border"]}; padding: 3px 9px; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 600; letter-spacing: 0.04em;">
        <span style="width: 6px; height: 6px; border-radius: 50%; background-color: {cfg["text"]};"></span>
        {cfg["label"]}
    </span>
    """)

def render_connection_chip(is_hardware: bool, is_connected: bool, port: str = "", baud: int = 115200) -> str:
    """Renders a compact hardware connection indicator chip with metadata."""
    if is_hardware:
        if is_connected:
            dot_color = "#39815B"
            text = f"Arduino Uno ({port})"
            meta = f"{baud} baud"
            bg = "#EBF5F0"
            border = "#C6E7D4"
        else:
            dot_color = "#B94A48"
            text = "Arduino Disconnected"
            meta = "Offline"
            bg = "#FDF0ED"
            border = "#F7CECA"
    else:
        dot_color = "#315B73"
        text = "HIL Simulation Rig"
        meta = "Active"
        bg = "#EDF2F5"
        border = "#D0DCE3"

    return clean_html(f"""
    <span style="display: inline-flex; align-items: center; gap: 7px; background-color: {bg}; border: 1px solid {border}; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 500; color: #20242B;">
        <span style="width: 6px; height: 6px; border-radius: 50%; background-color: {dot_color};"></span>
        <span>{text}</span>
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #68717D; margin-left: 2px;">{meta}</span>
    </span>
    """)

def render_top_header(
    page_name: str,
    is_hardware: bool,
    is_connected: bool,
    port: str = "",
    last_updated: str = "",
    is_paused: bool = False
) -> str:
    """Renders an enterprise-grade dashboard header bar."""
    conn_chip = render_connection_chip(is_hardware, is_connected, port)
    pulse_indicator = (
        '<span style="display: inline-flex; align-items: center; gap: 5px; font-size: 11px; color: #68717D; font-family: \'JetBrains Mono\', monospace;">'
        '<span style="width: 6px; height: 6px; border-radius: 50%; background-color: #39815B;"></span>1 Hz Stream</span>'
        if not is_paused else
        '<span style="display: inline-flex; align-items: center; gap: 5px; font-size: 11px; color: #8C5E1B; font-family: \'JetBrains Mono\', monospace;">'
        '<span style="width: 6px; height: 6px; border-radius: 50%; background-color: #B98536;"></span>PAUSED</span>'
    )

    return clean_html(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 14px; margin-bottom: 20px; border-bottom: 1px solid #E5E7EB;">
        <div>
            <div style="font-size: 11px; font-weight: 500; color: #68717D; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 2px;">
                PureRoute SCADA &bull; Node P-01
            </div>
            <div style="font-size: 22px; font-weight: 600; color: #20242B; letter-spacing: -0.01em;">
                {page_name}
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 14px;">
            {pulse_indicator}
            {conn_chip}
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #4B5563; background: #FFFFFF; border: 1px solid #E5E7EB; padding: 3px 8px; border-radius: 4px;">
                {last_updated}
            </span>
        </div>
    </div>
    """)

def render_system_status_banner(
    state: str,
    reason: str,
    pump_on: bool,
    lock_active: bool,
    faults_count: int,
    t_ms: int
) -> str:
    """
    Renders Section 5.A System Status: Prominent yet compact industrial status banner.
    """
    badge_html = render_status_badge(state)
    
    if pump_on:
        pump_pill = '<span style="color: #235E3F; background: #EBF5F0; border: 1px solid #C6E7D4; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-size: 11px; font-weight: 600;">PUMP RUNNING (12V)</span>'
    else:
        pump_pill = '<span style="color: #68717D; background: #F3F4F6; border: 1px solid #E5E7EB; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-size: 11px; font-weight: 600;">PUMP OFF</span>'

    if lock_active:
        lock_pill = '<span style="color: #2B5880; background: #EDF4FA; border: 1px solid #93C5FD; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-size: 11px; font-weight: 600;">AREA LOCKED (RO)</span>'
    else:
        lock_pill = '<span style="color: #235E3F; background: #EBF5F0; border: 1px solid #C6E7D4; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-size: 11px; font-weight: 600;">AREA UNLOCKED</span>'

    if faults_count == 0:
        safety_pill = '<span style="color: #235E3F; background: #EBF5F0; border: 1px solid #C6E7D4; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-size: 11px; font-weight: 600;">INTERLOCKS PASS (7/7)</span>'
    else:
        safety_pill = f'<span style="color: #93302E; background: #FDF0ED; border: 1px solid #F7CECA; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-size: 11px; font-weight: 600;">SAFETY STOP ({faults_count} FAULT)</span>'

    return clean_html(f"""
    <div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px; padding: 14px 18px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div style="display: flex; align-items: center; gap: 14px;">
                <div>
                    <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #68717D; margin-bottom: 4px;">OPERATING STATE</div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        {badge_html}
                        <span style="font-size: 13px; font-weight: 500; color: #20242B;">{reason}</span>
                    </div>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                {pump_pill}
                {lock_pill}
                {safety_pill}
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #68717D; background: #F9FAFB; border: 1px solid #E5E7EB; padding: 2px 7px; border-radius: 4px;">t={t_ms/1000.0:.1f}s</span>
            </div>
        </div>
    </div>
    """)

def render_metric_card(
    title: str,
    value_str: str,
    unit: str,
    sensor_chip: str,
    subtext: str,
    status_level: str = "ok"
) -> str:
    """
    Renders Section 5.B Live Sensor Metric card: Linear/Stripe style tile.
    """
    if status_level == "ok":
        badge_style = "color: #235E3F; background: #EBF5F0; border: 1px solid #C6E7D4;"
        badge_text = f"{sensor_chip} OK"
    elif status_level == "warn":
        badge_style = "color: #8C5E1B; background: #FDF6EB; border: 1px solid #F6DFB8;"
        badge_text = f"{sensor_chip} ADVISORY"
    else:
        badge_style = "color: #93302E; background: #FDF0ED; border: 1px solid #F7CECA;"
        badge_text = f"{sensor_chip} FAULT"

    return clean_html(f"""
    <div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px; padding: 14px 16px; height: 100%; box-sizing: border-box;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #68717D;">{title}</span>
            <span style="{badge_style} font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 3px; font-family: 'JetBrains Mono', monospace;">{badge_text}</span>
        </div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 28px; font-weight: 600; color: #20242B; line-height: 1.1; margin-bottom: 4px;">
            {value_str}<span style="font-size: 13px; font-weight: 400; color: #68717D; margin-left: 3px;">{unit}</span>
        </div>
        <div style="font-size: 11px; color: #68717D; font-family: 'JetBrains Mono', monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            {subtext}
        </div>
    </div>
    """)

def render_filter_health_card(
    fhi: float,
    counter_pct: float,
    flow: float,
    q0: float,
    litres: float,
    rated_litres: float,
    manometer_cm: float,
    pred_minutes: Optional[int]
) -> str:
    """
    Renders Section 5.C Filter Health component comparing flow FHI to counter estimate.
    """
    if fhi >= 70:
        fh_style = "color: #235E3F; background: #EBF5F0; border: 1px solid #C6E7D4;"
        fh_status = "HEALTHY"
    elif fhi >= 40:
        fh_style = "color: #8C5E1B; background: #FDF6EB; border: 1px solid #F6DFB8;"
        fh_status = "CLOGGING DETECTED"
    else:
        fh_style = "color: #93302E; background: #FDF0ED; border: 1px solid #F7CECA;"
        fh_status = "REPLACE REQUIRED"

    forecast_html = ""
    if pred_minutes is not None and pred_minutes > 0:
        forecast_html = f"""
        <div style="margin-top: 10px; font-size: 12px; color: #8C5E1B; background: #FDF6EB; border: 1px solid #F6DFB8; padding: 7px 10px; border-radius: 4px; display: flex; align-items: center; gap: 8px;">
            <span style="font-weight: 600;">Degradation Forecast:</span>
            <span>Estimated ~{pred_minutes} mins to replace boundary (FHI &lt; 40%) at current fouling rate.</span>
        </div>
        """
    elif fhi < 40:
        forecast_html = """
        <div style="margin-top: 10px; font-size: 12px; color: #93302E; background: #FDF0ED; border: 1px solid #F7CECA; padding: 7px 10px; border-radius: 4px; display: flex; align-items: center; gap: 8px;">
            <span style="font-weight: 600;">Immediate Action:</span>
            <span>Membrane silt fouling exceeds tolerance. Replace cartridge before continuing dispense.</span>
        </div>
        """

    return clean_html(f"""
    <div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px; padding: 16px 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #F1F3F5;">
            <span style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #68717D;">FILTER HEALTH INDEX (FHI)</span>
            <span style="font-size: 11px; color: #68717D; font-family: 'JetBrains Mono', monospace;">Flow Throughput &bull; Q/Q0</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 14px;">
            <div>
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 30px; font-weight: 600; color: #20242B;">{fhi:.1f}%</span>
                <span style="{fh_style} font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; margin-left: 10px;">{fh_status}</span>
            </div>
            <div style="font-size: 12px; color: #68717D; font-family: 'JetBrains Mono', monospace;">
                Manometer: <strong style="color: #20242B;">{manometer_cm:.1f} cm</strong>
            </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12px; border-top: 1px solid #F1F3F5; padding-top: 10px;">
            <div>
                <span style="color: #68717D; display: block; font-size: 11px;">Measured Flow (Q):</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-weight: 600; color: #20242B;">{flow:.2f} L/min</span>
            </div>
            <div>
                <span style="color: #68717D; display: block; font-size: 11px;">Fresh Baseline (Q0):</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-weight: 600; color: #20242B;">{q0:.2f} L/min</span>
            </div>
            <div>
                <span style="color: #68717D; display: block; font-size: 11px;">Dispensed Volume:</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-weight: 600; color: #20242B;">{litres:.1f} / {rated_litres:.0f} L</span>
            </div>
            <div>
                <span style="color: #68717D; display: block; font-size: 11px;">Blind Litre Counter:</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-weight: 600; color: #68717D;">{counter_pct:.1f}%</span>
            </div>
        </div>
        {forecast_html}
    </div>
    """)

def render_decision_matrix_table(current_state: str) -> str:
    """
    Renders Section 5.D Decision Priority Hierarchy table.
    """
    states = [
        {"prio": 1, "name": "FAULT", "code": "FAULT", "trigger": "Any of 7 hardware fail-safe conditions active", "exit": "Clear for 5s", "route": "Pump Stopped (0 L/min)"},
        {"prio": 2, "name": "LOCKED-RO", "code": "LOCKED_RO", "trigger": "CGWB groundwater hazard recorded & no test", "exit": "Certified test", "route": "RO+UV Mandatory"},
        {"prio": 3, "name": "REPLACE", "code": "REPLACE", "trigger": "FHI < 40% or flow Q < 0.30 L/min", "exit": "FHI > 50%", "route": "Service Notification"},
        {"prio": 4, "name": "FLUSH", "code": "FLUSH", "trigger": "Turbidity index TI > 25% (spike)", "exit": "TI < 20%", "route": "Purge to Drain"},
        {"prio": 5, "name": "RO+UV", "code": "RO", "trigger": "EC25 > 500 µS/cm (or TDS > 300 ppm)", "exit": "EC25 < 450 µS/cm", "route": "RO Permeate + UV"},
        {"prio": 6, "name": "UF+UV", "code": "UF_UV", "trigger": "EC25 ≤ 500 µS/cm, TI < 10%, no risk lock", "exit": "Continuous", "route": "Direct UF + UV-C"}
    ]

    rows_html = ""
    for s in states:
        is_active = (current_state.replace("+", "_").replace(" ", "_").replace("-", "_") == s["code"])
        bg_style = "background-color: #EDF2F5; font-weight: 600;" if is_active else ""
        status_chip = (
            '<span style="color: #315B73; background: #DDE7ED; font-weight: 700; padding: 2px 7px; border-radius: 3px; font-size: 10px;">ACTIVE</span>'
            if is_active else
            '<span style="color: #9CA3AF; font-size: 11px;">Standby</span>'
        )
        rows_html += f"""
        <tr style="border-bottom: 1px solid #F1F3F5; {bg_style}">
            <td style="padding: 7px 8px; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #4B5563;">{s['prio']}</td>
            <td style="padding: 7px 8px; font-weight: 600; font-size: 12px;">{s['name']}</td>
            <td style="padding: 7px 8px; font-size: 12px; color: #4B5563;">{s['trigger']}</td>
            <td style="padding: 7px 8px; font-size: 12px; color: #68717D; font-family: 'JetBrains Mono', monospace;">{s['exit']}</td>
            <td style="padding: 7px 8px; font-size: 12px; color: #4B5563;">{s['route']}</td>
            <td style="padding: 7px 8px; text-align: right;">{status_chip}</td>
        </tr>
        """

    return clean_html(f"""
    <div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px; padding: 16px 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #F1F3F5;">
            <span style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #68717D;">DECISION PRIORITY HIERARCHY</span>
            <span style="font-size: 11px; color: #68717D; font-family: 'JetBrains Mono', monospace;">5s Persistence &bull; Hysteresis Lock</span>
        </div>
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
            <thead>
                <tr style="border-bottom: 1px solid #E5E7EB; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: #68717D;">
                    <th style="padding: 6px 8px;">Prio</th>
                    <th style="padding: 6px 8px;">State</th>
                    <th style="padding: 6px 8px;">Trigger Condition</th>
                    <th style="padding: 6px 8px;">Exit Boundary</th>
                    <th style="padding: 6px 8px;">Hydraulic Route</th>
                    <th style="padding: 6px 8px; text-align: right;">Status</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """)

def create_light_telemetry_chart(
    df: pd.DataFrame,
    col_name: str,
    title: str,
    unit: str,
    line_color: str = "#315B73",
    thresholds: Optional[List[Dict[str, Any]]] = None,
    secondary_col: Optional[str] = None,
    secondary_name: str = "Secondary",
    secondary_color: str = "#94A3B8",
    height: int = 180
) -> go.Figure:
    """
    Minimal, clean time-series chart with white background, subtle gray gridlines,
    precise typography and no decorative clutter. Conforms to Section 5.E.
    """
    fig = go.Figure()
    x = df["time_s"] if "time_s" in df.columns else list(range(len(df)))

    # Primary line trace
    fig.add_trace(go.Scatter(
        x=x,
        y=df[col_name],
        name=f"{title}",
        mode="lines",
        line=dict(color=line_color, width=1.75),
        hovertemplate=f"%{{y:.1f}} {unit}<extra></extra>"
    ))

    # Optional comparison line (e.g. usage counter on FHI chart)
    if secondary_col and secondary_col in df.columns:
        fig.add_trace(go.Scatter(
            x=x,
            y=df[secondary_col],
            name=secondary_name,
            mode="lines",
            line=dict(color=secondary_color, width=1.5, dash="dash"),
            hovertemplate=f"%{{y:.1f}} {unit}<extra></extra>"
        ))

    # Reference limit lines
    if thresholds:
        for th in thresholds:
            fig.add_hline(
                y=th["value"],
                line_dash=th.get("dash", "dot"),
                line_color=th.get("color", "#94A3B8"),
                line_width=1,
                annotation_text=th.get("label", ""),
                annotation_position="top right",
                annotation_font=dict(size=9, color=th.get("color", "#68717D"))
            )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=40, r=16, t=28, b=24),
        height=height,
        title=dict(
            text=f"<span style='font-family: Inter, sans-serif; font-size: 12px; font-weight: 600; color: #20242B;'>{title}</span>"
                 f"<span style='font-family: Inter, sans-serif; font-size: 11px; font-weight: 400; color: #68717D;'> ({unit})</span>",
            x=0.01,
            y=0.96
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor="#E5E7EB",
            linewidth=1,
            tickfont=dict(size=9, color="#68717D", family="JetBrains Mono"),
            title=dict(text="Time elapsed (s)", font=dict(size=9, color="#68717D"))
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#F1F3F5",
            zeroline=False,
            showline=True,
            linecolor="#E5E7EB",
            linewidth=1,
            tickfont=dict(size=9, color="#68717D", family="JetBrains Mono")
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=9, color="#68717D"),
            bgcolor="rgba(255,255,255,0.8)"
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#20242B",
            font_size=11,
            font_family="JetBrains Mono",
            font_color="#FFFFFF"
        )
    )
    return fig

def render_card_header(title: str, subtitle: str = "") -> str:
    """Helper to render standardized card headers across dashboard tabs."""
    sub_html = f"<span style='font-family: \"JetBrains Mono\", monospace; font-size: 11px; color: #68717D;'>{subtitle}</span>" if subtitle else ""
    return clean_html(f"""
    <div class="pr-card-header">
        <span class="pr-card-title">{title}</span>
        {sub_html}
    </div>
    """)

def render_contaminant_indicator_card(
    name: str,
    formula: str,
    bis_limit_str: str,
    is_flagged: bool,
    test_value: Optional[float] = None,
    unit: str = "µg/L",
    is_test_valid: bool = False,
    test_source: str = ""
) -> str:
    """
    Renders Section 7 Area Risk Contaminant indicator card.
    Clearly distinguishes:
    - No risk flag found (never assumes safe without testing)
    - Risk flag present (CGWB 2024 regional hazard)
    - Valid test submitted (lab verified compliance or exceedance)
    """
    if is_test_valid and test_value is not None:
        # Determine pass/fail based on limit
        # parse numeric threshold from limit string
        num_str = "".join([c for c in bis_limit_str.split()[0] if c.isdigit() or c == "."])
        limit_num = float(num_str) if num_str else 0.0
        exceeded = test_value > limit_num
        if exceeded:
            status_chip = '<span style="color: #93302E; background: #FDF0ED; border: 1px solid #F7CECA; padding: 2px 7px; border-radius: 3px; font-size: 10px; font-weight: 600; font-family: monospace;">EXCEEDS LIMIT</span>'
            val_style = "color: #93302E;"
            desc_text = f"Measured {test_value} {unit} exceeds BIS limit. RO mandatory."
        else:
            status_chip = '<span style="color: #235E3F; background: #EBF5F0; border: 1px solid #C6E7D4; padding: 2px 7px; border-radius: 3px; font-size: 10px; font-weight: 600; font-family: monospace;">TEST COMPLIANT</span>'
            val_style = "color: #235E3F;"
            desc_text = f"Measured {test_value} {unit} verified below limit ({test_source.upper()})."
        main_val = f"<span style='{val_style} font-size: 20px; font-weight: 600; font-family: monospace;'>{test_value}</span> <span style='font-size: 12px; color: #68717D;'>{unit}</span>"
    elif is_flagged:
        status_chip = '<span style="color: #8C5E1B; background: #FDF6EB; border: 1px solid #F6DFB8; padding: 2px 7px; border-radius: 3px; font-size: 10px; font-weight: 600; font-family: monospace;">CGWB RISK FLAG</span>'
        main_val = "<span style='color: #8C5E1B; font-size: 18px; font-weight: 600; font-family: monospace;'>RO FORCED</span>"
        desc_text = "Documented exceedance in CGWB 2024 groundwater report. Locked to RO."
    else:
        status_chip = '<span style="color: #4B5563; background: #F3F4F6; border: 1px solid #E5E7EB; padding: 2px 7px; border-radius: 3px; font-size: 10px; font-weight: 600; font-family: monospace;">NO CGWB FLAG</span>'
        main_val = "<span style='color: #4B5563; font-size: 18px; font-weight: 600; font-family: monospace;'>UNRECORDED</span>"
        desc_text = "No recorded exceedance in CGWB 2024. Not certified safe without lab test."

    return clean_html(f"""
    <div style="background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px; padding: 14px 16px; height: 100%; box-sizing: border-box;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div style="font-size: 12px; font-weight: 600; color: #20242B;">
                {name} <span style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #68717D; font-weight: 400;">({formula})</span>
            </div>
            {status_chip}
        </div>
        <div style="margin-bottom: 6px;">
            {main_val}
        </div>
        <div style="font-size: 11px; color: #68717D; line-height: 1.4; margin-bottom: 8px;">
            {desc_text}
        </div>
        <div style="font-size: 10px; color: #68717D; font-family: 'JetBrains Mono', monospace; border-top: 1px solid #F1F3F5; padding-top: 6px;">
            BIS IS 10500 Limit: <strong style="color: #20242B;">{bis_limit_str}</strong>
        </div>
    </div>
    """)

