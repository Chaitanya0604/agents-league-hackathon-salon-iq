"""
Salon IQ — Streamlit Chat UI v2
Single conversation thread. Status pills for silent agents.
Run: streamlit run app.py
"""

import asyncio
import queue
import threading

import streamlit as st

from orchestrator import (
    PROJECT_ENDPOINT,
    AGENT_STATUS,
    SalonSession,
    route,
    generate_invoice_pdf,
    extract_invoice_block,
    is_booking_request,
)

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Glamour & Co.",
    page_icon="💅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# CSS  — aesthetics from v1, text uniformity fixes
# ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

:root {
  --cream:      #fdf8f3;
  --warm-white: #fffcf8;
  --brown-dark: #2d1f14;
  --brown-mid:  #4a3728;
  --brown-lite: #6b5242;
  --gold:       #c9a98a;
  --gold-light: #e8d5bc;
  --border:     #e8ddd5;
  --text-main:  #2d1f14;
  --text-muted: #9e8877;
}

/* ── Base ── */
.stApp {
  background: linear-gradient(135deg, #fdf8f3 0%, #f5ece0 100%);
  font-family: 'Inter', sans-serif;
}
#MainMenu, footer, header { visibility: hidden; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #2d1f14 0%, #1a110a 100%);
  border-right: 1px solid #4a3728;
}
[data-testid="stSidebar"] * { color: #f5ece4 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  color: #c9a98a !important;
  font-family: 'Playfair Display', serif !important;
}
[data-testid="stSidebar"] hr { border-color: #4a3728 !important; margin: 12px 0 !important; }
[data-testid="stSidebar"] .stButton > button {
  background: linear-gradient(135deg, #4a3728, #6b5242) !important;
  color: #fff !important; border: none !important;
  border-radius: 20px !important; padding: 8px 20px !important;
  font-size: 13px !important; width: 100% !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] {
  border-radius: 28px !important;
  border: 2px solid var(--gold) !important;
  box-shadow: 0 4px 20px rgba(74,55,40,.08) !important;
  background: var(--warm-white) !important;
}
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] > div > div {
  background: var(--warm-white) !important;
}
[data-testid="stChatInput"] textarea {
  font-family: 'Inter', sans-serif !important;
  font-size: 15px !important;
  color: #2d1f14 !important;
  -webkit-text-fill-color: #2d1f14 !important;
  caret-color: #2d1f14 !important;
  background: var(--warm-white) !important;
}
[data-testid="stChatInput"] textarea::placeholder {
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
  opacity: 1 !important;
}
[data-testid="stChatInput"] * { background-color: transparent !important; }
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div { background-color: var(--warm-white) !important; }

/* ── User bubble ── */
.bubble-user {
  display: flex; flex-direction: row-reverse;
  align-items: flex-end; gap: 10px; margin: 12px 0;
}
.bubble-user .avatar {
  width: 36px; height: 36px; flex-shrink: 0;
  background: linear-gradient(135deg, #4a3728, #6b5242);
  border-radius: 50%; display: flex; align-items: center;
  justify-content: center; color: #fff; font-size: 13px; font-weight: 600;
}
.bubble-user .msg {
  background: linear-gradient(135deg, #4a3728, #5c4435);
  color: #fff; padding: 12px 18px;
  border-radius: 20px 20px 4px 20px;
  font-family: 'Inter', sans-serif;
  font-size: 14px; font-weight: 400; line-height: 1.6;
  max-width: 72%;
  box-shadow: 0 2px 12px rgba(74,55,40,.2);
}

/* ── Bot bubble ── */
.bubble-bot {
  display: flex; align-items: flex-end; gap: 10px; margin: 12px 0;
}
.bubble-bot .avatar {
  width: 36px; height: 36px; flex-shrink: 0;
  background: linear-gradient(135deg, #c9a98a, #e8d5bc);
  border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-size: 18px;
}
.bubble-bot .msg {
  background: var(--warm-white); color: var(--text-main);
  padding: 14px 18px; border-radius: 20px 20px 20px 4px;
  font-family: 'Inter', sans-serif;
  font-size: 14px; font-weight: 400; line-height: 1.7;
  max-width: 78%;
  border: 1px solid var(--border);
  box-shadow: 0 2px 12px rgba(0,0,0,.05);
}
/* Normalise any nested elements inside bot bubble */
.bubble-bot .msg *,
.bubble-bot .msg p,
.bubble-bot .msg span,
.bubble-bot .msg li,
.bubble-bot .msg ul,
.bubble-bot .msg ol {
  font-family: 'Inter', sans-serif !important;
  font-size: 14px !important;
  font-weight: 400 !important;
  line-height: 1.7 !important;
  color: var(--text-main) !important;
}
.bubble-bot .msg b,
.bubble-bot .msg strong {
  font-weight: 600 !important;
}
.bubble-bot .msg h1,
.bubble-bot .msg h2,
.bubble-bot .msg h3,
.bubble-bot .msg h4 {
  font-family: 'Inter', sans-serif !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  margin: 6px 0 2px 0 !important;
}

/* ── Agent label ── */
.agent-label {
  display: inline-block;
  font-size: 10px; font-weight: 600; letter-spacing: 0.5px;
  color: var(--text-muted); text-transform: uppercase;
  margin-bottom: 4px; padding-left: 2px;
}

/* ── Status pills ── */
.status-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 14px; border-radius: 20px;
  font-family: 'Inter', sans-serif;
  font-size: 12px; font-weight: 500;
  background: var(--gold-light); color: var(--brown-mid);
  margin: 4px 0 4px 46px; border: 1px solid var(--gold);
  animation: pulse 1.5s ease-in-out infinite;
}
.status-pill.done {
  background: #d4edda; color: #155724;
  border-color: #c3e6cb; animation: none;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.6} }

/* ── Invoice ── */
.invoice-wrap {
  background: linear-gradient(135deg, #fdf8f3, #f5ece0);
  border: 1.5px solid var(--gold); border-radius: 12px;
  padding: 20px 24px; margin-top: 6px;
  box-shadow: 0 4px 20px rgba(201,169,138,.15);
}
.invoice-header {
  font-family: 'Playfair Display', serif;
  font-size: 17px; font-weight: 700; color: var(--brown-mid);
  text-align: center; margin-bottom: 2px; letter-spacing: 1px;
}
.invoice-sub {
  font-size: 10px; color: var(--text-muted);
  text-align: center; margin-bottom: 12px;
  letter-spacing: 2px; text-transform: uppercase;
}
.invoice-divider { border: none; border-top: 1px solid var(--gold-light); margin: 8px 0; }
.invoice-row {
  display: flex; justify-content: space-between;
  font-family: 'Inter', sans-serif; font-size: 13px;
  font-weight: 400; color: var(--brown-dark);
  padding: 3px 0; line-height: 1.5;
}
.invoice-row.meta {
  display: flex; gap: 12px;
  font-size: 13px; color: var(--brown-dark); padding: 2px 0;
}
.invoice-row.meta .key {
  color: var(--text-muted); min-width: 90px; font-weight: 400;
}
.invoice-row.meta .val { font-weight: 500; }
.invoice-section-label {
  font-family: 'Inter', sans-serif;
  font-size: 10px; font-weight: 600; letter-spacing: 2px;
  text-transform: uppercase; color: var(--text-muted);
  margin: 8px 0 4px 0;
}
.invoice-total-row {
  display: flex; justify-content: space-between;
  font-family: 'Playfair Display', serif;
  font-size: 15px; font-weight: 700; color: var(--brown-mid);
  margin-top: 4px;
}
.invoice-footer {
  text-align: center; color: var(--text-muted);
  font-style: italic;
  font-family: 'Inter', sans-serif; font-size: 12px;
  margin-top: 10px;
}

/* ── Welcome card ── */
.welcome-card {
  background: linear-gradient(135deg, #2d1f14 0%, #4a3728 100%);
  border-radius: 20px; padding: 32px 28px; text-align: center;
  margin-bottom: 24px; box-shadow: 0 8px 32px rgba(74,55,40,.25);
}
.welcome-title {
  font-family: 'Playfair Display', serif;
  font-size: 30px; font-weight: 700; color: #fff; margin-bottom: 4px;
}
.welcome-sub {
  font-size: 13px; color: #c9a98a; letter-spacing: 2px;
  text-transform: uppercase; margin-bottom: 12px;
}
.welcome-desc {
  font-family: 'Inter', sans-serif;
  font-size: 13px; font-weight: 400; color: #e8d5bc; line-height: 1.7;
}

/* ── Quick prompt buttons ── */
[data-testid="stColumn"]:has(.qp-btn) button {
  background: var(--warm-white) !important; color: var(--brown-mid) !important;
  border: 1.5px solid var(--gold) !important; border-radius: 20px !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important; font-weight: 400 !important;
  padding: 8px 16px !important; width: 100% !important;
}
[data-testid="stColumn"]:has(.qp-btn) button:hover {
  background: var(--gold-light) !important; border-color: var(--brown-mid) !important;
}

/* ── Download button ── */
.stDownloadButton > button {
  background: linear-gradient(135deg, #4a3728, #6b5242) !important;
  color: white !important; border: none !important;
  border-radius: 20px !important; padding: 10px 24px !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 13px !important; font-weight: 500 !important;
  width: 100% !important; margin-top: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# AGENT LABELS
# ─────────────────────────────────────────────────────────────

AGENT_LABELS = {
    "supervisor":      "💅 Concierge",
    "customer_memory": "🧠 Memory",
    "seasonal":        "🍂 Seasonal",
    "stylist":         "✂️ Stylist",
    "schedule":        "📅 Schedule",
    "pricing":         "💰 Pricing",
}

# ─────────────────────────────────────────────────────────────
# INVOICE HTML BUILDER
# ─────────────────────────────────────────────────────────────

def build_invoice_html(text: str) -> str:
    marker = "GLAMOUR & CO. — BOOKING CONFIRMATION"
    if marker not in text:
        # Plain bot message — just return escaped text preserving newlines
        return text.replace("\n", "<br>")

    dash_idx = text.find("---", max(0, text.find(marker) - 80))
    pre   = text[:dash_idx].strip()
    block = text[dash_idx:].strip()

    pre_html = (
        f"<p style='margin:0 0 10px 0;font-family:Inter,sans-serif;"
        f"font-size:14px;color:#2d1f14'>{pre}</p>"
    ) if pre else ""

    lines = block.split("\n")
    rows_html = ""
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        # Divider line
        if set(line) <= {"-", " "} and len(line) > 4:
            rows_html += '<hr class="invoice-divider">'; continue
        # Section header (e.g. SERVICES)
        if line.isupper() and "$" not in line and ":" not in line and len(line) < 30:
            rows_html += f'<div class="invoice-section-label">{line}</div>'; continue
        # TOTAL DUE
        if line.startswith("TOTAL DUE") or line.startswith("TOTAL"):
            parts = line.split("$", 1)
            amount = f"${parts[1].strip()}" if len(parts) > 1 else ""
            label  = parts[0].strip()
            rows_html += (
                f'<div class="invoice-total-row">'
                f'<span>{label}</span><span>{amount}</span>'
                f'</div>'
            ); continue
        # Footer
        if "thank you" in line.lower() or "see you" in line.lower() or "look forward" in line.lower():
            rows_html += f'<div class="invoice-footer">{line}</div>'; continue
        # Key : Value meta rows (no $)
        if ":" in line and "$" not in line:
            k, _, v = line.partition(":")
            rows_html += (
                f'<div class="invoice-row meta">'
                f'<span class="key">{k.strip()}</span>'
                f'<span class="val">{v.strip()}</span>'
                f'</div>'
            ); continue
        # Line with $ (service or subtotal/tax etc.)
        if "$" in line:
            parts = line.rsplit("$", 1)
            rows_html += (
                f'<div class="invoice-row">'
                f'<span>{parts[0].strip()}</span>'
                f'<span>${parts[1].strip()}</span>'
                f'</div>'
            ); continue
        # Plain text
        rows_html += (
            f'<p style="font-family:Inter,sans-serif;font-size:13px;'
            f'color:#6b5242;margin:2px 0">{line}</p>'
        )

    return f"""{pre_html}
<div class="invoice-wrap">
  <div class="invoice-header">✦ GLAMOUR & CO. ✦</div>
  <div class="invoice-sub">Booking Confirmation</div>
  {rows_html}
</div>"""

# ─────────────────────────────────────────────────────────────
# SESSION INIT
# ─────────────────────────────────────────────────────────────

def init():
    defaults = {
        "messages":      [],
        "customer_name": "",
        "salon_session": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if st.session_state.salon_session is None:
        st.session_state.salon_session = SalonSession()

# ─────────────────────────────────────────────────────────────
# BACKGROUND THREAD
# ─────────────────────────────────────────────────────────────

def _agent_thread(user_input: str, session: SalonSession, q: queue.Queue):
    async def _run():
        def on_chunk(text):
            q.put(("chunk", None, text))
        def on_status(agent_key, msg):
            q.put(("status", agent_key, msg))
        response = await route(user_input, session, on_chunk=on_chunk, on_status=on_status)
        q.put(("done", None, response))

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_run())
    except Exception as e:
        q.put(("error", None, str(e)))
    finally:
        loop.close()
        q.put(("finished", None, None))

# ─────────────────────────────────────────────────────────────
# RENDER
# ─────────────────────────────────────────────────────────────

def render_message(role: str, content: str, agent_key: str = "supervisor", msg_index: int = 0):
    name     = st.session_state.get("customer_name", "")
    initials = name[:2].upper() if name else "ME"

    if role == "user":
        st.markdown(f"""
        <div class="bubble-user">
          <div class="avatar">{initials}</div>
          <div class="msg">{content}</div>
        </div>""", unsafe_allow_html=True)
    else:
        label      = AGENT_LABELS.get(agent_key, "💅 Concierge")
        inner_html = build_invoice_html(content)
        is_invoice = "GLAMOUR & CO. — BOOKING CONFIRMATION" in content

        st.markdown(f"""
        <div class="bubble-bot">
          <div class="avatar">💅</div>
          <div class="msg">
            <div class="agent-label">{label}</div>
            {inner_html}
          </div>
        </div>""", unsafe_allow_html=True)

        if is_invoice:
            try:
                invoice_block = extract_invoice_block(content)
                if invoice_block:
                    pdf_bytes = generate_invoice_pdf(invoice_block)
                    st.download_button(
                        label="📄 Download Invoice PDF",
                        data=pdf_bytes,
                        file_name="glamour_co_invoice.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"pdf_{msg_index}",
                    )
            except Exception as e:
                st.caption(f"PDF unavailable: {e}")

# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────

def sidebar():
    with st.sidebar:
        st.markdown("## 💅 Glamour & Co.")
        st.markdown("*Your personal salon concierge*")
        st.divider()

        if st.button("＋ New session", use_container_width=True):
            st.session_state.messages      = []
            st.session_state.customer_name = ""
            st.session_state.salon_session = SalonSession()
            st.rerun()

        st.divider()

        st.markdown("### 💇 Our Services")
        services = [
            ("Haircut",       "$30",  "45 min"),
            ("Hair Coloring", "$80",  "120 min"),
            ("Facial",        "$70",  "90 min"),
            ("Manicure",      "$30",  "45 min"),
            ("Pedicure",      "$40",  "60 min"),
            ("Nail Art",      "$50",  "75 min"),
            ("Waxing",        "$35",  "45 min"),
            ("Eyebrow Wax",   "$15",  "20 min"),
        ]
        for name, price, dur in services:
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;"
                f"font-family:Inter,sans-serif;font-size:13px;font-weight:400;padding:3px 0'>"
                f"<span style='font-weight:500'>{name}</span>"
                f"<span style='color:#c9a98a'>{price} · {dur}</span></div>",
                unsafe_allow_html=True,
            )

        st.divider()

        st.markdown("### 🌟 Our Stylists")
        stylists = [
            ("Hailey",  "⭐ 4.78", "Hair Coloring, Facial"),
            ("Mia",     "⭐ 4.87", "Nails, Facial, Eyebrow"),
            ("Gigi",    "⭐ 4.82", "Waxing, Facial, Pedicure"),
            ("Olivia",  "⭐ 4.71", "Haircut, Coloring, Waxing"),
            ("Kendall", "⭐ 4.62", "Haircut, Nail Art, Eyebrow"),
        ]
        for name, rating, spec in stylists:
            st.markdown(
                f"<div style='padding:5px 0;border-bottom:1px solid #3d2a1e'>"
                f"<div style='display:flex;justify-content:space-between'>"
                f"<span style='font-family:Inter,sans-serif;font-weight:600;font-size:13px'>{name}</span>"
                f"<span style='font-size:11px;color:#c9a98a'>{rating}</span></div>"
                f"<div style='font-family:Inter,sans-serif;font-size:11px;font-weight:400;"
                f"color:#9e8877;margin-top:1px'>{spec}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.divider()

        st.markdown("### 🎁 Active Promotions")
        promos = [
            ("Holiday Glam",  "Hair Coloring + Facial → 10% off"),
            ("New Year Glam", "Full package → 15% off"),
            ("Valentine's",   "Nail Art + Facial → Free Eyebrow Wax"),
            ("Summer Smooth", "Waxing + Pedicure → 10% off"),
            ("Big Spender",   "Spend over $150 → 5% off"),
        ]
        for name, detail in promos:
            st.markdown(
                f"<div style='padding:4px 0;font-size:12px;font-family:Inter,sans-serif'>"
                f"<span style='color:#c9a98a;font-weight:600'>{name}</span><br>"
                f"<span style='color:#9e8877;font-weight:400'>{detail}</span></div>",
                unsafe_allow_html=True,
            )

        st.divider()
        st.caption("Powered by Microsoft Foundry · Azure AI")

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    init()
    sidebar()

    # Header
    _, col_c, _ = st.columns([1, 3, 1])
    with col_c:
        name     = st.session_state.customer_name
        greeting = f"Welcome back, {name}! 💅" if name else "Welcome to Glamour & Co."
        st.markdown(f"""
        <div class="welcome-card">
          <div class="welcome-title">{greeting}</div>
          <div class="welcome-sub">✦ Your Personal Salon Concierge ✦</div>
          <div class="welcome-desc">Book appointments · Discover seasonal offers · Get your perfect stylist</div>
        </div>
        """, unsafe_allow_html=True)

    _, chat_col, _ = st.columns([1, 6, 1])
    with chat_col:

        # Render history
        for i, msg in enumerate(st.session_state.messages):
            render_message(
                msg["role"],
                msg["content"],
                msg.get("agent_key", "supervisor"),
                msg_index=i,
            )

        # Quick prompts on empty chat
        if not st.session_state.messages:
            st.markdown(
                "<p style='text-align:center;color:#9e8877;"
                "font-family:Inter,sans-serif;font-size:13px;font-weight:400;"
                "margin:16px 0 10px 0'>✨ How can we help you today?</p>",
                unsafe_allow_html=True,
            )
            cols = st.columns(3)
            quick = [
                ("💇 Hair Coloring",       "I'd like to book a Hair Coloring"),
                ("🎂 Birthday Facial",     "I want a Facial for my birthday"),
                ("💅 Nail Art + Manicure", "Book Nail Art and Manicure please"),
            ]
            for i, (label, prompt) in enumerate(quick):
                with cols[i]:
                    st.markdown('<div class="qp-btn">', unsafe_allow_html=True)
                    if st.button(label, use_container_width=True, key=f"qp{i}"):
                        st.session_state.messages.append(
                            {"role": "user", "content": prompt, "agent_key": "user"}
                        )
                        st.session_state["_pending"] = prompt
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

        # Chat input
        user_input = st.chat_input("Ask me anything about your appointment…")
        if user_input:
            if not st.session_state.customer_name:
                for w in user_input.split():
                    w = w.strip(",.!?")
                    if w and w[0].isupper() and len(w) > 1 and w.lower() not in \
                            {"i", "hi", "hello", "hey", "book", "want", "need"}:
                        st.session_state.customer_name = w
                        break
            st.session_state.messages.append(
                {"role": "user", "content": user_input, "agent_key": "user"}
            )
            st.session_state["_pending"] = user_input
            st.rerun()

        # Process pending
        pending = st.session_state.pop("_pending", None)
        if pending:
            q: queue.Queue        = queue.Queue()
            session: SalonSession = st.session_state.salon_session

            t = threading.Thread(
                target=_agent_thread,
                args=(pending, session, q),
                daemon=True,
            )
            t.start()

            status_placeholder   = st.empty()
            response_placeholder = st.empty()
            status_pills: list[str] = []
            streamed       = ""
            final_response = ""
            final_agent    = "supervisor"

            while True:
                item = q.get()
                kind, key, data = item

                if kind == "finished":
                    break
                if kind == "error":
                    st.error(f"Error: {data}")
                    break
                if kind == "status":
                    status_pills.append(data)
                    if key:
                        final_agent = key
                    pills_html = "".join(
                        f'<div class="status-pill">⏳ {p}</div>'
                        for p in status_pills
                    )
                    status_placeholder.markdown(pills_html, unsafe_allow_html=True)
                if kind == "chunk":
                    streamed += data
                    label = AGENT_LABELS.get(final_agent, "💅 Concierge")
                    response_placeholder.markdown(
                        f'<div class="bubble-bot">'
                        f'<div class="avatar">💅</div>'
                        f'<div class="msg">'
                        f'<div class="agent-label">{label}</div>'
                        f'{streamed}▌'
                        f'</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                if kind == "done":
                    final_response = data

            t.join()

            # Clear streaming placeholders
            status_placeholder.empty()
            response_placeholder.empty()

            # Show done pills
            if status_pills:
                done_html = "".join(
                    f'<div class="status-pill done">✓ {p}</div>'
                    for p in status_pills
                )
                st.markdown(done_html, unsafe_allow_html=True)

            if final_response:
                msg_index = len(st.session_state.messages)
                st.session_state.messages.append({
                    "role":      "assistant",
                    "content":   final_response,
                    "agent_key": final_agent,
                })

                # Immediate invoice PDF download
                if "GLAMOUR & CO. — BOOKING CONFIRMATION" in final_response:
                    try:
                        invoice_block = extract_invoice_block(final_response)
                        if invoice_block:
                            pdf_bytes = generate_invoice_pdf(invoice_block)
                            st.download_button(
                                label="📄 Download Invoice PDF",
                                data=pdf_bytes,
                                file_name="glamour_co_invoice.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                                key=f"pdf_fresh_{msg_index}",
                            )
                    except Exception as e:
                        st.caption(f"PDF unavailable: {e}")

            st.rerun()


if __name__ == "__main__":
    main()