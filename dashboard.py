import os
import json
import hashlib
import requests
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from kryptika.core.transaction import Wallet, Transaction

st.set_page_config(
    page_title="KRYPTIKA",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
  --bg: #FFFFFF; --surface: #F8FAFC; --surface-2: #F1F5F9; --border: #E2E8F0;
  --border-hi: #CBD5E1; --glow: rgba(14, 165, 233, 0.15); --green: #10B981;
  --green-dk: #059669; --green-dim: rgba(16, 185, 129, 0.12); --amber: #F59E0B;
  --amber-dim: rgba(245, 158, 11, 0.12); --red: #EF4444; --red-dim: rgba(239, 68, 68, 0.12);
  --blue: #3B82F6; --blue-dim: rgba(59, 130, 246, 0.12); --cyan: #0EA5E9;
  --txt-1: #0F172A; --txt-2: #334155; --txt-3: #475569; --txt-4: #64748B;
  --r: 8px; --r2: 12px; --mono: 'JetBrains Mono', monospace; --head: 'Inter', sans-serif;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"], .stApp { font-family: var(--mono); background: var(--bg) !important; color: var(--txt-1); }

[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] { visibility: visible !important; display: flex !important; pointer-events: auto !important; position: fixed !important; top: 0.55rem !important; left: 0.55rem !important; z-index: 999999 !important; background: var(--surface) !important; border: 1px solid var(--border-hi) !important; border-radius: var(--r) !important; padding: 4px !important; }
[data-testid="stExpandSidebarButton"] svg, [data-testid="stSidebarCollapseButton"] svg { fill: var(--cyan) !important; width: 18px !important; height: 18px !important; }
[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border) !important; }
[data-testid="stSidebar"] > div { padding: 0 !important; }
[data-testid="stSidebar"] .stButton > button { background: transparent !important; border: 1px solid transparent !important; color: var(--txt-2) !important; font-family: var(--mono) !important; font-size: 0.78rem !important; font-weight: 500 !important; letter-spacing: 0.04em !important; border-radius: var(--r) !important; padding: 8px 14px !important; text-align: left !important; justify-content: flex-start !important; width: 100% !important; transition: all 0.12s !important; }
[data-testid="stSidebar"] .stButton > button:hover { background: var(--blue-dim) !important; border-color: var(--border-hi) !important; color: var(--cyan) !important; }

.main-wrap { padding: 28px 36px; }
.ph { display: flex; align-items: baseline; gap: 16px; margin-bottom: 28px; padding-bottom: 14px; border-bottom: 1px solid var(--border); }
.ph-title { font-family: var(--head); font-size: 1.9rem; font-weight: 800; letter-spacing: -0.02em; color: var(--txt-1); }
.ph-sub { font-size: 0.6rem; letter-spacing: 0.2em; text-transform: uppercase; color: var(--txt-3); font-weight: 600; }

.hero-box { background: linear-gradient(135deg, var(--surface-2) 0%, var(--blue-dim) 100%); border: 1px solid var(--border-hi); border-radius: var(--r2); padding: 32px 24px; margin-bottom: 24px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; width: 100%; }
.hero-box h2 { font-family: var(--head); font-size: clamp(1.2rem, 4vw, 1.8rem); color: var(--txt-1); margin-bottom: 8px; font-weight: 800; }
.hero-box p { font-size: clamp(0.75rem, 2vw, 0.9rem); color: var(--txt-3); max-width: 600px; line-height: 1.6; }

.tile { background: var(--bg); border: 1px solid var(--border); border-radius: var(--r2); padding: 18px 20px; position: relative; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
.tile::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, var(--cyan) 0%, var(--blue) 100%); }
.tile-label { font-family: var(--head); font-size: 0.65rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--txt-3); margin-bottom: 10px; font-weight: 700; }
.tile-val { font-family: var(--head); font-size: 2rem; font-weight: 800; color: var(--txt-1); line-height: 1; }
.tile-val.sm { font-size: 1.3rem; }
.tile-val.xs { font-size: 1.0rem; }
.tile-unit { font-size: 0.65rem; color: var(--txt-4); margin-top: 6px; font-weight: 500; }

.sh { display: flex; align-items: center; gap: 10px; margin: 24px 0 12px; font-family: var(--head); font-size: 0.75rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--txt-2); font-weight: 700; }
.sh::after { content: ''; flex: 1; height: 1px; background: var(--border); }

.brow, .trow { background: var(--bg); border: 1px solid var(--border); border-radius: var(--r); margin-bottom: 6px; display: grid; align-items: center; gap: 12px; font-size: 0.75rem; transition: all 0.12s; }
.brow { padding: 14px 16px; grid-template-columns: 60px 1fr 72px 80px 110px; }
.trow { padding: 12px 14px; grid-template-columns: 80px 1fr 20px 1fr 90px 68px; }
.brow:hover, .trow:hover { border-color: var(--border-hi); box-shadow: 0 2px 4px rgba(0,0,0,0.02); }

.col-hdr { display: grid; gap: 12px; font-family: var(--head); font-size: 0.6rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--txt-3); padding: 0 16px 8px; font-weight: 700; }
.col-hdr.b { grid-template-columns: 60px 1fr 72px 80px 110px; }
.col-hdr.t { grid-template-columns: 80px 1fr 20px 1fr 90px 68px; }

