"""
Salon IQ — Orchestrator v2
Single-thread, stage-managed booking flow.

Flow: supervisor -> customer_memory -> seasonal -> stylist -> schedule -> pricing
"""

import asyncio
import json
import re

from agent_framework_foundry import FoundryAgent
from azure.identity.aio import AzureCliCredential

# ── Config ────────────────────────────────────────────────────────────────────

PROJECT_ENDPOINT = (
    "https://cmturmari-salon-iq-resource.services.ai.azure.com"
    "/api/projects/cmturmari-salon-iq"
)

AGENTS = {
    "supervisor":      {"name": "supervisor-agent",       "version": "15"},
    "customer_memory": {"name": "customer-memory-agent",  "version": "14"},
    "seasonal":        {"name": "seasonal-agent",         "version": "10"},
    "stylist":         {"name": "stylist-agent",          "version": "4"},
    "schedule":        {"name": "schedule-agent",         "version": "10"},
    "pricing":         {"name": "pricing-agent",          "version": "23"},
}

TALKING_AGENTS = {"customer_memory", "seasonal", "schedule"}
SILENT_AGENTS  = {"stylist", "pricing"}

BOOKING_FLOW = ["customer_memory", "seasonal", "stylist", "schedule", "pricing"]

AGENT_STATUS = {
    "customer_memory": "🧠 Checking your history…",
    "seasonal":        "🍂 Finding seasonal offers…",
    "stylist":         "✂️  Selecting your stylist…",
    "schedule":        "📅 Checking availability…",
    "pricing":         "💰 Calculating your total…",
}

BOOKING_KEYWORDS = [
    "book", "booking", "appointment", "schedule", "reserve",
    "slot", "available", "availability", "visit", "come in",
    "hair", "facial", "nail", "wax", "manicure", "pedicure",
    "coloring", "colouring", "cut", "eyebrow",
]

AUTO_SELECT_PHRASES = [
    "just book", "you decide", "any time", "anytime", "whatever works",
    "you choose", "pick one", "earliest", "no preference", "doesn't matter",
    "dont matter", "don't mind", "dont mind", "surprise me",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def is_booking_request(text: str) -> bool:
    return any(kw in text.lower() for kw in BOOKING_KEYWORDS)


def wants_auto_selection(text: str) -> bool:
    return any(p in text.lower() for p in AUTO_SELECT_PHRASES)


def extract_json(text: str) -> dict | None:
    fenced = re.search(r"```json\s*([\s\S]*?)```", text)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return None


def is_complete_json(text: str, agent_key: str) -> bool:
    data = extract_json(text)
    if data is None:
        return False
    if data.get("waiting_for_customer", False):
        return False
    completion_keys = {
        "customer_memory": "customer_status",
        "seasonal":        "confirmed_services",
        "schedule":        "booking_status",
    }
    required = completion_keys.get(agent_key)
    return required is not None and required in data


def strip_json_blob(text: str) -> str:
    cleaned = re.sub(r"```json\s*[\s\S]*?```", "", text)
    start = cleaned.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(cleaned)):
            if cleaned[i] == "{":
                depth += 1
            elif cleaned[i] == "}":
                depth -= 1
                if depth == 0:
                    cleaned = cleaned[:start] + cleaned[i + 1:]
                    break
    return cleaned.strip()


def show_to_user(response: str, on_chunk) -> str:
    clean = strip_json_blob(response) or response
    clean = clean.strip()
    if on_chunk and clean:
        on_chunk(clean)
    return clean


def _extract_day(conversation: str) -> str:
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    times = ["morning", "afternoon", "evening"]
    conv = conversation.lower()
    found_day, found_time = "", ""
    for d in days:
        if d in conv:
            found_day = d.capitalize()
            break
    for t in times:
        if t in conv:
            found_time = t
            break
    if found_day and found_time:
        return f"{found_day} {found_time}"
    return found_day or "flexible"


def _extract_occasion(conversation: str) -> str:
    occasions = [
        "date night", "birthday", "wedding", "party", "anniversary",
        "prom", "graduation", "holiday", "christmas", "valentine",
    ]
    conv = conversation.lower()
    for o in occasions:
        if o in conv:
            return o
    return ""


def _extract_name(conversation: str) -> str:
    """Pull customer name from conversation history if supervisor already got it."""
    for line in conversation.split("\n"):
        if line.upper().startswith("USER:"):
            words = line.split(":", 1)[-1].strip().split()
            for w in words:
                w = w.strip(",.!?")
                if w and w[0].isupper() and len(w) > 1 and w.lower() not in {
                    "i", "hi", "hello", "hey", "book", "want", "need",
                    "please", "can", "would", "like", "yes", "no",
                }:
                    return w
    return ""


