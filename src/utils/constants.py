"""
Shared constants for thresholds, display options, and per-metric accent colors.
Centralising these avoids magic numbers scattered across the codebase.
"""

# Client view options used in bar chart radios
TOP_N_OPTIONS   = [5, 10, 15, 20, 25, 30]
TOP_N_DEFAULT   = 15
CLIENT_VIEWS    = ["Top 15", "Top 30", "All > $100k"]
CLIENT_VIEWS_LAB = ["Top 15", "Top 30", "All"]   # labor / fixed-cost (no $100k floor)

# COGS anomaly threshold
COGS_HIGH_PCT   = 60    # COGS / Rev > this → client warning

# Explorer / signal flags
GM_LOW_PCT      = 20    # GM% below this → amber
CM_NEGATIVE     = 0     # CM% below this → red
COGS_FLAG_PCT   = 65    # COGS% above this → amber signal
LABOR_HIGH_PCT  = 40    # Labor% above this → blue signal
CM_STRONG_PCT   = 50    # CM% above this → green signal
CONC_TOP1       = 30    # top entity > this % of rev → red concentration flag
CONC_TOP3       = 60    # top 3 entities > this % → amber

# Bubble segment labels → display names (used in Profitability tab)
GM_SEGMENT_DISPLAY = {
    "High Rev / High Margin":  "Stars — Protect & Grow",
    "Low Rev / High Margin":   "Rising — Invest & Scale",
    "High Rev / Low Margin":   "Volume — Improve Margins",
    "Low Rev / Low Margin":    "At Risk — Review",
}
CM_SEGMENT_DISPLAY = {
    "High Rev / High Contribution": "Stars — Protect & Grow",
    "Low Rev / High Contribution":  "Rising — Invest & Scale",
    "High Rev / Low Contribution":  "Volume — Reduce Labor",
    "Low Rev / Low Contribution":   "At Risk — Review",
}
# Per-metric accent colors — used for bar fills, trend lines, and narrative borders.
# Keeping them here ensures every tab referencing the same metric uses the same hue.
METRIC_COLOR = {
    "revenue":      "#60a5fa",   # blue
    "cogs":         "#f87171",   # red
    "fixed_cost":   "#a78bfa",   # purple
    "labor":        "#fb923c",   # orange
    "gross_margin": "#4ade80",   # green
    "contribution": "#d7f34a",   # MarketCast yellow
}

SEGMENT_COLORS = {
    "Stars — Protect & Grow":   "#4ade80",
    "Rising — Invest & Scale":  "#60a5fa",
    "Volume — Improve Margins": "#fb923c",
    "Volume — Reduce Labor":    "#fb923c",
    "At Risk — Review":         "#f87171",
}