.blk-idx { font-family: var(--head); font-size: 1.1rem; font-weight: 700; color: var(--cyan); }
.blk-hash { color: var(--txt-2); font-size: 0.65rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.blk-txs { color: var(--blue); text-align: center; font-weight: 700; }
.blk-non { color: var(--txt-3); font-size: 0.7rem; text-align: right; }
.blk-time { color: var(--txt-4); font-size: 0.65rem; text-align: right; }

.tx-addr { color: var(--txt-2); font-size: 0.65rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
.tx-arrow { color: var(--border-hi); text-align: center; font-size: 0.9rem; font-weight: 700; }
.tx-amount { color: var(--txt-1); font-weight: 700; text-align: right; }
.tx-fee { color: var(--txt-4); font-size: 0.65rem; text-align: right; }

.badge { display: inline-block; font-family: var(--head); font-size: 0.6rem; font-weight: 700; letter-spacing: 0.05em; border-radius: 4px; padding: 4px 8px; white-space: nowrap; line-height: 1.2; text-align: center; }
.b-reward { color: var(--green-dk); background: var(--green-dim); border: 1px solid rgba(16,185,129,0.3); }
.b-sent { color: var(--red); background: var(--red-dim); border: 1px solid rgba(239,68,68,0.3); }
.b-recv { color: var(--blue); background: var(--blue-dim); border: 1px solid rgba(59,130,246,0.3); }
.b-pend { color: var(--amber); background: var(--amber-dim); border: 1px solid rgba(245,158,11,0.3); }

.wcard { background: var(--bg); border: 1px solid var(--border); border-radius: var(--r2); padding: 20px; margin-bottom: 12px; position: relative; overflow: hidden; transition: all 0.15s; }
.wcard:hover { border-color: var(--border-hi); box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
.wcard.active { border-color: var(--cyan); background: rgba(14,165,233,0.02); box-shadow: 0 0 0 1px var(--cyan); }
.wcard-badge { position: absolute; top: 16px; right: 16px; font-family: var(--head); font-size: 0.6rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--cyan); background: var(--blue-dim); border-radius: 4px; padding: 4px 8px; font-weight: 700; }
.wcard-name { font-family: var(--head); font-size: 1.1rem; font-weight: 700; color: var(--txt-1); margin-bottom: 6px; }
.wcard-addr { font-size: 0.6rem; color: var(--txt-3); word-break: break-all; overflow-wrap: break-word; margin-bottom: 16px; line-height: 1.6; }
.wcard-balance { font-family: var(--head); font-size: 1.8rem; font-weight: 800; color: var(--txt-1); }
.wcard-unit { font-size: 0.8rem; color: var(--txt-4); margin-left: 6px; font-weight: 500; }

.sbox { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 16px 20px; margin: 16px 0; }
.srow { display: flex; justify-content: space-between; align-items: baseline; padding: 9px 0; border-bottom: 1px solid var(--border); font-size: 0.8rem; gap: 12px; }
.srow:last-child { border-bottom: none; font-weight: 700; color: var(--txt-1); }
.skey { color: var(--txt-3); font-weight: 500; flex-shrink: 0; white-space: nowrap; }
.sval { color: var(--txt-1); text-align: right; font-size: 0.8rem; font-weight: 600; word-break: break-all; overflow-wrap: break-word; }

.rbox { background: var(--green-dim); border: 1px solid rgba(16,185,129,0.2); border-radius: var(--r); padding: 18px 20px; margin-top: 16px; }
.rrow { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.8rem; }
.rkey { color: var(--txt-2); font-weight: 500; flex-shrink: 0; margin-right: 12px; }
.rval { color: var(--green-dk); font-weight: 700; font-size: 0.75rem; text-align: right; word-break: break-all; overflow-wrap: break-word; max-width: 70%; }

.hash-box { font-size: 0.65rem; color: var(--cyan); word-break: break-all; overflow-wrap: break-word; line-height: 1.6; padding: 12px 16px; background: var(--blue-dim); border: 1px solid rgba(14,165,233,0.2); border-radius: var(--r); margin-top: 10px; font-weight: 500; }
.err-box { font-size: 0.75rem; color: var(--red); word-break: break-word; padding: 12px 16px; background: var(--red-dim); border: 1px solid rgba(239,68,68,0.2); border-radius: var(--r); margin-top: 10px; font-weight: 500; }

.mine-box { background: var(--bg); border: 1px solid var(--border); border-radius: var(--r2); padding: 24px; margin: 16px 0; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
.mine-num { font-family: var(--head); font-size: 3.5rem; font-weight: 800; color: var(--cyan); line-height: 1; }
.mine-label { font-family: var(--head); font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--txt-3); margin-top: 12px; font-weight: 600; }

.peer-row { background: var(--bg); border: 1px solid var(--border); border-radius: var(--r); padding: 14px 18px; margin-bottom: 8px; display: flex; align-items: center; gap: 12px; font-size: 0.8rem; }
.peer-dot { color: var(--green); font-size: 1.2rem; }
.peer-addr { color: var(--txt-1); flex: 1; font-weight: 500; }

.act-line { display: flex; gap: 16px; align-items: center; font-size: 0.75rem; padding: 8px 0; border-bottom: 1px solid var(--border); }
.act-time { color: var(--txt-4); width: 140px; flex-shrink: 0; }
.act-msg { color: var(--txt-2); flex: 1; }
.act-msg.hi { color: var(--cyan); font-weight: 600; }

.stTextInput > div > div > input, .stNumberInput > div > div > input, .stTextArea > div > div > textarea { background: var(--bg) !important; border: 1px solid var(--border-hi) !important; border-radius: var(--r) !important; color: var(--txt-1) !important; font-family: var(--mono) !important; font-size: 0.85rem !important; padding: 10px 14px !important; }
.stTextInput > div > div > input:focus, .stNumberInput > div > div > input:focus, .stTextArea > div > div > textarea:focus { border-color: var(--cyan) !important; box-shadow: 0 0 0 3px var(--glow) !important; }
.stSelectbox > div > div { background: var(--bg) !important; border: 1px solid var(--border-hi) !important; color: var(--txt-1) !important; font-family: var(--mono) !important; font-size: 0.85rem !important; border-radius: var(--r) !important; padding: 2px !important; }
label, .stTextInput label, .stSelectbox label, .stNumberInput label { font-family: var(--head) !important; font-size: 0.7rem !important; letter-spacing: 0.05em !important; text-transform: uppercase !important; color: var(--txt-3) !important; font-weight: 700 !important; margin-bottom: 6px !important; }

.main-wrap .stButton > button, [data-testid="column"] .stButton > button { background: var(--bg) !important; border: 1px solid var(--border-hi) !important; color: var(--txt-2) !important; font-family: var(--head) !important; font-size: 0.75rem !important; font-weight: 700 !important; letter-spacing: 0.05em !important; text-transform: uppercase !important; border-radius: var(--r) !important; padding: 12px 24px !important; transition: all 0.15s !important; }
.main-wrap .stButton > button:hover, [data-testid="column"] .stButton > button:hover { background: var(--surface) !important; border-color: var(--cyan) !important; color: var(--cyan) !important; box-shadow: 0 2px 8px var(--glow) !important; }

.stSuccess > div { background: var(--green-dim) !important; border: 1px solid rgba(16,185,129,0.3) !important; color: var(--green-dk) !important; font-family: var(--mono) !important; font-size: 0.8rem !important; border-radius: var(--r) !important; word-break: break-word; }
.stError > div, .stException > div { background: var(--red-dim) !important; border: 1px solid rgba(239,68,68,0.3) !important; color: var(--red) !important; font-family: var(--mono) !important; font-size: 0.8rem !important; border-radius: var(--r) !important; word-break: break-word; }
.stInfo > div { background: var(--blue-dim) !important; border: 1px solid rgba(59,130,246,0.3) !important; color: var(--blue) !important; font-family: var(--mono) !important; font-size: 0.8rem !important; border-radius: var(--r) !important; word-break: break-word; }
.stWarning > div { background: var(--amber-dim) !important; border: 1px solid rgba(245,158,11,0.3) !important; color: #B45309 !important; font-family: var(--mono) !important; font-size: 0.8rem !important; border-radius: var(--r) !important; word-break: break-word; }

.stTabs [data-baseweb="tab-list"] { background: transparent !important; border-bottom: 2px solid var(--border) !important; gap: 24px !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: var(--txt-3) !important; font-family: var(--head) !important; font-size: 0.8rem !important; letter-spacing: 0.05em !important; text-transform: uppercase !important; border: none !important; border-bottom: 2px transparent !important; border-radius: 0 !important; padding: 12px 0 !important; font-weight: 700 !important; margin-bottom: -2px !important; }
.stTabs [aria-selected="true"] { color: var(--cyan) !important; border-bottom-color: var(--cyan) !important; }

.streamlit-expanderHeader { background: var(--bg) !important; border: 1px solid var(--border) !important; border-radius: var(--r) !important; font-family: var(--mono) !important; font-size: 0.8rem !important; color: var(--txt-1) !important; font-weight: 500 !important; }
.streamlit-expanderContent { background: var(--surface) !important; border: 1px solid var(--border) !important; border-top: none !important; }

.stSpinner > div { border-top-color: var(--cyan) !important; }
.stProgress > div > div { background: var(--cyan) !important; }
.stCode, code, pre { background: var(--surface) !important; border: 1px solid var(--border) !important; color: var(--txt-1) !important; font-family: var(--mono) !important; font-size: 0.8rem !important; border-radius: var(--r) !important; white-space: pre-wrap !important; word-break: break-all !important; overflow-wrap: break-word !important; }
hr { border: none; border-top: 1px solid var(--border) !important; margin: 24px 0 !important; }
.stCaption { color: var(--txt-3) !important; font-family: var(--mono) !important; font-size: 0.75rem !important; }
.stToggle { accent-color: var(--cyan); }
.stRadio > div { display: none; }

.chart-wrap { background: var(--bg); border: 1px solid var(--border); border-radius: var(--r); padding: 8px; margin-bottom: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); }
.tlabel { font-family: var(--head); font-size: 0.65rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--txt-3); margin-bottom: 6px; font-weight: 700; }
.hash-txt { font-size: 0.65rem; color: var(--txt-2); word-break: break-all; overflow-wrap: break-word; line-height: 1.6; font-weight: 500; }
.note-txt { font-size: 0.7rem; color: var(--txt-3); margin-top: 6px; line-height: 1.6; }

@media (max-width: 768px) {
  .main-wrap { padding: 16px; }
  .col-hdr { display: none; }
  .brow, .trow { grid-template-columns: 1fr !important; gap: 8px; padding: 16px; text-align: left !important; }
  .tx-amount, .tx-fee, .blk-non, .blk-time { text-align: left !important; }
  .tx-arrow { display: none; }
}
</style>
""", unsafe_allow_html=True)

# ── API & Helper Functions ─────────────────────────────────────────────────────
def api(method: str, path: str, payload=None, timeout: int = 8):
    url = f"{st.session_state.node_url}{path}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=timeout)
        else:
            r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Node offline or unreachable."
    except requests.exceptions.Timeout:
        return None, "Request timed out."
    except requests.exceptions.HTTPError:
        try:
            return None, r.json().get("error", "HTTP Error")
        except Exception:
            return None, "HTTP Error"
    except Exception as exc:
        return None, str(exc)

def short(addr: str, n: int = 8) -> str:
    if not addr or len(addr) < n * 2 + 4: return addr or "---"
    return f"{addr[:n]}...{addr[-4:]}"

def ts(unix: float) -> str:
    try:    return datetime.fromtimestamp(unix).strftime("%Y-%m-%d %H:%M:%S")
    except: return "---"

def ts_short(unix: float) -> str:
    try:    return datetime.fromtimestamp(unix).strftime("%d %b  %H:%M")
    except: return "---"

def fmt(v, decimals: int = 4) -> str:
    try:    return f"{float(v):.{decimals}f}"
    except: return str(v)

def tile_val_class(value) -> str:
    digits = str(value).replace(".", "").replace("-", "")
    if len(digits) > 9: return "xs"
    if len(digits) > 6: return "sm"
    return ""

def stat_tile(col, value, label, unit=""):
    vc = tile_val_class(value)
    col.markdown(f"""
    <div class="tile">
      <div class="tile-label">{label}</div>
      <div class="tile-val {vc}">{value}</div>
      <div class="tile-unit">{unit}</div>
    </div>""", unsafe_allow_html=True)

def offline_banner(err: str):
    st.markdown(f'<div class="err-box">⚠ Node unreachable — {err}</div>', unsafe_allow_html=True)

# ── Unified File System Wallets DB ─────────────────────────────────────────────
_WALLETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wallets.json")

def _load_db() -> dict:
    try:
        with open(_WALLETS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_db(wallets_dict: dict, active_name: str) -> None:
    try:
        data = dict(wallets_dict)
        if active_name and active_name in data:
            data["__active__"] = active_name
        with open(_WALLETS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# Initialize DB data safely
_db = _load_db()
_init_active = _db.pop("__active__", None)
_init_wallets = {
    k: v for k, v in _db.items()
    if isinstance(v, dict) and "address" in v and ("private_key_hex" in v or "private_key" in v)
}

# ── State Initialization ───────────────────────────────────────────────────────
_defaults = {
    "node_url":       "http://localhost:5000",
    "page":           "Overview",
    "wallets":        _init_wallets,
    "active_wallet":  _init_active if _init_active in _init_wallets else None,
    "last_tx_id":     None,
    "last_mine":      None,
    "confirm_remove": None,
    "send_to_ui":     "",
    "send_amt_ui":    1.0,
    "send_fee_ui":    0.2, 
    "send_note_ui":   "",
    "auto_refresh":   False
}

for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.page != "Wallet":
    st.session_state.confirm_remove = None

# ── Sidebar Navigation ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:24px 20px 18px; border-bottom:1px solid var(--border); background:linear-gradient(180deg,rgba(14,165,233,0.03) 0%,transparent 100%)">
      <div style="font-family:var(--head);font-size:1.35rem;font-weight:800; color:var(--cyan);letter-spacing:0.05em">&#x2B21; KRYPTIKA</div>
      <div style="font-size:0.65rem;color:var(--txt-4);letter-spacing:0.1em; margin-top:6px;text-transform:uppercase;font-weight:600">Blockchain Terminal</div>
    </div>
    """, unsafe_allow_html=True)

    presets = ["http://localhost:5000", "http://localhost:5001", "http://localhost:5002", "custom..."]
    with st.container():
        st.markdown('<div style="padding:16px 16px 12px;border-bottom:1px solid var(--border)">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:var(--head);font-size:0.6rem;letter-spacing:0.1em;text-transform:uppercase; color:var(--txt-3);margin-bottom:8px;font-weight:700">Connected Node</div>', unsafe_allow_html=True)
        
        chosen = st.selectbox("node_sel", presets, index=presets.index(st.session_state.node_url) if st.session_state.node_url in presets else 3, label_visibility="collapsed", key="node_preset")
        
        if chosen == "custom...":
            custom_url = st.text_input("custom_url", value="", placeholder="http://host:port", label_visibility="collapsed")
            if custom_url:
                if not custom_url.startswith("http"): custom_url = "http://" + custom_url
                custom_url = custom_url.rstrip("/")
                try:
                    r = requests.get(f"{custom_url}/status", timeout=2)
                    r.raise_for_status()
                    st.session_state.node_url = custom_url
                    st.rerun()
                except Exception:
                    st.error("Invalid node URL or node is offline.")
        elif chosen != st.session_state.node_url:
            st.session_state.node_url = chosen
            st.rerun()

        status_data, status_err = api("GET", "/status")
        if status_err:
            st.markdown('<span style="color:var(--red);font-size:0.75rem;font-weight:700">&#x25CF; OFFLINE</span>', unsafe_allow_html=True)
        else:
            h  = status_data.get("height", "?")
            mp = status_data.get("mempool", "?")
            p  = status_data.get("peers", [])
            if isinstance(p, list): p = len(p)
            st.markdown(f'<span style="color:var(--green-dk);font-size:0.75rem;font-weight:700">&#x25CF; ONLINE</span><div style="font-size:0.7rem;color:var(--txt-3);margin-top:6px;font-weight:500">H:{h} &nbsp;·&nbsp; MP:{mp} &nbsp;·&nbsp; P:{p}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    pages = [
        ("Overview",         "▦"),
        ("Chain Explorer",   "▣"),
        ("Mempool",          "□"),
        ("Wallet",           "○"),
        ("Send",             "→"),
        ("Mine",             "◆"),
        ("Peers",            "◎"),
        ("Chain Validator",  "✓"),
    ]
    st.markdown('<div style="padding:16px 14px 0">', unsafe_allow_html=True)
    for p_name, icon in pages:
        if st.button(f"{icon}  {p_name}", key=f"nav_{p_name}", use_container_width=True):
            st.session_state.page = p_name
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    col_r, col_a = st.columns(2)
    with col_r:
        if st.button("↺ Refresh", use_container_width=True): st.rerun()
    with col_a:
        st.toggle("Auto", key="auto_refresh")

