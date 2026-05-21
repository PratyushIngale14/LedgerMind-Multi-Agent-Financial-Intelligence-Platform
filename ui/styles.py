"""
Professional styling for the LedgerMind Streamlit interface.

Design philosophy: editorial, restrained, financial-document inspired.
Charcoal text, off-white background, deep navy accents. No emojis. No
gradient blobs. Typography does the work.
"""

CUSTOM_CSS = """
<style>
    /* Import a serious editorial typeface pair */
    @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600&display=swap');

    .stApp {
        background-color: #FAF9F6;
    }

    /* Sidebar: force light background and dark text */
    section[data-testid="stSidebar"] {
        background-color: #F4F2EC !important;
        border-right: 1px solid #D4CFC2;
    }

    section[data-testid="stSidebar"] * {
        color: #2C3E50 !important;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4 {
        color: #1A2332 !important;
        font-family: 'Source Serif 4', Georgia, serif !important;
    }

    /* Sidebar buttons (sample question buttons) */
    section[data-testid="stSidebar"] .stButton button {
        background: #FFFFFF !important;
        color: #1A2332 !important;
        border: 1px solid #D4CFC2 !important;
        border-radius: 2px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 400 !important;
        text-align: left !important;
        padding: 0.6rem 0.85rem !important;
        font-size: 0.85rem !important;
        line-height: 1.35 !important;
        white-space: normal !important;
        height: auto !important;
    }

    section[data-testid="stSidebar"] .stButton button *,
    section[data-testid="stSidebar"] .stButton button p {
        color: #1A2332 !important;
    }

    section[data-testid="stSidebar"] .stButton button:hover {
        background: #1A2332 !important;
        color: #FAF9F6 !important;
        border-color: #1A2332 !important;
    }

    section[data-testid="stSidebar"] .stButton button:hover *,
    section[data-testid="stSidebar"] .stButton button:hover p {
        color: #FAF9F6 !important;
    }

    /* Main heading */
    h1 {
        font-family: 'Source Serif 4', Georgia, serif !important;
        font-weight: 600 !important;
        color: #1A2332 !important;
        letter-spacing: -0.02em;
    }

    h2, h3, h4 {
        font-family: 'Source Serif 4', Georgia, serif !important;
        font-weight: 600 !important;
        color: #1A2332 !important;
    }

    /* Body text */
    .stMarkdown, .stText, p, div {
        font-family: 'Inter', -apple-system, system-ui, sans-serif;
        color: #2C3E50;
    }

    /* Subtle section divider */
    hr {
        border-color: #D4CFC2 !important;
        margin: 1.5rem 0 !important;
    }

    /* Agent card styling */
    .agent-card {
        background: #FFFFFF;
        border: 1px solid #E5E1D6;
        border-left: 3px solid #2C4A6B;
        padding: 1.25rem 1.5rem;
        margin: 0.75rem 0;
        border-radius: 2px;
        color: #2C3E50;
    }

    .agent-card *, .agent-card p, .agent-card li, .agent-card span, .agent-card div {
        color: inherit;
    }

    .agent-card-abstain {
        background: #F8F6F0;
        border: 1px solid #E5E1D6;
        border-left: 3px solid #8B8478;
        padding: 1.25rem 1.5rem;
        margin: 0.75rem 0;
        border-radius: 2px;
        opacity: 0.85;
        color: #2C3E50;
    }

    .agent-card-abstain *, .agent-card-abstain p, .agent-card-abstain span, .agent-card-abstain div {
        color: inherit;
    }

    .agent-name {
        font-family: 'Source Serif 4', Georgia, serif;
        font-weight: 700;
        font-size: 1.05rem;
        color: #1A2332;
        margin-bottom: 0.25rem;
    }

    .agent-role {
        font-family: 'Inter', sans-serif;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6B7280;
        margin-bottom: 0.75rem;
    }

    .verdict-text {
        font-family: 'Source Serif 4', Georgia, serif;
        font-size: 1.0rem;
        color: #1A2332;
        margin: 0.5rem 0;
        line-height: 1.5;
    }

    .reasoning-text {
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
        color: #4B5563;
        line-height: 1.6;
        margin-top: 0.5rem;
    }

    .confidence-bar-container {
        margin-top: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .confidence-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #6B7280;
    }

    .confidence-value {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.85rem;
        color: #1A2332;
    }

    .citation-block {
        background: #F4F2EC;
        padding: 0.5rem 0.75rem;
        margin-top: 0.5rem;
        font-size: 0.8rem;
        font-family: 'Inter', sans-serif;
        color: #4B5563;
        border-radius: 2px;
    }

    .flag-pill {
        display: inline-block;
        background: #FFF3E0;
        color: #8B4500;
        padding: 0.2rem 0.6rem;
        margin: 0.15rem 0.25rem 0.15rem 0;
        font-size: 0.75rem;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        border-radius: 2px;
        border: 1px solid #E6CCAA;
    }

    .summary-block {
        background: #1A2332;
        color: #FAF9F6;
        padding: 1.5rem 1.75rem;
        margin: 1rem 0;
        border-radius: 2px;
    }

    /* Force everything inside the summary block to be light-colored */
    .summary-block,
    .summary-block *,
    .summary-block p,
    .summary-block li,
    .summary-block ul,
    .summary-block ol,
    .summary-block strong,
    .summary-block b,
    .summary-block span,
    .summary-block div,
    .summary-block h3,
    .summary-block h4 {
        color: #FAF9F6 !important;
    }

    .summary-block h3 {
        font-family: 'Source Serif 4', Georgia, serif !important;
        margin-top: 0 !important;
    }

    .summary-block h4 {
        font-family: 'Source Serif 4', Georgia, serif !important;
    }

    .summary-block strong, .summary-block b {
        font-weight: 700 !important;
        color: #FFFFFF !important;
    }

    .summary-block ul, .summary-block ol {
        padding-left: 1.5rem;
    }

    .summary-block a {
        color: #A8C5E8 !important;
    }

    /* Buttons (main canvas only — sidebar buttons styled separately above) */
    .main .stButton button,
    div[data-testid="stAppViewContainer"] > section:not([data-testid="stSidebar"]) .stButton button {
        background: #1A2332 !important;
        color: #FAF9F6 !important;
        border: none !important;
        border-radius: 2px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        letter-spacing: 0.03em !important;
        padding: 0.5rem 1.25rem !important;
    }

    .main .stButton button *,
    .main .stButton button p,
    div[data-testid="stAppViewContainer"] > section:not([data-testid="stSidebar"]) .stButton button * {
        color: #FAF9F6 !important;
    }

    .main .stButton button:hover,
    div[data-testid="stAppViewContainer"] > section:not([data-testid="stSidebar"]) .stButton button:hover {
        background: #2C4A6B !important;
        color: #FAF9F6 !important;
    }

    .main .stButton button:hover *,
    div[data-testid="stAppViewContainer"] > section:not([data-testid="stSidebar"]) .stButton button:hover * {
        color: #FAF9F6 !important;
    }

    /* Text input */
    .stTextInput input, .stTextArea textarea {
        background: #FFFFFF !important;
        border: 1px solid #D4CFC2 !important;
        border-radius: 2px !important;
        font-family: 'Inter', sans-serif !important;
        color: #1A2332 !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #2C4A6B !important;
        box-shadow: 0 0 0 1px #2C4A6B !important;
    }

    /* Hide Streamlit branding */
    #MainMenu, footer, header {
        visibility: hidden;
    }
</style>
"""