# ── Core agent caller ─────────────────────────────────────────────────────────

async def call_agent(
    agent_key: str,
    prompt: str,
    on_chunk=None,
    retries: int = 5,
    retry_delay: float = 5.0,
) -> str:
    cfg = AGENTS[agent_key]
    for attempt in range(retries):
        full: list[str] = []
        try:
            async with AzureCliCredential() as credential:
                async with FoundryAgent(
                    project_endpoint=PROJECT_ENDPOINT,
                    agent_name=cfg["name"],
                    agent_version=cfg["version"],
                    credential=credential,
                ) as agent:
                    async for chunk in agent.run(prompt, stream=True):
                        if chunk.text:
                            full.append(chunk.text)
                            if on_chunk:
                                on_chunk(chunk.text)
            return "".join(full).strip()
        except Exception as e:
            err = str(e)
            is_retriable = any(x in err for x in [
                "401", "404", "MCP", "Workspace", "Unauthorized", "Authentication"
            ])
            if is_retriable and attempt < retries - 1:
                print(f"\n  [Retrying {agent_key} — attempt {attempt+2}/{retries}]", flush=True)
                await asyncio.sleep(retry_delay)
                continue
            raise
    return ""


# ── Session ───────────────────────────────────────────────────────────────────

class SalonSession:
    def __init__(self):
        self.stage: str = "supervisor"
        self.pipeline_index: int = 0
        self.conversation: str = ""
        self.accumulated_json: dict = {}
        self.booking_active: bool = False
        self.memory_turns: int = 0      # how many times memory agent has spoken
        self.seasonal_turns: int = 0    # how many times seasonal agent has spoken
        self.seasonal_replies: int = 0  # how many times user has replied to seasonal
        self.schedule_turns: int = 0    # how many times schedule agent has spoken

    def advance_stage(self):
        self.pipeline_index += 1
        if self.pipeline_index < len(BOOKING_FLOW):
            self.stage = BOOKING_FLOW[self.pipeline_index]
        else:
            self.stage = "done"

    def append_history(self, role: str, text: str):
        self.conversation += f"\n{role.upper()}: {text}"

    def build_agent_prompt(self, user_input: str) -> str:
        parts = []
        if self.conversation:
            parts.append(f"[CONVERSATION SO FAR]\n{self.conversation}")
        if self.accumulated_json:
            parts.append(
                f"[DATA FROM PREVIOUS STEPS]\n"
                f"{json.dumps(self.accumulated_json, indent=2)}"
            )
        parts.append(f"[USER MESSAGE]\n{user_input}")
        return "\n\n".join(parts)


# ── Force-advance helpers ─────────────────────────────────────────────────────

def force_memory_json(session: SalonSession) -> dict:
    """Build customer_memory JSON from conversation when agent won't return one."""
    return {
        "customer_status":    "new",
        "customer_name":      _extract_name(session.conversation),
        "preferred_day":      "",
        "requested_day":      _extract_day(session.conversation),
        "occasion":           _extract_occasion(session.conversation),
        "favourite_services": [],
        "top_stylist_1":      "",
        "top_stylist_2":      "",
        "customer_notes":     "",
    }


def force_seasonal_json(session: SalonSession) -> dict:
    """Build seasonal JSON from accumulated data when agent won't return one."""
    services = session.accumulated_json.get("favourite_services", [])
    return {
        "confirmed_services":  services,
        "promotion_name":      "",
        "discount_percent":    0,
        "free_service":        "",
        "waiting_for_customer": False,
    }


def force_schedule_json(session: SalonSession) -> dict:
    """Build schedule JSON from accumulated data when agent won't return one."""
    d = session.accumulated_json
    stylist = ""
    shortlist = d.get("shortlist", [])
    if shortlist:
        first = shortlist[0]
        stylist = first.get("name", str(first)) if isinstance(first, dict) else str(first)
    if not stylist:
        stylist = d.get("top_stylist_1", "")
    return {
        "booking_status":       "confirmed",
        "confirmed_date":       d.get("requested_day", "Thursday"),
        "confirmed_time":       "2:00 PM",
        "confirmed_stylist":    stylist,
        "waiting_for_customer": False,
    }