page = st.session_state.page

# ── Page Routers ───────────────────────────────────────────────────────────────
if page == "Overview":
    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="ph">
      <div class="ph-title">Overview</div>
      <div class="ph-sub">Live Network State</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div class="hero-box">
      <h2>Welcome to Kryptika Terminal</h2>
      <p>Your responsive, decentralized command center. Connect a node, manage your wallets, track the mempool, and start mining KRY securely.</p>
    </div>
    """, unsafe_allow_html=True)

    if status_err:
        offline_banner(status_err)
        st.stop()

    height  = status_data.get("height", 0)
    mempool = status_data.get("mempool", 0)
    peers   = status_data.get("peers", [])
    uptime  = status_data.get("uptime_secs", 0)
    if isinstance(peers, list): peers = len(peers)
    uptime_fmt = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m" if uptime else "?"

    c1, c2, c3, c4 = st.columns(4)
    stat_tile(c1, height, "Chain Height", "blocks")
    stat_tile(c2, mempool, "Mempool", "pending tx")
    stat_tile(c3, peers, "Peers", "connected")
    stat_tile(c4, uptime_fmt, "Node Uptime", "hh mm")

    chain_data, chain_err = api("GET", "/chain")
    if not chain_err:
        blocks = chain_data if isinstance(chain_data, list) else []
        if blocks:
            last_block = blocks[-1]
            lh = last_block.get("hash", "---")
            lt = ts(last_block.get("timestamp", 0))
            st.markdown(f'<div class="note-txt" style="margin:8px 0 24px">Latest block: <span class="hash-txt" style="color:var(--cyan);font-weight:600;font-size:0.65rem;">{lh}</span> &nbsp;·&nbsp; {lt}</div>', unsafe_allow_html=True)

        col_chart1, col_chart2 = st.columns([3, 2])

        with col_chart1:
            st.markdown('<div class="sh">Transactions per Block</div>', unsafe_allow_html=True)
            if len(blocks) > 1:
                chart_blocks = blocks[-100:]
                idxs  = [b["index"] for b in chart_blocks]
                txcnt = [len(b.get("transactions", [])) for b in chart_blocks]
                
                cumul_start = sum(len(b.get("transactions", [])) for b in blocks[:-100]) if len(blocks) > 100 else 0
                cumul, s = [], cumul_start
                for t in txcnt:
                    s += t; cumul.append(s)

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=idxs, y=txcnt, name="Tx / Block", marker_color="rgba(14,165,233,0.3)",
                    marker_line_color="#0EA5E9", marker_line_width=1, hovertemplate="Block #%{x}<br>%{y} tx<extra></extra>",
                ))
                fig.add_trace(go.Scatter(
                    x=idxs, y=cumul, name="Cumulative", line=dict(color="#3B82F6", width=2.5), mode="lines", yaxis="y2",
                    hovertemplate="Block #%{x}<br>Total: %{y}<extra></extra>",
                ))
                fig.update_layout(
                    paper_bgcolor="#FFFFFF", plot_bgcolor="#F8FAFC", font=dict(color="#475569", family="JetBrains Mono", size=10),
                    xaxis=dict(showgrid=False, color="#64748B"), yaxis=dict(showgrid=True, gridcolor="#E2E8F0", color="#64748B", zeroline=False),
                    yaxis2=dict(overlaying="y", side="right", showgrid=False, color="#64748B"),
                    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10, color="#334155")), margin=dict(l=0, r=0, t=8, b=0), height=220, bargap=0.3,
                )
                st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.caption("Mine more blocks to see charts.")

        with col_chart2:
            st.markdown('<div class="sh">Mining Intervals (s)</div>', unsafe_allow_html=True)
            if len(blocks) > 2:
                chart_blocks = blocks[-100:]
                gaps = [round(chart_blocks[i]["timestamp"] - chart_blocks[i-1]["timestamp"], 1) for i in range(1, len(chart_blocks))]
                avg_gap = sum(gaps) / len(gaps) if gaps else 0

                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=[b["index"] for b in chart_blocks[1:]], y=gaps, fill="tozeroy", fillcolor="rgba(16,185,129,0.1)",
                    line=dict(color="#10B981", width=2), mode="lines", hovertemplate="Block #%{x}<br>%{y}s<extra></extra>",
                ))
                fig2.add_hline(y=avg_gap, line_dash="dot", line_color="rgba(16,185,129,0.5)", line_width=2)
                fig2.update_layout(
                    paper_bgcolor="#FFFFFF", plot_bgcolor="#F8FAFC", font=dict(color="#475569", family="JetBrains Mono", size=10),
                    xaxis=dict(showgrid=False, color="#64748B"), yaxis=dict(showgrid=True, gridcolor="#E2E8F0", color="#64748B", title="", zeroline=False),
                    margin=dict(l=0, r=0, t=8, b=0), height=220, showlegend=False,
                )
                st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="note-txt" style="text-align:center">avg interval: <span style="color:var(--green-dk);font-weight:600">{avg_gap:.1f}s</span></div>', unsafe_allow_html=True)
            else:
                st.caption("Mine more blocks to see intervals.")

    st.markdown('<div class="sh">Recent Activity</div>', unsafe_allow_html=True)
    if not chain_err and blocks:
        for b in list(reversed(blocks))[:8]:
            stamp = ts(b.get("timestamp", 0))
            for tx in b.get("transactions", []):
                is_cb = tx.get("sender") == "COINBASE"
                typ   = "REWARD" if is_cb else "TRANSFER"
                hi    = "hi" if is_cb else ""
                st.markdown(f'<div class="act-line"><span class="act-time">{stamp}</span><span class="act-msg {hi}">Block #{b["index"]} &nbsp;{typ}&nbsp; <b>{fmt(tx.get("amount","?"))} KRY</b></span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Chain Explorer":
    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="ph">
      <div class="ph-title">Chain Explorer</div>
      <div class="ph-sub">Browse All Blocks</div>
    </div>""", unsafe_allow_html=True)

    chain_data, chain_err = api("GET", "/chain")
    if chain_err:
        offline_banner(chain_err)
    else:
        blocks = chain_data if isinstance(chain_data, list) else []
        col_s, col_info = st.columns([3, 1])
        with col_s:
            search = st.text_input("search_block", placeholder="Search by index or hash fragment...", label_visibility="collapsed")
        with col_info:
            st.markdown(f'<div class="note-txt" style="padding-top:10px;text-align:right"><span style="color:var(--cyan);font-weight:700">{len(blocks)}</span> blocks total</div>', unsafe_allow_html=True)

        filtered = list(reversed(blocks))
        if search.strip():
            s = search.strip().lower()
            filtered = [b for b in filtered if str(b.get("index")) == s or s in b.get("hash", "").lower()]
            if not filtered: st.warning("No blocks matched.")

        for i, block in enumerate(filtered[:100]): 
            idx   = block.get("index", "?")
            bh    = block.get("hash", "---")
            txs   = block.get("transactions", [])
            nonce = block.get("nonce", "?")
            stamp = ts_short(block.get("timestamp", 0))

            with st.expander(f"#{idx}  ·  {len(txs)} tx  ·  {bh[:20]}…  ·  {stamp}", expanded=(i == 0)):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown('<div class="tlabel">Block Hash</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="hash-txt" style="color:var(--cyan); font-size:0.65rem;">{bh}</div>', unsafe_allow_html=True)
                with col2:
                    st.markdown('<div class="tlabel">Previous Hash</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="hash-txt" style="font-size:0.65rem;">{block.get("prev_hash", "---")}</div>', unsafe_allow_html=True)

                mc1, mc2, mc3 = st.columns(3)
                mc1.markdown(f'<div class="tlabel" style="margin-top:16px">Nonce</div><div style="color:var(--txt-1);font-size:1rem;font-weight:700">{nonce}</div>', unsafe_allow_html=True)
                mc2.markdown(f'<div class="tlabel" style="margin-top:16px">Timestamp</div><div style="color:var(--txt-2);font-size:0.8rem;font-weight:500">{ts(block.get("timestamp",0))}</div>', unsafe_allow_html=True)
                mc3.markdown(f'<div class="tlabel" style="margin-top:16px">Transactions</div><div style="color:var(--blue);font-size:1rem;font-weight:700">{len(txs)}</div>', unsafe_allow_html=True)

                if txs:
                    st.markdown('<div class="tlabel" style="margin-top:20px;border-bottom:1px solid var(--border);padding-bottom:8px;margin-bottom:12px">Transactions</div>', unsafe_allow_html=True)
                    for tx in txs:
                        sender    = tx.get("sender", "COINBASE")
                        recipient = tx.get("recipient", "---")
                        amount    = tx.get("amount", 0)
                        fee       = tx.get("fee", 0)
                        note      = tx.get("note", "")
                        is_cb     = (sender == "COINBASE")
                        typ_cls   = "b-reward" if is_cb else "b-recv"
                        typ_lbl   = "COINBASE" if is_cb else "TRANSFER"
                        st.markdown(f'<div class="trow"><span class="badge {typ_cls}">{typ_lbl}</span><span class="tx-addr" style="font-size:0.65rem;">{sender}</span><span class="tx-arrow">→</span><span class="tx-addr" style="font-size:0.65rem;">{recipient}</span><span class="tx-amount">{fmt(amount)} KRY</span><span class="tx-fee">fee {fmt(fee)}</span></div>' + (f'<div class="note-txt" style="padding-left:96px; word-break:break-all; font-size:0.65rem;">"{note}"</div>' if note else ""), unsafe_allow_html=True)
        if len(filtered) > 100:
            st.markdown('<div class="note-txt" style="text-align:center;margin-top:16px;">(Showing last 100 matched blocks to prevent browser lag)</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Mempool":
    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="ph">
      <div class="ph-title">Mempool</div>
      <div class="ph-sub">Pending Transactions</div>
    </div>""", unsafe_allow_html=True)

    pending_data, pending_err = api("GET", "/transactions/pending")
    if pending_err:
        offline_banner(pending_err)
    else:
        txs        = pending_data.get("transactions", [])
        total_fees = sum(float(tx.get("fee", 0)) for tx in txs)
        total_vol  = sum(float(tx.get("amount", 0)) for tx in txs)

        c1, c2, c3 = st.columns(3)
        stat_tile(c1, len(txs), "Pending Transactions", "unconfirmed")
        stat_tile(c2, f"{total_vol:.4f}", "Total Volume", "KRY")
        stat_tile(c3, f"{total_fees:.4f}", "Total Fees", "KRY bonus")

        st.markdown('<div class="sh">Unconfirmed Transactions</div>', unsafe_allow_html=True)

        if not txs:
            st.markdown('<div style="padding:60px;text-align:center;color:var(--txt-4);font-size:0.8rem;letter-spacing:0.1em;text-transform:uppercase;font-weight:600">— Mempool empty —</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="col-hdr t"><span>Type</span><span>Sender</span><span></span><span>Recipient</span><span style="text-align:right">Amount</span><span style="text-align:right">Fee</span></div>', unsafe_allow_html=True)
            for tx in txs:
                st.markdown(f'<div class="trow"><span class="badge b-pend">PENDING</span><span class="tx-addr" style="font-size:0.65rem;">{tx.get("sender","---")}</span><span class="tx-arrow">→</span><span class="tx-addr" style="font-size:0.65rem;">{tx.get("recipient","---")}</span><span class="tx-amount">{fmt(tx.get("amount",0))} KRY</span><span class="tx-fee">{fmt(tx.get("fee",0))}</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Wallet":
    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="ph">
      <div class="ph-title">Wallet</div>
      <div class="ph-sub">Key Management</div>
    </div>""", unsafe_allow_html=True)

    tab_my, tab_new, tab_hist = st.tabs(["My Wallets", "Create / Import", "History"])

    with tab_my:
        if not st.session_state.wallets:
            st.markdown('<div style="padding:60px;text-align:center;color:var(--txt-4);font-size:0.8rem;letter-spacing:0.1em;text-transform:uppercase;font-weight:600">— No wallets yet —</div>', unsafe_allow_html=True)
        else:
            for name, w in list(st.session_state.wallets.items()):
                addr = w["address"]
                bal_data, bal_err = api("GET", f"/balance/{addr}")
                balance   = fmt(bal_data.get("balance", 0)) if not bal_err else "?"
                is_active = (st.session_state.active_wallet == name)

                st.markdown(f'<div class="wcard {"active" if is_active else ""}">' + ('<div class="wcard-badge">DEFAULT</div>' if is_active else "") + f'<div class="wcard-name">{name}</div><div class="wcard-addr" style="font-size:0.65rem;">{addr}</div><div class="wcard-balance">{balance}<span class="wcard-unit">KRY</span></div></div>', unsafe_allow_html=True)

                ba, bb, bc, _ = st.columns([1, 1, 1, 3])
                if ba.button("Make Default", key=f"act_{name}"):
                    st.session_state.active_wallet = name
                    _save_db(st.session_state.wallets, st.session_state.active_wallet)
                    st.rerun()

                if bb.button("Remove", key=f"rm_{name}"):
                    st.session_state.confirm_remove = name

                if st.session_state.confirm_remove == name:
                    confirm_input = st.text_input(f"Type '{name}' to confirm deletion", key=f"confirm_input_{name}")
                    col_yes, col_no, _ = st.columns([1, 1, 4])
                    if col_yes.button("⚠ Delete", key=f"confirm_yes_{name}"):
                        if confirm_input == name:
                            del st.session_state.wallets[name]
                            if st.session_state.active_wallet == name:
                                st.session_state.active_wallet = None
                            _save_db(st.session_state.wallets, st.session_state.active_wallet)
                            st.session_state.confirm_remove = None
                            st.rerun()
                        else:
                            st.error("Name doesn't match. Deletion cancelled.")
                    if col_no.button("Cancel", key=f"confirm_no_{name}"):
                        st.session_state.confirm_remove = None
                        st.rerun()

    with tab_new:
        col_gen, col_imp = st.columns(2)
        with col_gen:
            st.markdown('<div class="sh">Generate New Wallet</div>', unsafe_allow_html=True)
            new_name = st.text_input("Wallet name", placeholder="alice", key="new_wname")
            if st.button("Generate Keypair", key="btn_gen"):
                if not new_name.strip(): st.error("Enter a name.")
                elif new_name in st.session_state.wallets: st.error("Name already taken.")
                else:
                    try:
                        wlt = Wallet(name=new_name.strip())
                        priv_val = getattr(wlt, 'private_key_hex', getattr(wlt, 'private_key', ''))
                        priv_hex = priv_val() if callable(priv_val) else priv_val
                        
                        st.session_state.wallets[new_name] = {"address": wlt.address, "private_key_hex": priv_hex}
                        st.session_state.active_wallet = new_name
                        _save_db(st.session_state.wallets, st.session_state.active_wallet)
                        
                        st.success(f"Wallet '{new_name}' generated.")
                        st.code(wlt.address, language=None)
                        st.markdown(f'<div class="note-txt" style="margin-top:10px;font-weight:500;color:#B45309">⚠ Save your private key — it cannot be recovered:<br><span style="word-break:break-all;overflow-wrap:break-word;font-family:var(--mono);font-size:0.6rem;color:var(--txt-1)">{priv_hex}</span></div>', unsafe_allow_html=True)
                    except Exception as exc:
                        st.error(f"Failed: {exc}")

        with col_imp:
            st.markdown('<div class="sh">Import Existing Wallet</div>', unsafe_allow_html=True)
            imp_name = st.text_input("Name", placeholder="bob", key="imp_wname")
            imp_priv = st.text_input("Private key (hex)", type="password", key="imp_priv")
            if st.button("Import", key="btn_imp"):
                if not imp_name.strip() or not imp_priv.strip(): st.error("Both fields are required.")
                else:
                    try:
                        priv_hex = imp_priv.strip()
                        wlt = Wallet.from_private_key(priv_hex, name=imp_name.strip())
                        st.session_state.wallets[imp_name] = {"address": wlt.address, "private_key_hex": priv_hex}
                        st.session_state.active_wallet = imp_name
                        _save_db(st.session_state.wallets, st.session_state.active_wallet)
                        
                        st.success(f"Wallet '{imp_name}' imported.")
                        st.code(wlt.address, language=None)
                    except Exception as exc:
                        st.error(f"Import failed: {exc}")

        st.markdown('<div class="sh" style="margin-top:32px">Lookup Any Address</div>', unsafe_allow_html=True)
        lookup = st.text_input("Address (64 hex chars)", key="lookup_addr")
        if lookup.strip():
            bd, be = api("GET", f"/balance/{lookup.strip()}")
            if be: st.error(be)
            else: st.markdown(f'<div class="mine-box"><div class="mine-num" style="color:var(--txt-1)">{fmt(bd.get("balance",0))}</div><div class="mine-label">KRY Balance</div></div>', unsafe_allow_html=True)

    with tab_hist:
        if not st.session_state.wallets:
            st.info("Create a wallet first.")
        else:
            chosen = st.selectbox("Wallet", list(st.session_state.wallets.keys()), key="hist_sel")
            addr   = st.session_state.wallets[chosen]["address"]
            hd, he = api("GET", f"/history/{addr}")
            if he: offline_banner(he)
            else:
                txs = hd.get("history", [])
                if not txs:
                    st.markdown('<div style="padding:50px;text-align:center;color:var(--txt-4);font-size:0.8rem;letter-spacing:0.1em;text-transform:uppercase;font-weight:600">— No confirmed transactions yet —</div>', unsafe_allow_html=True)
                else:
                    running, rows = 0.0, []
                    for tx in txs:
                        is_in = tx.get("recipient") == addr
                        is_cb = tx.get("sender") == "COINBASE"
                        amt   = float(tx.get("amount", 0))
                        fee   = float(tx.get("fee", 0))
                        if is_in:
                            running += amt
                            delta, typ_cls, typ_lbl = f"+{fmt(amt)}", "b-reward" if is_cb else "b-recv", "REWARD" if is_cb else "IN"
                        else:
                            running -= (amt + fee)
                            delta, typ_cls, typ_lbl = f"-{fmt(amt+fee)}", "b-sent", "OUT"
                        rows.append((tx, typ_cls, typ_lbl, delta, round(running, 8)))

                    st.markdown(f'<div class="note-txt" style="margin-bottom:16px"><span style="color:var(--cyan);font-weight:700">{len(rows)}</span> confirmed transaction(s)</div>', unsafe_allow_html=True)

                    for tx, typ_cls, typ_lbl, delta, bal in reversed(rows):
                        note  = tx.get("note", "")
                        blk   = tx.get("block", "?")
                        stamp = ts_short(tx.get("timestamp", 0))
                        plus  = delta.startswith("+")
                        st.markdown(f'<div class="trow" style="grid-template-columns:80px 1fr 20px 1fr 90px 90px 80px"><span class="badge {typ_cls}">{typ_lbl}</span><span class="tx-addr" style="font-size:0.65rem;">{tx.get("sender","---")}</span><span class="tx-arrow">→</span><span class="tx-addr" style="font-size:0.65rem;">{tx.get("recipient","---")}</span><span class="tx-amount" style="color:{"var(--green-dk)" if plus else "var(--red)"}">{delta}</span><span class="tx-fee">bal {fmt(bal)}</span><span class="tx-fee">#{blk} {stamp}</span></div>' + (f'<div class="note-txt" style="padding:0 0 8px 104px; word-break:break-all; font-size:0.65rem;">"{note}"</div>' if note else ""), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Send":
    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="ph">
      <div class="ph-title">Send</div>
      <div class="ph-sub">Sign & Broadcast Transaction</div>
    </div>""", unsafe_allow_html=True)

    wallets = st.session_state.wallets
    if not wallets:
        st.warning("Create a wallet first.")
        st.stop()

    col_form, col_info = st.columns([3, 2])

    with col_form:
        sender_name = st.selectbox("From wallet", list(wallets.keys()), index=list(wallets.keys()).index(st.session_state.active_wallet) if st.session_state.active_wallet in wallets else 0, key="send_from")
        sender_w = wallets[sender_name]
        bal_data, bal_err = api("GET", f"/balance/{sender_w['address']}")
        avail = float(bal_data.get("balance", 0)) if not bal_err else 0.0

        recipient = st.text_input("Recipient address", placeholder="64-character hex", key="send_to_ui")
        amount    = st.number_input("Amount (KRY)", min_value=0.00000001, value=float(st.session_state.send_amt_ui), step=0.1, format="%.8f", key="send_amt_ui")
        fee       = st.number_input("Fee (KRY)", min_value=0.0, value=float(st.session_state.send_fee_ui), step=0.01, format="%.8f", key="send_fee_ui")
        note      = st.text_input("Note (optional)", value=st.session_state.send_note_ui, placeholder="what is this for?", key="send_note_ui").strip()

    with col_info:
        st.markdown('<div class="sh">Transaction Summary</div>', unsafe_allow_html=True)
        total = amount + fee
        remain_color = "var(--green-dk)" if avail - total >= 0 else "var(--red)"
        st.markdown(f"""
        <div class="sbox">
          <div class="srow"><span class="skey">From</span><span class="sval">{sender_name}</span></div>
          <div class="srow"><span class="skey">Balance</span><span class="sval">{fmt(avail)} KRY</span></div>
          <div class="srow"><span class="skey">Amount</span><span class="sval">{fmt(amount)} KRY</span></div>
          <div class="srow"><span class="skey">Fee</span><span class="sval">{fmt(fee)} KRY</span></div>
          <div class="srow"><span class="skey">Total Out</span><span class="sval" style="color:var(--cyan)">{fmt(total)} KRY</span></div>
          <div class="srow">
            <span class="skey">Remaining</span>
            <span class="sval" style="color:{remain_color}">{fmt(avail - total)} KRY</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        if not bal_err and avail - total < 0:
            st.error("Insufficient balance.")

    st.markdown("---")
    if st.button("Sign & Broadcast  →", key="btn_send"):
        r_addr = recipient.strip()
        err_msg = None
        if not r_addr: err_msg = "Recipient address is required."
        elif len(r_addr) != 64: err_msg = "Address must be exactly 64 hex characters."
        elif not all(c in "0123456789abcdefABCDEF" for c in r_addr): err_msg = "Address must contain only hex characters (0-9, a-f)."
        elif not bal_err and total > avail: err_msg = "Insufficient balance."

        if err_msg:
            st.error(err_msg)
        else:
            try:
                priv_hex = sender_w.get("private_key_hex") or sender_w.get("private_key")
                wlt = Wallet.from_private_key(priv_hex, name=sender_name)
                
                tx = Transaction.create(wlt, r_addr, float(amount), float(fee), note)
                result, err = api("POST", "/transactions/new", tx.to_dict())
                
                if err: st.error(f"Broadcast failed: {err}")
                else:
                    st.session_state.last_tx_id = tx.tx_id
                    st.success("Transaction broadcast to node!")
                    st.markdown(f'<div class="hash-box" style="font-size:0.65rem;">TX ID: {tx.tx_id}</div>', unsafe_allow_html=True)
                    st.session_state.send_to_ui = ""
                    st.session_state.send_amt_ui = 1.0
                    st.session_state.send_fee_ui = 0.2
                    st.session_state.send_note_ui = ""
                    st.rerun()
            except Exception as exc:
                st.error(f"Signing failed: {exc}")

    if st.session_state.last_tx_id:
        st.markdown(f'<div class="note-txt" style="margin-top:16px;font-weight:500">Last tx: <span class="hash-txt" style="color:var(--txt-1); font-size:0.65rem;">{st.session_state.last_tx_id}</span> — mine a block to confirm.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Mine":
    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="ph">
      <div class="ph-title">Mine</div>
      <div class="ph-sub">Proof of Work</div>
    </div>""", unsafe_allow_html=True)

    wallets = st.session_state.wallets
    if not wallets:
        st.warning("Create a wallet first — mining reward needs an address.")
        st.stop()

    col_l, col_r = st.columns([2, 3])

    with col_l:
        miner_name = st.selectbox("Reward wallet", list(wallets.keys()), index=list(wallets.keys()).index(st.session_state.active_wallet) if st.session_state.active_wallet in wallets else 0, key="mine_wallet")
        miner_addr = wallets[miner_name]["address"]

        st.markdown(f'<div class="note-txt" style="margin-bottom:20px;font-weight:500;">Reward address:<br><span style="color:var(--txt-2);font-family:var(--mono);font-size:0.6rem;word-break:break-all;overflow-wrap:break-word;">{miner_addr}</span></div>', unsafe_allow_html=True)

        pd, _ = api("GET", "/transactions/pending")
        mp_count = len(pd.get("transactions", [])) if pd else 0

        st.markdown(f"""
        <div class="mine-box">
          <div class="mine-num">{mp_count}</div>
          <div class="mine-label">Pending transactions</div>
        </div>
        """, unsafe_allow_html=True)

        if not status_err:
            st.markdown('<div class="sh" style="margin-top:24px">Node Info</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="sbox" style="margin-top:0;">
              <div class="srow"><span class="skey">Height</span><span class="sval">{status_data.get("height","?")}</span></div>
              <div class="srow"><span class="skey">Difficulty</span><span class="sval">{status_data.get("difficulty","?")} zeros</span></div>
              <div class="srow"><span class="skey">Base Reward</span><span class="sval">10.0 KRY</span></div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("Start Mining  →", key="btn_mine"):
            with st.spinner("Mining — Proof of Work in progress…"):
                result, err = api("GET", f"/mine?address={miner_addr}", timeout=180)
            if err:
                st.error(f"Mining failed: {err}")
            else:
                st.session_state.last_mine = result
                st.rerun()

    with col_r:
        st.markdown('<div class="sh" style="margin-top:0;">Last Mining Result</div>', unsafe_allow_html=True)
        last = st.session_state.last_mine
        if last:
            idx    = last.get("index", "?")
            nonce  = last.get("nonce", "?")
            reward = last.get("miner_reward", "?")
            bh     = last.get("hash", "---")
            txcnt  = last.get("transactions", "?")
            st.markdown(f"""
            <div class="rbox" style="margin-top:0;">
              <div class="rrow"><span class="rkey">Block Index</span><span class="rval">#{idx}</span></div>
              <div class="rrow"><span class="rkey">Txs Confirmed</span><span class="rval" style="color:var(--txt-1)">{txcnt}</span></div>
              <div class="rrow"><span class="rkey">Nonce Found</span><span class="rval" style="color:var(--txt-1)">{f"{nonce:,}" if isinstance(nonce, int) else nonce}</span></div>
              <div class="rrow"><span class="rkey">Miner Reward</span><span class="rval" style="color:var(--green-dk)">{fmt(reward)} KRY</span></div>
            </div>
            <div class="hash-box" style="margin-top:12px; font-size:0.65rem;">{bh}</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="padding:60px;text-align:center;color:var(--txt-4);font-size:0.8rem;letter-spacing:0.1em;text-transform:uppercase;font-weight:600">— No blocks mined this session —</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Peers":
    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="ph">
      <div class="ph-title">Peers</div>
      <div class="ph-sub">P2P Network</div>
    </div>""", unsafe_allow_html=True)

    peers_data, peers_err = api("GET", "/peers")
    if peers_err:
        offline_banner(peers_err)
    else:
        peers = peers_data.get("peers", [])

        c1, c2 = st.columns(2)
        stat_tile(c1, len(peers), "Connected Peers", "nodes")
        c2.markdown(f'<div class="tile"><div class="tile-label">This Node</div><div class="tile-val sm" style="color:var(--cyan)">{st.session_state.node_url.replace("http://","")}</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="sh">Connected Nodes</div>', unsafe_allow_html=True)
        if not peers:
            st.markdown('<div style="padding:50px;text-align:center;color:var(--txt-4);font-size:0.8rem;letter-spacing:0.1em;text-transform:uppercase;font-weight:600">— No peers connected —</div>', unsafe_allow_html=True)
        else:
            for peer in peers:
                st.markdown(f'<div class="peer-row"><span class="peer-dot">●</span><span class="peer-addr" style="font-size:0.65rem;">{peer}</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="sh" style="margin-top:32px">Manage Peers</div>', unsafe_allow_html=True)
    col_add, col_sync = st.columns(2)

    with col_add:
        new_peer = st.text_input("Add peer address", placeholder="http://localhost:5001", key="new_peer")
        if st.button("Add Peer", key="btn_add_peer"):
            target_peer = new_peer.strip()
            if not target_peer: st.error("Enter an address.")
            else:
                if not target_peer.startswith("http"): target_peer = "http://" + target_peer
                target_peer = target_peer.rstrip("/")
                local_node = st.session_state.node_url

                result, err = api("POST", "/peers/add", {"address": target_peer})
                if err: st.error(f"Local addition failed: {err}")
                else:
                    try:
                        requests.post(f"{target_peer}/peers/add", json={"address": local_node}, timeout=3)
                        st.success(f"✓ Mutual connection established: {local_node} ⟷ {target_peer}")
                    except Exception:
                        st.warning(f"Added {target_peer} locally, but the remote node didn't respond to the mutual handshake. Is it online?")
                    st.rerun()

    with col_sync:
        st.markdown('<div class="note-txt" style="margin-bottom:12px;font-weight:500">Pull the longest valid chain from all peers.</div>', unsafe_allow_html=True)
        if st.button("Sync with Peers", key="btn_sync"):
            with st.spinner("Syncing…"):
                result, err = api("GET", "/peers/sync")
            if err: st.error(err)
            else:
                replaced = result.get("replaced", False)
                height   = result.get("height", "?")
                if replaced: st.success(f"Chain updated. New height: {height}")
                else: st.info(f"Already on the longest chain. Height: {height}")
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Chain Validator":
    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="ph">
      <div class="ph-title">Chain Validator</div>
      <div class="ph-sub">Verify Chain Integrity</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="note-txt" style="margin-bottom:24px;font-size:0.85rem;color:var(--txt-2);line-height:1.6">Fetches the full chain from the node and verifies: hash linkage, proof-of-work, and transaction signatures. Any tampered block is flagged.</div>', unsafe_allow_html=True)

    if st.button("Run Chain Validation", key="btn_validate"):
        with st.spinner("Fetching and validating chain…"):
            val_data, val_err = api("GET", "/validate")
            if val_err:
                chain_data, chain_err = api("GET", "/chain")
                if chain_err:
                    offline_banner(chain_err)
                else:
                    blocks = chain_data if isinstance(chain_data, list) else []
                    issues = []

                    def _block_hash(b: dict) -> str:
                        payload = {k: v for k, v in b.items() if k != "hash"}
                        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

                    for i, block in enumerate(blocks):
                        computed = _block_hash(block)
                        stored   = block.get("hash", "")
                        if computed != stored: issues.append(f"Block #{block.get('index','?')}: hash mismatch")
                        if i > 0:
                            prev_hash = blocks[i-1].get("hash", "")
                            if block.get("prev_hash") != prev_hash: issues.append(f"Block #{block.get('index','?')}: broken link")
                        _status, _serr = api("GET", "/status")
                        diff = _status.get("difficulty", 2) if not _serr else 2
                        if not stored.startswith("0" * int(diff)): issues.append(f"Block #{block.get('index','?')}: PoW invalid")

                    if issues:
                        st.error(f"⚠ Chain has {len(issues)} issue(s):")
                        for issue in issues: st.markdown(f'<div class="err-box">{issue}</div>', unsafe_allow_html=True)
                    else:
                        st.success(f"✓ Chain valid — {len(blocks)} blocks, all hashes/links/PoW verified.")
                        st.markdown(f'<div class="hash-box" style="margin-top:16px;background:var(--green-dim);color:var(--green-dk);border-color:rgba(16,185,129,0.3)">Blocks checked: {len(blocks)} &nbsp;·&nbsp; Issues found: 0 &nbsp;·&nbsp; Chain is VALID</div>', unsafe_allow_html=True)
            else:
                is_valid = val_data.get("valid", val_data.get("is_valid", False))
                reason   = val_data.get("reason", val_data.get("message", ""))
                if is_valid: st.success("✓ Node reports chain is VALID.")
                else: st.error(f"⚠ Node reports chain is INVALID: {reason}")
    st.markdown('</div>', unsafe_allow_html=True)

# ── Non-blocking Polling (HTML Script Injection) ───────────────────────────────
if st.session_state.get("auto_refresh"):
    components.html(
        "<script>setTimeout(function(){window.parent.location.reload()}, 5000);</script>", 
        height=0, 
        width=0
    )