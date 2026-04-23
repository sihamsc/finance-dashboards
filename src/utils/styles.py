APP_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        background: #07090e;
        color: #f3f4f6;
    }

    .block-container {
        padding: 1.6rem 2.1rem 2.3rem 2.1rem;
        max-width: 100% !important;
    }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1016 0%, #090b10 100%);
        border-right: 1px solid #1b2230;
    }

    div[data-testid="stSidebar"] .block-container {
        padding: 1.25rem 0.95rem 1.8rem 0.95rem;
        display: flex;
        flex-direction: column;
        min-height: 100vh;
    }

    .sb-brand {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 1rem;
    }

    .sb-logo {
        width: 28px;
        height: 28px;
        object-fit: contain;
        border-radius: 6px;
        flex-shrink: 0;
    }

    .sb-brand-name {
        font-size: 17px;
        font-weight: 700;
        color: #f5f7fb;
        letter-spacing: -0.02em;
        line-height: 1;
    }

    .sb-brand-sub {
        font-family: 'DM Mono', monospace;
        font-size: 9px;
        color: #667085;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-top: 3px;
    }

    .sb-section {
        background: #0f131b;
        border: 1px solid #1b2230;
        border-radius: 14px;
        padding: 0.95rem 0.85rem 0.5rem 0.85rem;
        margin-bottom: 0.8rem;
    }

    .sb-section-title {
        font-family: 'DM Mono', monospace;
        font-size: 9px;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #6b7280;
        margin-bottom: 0.65rem;
    }

    .sb-active-view {
        background: linear-gradient(180deg, rgba(215,243,74,0.08) 0%, rgba(215,243,74,0.03) 100%);
        border: 1px solid rgba(215,243,74,0.16);
        border-radius: 12px;
        padding: 0.8rem 0.9rem;
        margin-top: 0.2rem;
    }

    .sb-view-label {
        font-family: 'DM Mono', monospace;
        font-size: 9px;
        color: #d7f34a;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }

    .sb-view-value {
        font-size: 13px;
        font-weight: 600;
        color: #f3f4f6;
        margin-bottom: 0.35rem;
    }

    .sb-view-sub {
        font-size: 11px;
        color: #9ca3af;
        line-height: 1.45;
    }

    .sb-bottom-spacer {
        flex: 1 1 auto;
        min-height: 1rem;
    }

    .stSelectbox label,
    .stRadio > label,
    .stSelectSlider > label,
    .stToggle label,
    .stTextInput label {
        font-family: 'DM Mono', monospace !important;
        font-size: 9px !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        color: #6b7280 !important;
    }

    div[data-baseweb="select"] > div {
        background: #090d14 !important;
        border: 1px solid #202938 !important;
        border-radius: 10px !important;
    }

    div[data-baseweb="select"] span {
        color: #e5e7eb !important;
    }

    div[data-baseweb="select"] svg {
        fill: #6b7280 !important;
    }

    div[role="radiogroup"] label {
        background: #0a0d14;
        border: 1px solid #202938;
        border-radius: 10px;
        padding: 0.35rem 0.6rem;
    }

    .metric-card {
        background: linear-gradient(180deg, #0c1017 0%, #0a0d13 100%);
        border: 1px solid #1b2230;
        border-radius: 14px;
        padding: 0.95rem 1.05rem;
        min-height: 88px;
    }

    .metric-label {
        font-family: 'DM Mono', monospace;
        font-size: 9px;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: #6b7280;
        margin-bottom: 0.45rem;
        white-space: nowrap;
    }

    .metric-value {
        font-size: 19px;
        font-weight: 700;
        color: #f8fafc;
        line-height: 1.05;
        letter-spacing: -0.03em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .metric-delta {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        margin-top: 0.45rem;
        white-space: nowrap;
    }

    .delta-pos { color: #4ade80; }
    .delta-neg { color: #f87171; }

    .formula-bar {
        background: #0b0f16;
        border: 1px solid #18202d;
        border-radius: 12px;
        padding: 0.75rem 0.95rem;
        margin-bottom: 1rem;
    }

    .formula-text {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        color: #a3aab8;
        letter-spacing: 0.02em;
    }

    .section-header {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #6b7280;
        border-bottom: 1px solid #161c27;
        padding-bottom: 0.45rem;
        margin-bottom: 1rem;
        margin-top: 1.6rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        background: transparent;
        border-bottom: 1px solid #161c27;
        gap: 0;
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #667085;
        padding: 0.7rem 1.25rem;
        border-radius: 0;
        border-bottom: 2px solid transparent;
        background: transparent;
    }

    .stTabs [aria-selected="true"] {
        color: #d7f34a !important;
        border-bottom: 2px solid #d7f34a !important;
        background: transparent !important;
    }

    .stExpander {
        border: 1px solid #1b2230 !important;
        border-radius: 12px !important;
        background: #0b0f16 !important;
    }
</style>
"""