def _build_invoice_fallback(d: dict) -> str:
    """
    Build a plain-text invoice from accumulated_json when the pricing
    agent returns nothing useful.
    """
    name     = d.get("customer_name", "Guest")
    date     = d.get("confirmed_date", d.get("requested_day", "TBC"))
    time     = d.get("confirmed_time", "TBC")
    occasion = d.get("occasion", "General visit")

    # Stylist: prefer confirmed_stylist from schedule, then first in shortlist, then history
    stylist = d.get("confirmed_stylist", "")
    if not stylist:
        shortlist = d.get("shortlist", [])
        if shortlist:
            first = shortlist[0]
            stylist = first.get("name", str(first)) if isinstance(first, dict) else str(first)
    if not stylist:
        stylist = d.get("top_stylist_1", "TBC")

    services  = d.get("confirmed_services", d.get("favourite_services", []))
    promo     = d.get("promotion_name", "")
    discount  = float(d.get("discount_percent", 0))
    free_svc  = d.get("free_service", "")

    # Price lookup
    prices = {
        "haircut": 30, "hair coloring": 80, "facial": 70,
        "manicure": 30, "pedicure": 40, "nail art": 50,
        "waxing": 35, "eyebrow wax": 15,
    }

    subtotal = 0.0
    service_lines = ""
    for svc in services:
        price = prices.get(svc.lower(), 0)
        subtotal += price
        service_lines += f"\n{svc:<38} ${price:.2f}"

    if free_svc:
        service_lines += f"\n{free_svc} (complimentary){'':>10} $0.00"

    discount_amt = round(subtotal * discount / 100, 2)
    total        = round(subtotal - discount_amt, 2)
    tax          = round(total * 0.085, 2)
    total_due    = round(total + tax, 2)

    discount_line = ""
    if discount > 0:
        discount_line = (
            f"\nPromotion  : {promo}"
            f"\nDiscount   : {discount}% — you save           ${discount_amt:.2f}"
        )

    return f"""
--------------------------------------------------
       GLAMOUR & CO. — BOOKING CONFIRMATION
--------------------------------------------------
Customer   : {name}
Date       : {date}
Time       : {time}
Stylist    : {stylist}
Occasion   : {occasion}
--------------------------------------------------
SERVICES
--------------------------------------------------{service_lines}
--------------------------------------------------
Subtotal                               ${subtotal:.2f}{discount_line}
--------------------------------------------------
Total (before tax)                     ${total:.2f}
Tax (8.5%)                             ${tax:.2f}
--------------------------------------------------
TOTAL DUE                              ${total_due:.2f}
--------------------------------------------------
Thank you for choosing Glamour & Co.! See you soon 💅
--------------------------------------------------
""".strip()


# ── Route ─────────────────────────────────────────────────────────────────────

