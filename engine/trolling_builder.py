import os
import json
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/trolling-motor-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4").strip()
CUSTOM_BOAT = os.environ.get("CUSTOM_BOAT", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_boats.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

# Format: (Boat / Motor Model Name, Loaded Weight lbs, Rec Thrust lbs, System Volts, Bow Waterline Inches, Rec Shaft Inches, Max Amps)
SEED_BOATS = [
    ("Minn Kota Terrova 80 lb 24V 60-Inch GPS Spot-Lock", 3600, 80, 24, 28, 60, 56),
    ("Minn Kota Ultrex QUEST 90/115 lb 24V/36V Brushless", 4500, 112, 36, 24, 52, 52),
    ("Garmin Force Kraken 100 lb 36V 75-Inch Offshore", 5200, 100, 36, 38, 75, 54),
    ("Garmin Force 57-Inch 24V/36V Freshwater Bass Motor", 3800, 80, 24, 24, 57, 50),
    ("Minn Kota Riptide Terrova 112 lb 36V 72-Inch Saltwater", 5000, 112, 36, 36, 72, 52),
    ("Minn Kota PowerDrive 55 lb 12V 54-Inch Bow-Mount", 2400, 55, 12, 22, 54, 50),
    ("MotorGuide Xi3 70 lb 24V 60-Inch Pinpoint GPS", 3200, 70, 24, 26, 60, 48),
    ("MotorGuide Xi5 105 lb 36V 60-Inch Wireless Saltwater", 4600, 105, 36, 28, 60, 52),
    ("Lowrance Ghost 47-Inch 24V/36V Brushless Bass Motor", 3900, 97, 24, 20, 47, 52),
    ("Lowrance Recon 72-Inch 36V Saltwater GPS Motor", 5100, 105, 36, 36, 72, 54),
    ("Newport Vessels NK180PRO 1.8HP 24V/36V Kayak Motor", 900, 65, 24, 12, 36, 30),
    ("Minn Kota Endura Max 55 lb 12V Digital Maximizer", 2200, 55, 12, 18, 42, 50),
    ("16-Foot Aluminum Jon Boat & Utility Skiff", 1800, 55, 12, 18, 45, 50),
    ("17-Foot Tracker Pro Team 175 TXW Aluminum Bass Boat", 2600, 70, 24, 20, 45, 52),
    ("18-Foot Fiberglass Bass Boat (Ranger / Nitro / Skeeter)", 3500, 80, 24, 22, 52, 56),
    ("20-Foot Tournament Bass Boat (250HP Outboard)", 4300, 112, 36, 23, 52, 52),
    ("19-Foot Carolina Skiff & Shallow Bay Boat", 3400, 80, 24, 26, 60, 56),
    ("22-Foot Center Console Inshore/Offshore Bay Boat", 4800, 112, 36, 34, 72, 52),
    ("24-Foot Offshore Center Console Fishing Boat", 6200, 112, 36, 42, 87, 56),
    ("20-Foot Family Fishing Pontoon Boat", 3600, 80, 24, 26, 60, 56),
    ("24-Foot Tri-Toon Deck & Fishing Pontoon Boat", 4600, 112, 36, 28, 60, 52),
    ("17-Foot Deep-V Aluminum Walleye Boat (Lund / Crestliner)", 3300, 80, 24, 28, 60, 56),
    ("19-Foot Deep-V Multi-Species Walleye Boat", 4100, 112, 36, 32, 60, 52),
    ("12-Foot Pedal & Tournament Fishing Kayak", 650, 45, 12, 10, 36, 42),
    ("14-FootSolo Skiff & Micro Flats Boat", 1100, 55, 12, 14, 42, 50),
    ("18-Foot Technical Poling Flats Skiff", 2300, 80, 24, 18, 52, 56),
    ("21-Foot Aluminum Center Console River Jet Boat", 3700, 80, 24, 26, 60, 56),
    ("Minn Kota Ulterra 80 lb 24V 60-Inch Auto-Stow/Deploy", 3700, 80, 24, 28, 60, 56),
    ("Minn Kota Riptide Instinct QUEST 100 lb 36V 87-Inch", 5800, 112, 36, 44, 87, 56),
    ("Power-Pole MOVE ZR 45-Inch 24V/36V Titanium Brushless", 4000, 100, 36, 20, 45, 50)
]


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not parse {filepath}: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=80.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def discover_google_trolling_queries():
    """Mengambil kueri model trolling motor & ukuran perahu dari Google Autocomplete US."""
    discovered = []
    seeds = [
        "what size trolling motor for ",
        "minn kota terrova ",
        "trolling motor shaft length for ",
        "lifepo4 battery size for "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        discovered.append((cleaned.title(), 3500, 80, 24, 26, 60, 56))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")
    return discovered


def build_deterministic_trolling_data(boat_tuple):
    """Mesin Fisika Propulsi Kapal & Kelistrikan Baterai ABYC E-11 (100% bebas gagal)."""
    item_name, boat_lbs, thrust_lbs, sys_volts, bow_in, shaft_in, max_amps = boat_tuple

    # Average Spot-Lock / 50% Cruise Amp Draw (~35% dari Max Full-Throttle Amps)
    cruise_amps = round(max_amps * 0.35, 1)
    # Runtime dengan baterai LiFePO4 100Ah (100% usable DoD) vs Lead-Acid/AGM 100Ah (50% usable DoD)
    lifepo4_100ah_hrs = round(100.0 / cruise_amps, 1)
    agm_100ah_hrs = round(50.0 / cruise_amps, 1)

    num_12v_batteries = sys_volts // 12
    bank_label = (
        f"Single {sys_volts}V 100Ah LiFePO4 Battery (or {num_12v_batteries}x 12V 100Ah in Series)"
        if sys_volts > 12
        else "12V 100Ah Deep-Cycle LiFePO4 Marine Battery"
    )

    return {
        "boat_name": item_name,
        "seo_title": f"{item_name} Thrust, Shaft Length & LiFePO4 Battery Calculator (2026)",
        "meta_description": f"Calculate exact trolling motor thrust ({thrust_lbs} lbs / {sys_volts}V), shaft length ({shaft_in}\"), LiFePO4 battery runtime ({lifepo4_100ah_hrs} hrs), and ABYC 60A wiring for {item_name}.",
        "specs": {
            "loaded_boat_lbs": boat_lbs,
            "recommended_thrust_lbs": thrust_lbs,
            "system_voltage": sys_volts,
            "bow_to_waterline_in": bow_in,
            "recommended_shaft_in": shaft_in,
            "max_amp_draw": max_amps,
            "cruise_amp_draw": cruise_amps,
            "lifepo4_100ah_runtime_hrs": lifepo4_100ah_hrs
        },
        "marine_verdict": f"For {item_name} (~{boat_lbs:,} lbs wet weight with fuel, gear, and anglers), marine propulsion standards (2 lbs thrust per 100 lbs weight plus current reserve) call for an {thrust_lbs} lb thrust ({sys_volts}V) trolling motor with a {shaft_in}-inch shaft (for a {bow_in}\" bow-to-waterline height). Drawing ~{cruise_amps}A during typical GPS Spot-Lock & cruising ({max_amps}A wide-open), a {sys_volts}V 100Ah LiFePO4 battery bank delivers ~{lifepo4_100ah_hrs} hours of active fishing time compared to just {agm_100ah_hrs} hours on heavy lead-acid batteries.",
        "hardware_bundle": [
            {
                "badge": f"{thrust_lbs} lb / {sys_volts}V Motor",
                "title": f"{thrust_lbs} lb Thrust {sys_volts}V {shaft_in}-Inch GPS Spot-Lock Bow-Mount Trolling Motor",
                "price_range": "$899 - $2,999",
                "amazon_query": f"{thrust_lbs} lb {sys_volts}V {shaft_in} Inch GPS Trolling Motor Minn Kota Garmin",
                "boat_note": f"Provides {thrust_lbs} lbs of thrust with digital pulse-width modulation (PWM) to hold {boat_lbs:,} lb hulls in wind and current."
            },
            {
                "badge": f"{sys_volts}V 100Ah LiFePO4",
                "title": bank_label,
                "price_range": "$239 - $799",
                "amazon_query": f"{sys_volts}V 100Ah LiFePO4 Deep Cycle Marine Battery Trolling Motor",
                "boat_note": f"Saves 65% hull weight over lead-acid and delivers flat {sys_volts}V+ voltage for full thrust until 100% Depth of Discharge."
            },
            {
                "badge": f"{num_12v_batteries}-Bank Marine Charger",
                "title": f"Onboard Waterproof IP68 {num_12v_batteries}-Bank Smart Marine Battery Charger (LiFePO4 & AGM Profile)",
                "price_range": "$139 - $349",
                "amazon_query": f"NOCO Genius PRO {num_12v_batteries} Bank Onboard Marine Battery Charger LiFePO4",
                "boat_note": "Bolts directly inside the boat bilge/locker to recharge your battery bank overnight via a single AC extension cord."
            },
            {
                "badge": "ABYC 60A Wiring & Plug",
                "title": "60-Amp Waterproof Manual-Reset Circuit Breaker + 6 AWG Tinned Marine Wire & 12V/24V/36V Plug",
                "price_range": "$59 - $149",
                "amazon_query": "60 Amp Marine Circuit Breaker Trolling Motor Plug 6 AWG Tinned Wire",
                "boat_note": f"Meets ABYC E-11 standards for {max_amps}A peak draw with <3% voltage drop from battery locker to bow receptacle."
            }
        ],
        "abyc_checklist": [
            f"Install a 60-Amp waterproof manual-reset thermal circuit breaker within 7 inches of the positive battery terminal per ABYC E-11 rules to protect your {max_amps}A trolling motor circuit.",
            "Use 6 AWG UL-1426 Tinned Marine Copper Wire for bow-to-stern runs up to 20 feet; untinned automotive wire corrodes rapidly in humid boat hulls and causes voltage drop.",
            f"Measure from the top of the bow gunwale straight down to the waterline ({bow_in}\") and add at least 20\" for flat water or 24\"–28\" for choppy open water to confirm your {shaft_in}\" shaft never cavitates in waves.",
            "Always unplug the bow trolling motor receptacle or trip the 60A breaker to 'OFF' before plugging in your onboard AC battery charger to protect sensitive GPS control boards from charging spikes."
        ],
        "faqs": [
            {
                "q": f"How much trolling motor thrust do I need for {item_name} ({boat_lbs:,} lbs)?",
                "a": f"Using the industry rule of 2 lbs of thrust per 100 lbs of fully loaded wet weight ({boat_lbs:,} lbs = {int(round(boat_lbs / 50.0))} lbs minimum) plus a 15%–20% reserve for wind and tidal current, an {thrust_lbs} lb thrust ({sys_volts}V) motor is the ideal match."
            },
            {
                "q": f"What shaft length do I need for a {bow_in}-inch bow-to-waterline measurement?",
                "a": f"With {bow_in} inches from the bow mounting deck to the waterline, add 20 inches for calm lakes ({bow_in + 20}\") or 24+ inches for rough open water ({bow_in + 24}\"), making a {shaft_in}-inch shaft the proper fit so the prop stays submerged."
            },
            {
                "q": f"How long will a 100Ah LiFePO4 battery run an {thrust_lbs} lb ({sys_volts}V) trolling motor?",
                "a": f"At full wide-open throttle ({max_amps}A), a 100Ah LiFePO4 battery runs continuously for {round(100.0 / max_amps, 1)} hours. In real-world GPS Spot-Lock and 40%–50% speed fishing (~{cruise_amps}A average draw), a 100Ah LiFePO4 bank lasts {lifepo4_100ah_hrs} hours (1 to 2 full tournament days)."
            }
        ]
    }


def generate_trolling_data(boat_tuple):
    """Memanggil Gemini 2.5 Flash API; jika gagal otomatis memakai Deterministic ABYC Propulsion Engine."""
    if not GEMINI_API_KEY:
        return build_deterministic_trolling_data(boat_tuple)

    item_name, boat_lbs, thrust_lbs, sys_volts, bow_in, shaft_in, max_amps = boat_tuple
    cruise_amps = round(max_amps * 0.35, 1)
    lifepo4_hrs = round(100.0 / cruise_amps, 1)

    prompt = f"""
You are an ABYC Certified Marine Electrical Technician & Naval Propulsion Engineer. Create an accurate 2026 trolling motor thrust (lbs), shaft length (inches), and LiFePO4 deep-cycle battery sizing guide for: "{item_name}".
Baseline reference specs: Loaded Boat Weight={boat_lbs} lbs, Recommended Thrust={thrust_lbs} lbs ({sys_volts}V), Bow-to-Waterline={bow_in} inches, Recommended Shaft={shaft_in} inches, Max Draw={max_amps}A, Cruise Draw={cruise_amps}A, 100Ah LiFePO4 Runtime={lifepo4_hrs} hours.
Return ONLY a valid JSON object matching this exact schema:
{{
  "boat_name": "{item_name}",
  "seo_title": "{item_name} Thrust, Shaft Length & LiFePO4 Battery Calculator (2026)",
  "meta_description": "Calculate exact trolling motor thrust (lbs), shaft length (inches), LiFePO4 battery runtime, and ABYC 60A wire gauge for {item_name}.",
  "specs": {{
    "loaded_boat_lbs": {boat_lbs},
    "recommended_thrust_lbs": {thrust_lbs},
    "system_voltage": {sys_volts},
    "bow_to_waterline_in": {bow_in},
    "recommended_shaft_in": {shaft_in},
    "max_amp_draw": {max_amps},
    "cruise_amp_draw": {cruise_amps},
    "lifepo4_100ah_runtime_hrs": {lifepo4_hrs}
  }},
  "marine_verdict": "3-sentence technical summary stating loaded boat weight, required thrust & voltage, shaft length for the bow height, and 100Ah LiFePO4 runtime vs lead-acid.",
  "hardware_bundle": [
    {{
      "badge": "GPS Trolling Motor",
      "title": "Exact Thrust, Voltage, and Shaft Length GPS Trolling Motor recommendation",
      "price_range": "$899 - $2,999",
      "amazon_query": "{thrust_lbs} lb {sys_volts}V {shaft_in} Inch GPS Trolling Motor",
      "boat_note": "1-sentence Spot-Lock and thrust performance note"
    }},
    {{
      "badge": "LiFePO4 Marine Battery",
      "title": "Exact {sys_volts}V 100Ah Deep-Cycle LiFePO4 Marine Battery recommendation",
      "price_range": "$249 - $799",
      "amazon_query": "{sys_volts}V 100Ah LiFePO4 Marine Battery Trolling Motor",
      "boat_note": "1-sentence weight savings and 100% DoD runtime note"
    }},
    {{
      "badge": "Onboard Marine Charger",
      "title": "Waterproof IP68 Onboard Smart Marine Battery Charger (LiFePO4 Rated)",
      "price_range": "$139 - $349",
      "amazon_query": "NOCO Genius PRO Onboard Marine Battery Charger LiFePO4",
      "boat_note": "1-sentence waterproof charging note"
    }},
    {{
      "badge": "60A Breaker & Plug Kit",
      "title": "60A Waterproof Marine Circuit Breaker + 6 AWG Tinned Wire & Bow Receptacle Plug",
      "price_range": "$59 - $149",
      "amazon_query": "60 Amp Marine Circuit Breaker Trolling Motor Plug 6 AWG",
      "boat_note": "1-sentence ABYC E-11 overcurrent and voltage drop note"
    }}
  ],
  "abyc_checklist": [
    "Step 1 regarding 60A circuit breaker placement within 7 inches of battery",
    "Step 2 regarding 6 AWG UL-1426 tinned marine copper wire",
    "Step 3 regarding bow-to-waterline + 22 inch shaft submergence",
    "Step 4 regarding disconnecting power before AC charging"
  ],
  "faqs": [
    {{"q": "How much trolling motor thrust do I need for {item_name}?", "a": "Exact lbs of thrust and voltage calculation based on loaded displacement."}},
    {{"q": "What shaft length is required for {item_name}?", "a": "Exact shaft inches for calm vs rough water based on bow height."}},
    {{"q": "How long will a 100Ah LiFePO4 battery run on {item_name}?", "a": "Exact hours at wide-open throttle vs 50% Spot-Lock cruise."}}
  ]
}}
"""

    for model_id in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                parsed = json.loads(raw_text)
                if "specs" in parsed and "hardware_bundle" in parsed:
                    return parsed
        except Exception as e:
            print(f"[WARN] Gemini ({model_id}) notice for '{item_name}': {e}")

    return build_deterministic_trolling_data(boat_tuple)


def build_trolling_html_page(data, slug, mon_cfg):
    boat_name = data.get("boat_name", "Fishing Boat & Trolling Motor")
    sp = data.get("specs", {})
    boat_lbs = int(safe_float(sp.get("loaded_boat_lbs", 3500), 3500))
    thrust_lbs = int(safe_float(sp.get("recommended_thrust_lbs", 80), 80))
    sys_volts = int(safe_float(sp.get("system_voltage", 24), 24))
    bow_in = int(safe_float(sp.get("bow_to_waterline_in", 26), 26))
    shaft_in = int(safe_float(sp.get("recommended_shaft_in", 60), 60))
    max_amps = int(safe_float(sp.get("max_amp_draw", 56), 56))
    cruise_amps = round(safe_float(sp.get("cruise_amp_draw", 19.5), 19.5), 1)
    lifepo4_hrs = round(safe_float(sp.get("lifepo4_100ah_runtime_hrs", 5.1), 5.1), 1)

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "GPS+Trolling+Motor+LiFePO4+Marine+Battery"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{boat_name} Trolling Motor Thrust & Battery Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "GPS Trolling Motor")), mon_cfg)
        bundle_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-emerald-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Marine Gear')}</span>
              <span class="text-sm font-bold text-cyan-400">{item.get('price_range', '$139+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">⚓ {item.get('boat_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Boat Weight, Thrust, Shaft & Battery Reference Matrix
    matrix_rows_html = ""
    tiers = [
        ("Up to 2,200 lbs (14'–16' Skiff)", "55 lb Thrust (12V)", "16\"–22\" Bow → 45\"–54\" Shaft", "12V 100Ah LiFePO4", "60A Breaker / 6 AWG"),
        ("2,200 – 3,200 lbs (17' Bass/Bay)", "70 lb Thrust (24V)", "20\"–26\" Bow → 52\"–60\" Shaft", "24V 100Ah (or 2x 12V)", "60A Breaker / 6 AWG"),
        ("3,200 – 4,000 lbs (18'–19' Boat)", "80 lb Thrust (24V)", "22\"–28\" Bow → 54\"–60\" Shaft", "24V 100Ah LiFePO4", "60A Breaker / 6 AWG"),
        ("4,000 – 5,200 lbs (20'–22' Bay)", "100–112 lb (36V)", "28\"–36\" Bow → 60\"–72\" Shaft", "36V 100Ah (or 3x 12V)", "60A Breaker / 6 AWG"),
        ("5,200 – 7,000 lbs (23'–26' Offshore)", "112–115 lb (36V)", "36\"–46\" Bow → 72\"–87\" Shaft", "36V 100Ah Dual-Bank", "60A Breaker / 4 AWG")
    ]
    for wt_s, thr_s, shf_s, bat_s, wir_s in tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">{wt_s}</td>
          <td class="py-3 px-4 font-bold text-emerald-400">{thr_s}</td>
          <td class="py-3 px-4 text-slate-300">{shf_s}</td>
          <td class="py-3 px-4 text-cyan-400 font-semibold">{bat_s}</td>
          <td class="py-3 px-4 text-xs text-slate-400">{wir_s}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("abyc_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer hover:border-slate-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-emerald-500 rounded cursor-pointer boat-check">
          <span class="text-sm text-slate-200 leading-relaxed"><strong>ABYC Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-slate-900 border border-slate-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-slate-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', boat_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', boat_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-emerald-500 text-slate-950 px-2 py-0.5 rounded font-black">THRUST</span>MotorIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Trolling Motors & LiFePO4 →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-emerald-500 text-slate-950 px-3 py-1 rounded-full">{thrust_lbs} lb Thrust ({sys_volts}V)</span>
        <span class="text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-3 py-1 rounded-full">Shaft: {shaft_in}" (Bow: {bow_in}")</span>
        <span class="text-xs font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full">Boat Weight: ~{boat_lbs:,} lbs | 100Ah Runtime: ~{lifepo4_hrs} hrs</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', boat_name)}</h1>
      <div class="mt-4 bg-slate-900 border-l-4 border-emerald-500 p-4 rounded-r-xl text-sm text-slate-200 leading-relaxed">
        <strong>ABYC Marine Propulsion & Battery Verdict:</strong> {data.get('marine_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE TROLLING MOTOR THRUST, SHAFT LENGTH & LIFEPO4 RUNTIME CALCULATOR -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {boat_name} Thrust, Shaft & Battery Calculator</h2>
      <p class="text-xs text-slate-400 mb-6">Adjust your loaded boat displacement, bow-to-waterline height, water conditions, and LiFePO4 battery Ah capacity to compute exact thrust, shaft length, and Spot-Lock runtime.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="weightSlider" class="text-slate-300">Loaded Wet Boat Weight (Hull + Motor + Fuel + Crew lbs)</label>
              <span class="text-emerald-400 font-bold"><span id="weightVal">{boat_lbs:,}</span> lbs</span>
            </div>
            <input id="weightSlider" type="range" min="600" max="7500" step="100" value="{boat_lbs}" class="w-full accent-emerald-500 cursor-pointer">
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="bowSlider" class="text-slate-300">Bow Deck to Waterline Height (Inches)</label>
              <span class="text-emerald-400 font-bold"><span id="bowVal">{bow_in}</span>"</span>
            </div>
            <input id="bowSlider" type="range" min="10" max="48" step="2" value="{bow_in}" class="w-full accent-emerald-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="waterSelect" class="block text-xs font-medium text-slate-400 mb-1">Wind / Wave Conditions</label>
              <select id="waterSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500">
                <option value="1.00">Calm Lake / Pond (Standard)</option>
                <option value="1.20" selected>Moderate Wind / River Current (+20%)</option>
                <option value="1.35">Offshore Swell / Heavy Tidal (+35%)</option>
              </select>
            </div>
            <div>
              <label for="ahSelect" class="block text-xs font-medium text-slate-400 mb-1">LiFePO4 Battery Capacity</label>
              <select id="ahSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500">
                <option value="50">50Ah Compact LiFePO4</option>
                <option value="100" selected>100Ah Standard Tournament</option>
                <option value="150">150Ah Extended Offshore</option>
                <option value="200">200Ah Multi-Day Bank</option>
              </select>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Required Motor Spec</span>
            <div id="thrustOut" class="text-xl sm:text-2xl font-black text-white mt-1">{thrust_lbs} lb ({sys_volts}V)</div>
            <p id="shaftOut" class="text-xs text-emerald-400 font-semibold mt-1">Min Shaft: {shaft_in}" Length</p>
          </div>

          <div class="bg-slate-950 border border-cyan-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-cyan-400 font-bold">Spot-Lock Runtime</span>
            <div class="text-xl sm:text-2xl font-black text-cyan-400 mt-1">~<span id="runtimeOut">{lifepo4_hrs}</span> <span class="text-xs font-normal text-slate-400">hrs</span></div>
            <p id="leadCompOut" class="text-xs text-slate-400 mt-1">vs 2.5 hrs on Lead-Acid</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-emerald-950/40 border border-emerald-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="boatAdviceBanner" class="text-sm text-emerald-100 font-medium"></div>
        <a id="dynamicBoatBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Motor & LiFePO4 on Amazon →
        </a>
      </div>
    </section>

    <!-- 4-CARD HARDWARE BUNDLE -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {boat_name} Trolling Motor & LiFePO4 Power Bundle</h2>
        <span class="text-xs text-slate-400">ABYC E-11 & IP68 Marine Rated</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <!-- BOAT WEIGHT & THRUST MATRIX TABLE -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Boat Weight, Thrust (12V/24V/36V), Shaft Length & Battery Sizing Chart</h2>
      <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-950/60 text-slate-400 uppercase text-xs">
              <th class="py-3.5 px-4">Loaded Boat Weight</th>
              <th class="py-3.5 px-4 text-emerald-400">Recommended Thrust & Volts</th>
              <th class="py-3.5 px-4">Bow Height → Shaft Length</th>
              <th class="py-3.5 px-4 text-cyan-400">LiFePO4 Battery Bank</th>
              <th class="py-3.5 px-4">ABYC Circuit Protection</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <!-- ABYC INSTALLATION CHECKLIST -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">ABYC Marine Wiring & Battery Rigging Checklist</h2>
        <span id="boatBadge" class="text-xs font-bold bg-slate-800 text-emerald-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <!-- FAQ -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({boat_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500 px-4">
    <p>© {datetime.now(timezone.utc).year} ThrustMotorIndex. Independent Marine Propulsion & LiFePO4 Battery Engineering Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const weightSlider = document.getElementById('weightSlider');
    const bowSlider = document.getElementById('bowSlider');
    const waterSelect = document.getElementById('waterSelect');
    const ahSelect = document.getElementById('ahSelect');
    const weightVal = document.getElementById('weightVal');
    const bowVal = document.getElementById('bowVal');
    const thrustOut = document.getElementById('thrustOut');
    const shaftOut = document.getElementById('shaftOut');
    const runtimeOut = document.getElementById('runtimeOut');
    const leadCompOut = document.getElementById('leadCompOut');
    const boatAdviceBanner = document.getElementById('boatAdviceBanner');
    const dynamicBoatBtn = document.getElementById('dynamicBoatBtn');

    function recalculateBoat() {{
      const lbs = parseInt(weightSlider.value, 10);
      const bowIn = parseInt(bowSlider.value, 10);
      const condMult = parseFloat(waterSelect.value);
      const batteryAh = parseInt(ahSelect.value, 10);

      weightVal.textContent = lbs.toLocaleString();
      bowVal.textContent = bowIn;

      const rawThrust = (lbs / 100.0) * 2.0 * condMult;
      let recThrust = 55;
      let recVolts = 12;
      let avgCruiseAmps = 17.5;

      if (rawThrust <= 55) {{
        recThrust = 55;
        recVolts = 12;
        avgCruiseAmps = 17.5;
      }} else if (rawThrust <= 72) {{
        recThrust = 70;
        recVolts = 24;
        avgCruiseAmps = 18.0;
      }} else if (rawThrust <= 85) {{
        recThrust = 80;
        recVolts = 24;
        avgCruiseAmps = 19.5;
      }} else {{
        recThrust = 112;
        recVolts = 36;
        avgCruiseAmps = 18.5;
      }}

      const waveAdd = condMult > 1.25 ? 26 : 22;
      const rawShaft = bowIn + waveAdd;
      let stdShaft = 45;
      if (rawShaft <= 45) stdShaft = 45;
      else if (rawShaft <= 54) stdShaft = 54;
      else if (rawShaft <= 60) stdShaft = 60;
      else if (rawShaft <= 72) stdShaft = 72;
      else stdShaft = 87;

      const lifepo4Hrs = (batteryAh / avgCruiseAmps).toFixed(1);
      const leadHrs = ((batteryAh * 0.50) / avgCruiseAmps).toFixed(1);

      thrustOut.textContent = `${{recThrust}} lb (${{recVolts}}V)`;
      shaftOut.textContent = `Min Shaft: ${{stdShaft}}" Length`;
      runtimeOut.textContent = lifepo4Hrs;
      leadCompOut.textContent = `vs ${{leadHrs}} hrs on Lead-Acid`;

      boatAdviceBanner.innerHTML = `⚓ <strong>ABYC Rigging Spec:</strong> Pair a <strong>${{recThrust}} lb (${{recVolts}}V) ${{stdShaft}}-Inch GPS Trolling Motor</strong> with a <strong>${{recVolts}}V ${{batteryAh}}Ah Deep-Cycle LiFePO4 Battery</strong> and a 60A waterproof circuit breaker.`;
      dynamicBoatBtn.href = `https://${{amzDomain}}/s?k=${{recThrust}}+lb+${{recVolts}}V+Trolling+Motor+${{recVolts}}V+${{batteryAh}}Ah+LiFePO4+Marine+Battery&tag=${{amzTag}}`;
    }}

    weightSlider.addEventListener('input', recalculateBoat);
    bowSlider.addEventListener('input', recalculateBoat);
    waterSelect.addEventListener('change', recalculateBoat);
    ahSelect.addEventListener('change', recalculateBoat);
    recalculateBoat();

    const checks = document.querySelectorAll('.boat-check');
    const badge = document.getElementById('boatBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "GPS+Trolling+Motor+LiFePO4+Marine+Battery"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-slate-900 border border-slate-800 hover:border-emerald-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-emerald-500 text-slate-950 px-2.5 py-0.5 rounded">{item.get('thrust_lbs', 80)} lb ({item.get('volts', 24)}V)</span>
            <span class="text-xs text-slate-400">{item.get('shaft_in', 60)}" Shaft</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-emerald-400 transition">{item['boat_name']} Calculator</h2>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-emerald-400">Calculate Thrust, Shaft & LiFePO4 →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ThrustMotorIndex — Trolling Motor Thrust, Shaft Length & LiFePO4 Battery Calculator (2026)</title>
  <meta name="description" content="Calculate exact trolling motor thrust (55lb, 80lb, 112lb), shaft length (inches), and 12V/24V/36V LiFePO4 marine battery runtime for Minn Kota, Garmin, Lowrance, and MotorGuide setups.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="ThrustMotorIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-emerald-500 text-slate-950 px-2 py-0.5 rounded font-black">THRUST</span>MotorIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Trolling Motors & LiFePO4 →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Trolling Motor Thrust, Shaft & LiFePO4 Battery Database</h1>
      <p class="text-slate-400 mt-3 text-base sm:text-lg">Select your boat type or trolling motor model below to calculate required thrust (lbs), bow-to-waterline shaft length, and 12V/24V/36V LiFePO4 Spot-Lock runtime.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search boat or motor (e.g. Minn Kota Terrova, Garmin Kraken, 18 ft Bass Boat, Pontoon, 24V 80 lb...)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-emerald-500">
      </div>
    </div>

    <div id="boatGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
    <p>© {datetime.now(timezone.utc).year} ThrustMotorIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('boatGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>ThrustMotorIndex Marine Trolling Motor & LiFePO4 Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Trolling Motor Thrust, Shaft Length & LiFePO4 Marine Battery Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[INDEXNOW] Pushed {len(new_urls)} URLs (HTTP {resp.status})")
    except Exception as e:
        print(f"[WARN] IndexNow ping notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published}

    candidates = []
    if CUSTOM_BOAT:
        candidates.append((CUSTOM_BOAT.strip(), 3600, 80, 24, 26, 60, 56))
    candidates.extend(SEED_BOATS)
    candidates.extend(discover_google_trolling_queries())

    new_urls = []
    count = 0

    for boat_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        b_name = boat_tuple[0]
        slug = slugify(f"{b_name}-thrust-shaft-battery-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating trolling motor thrust & LiFePO4 calculator for: {b_name}...")
        try:
            data = generate_trolling_data(boat_tuple)
            build_trolling_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "boat_name": data.get("boat_name", b_name),
                "slug": slug,
                "title": data.get("seo_title", f"{b_name} Trolling Motor Calculator"),
                "description": data.get("meta_description", ""),
                "thrust_lbs": int(safe_float(sp.get("recommended_thrust_lbs", boat_tuple[2]), boat_tuple[2])),
                "volts": int(safe_float(sp.get("system_voltage", boat_tuple[3]), boat_tuple[3])),
                "shaft_in": int(safe_float(sp.get("recommended_shaft_in", boat_tuple[5]), boat_tuple[5])),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Failed building {b_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new trolling motor & LiFePO4 calculator pages.")


if __name__ == "__main__":
    main()
