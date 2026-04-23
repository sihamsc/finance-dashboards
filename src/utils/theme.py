THEME_OPTIONS = [
    "Executive / minimal",
    "Finance / Bloomberg-ish",
    "MarketCast-accented",
    "Monochrome blue",
    "Grey + accent",
]

def get_theme_palette(name: str):
    themes = {
        "Executive / minimal": {
            "series": ["#7aa2f7", "#5b7cbe", "#4b5563", "#94a3b8", "#64748b"],
            "blue_scale": ["#1e3a5f", "#2f5f9e", "#7aa2f7"],
            "donut": ["#93c5fd", "#60a5fa", "#3b82f6"],
            "wf_total": "#d4af37",
            "wf_pos": "#4ade80",
            "wf_neg": "#f87171",
            "line_current": "#7aa2f7",
            "line_prior": "#475569",
            "accent_scale": ["#122033", "#60a5fa"],
        },
        "Finance / Bloomberg-ish": {
            "series": ["#4c78a8", "#2f4b7c", "#6b7280", "#9ca3af", "#1f5a91"],
            "blue_scale": ["#0f2d4a", "#1f5a91", "#5fa8ff"],
            "donut": ["#0f4c81", "#2563eb", "#60a5fa"],
            "wf_total": "#93c5fd",
            "wf_pos": "#4ade80",
            "wf_neg": "#ef4444",
            "line_current": "#60a5fa",
            "line_prior": "#6b7280",
            "accent_scale": ["#0f2d4a", "#5fa8ff"],
        },
        "MarketCast-accented": {
            "series": ["#d7f34a", "#4ade80", "#60a5fa", "#a78bfa", "#fb923c"],
            "blue_scale": ["#1e3a5f", "#3b82f6", "#d7f34a"],
            "donut": ["#d7f34a", "#60a5fa", "#a78bfa"],
            "wf_total": "#d7f34a",
            "wf_pos": "#4ade80",
            "wf_neg": "#f87171",
            "line_current": "#d7f34a",
            "line_prior": "#475569",
            "accent_scale": ["#141a0d", "#d7f34a"],
        },
        "Monochrome blue": {
            "series": ["#93c5fd", "#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8"],
            "blue_scale": ["#17324d", "#2b6ea5", "#93c5fd"],
            "donut": ["#93c5fd", "#60a5fa", "#2563eb"],
            "wf_total": "#60a5fa",
            "wf_pos": "#4ade80",
            "wf_neg": "#f87171",
            "line_current": "#60a5fa",
            "line_prior": "#475569",
            "accent_scale": ["#122033", "#60a5fa"],
        },
        "Grey + accent": {
            "series": ["#94a3b8", "#64748b", "#475569", "#d7f34a", "#334155"],
            "blue_scale": ["#334155", "#64748b", "#d7f34a"],
            "donut": ["#475569", "#64748b", "#d7f34a"],
            "wf_total": "#d7f34a",
            "wf_pos": "#4ade80",
            "wf_neg": "#f87171",
            "line_current": "#94a3b8",
            "line_prior": "#475569",
            "accent_scale": ["#334155", "#d7f34a"],
        },
    }
    return themes[name]

PT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#94a3b8", size=11),
    xaxis=dict(
        gridcolor="#141924",
        linecolor="#1b2230",
        tickcolor="#1b2230",
        tickfont=dict(color="#cbd5e1"),
        title_font=dict(color="#cbd5e1"),
    ),
    yaxis=dict(
        gridcolor="#141924",
        linecolor="#1b2230",
        tickcolor="#1b2230",
        tickfont=dict(color="#cbd5e1"),
        title_font=dict(color="#cbd5e1"),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", size=10),
    ),
    margin=dict(l=0, r=0, t=40, b=0),
)