async def route(
    user_input: str,
    session: SalonSession,
    on_chunk=None,
    on_status=None,
) -> str:
    session.append_history("user", user_input)

    # Not in booking → supervisor handles everything
    if not session.booking_active:
        if is_booking_request(user_input):
            session.booking_active = True
            session.pipeline_index = 0
            session.stage = BOOKING_FLOW[0]
        else:
            prompt = f"{session.conversation}\n\nUser: {user_input}" if session.conversation else user_input
            response = await call_agent("supervisor", prompt, on_chunk=on_chunk)
            session.append_history("assistant", response)
            return response

    # Booking finished → supervisor handles follow-ups
    if session.stage == "done":
        prompt = f"{session.conversation}\n\nUser: {user_input}"
        response = await call_agent("supervisor", prompt, on_chunk=on_chunk)
        session.append_history("assistant", response)
        return response

    # ── Pipeline loop ─────────────────────────────────────────────────────────
    while True:
        current_agent = session.stage

        if current_agent == "done":
            return "Your booking is complete! 🎉"

        if on_status:
            on_status(current_agent, AGENT_STATUS[current_agent])

        prompt = session.build_agent_prompt(user_input)

        if current_agent == "schedule" and wants_auto_selection(user_input):
            prompt += (
                "\n\n[INSTRUCTION] The customer has no time preference. "
                "Automatically select the earliest available slot, confirm the "
                "booking, and return completion JSON with booking_status set and "
                "waiting_for_customer: false. Do not ask further questions."
            )

        # ── customer_memory ───────────────────────────────────────────────────
        if current_agent == "customer_memory":
            response = await call_agent(current_agent, prompt)
            if is_complete_json(response, "customer_memory"):
                data = extract_json(response)
                if data:
                    session.accumulated_json.update(data)
                session.append_history("customer_memory_agent", strip_json_blob(response))
                session.advance_stage()
                continue
            else:
                session.memory_turns += 1
                if session.memory_turns >= 2:
                    # Agent has had enough turns — force-build JSON and advance
                    session.accumulated_json.update(force_memory_json(session))
                    session.append_history("customer_memory_agent", strip_json_blob(response))
                    session.advance_stage()
                    continue
                else:
                    clean = show_to_user(response, on_chunk)
                    session.append_history("customer_memory_agent", clean)
                    session.append_history("assistant", clean)
                    return clean

        # ── seasonal ──────────────────────────────────────────────────────────
        # Talks to customer up to 4 times before force-advancing:
        #   Turn 1: show promos + ask about add-ons
        #   Turn 2: follow-up / clarification
        #   Turn 3: confirm final service list
        #   Turn 4: if still not done, one last attempt
        #   Turn 5+: hard-cap force-advance
        if current_agent == "seasonal":
            response = await call_agent(current_agent, prompt)
            session.seasonal_turns += 1

            # Allow advance only if agent signals done AND user has replied >= 4 times
            if is_complete_json(response, "seasonal") and session.seasonal_replies >= 4:
                data = extract_json(response)
                if data:
                    session.accumulated_json.update(data)
                session.append_history("seasonal_agent", strip_json_blob(response))
                session.advance_stage()
                continue
            elif session.seasonal_turns >= 5:
                # Hard cap — force-advance after 5 agent turns no matter what
                data = extract_json(response)
                if data:
                    session.accumulated_json.update(data)
                else:
                    session.accumulated_json.update(force_seasonal_json(session))
                session.append_history("seasonal_agent", strip_json_blob(response))
                session.advance_stage()
                continue
            else:
                # Show response to user and wait for their next message
                clean = show_to_user(response, on_chunk)
                session.seasonal_replies += 1
                session.append_history("seasonal_agent", clean)
                session.append_history("assistant", clean)
                return clean

        # ── stylist (always silent) ───────────────────────────────────────────
        if current_agent == "stylist":
            response = await call_agent(current_agent, prompt)
            data = extract_json(response)
            if data:
                session.accumulated_json.update(data)
            else:
                session.accumulated_json.setdefault("shortlist", [])
                session.accumulated_json.setdefault("no_stylist_found", False)
            session.append_history("stylist_agent", strip_json_blob(response))
            session.advance_stage()
            continue

        # ── schedule ──────────────────────────────────────────────────────────
        # Talks to customer up to 4 times before force-advancing.
        if current_agent == "schedule":
            response = await call_agent(current_agent, prompt)
            if is_complete_json(response, "schedule"):
                data = extract_json(response)
                if data:
                    session.accumulated_json.update(data)
                session.append_history("schedule_agent", strip_json_blob(response))
                session.advance_stage()
                continue
            else:
                session.schedule_turns += 1
                if session.schedule_turns >= 4:
                    # Force-advance after 4 turns
                    session.accumulated_json.update(force_schedule_json(session))
                    session.append_history("schedule_agent", strip_json_blob(response))
                    session.advance_stage()
                    continue
                else:
                    clean = show_to_user(response, on_chunk)
                    if not clean:
                        clean = "What day and time would you prefer for your appointment?"
                    session.append_history("schedule_agent", clean)
                    session.append_history("assistant", clean)
                    return clean

        # ── pricing (always silent, final) ────────────────────────────────────
        if current_agent == "pricing":
            response = await call_agent(current_agent, prompt)
            data = extract_json(response)
            if data:
                session.accumulated_json.update(data)

            # Try stripped prose first
            clean = strip_json_blob(response).strip()

            # If nothing left after stripping, build invoice from accumulated_json
            if not clean:
                clean = _build_invoice_fallback(session.accumulated_json)

            session.append_history("pricing_agent", clean)
            session.stage = "done"
            session.append_history("assistant", clean)
            if on_chunk:
                on_chunk(clean)
            return clean

        return "Something went wrong. Please try again."


# ── PDF generator ─────────────────────────────────────────────────────────────

def generate_invoice_pdf(invoice_text: str) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
    except ImportError:
        raise ImportError("Install reportlab first: pip install reportlab")

    from datetime import datetime
    import io

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    bg_colour    = colors.HexColor("#fdf6f0")
    dark_brown   = colors.HexColor("#2d1f14")
    accent_brown = colors.HexColor("#4a3728")
    light_line   = colors.HexColor("#c9b8a8")
    gold         = colors.HexColor("#c9a98a")

    # Header band
    c.setFillColor(bg_colour)
    c.rect(0, 0, width, height, fill=True, stroke=False)
    c.setFillColor(accent_brown)
    c.rect(0, height - 18 * mm, width, 18 * mm, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 12 * mm, "GLAMOUR & CO.")
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, height - 16 * mm, "Booking Confirmation")
    c.setFillColor(light_line)
    c.setFont("Helvetica", 7)
    c.drawRightString(
        width - 15 * mm, height - 22 * mm,
        f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}",
    )

    lines = [ln for ln in invoice_text.split("\n") if ln.strip()]
    y = height - 30 * mm
    left_margin  = 20 * mm
    right_margin = width - 20 * mm
    line_height  = 6.5 * mm

    for raw_line in lines:
        line = raw_line.strip()
        if y < 25 * mm:
            c.showPage()
            c.setFillColor(bg_colour)
            c.rect(0, 0, width, height, fill=True, stroke=False)
            y = height - 20 * mm

        # Divider
        if set(line) <= {"-", " "} and len(line) > 5:
            c.setStrokeColor(light_line)
            c.setLineWidth(0.5)
            c.line(left_margin, y, right_margin, y)
            y -= 3 * mm
            continue

        # Section headers (ALL CAPS, no $ or :)
        if line.isupper() and len(line) < 30 and "$" not in line and ":" not in line:
            c.setFillColor(accent_brown)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(left_margin, y, line)
            y -= line_height
            continue

        # TOTAL DUE
        if line.startswith("TOTAL DUE") or line.startswith("TOTAL"):
            c.setFillColor(accent_brown)
            c.setFont("Helvetica-Bold", 12)
            parts = line.split("$", 1)
            c.drawString(left_margin, y, parts[0].strip())
            if len(parts) > 1:
                c.drawRightString(right_margin, y, f"${parts[1].strip()}")
            y -= line_height * 1.4
            continue

        # Key : Value meta rows
        if ":" in line and "$" not in line and not line.startswith("Tax"):
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            c.setFillColor(dark_brown)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(left_margin, y, key)
            key_width = c.stringWidth(key, "Helvetica-Bold", 9)
            min_gap = 4 * mm
            value_x = max(left_margin + 40 * mm, left_margin + key_width + min_gap)
            c.setFont("Helvetica", 9)
            c.drawString(value_x, y, val)
            y -= line_height
            continue

        # Lines with $ (services, subtotal, tax, discount etc.)
        if "$" in line:
            parts = line.rsplit("$", 1)
            c.setFillColor(dark_brown)
            c.setFont("Helvetica", 9)
            c.drawString(left_margin, y, parts[0].strip())
            c.drawRightString(right_margin, y, f"${parts[1].strip()}")
            y -= line_height
            continue

        # Footer (thank-you / closing lines — keep these centered as a block)
        footer_phrases = (
            "thank you", "see you", "look forward",
            "seeing you again", "visit us again",
        )
        if any(p in line.lower() for p in footer_phrases):
            c.setFillColor(gold)
            c.setFont("Helvetica-Oblique", 9)
            c.drawCentredString(width / 2, y, line)
            y -= line_height
            continue
        
        # Default
        c.setFillColor(dark_brown)
        c.setFont("Helvetica", 9)
        c.drawString(left_margin, y, line)
        y -= line_height

    # Footer band
    c.setFillColor(accent_brown)
    c.rect(0, 0, width, 10 * mm, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 7)
    c.drawCentredString(width / 2, 3.5 * mm, "glamourandco.com  |  info@glamourandco.com")
    c.save()
    buffer.seek(0)
    return buffer.read()


def extract_invoice_block(text: str) -> str | None:
    marker = "GLAMOUR & CO. — BOOKING CONFIRMATION"
    if marker not in text:
        return None
    start = text.find("--------------------------------------------------", max(0, text.find(marker) - 60))
    if start == -1:
        return None
    end = text.rfind("--------------------------------------------------")
    if end == start:
        return None
    return text[start: end + 50].strip()


# ── CLI ───────────────────────────────────────────────────────────────────────

async def cli():
    print("\n" + "=" * 54)
    print("  GLAMOUR & CO. — SALON BOOKING ASSISTANT")
    print("=" * 54)
    print("Type 'quit' to exit.\n")

    session = SalonSession()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in ["quit", "exit", "q"]:
            print("\nThank you for visiting Glamour & Co. Goodbye! 💅")
            break

        print("\nAssistant: ", end="", flush=True)

        def on_status(agent_key, msg):
            print(f"\n  {msg}", end="", flush=True)

        await route(
            user_input,
            session,
            on_chunk=lambda t: print(t, end="", flush=True),
            on_status=on_status,
        )
        print("\n")


if __name__ == "__main__":
    try:
        asyncio.run(cli())
    except KeyboardInterrupt:
        print("\nBye.")