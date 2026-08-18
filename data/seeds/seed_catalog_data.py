"""Seed the AR-15 parts catalog: categories and original sample products.

All product specs, pricing, and descriptions here are original placeholder data
written for this project -- not scraped or copied from any retailer or
competitor catalog. Every affiliate_url is a "#" placeholder until a real
retailer affiliate feed is wired up.

Local development only. Run from backend/ with:
    uv run python ../data/seeds/seed_catalog_data.py
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "src"))

from sqlalchemy import select

from site_api.core.config import Settings
from site_api.core.slugify import slugify
from site_api.db.database import Database
from site_api.db.models import PartCategoryRecord, ProductRecord

# (slug, name, section, sort_order)
# Matches the standard upper/lower group breakdown of an AR-15
# (see https://www.wingtactical.com/parts-of-an-ar-15/ for the reference taxonomy).
CATEGORIES = [
    ("upper-receiver", "Upper Receiver", "upper", 1),
    ("barrel", "Barrel", "upper", 2),
    ("gas-system", "Gas Block & Tube", "upper", 3),
    ("handguard", "Handguard", "upper", 4),
    ("bolt-carrier-group", "Bolt Carrier Group", "upper", 5),
    ("charging-handle", "Charging Handle", "upper", 6),
    ("lower-receiver", "Lower Receiver", "lower", 7),
    ("trigger", "Trigger", "lower", 8),
    ("pistol-grip", "Pistol Grip", "lower", 9),
    ("magazine", "Magazine", "lower", 10),
    ("stock-brace", "Stock & Brace", "stock", 11),
    ("optic", "Optic", "optics", 12),
    ("muzzle-device", "Muzzle Device", "accessories", 13),
]

# category_slug -> list of (brand, name, sku, price_cents, weight_oz, description, tags)
PRODUCTS: dict[str, list[tuple[str, str, str, int, float, str, list[str]]]] = {
    "upper-receiver": [
        ("Aero Precision", "M4E1 Stripped Upper Receiver", "AP-UP-M4E1", 12900, 7.2,
         "Forged 7075-T6 upper receiver machined to mil-spec dimensions.",
         ["material:forged", "style:mil-spec"]),
        ("Sons of Liberty Gun Works", "Billet Stripped Upper Receiver", "SOLGW-UP-BLT", 21900, 6.8,
         "Billet upper machined from a single block of 7075-T6 aluminum.",
         ["material:billet", "style:mil-spec"]),
        ("Anderson Manufacturing", "AM-15 Stripped Upper Receiver", "AM-UP-15", 7900, 7.4,
         "Entry-level forged upper receiver, mil-spec dimensions.",
         ["material:forged", "style:mil-spec"]),
        ("Spike's Tactical", "Spider Stripped Upper Receiver", "ST-UP-SPD", 14900, 7.1,
         "Forged upper with laser-engraved spider logo, mil-spec dimensions.",
         ["material:forged", "style:mil-spec"]),
        ("Battle Arms Development", "Billet Upper Receiver", "BAD-UP-BLT", 24900, 6.6,
         "Lightweight billet upper with flared magwell-matching lines.",
         ["material:billet", "style:mil-spec"]),
        ("Palmetto State Armory", "PA-15 Stripped Upper Receiver", "PSA-UP-15", 6900, 7.4,
         "Budget-friendly forged upper, mil-spec dimensions.",
         ["material:forged", "style:mil-spec"]),
    ],
    "barrel": [
        ("BCM", "Standard 16in 5.56 Government Profile Barrel", "BCM-BBL-16-GOV", 22900, 28.5,
         "Chrome-lined mid-length gas system barrel, government profile.",
         ["caliber:556", "gassystem:mid", "thread:1-2x28", "handguard:mil-spec",
          "twist:1-7", "contour:government", "finish:phosphate"]),
        ("Faxon Firearms", "16in Gunner Profile 5.56 NATO Barrel", "FAX-BBL-16-GNR", 24500, 26.0,
         "Nitride-treated gunner profile barrel, carbine-length gas system.",
         ["caliber:556", "gassystem:carbine", "thread:1-2x28", "handguard:mil-spec",
          "twist:1-8", "contour:gunner", "finish:nitride"]),
        ("Ballistic Advantage", "10.5in .300 BLK Pistol Barrel", "BA-BBL-105-BLK", 18900, 20.0,
         "Pistol-length gas system barrel chambered in .300 Blackout.",
         ["caliber:300blk", "gassystem:pistol", "thread:5-8x24", "handguard:mil-spec",
          "twist:1-8", "contour:carbine", "finish:nitride"]),
        ("Odin Works", "18in 6.5 Grendel Rifle Barrel", "ODIN-BBL-18-GRN", 27900, 32.0,
         "Rifle-length gas system heavy barrel chambered in 6.5 Grendel.",
         ["caliber:65grendel", "gassystem:rifle", "thread:5-8x24", "handguard:proprietary-odinworks",
          "twist:1-8", "contour:heavy", "finish:stainless"]),
        ("Criterion Barrels", "14.5in Hybrid Profile 5.56 Barrel", "CRIT-BBL-145-HYB", 31900, 25.0,
         "Chrome-lined hybrid-profile barrel, mid-length gas system.",
         ["caliber:556", "gassystem:mid", "thread:1-2x28", "handguard:mil-spec",
          "twist:1-7", "contour:hybrid", "finish:chrome-lined"]),
        ("Proof Research", "16in Carbon Fiber 5.56 Barrel", "PRF-BBL-16-CF", 62900, 16.5,
         "Carbon-fiber-wrapped stainless barrel, mid-length gas system.",
         ["caliber:556", "gassystem:mid", "thread:1-2x28", "handguard:mil-spec",
          "twist:1-8", "contour:carbon-wrapped", "finish:carbon-fiber"]),
    ],
    "gas-system": [
        ("Odin Works", "Low-Profile Gas Block .750", "ODIN-GB-750", 3400, 1.8,
         "Clamp-on low-profile gas block for .750in gas journals.",
         ["gassystem:carbine", "mounttype:clamp-on", "bore:750"]),
        ("BCM", "Carbine-Length Gas Tube", "BCM-GT-CAR", 1600, 0.6,
         "Mil-spec stainless carbine-length gas tube.",
         ["gassystem:carbine", "material:stainless"]),
        ("Superlative Arms", "Adjustable Gas Block .750", "SUP-GB-ADJ750", 8900, 2.2,
         "Bleed-off adjustable gas block for tuning suppressed or over-gassed builds.",
         ["gassystem:mid", "mounttype:set-screw", "bore:750", "adjustable:yes"]),
        ("VLTOR", "Mid-Length Gas Tube", "VLT-GT-MID", 1800, 0.7,
         "Mil-spec stainless mid-length gas tube.",
         ["gassystem:mid", "material:stainless"]),
        ("Seekins Precision", "Low-Profile Gas Block .936", "SEEK-GB-936", 5900, 2.0,
         "Clamp-on low-profile gas block for .936in gas journals.",
         ["gassystem:rifle", "mounttype:clamp-on", "bore:936"]),
        ("Faxon Firearms", "Rifle-Length Gas Tube", "FAX-GT-RIF", 2000, 0.8,
         "Mil-spec stainless rifle-length gas tube.",
         ["gassystem:rifle", "material:stainless"]),
    ],
    "handguard": [
        ("Geissele Automatics", "MK16 13in M-LOK Rail", "GEI-HG-MK16-13", 28900, 14.5,
         "Free-float M-LOK handguard with continuous top rail.",
         ["handguard:mil-spec", "gassystem:mid", "length:13", "mount:m-lok"]),
        ("Midwest Industries", "G4M 15in M-LOK Handguard", "MI-HG-G4M-15", 17900, 15.8,
         "Slim free-float M-LOK handguard, rifle-length compatible.",
         ["handguard:mil-spec", "gassystem:rifle", "length:15", "mount:m-lok"]),
        ("BCM", "MCMR 9in M-LOK Handguard", "BCM-HG-MCMR-9", 19900, 10.6,
         "Modular free-float handguard for carbine-length gas systems.",
         ["handguard:mil-spec", "gassystem:carbine", "length:9", "mount:m-lok"]),
        ("Odin Works", "O2 Lite 15in Handguard", "ODIN-HG-O2-15", 15900, 13.2,
         "Lightweight free-float handguard using Odin Works' proprietary mount.",
         ["handguard:proprietary-odinworks", "gassystem:rifle", "length:15", "mount:m-lok"]),
        ("Aero Precision", "Atlas R-ONE 12in Handguard", "AP-HG-R1-12", 16900, 12.8,
         "Free-float M-LOK handguard with a low-profile, slim design.",
         ["handguard:mil-spec", "gassystem:mid", "length:12", "mount:m-lok"]),
        ("Faxon Firearms", "Streamline 10in Handguard", "FAX-HG-SL-10", 14900, 9.4,
         "Compact free-float M-LOK handguard for carbine builds.",
         ["handguard:mil-spec", "gassystem:carbine", "length:10", "mount:m-lok"]),
    ],
    "bolt-carrier-group": [
        ("BCM", "Bolt Carrier Group 5.56", "BCM-BCG-556", 15900, 11.0,
         "Full-auto profile BCG, mil-spec phosphate coating, magnetic-particle inspected.",
         ["caliber:556", "coating:phosphate", "style:full-auto"]),
        ("Toolcraft", "NiB Coated Bolt Carrier Group 5.56", "TC-BCG-556-NIB", 18900, 11.0,
         "Nickel-boron coated BCG for smoother cycling and easy cleaning.",
         ["caliber:556", "coating:nib", "style:full-auto"]),
        ("Sons of Liberty Gun Works", "BCG .300 Blackout", "SOLGW-BCG-BLK", 17900, 11.0,
         "Full-auto profile BCG chambered for .300 Blackout.",
         ["caliber:300blk", "coating:phosphate", "style:full-auto"]),
        ("Odin Works", "Bolt Carrier Group 6.5 Grendel", "ODIN-BCG-GRN", 19900, 11.4,
         "Nitride-coated BCG machined for 6.5 Grendel bolt geometry.",
         ["caliber:65grendel", "coating:nitride", "style:full-auto"]),
        ("Aero Precision", "Bolt Carrier Group 5.56", "AP-BCG-556", 14900, 11.0,
         "Mil-spec phosphate BCG, shot-peened and magnetic-particle inspected.",
         ["caliber:556", "coating:phosphate", "style:full-auto"]),
        ("Rise Armament", "Match Bolt Carrier Group 5.56", "RA-BCG-556-M", 21900, 10.8,
         "Nickel-boron coated semi-auto-only match BCG.",
         ["caliber:556", "coating:nickel-boron", "style:semi-auto"]),
    ],
    "charging-handle": [
        ("BCM", "Gunfighter Charging Handle Mod 4", "BCM-CH-GF4", 5900, 3.1,
         "Extended latch charging handle sized for mil-spec upper receivers.",
         ["size:mil-spec"]),
        ("Radian Weapons", "Raptor-LT Charging Handle", "RAD-CH-RLT", 8900, 2.9,
         "Ambidextrous lightweight charging handle with dual latches.",
         ["size:mil-spec"]),
        ("Geissele Automatics", "Airborne Charging Handle", "GEI-CH-AIR", 6500, 3.0,
         "Low-profile ambidextrous charging handle.",
         ["size:mil-spec"]),
        ("VLTOR", "Extended Latch Charging Handle", "VLT-CH-EXT", 4900, 3.2,
         "Mil-spec charging handle with an extended latch.",
         ["size:mil-spec"]),
        ("Odin Works", "Ambi Charging Handle", "ODIN-CH-AMBI", 5500, 3.0,
         "Ambidextrous charging handle with oversized latches.",
         ["size:mil-spec"]),
        ("Forward Controls Design", "Charging Handle", "FCD-CH-STD", 7900, 2.8,
         "Billet ambidextrous charging handle with low-profile latch.",
         ["size:mil-spec"]),
    ],
    "lower-receiver": [
        ("Aero Precision", "M4E1 Stripped Lower Receiver", "AP-LO-M4E1", 12900, 8.0,
         "Forged 7075-T6 lower receiver machined to mil-spec dimensions.",
         ["material:forged", "style:mil-spec"]),
        ("Anderson Manufacturing", "AM-15 Stripped Lower Receiver", "AM-LO-15", 6900, 8.2,
         "Entry-level forged lower receiver, mil-spec dimensions.",
         ["material:forged", "style:mil-spec"]),
        ("Sons of Liberty Gun Works", "Billet Stripped Lower Receiver", "SOLGW-LO-BLT", 22900, 7.6,
         "Billet lower with flared magwell, machined from 7075-T6 aluminum.",
         ["material:billet", "style:mil-spec"]),
        ("Spike's Tactical", "Spider Stripped Lower Receiver", "ST-LO-SPD", 15900, 7.9,
         "Forged lower with laser-engraved spider logo, mil-spec dimensions.",
         ["material:forged", "style:mil-spec"]),
        ("Battle Arms Development", "Billet Lower Receiver", "BAD-LO-BLT", 25900, 7.4,
         "Lightweight billet lower with an integral trigger guard.",
         ["material:billet", "style:mil-spec"]),
        ("Palmetto State Armory", "PA-15 Stripped Lower Receiver", "PSA-LO-15", 5900, 8.2,
         "Budget-friendly forged lower, mil-spec dimensions.",
         ["material:forged", "style:mil-spec"]),
    ],
    "trigger": [
        ("Geissele Automatics", "SSA-E Two Stage Trigger", "GEI-TRG-SSAE", 24000, 5.5,
         "Two-stage trigger with a crisp, consistent 3.5 lb pull.",
         ["type:two-stage", "pull:3.5lb"]),
        ("CMC Triggers", "Single Stage Flat Trigger", "CMC-TRG-FLAT", 19900, 5.0,
         "Drop-in single-stage flat trigger, 3.5 lb pull weight.",
         ["type:single-stage", "pull:3.5lb"]),
        ("Timney Triggers", "Competition Trigger", "TIM-TRG-COMP", 22000, 5.2,
         "Drop-in single-stage trigger tuned for a crisp 3 lb pull.",
         ["type:single-stage", "pull:3lb"]),
        ("Elftmann Tactical", "3 Gun Trigger", "ELF-TRG-3G", 25900, 5.4,
         "Adjustable single-stage trigger designed for competition use.",
         ["type:single-stage", "pull:3.5lb"]),
        ("Rise Armament", "RA-434 Trigger", "RA-TRG-434", 15900, 5.3,
         "Single-stage drop-in trigger with a 3.5 lb pull.",
         ["type:single-stage", "pull:3.5lb"]),
        ("TriggerTech", "AR Diamond Trigger", "TT-TRG-DIA", 27900, 5.1,
         "Frictionless release single-stage trigger, 2.5 lb pull.",
         ["type:single-stage", "pull:2.5lb"]),
    ],
    "pistol-grip": [
        ("Magpul", "MOE Grip", "MAG-GRP-MOE", 2000, 3.0,
         "Ergonomic polymer pistol grip with a moderate palm swell.",
         ["material:polymer", "texture:moe"]),
        ("BCM", "Gunfighter Grip Mod 3", "BCM-GRP-GF3", 2400, 3.0,
         "Slim polymer grip with an aggressive texture for a secure hold.",
         ["material:polymer", "texture:gunfighter"]),
        ("Hogue", "OverMolded Grip", "HOG-GRP-OM", 2200, 3.4,
         "Rubber overmolded grip with finger grooves for control.",
         ["material:rubber", "texture:finger-groove"]),
        ("Ergo Grip", "SUREGRIP", "ERGO-GRP-SG", 1800, 3.1,
         "Polymer grip with a pronounced palm swell for reduced fatigue.",
         ["material:polymer", "texture:palm-swell"]),
        ("Magpul", "MOE-K2 Grip", "MAG-GRP-K2", 2100, 3.0,
         "Vertical grip angle with a beavertail for wrist comfort.",
         ["material:polymer", "texture:k2"]),
        ("B5 Systems", "Type 23 P-Grip", "B5-GRP-T23", 2500, 3.2,
         "Polymer grip with an adjustable palm shelf.",
         ["material:polymer", "texture:type23"]),
    ],
    "magazine": [
        ("Magpul", "PMAG 30 GEN M3", "MAG-MAG-PM3-30", 1500, 4.2,
         "30-round polymer magazine, the standard-issue AR-15 magazine.",
         ["caliber:556", "capacity:30", "material:polymer"]),
        ("Lancer Systems", "L5AWM 30rd Magazine", "LAN-MAG-L5-30", 1800, 4.4,
         "30-round translucent polymer magazine with steel feed lips.",
         ["caliber:556", "capacity:30", "material:polymer-translucent"]),
        ("Magpul", "PMAG 30 GEN M3 .300 BLK", "MAG-MAG-PM3-300B", 1600, 4.2,
         "30-round polymer magazine marked and tuned for .300 Blackout.",
         ["caliber:300blk", "capacity:30", "material:polymer"]),
        ("C Products Defense", "6.5 Grendel 26rd Magazine", "CPD-MAG-GRN-26", 2900, 5.6,
         "26-round stainless steel magazine for 6.5 Grendel.",
         ["caliber:65grendel", "capacity:26", "material:stainless-steel"]),
        ("D&H Industries", "USGI 30rd Aluminum Magazine", "DH-MAG-USGI-30", 1200, 4.0,
         "Mil-spec aluminum magazine with a stainless spring.",
         ["caliber:556", "capacity:30", "material:aluminum"]),
        ("Magpul", "PMAG 10 GEN M3", "MAG-MAG-PM3-10", 1400, 3.4,
         "10-round polymer magazine for capacity-restricted states.",
         ["caliber:556", "capacity:10", "material:polymer"]),
    ],
    "stock-brace": [
        ("Magpul", "SL-K Carbine Stock", "MAG-STK-SLK", 8900, 8.0,
         "Slim, low-profile fixed carbine stock for mil-spec tubes.",
         ["buffertube:mil-spec", "type:fixed-stock"]),
        ("SB Tactical", "SBA3 Pistol Brace", "SBT-STK-SBA3", 12900, 10.4,
         "Adjustable pistol stabilizing brace for mil-spec tubes.",
         ["buffertube:mil-spec", "type:pistol-brace"]),
        ("B5 Systems", "SOPMOD Bravo Stock", "B5-STK-SOPB", 9900, 9.6,
         "Adjustable fixed stock with multiple cheek-weld heights.",
         ["buffertube:mil-spec", "type:fixed-stock"]),
        ("Magpul", "MOE Carbine Stock (Commercial)", "MAG-STK-MOEC", 5900, 7.8,
         "Adjustable carbine stock sized for commercial-diameter tubes.",
         ["buffertube:commercial", "type:fixed-stock"]),
        ("VLTOR", "IMOD Stock", "VLT-STK-IMOD", 9500, 9.2,
         "Adjustable stock with an internal storage compartment.",
         ["buffertube:mil-spec", "type:fixed-stock"]),
        ("Maxim Defense", "CQB Pistol Brace", "MAX-STK-CQB", 24900, 11.0,
         "Compact folding pistol stabilizing brace for mil-spec tubes.",
         ["buffertube:mil-spec", "type:pistol-brace"]),
        ("Generic", "Mil-Spec Carbine Receiver Extension", "GEN-BT-MS", 1800, 3.6,
         "Six-position mil-spec diameter receiver extension.",
         ["buffertube:mil-spec", "diameter:1.148", "type:buffer-tube"]),
        ("Generic", "Commercial Carbine Receiver Extension", "GEN-BT-COM", 1600, 3.7,
         "Six-position commercial diameter receiver extension.",
         ["buffertube:commercial", "diameter:1.17", "type:buffer-tube"]),
        ("BCM", "Mil-Spec Receiver Extension", "BCM-BT-MS", 2900, 3.5,
         "Mil-spec diameter receiver extension, six-position.",
         ["buffertube:mil-spec", "diameter:1.148", "type:buffer-tube"]),
        ("LMT", "Mil-Spec Buffer Tube", "LMT-BT-MS", 3400, 3.6,
         "Mil-spec diameter receiver extension.",
         ["buffertube:mil-spec", "diameter:1.148", "type:buffer-tube"]),
        ("Magpul", "Mil-Spec Buffer Tube", "MAG-BT-MS", 2500, 3.5,
         "Mil-spec diameter receiver extension, six-position.",
         ["buffertube:mil-spec", "diameter:1.148", "type:buffer-tube"]),
        ("VLTOR", "A5 Receiver Extension", "VLT-BT-A5", 4500, 3.9,
         "Extended-length receiver extension for the VLTOR A5 buffer system.",
         ["buffertube:mil-spec", "diameter:1.148", "system:a5", "type:buffer-tube"]),
        ("Sprinco", "Carbine Buffer Kit", "SPR-BUF-CAR", 3900, 5.5,
         "Carbine-weight buffer with a chrome-silicon spring.",
         ["weight:carbine", "springtype:standard", "type:buffer-kit"]),
        ("JP Enterprises", "Silent Captured Spring Kit", "JP-BUF-SCS", 8900, 5.9,
         "Silent captured spring system for smooth, quiet cycling.",
         ["weight:h2", "springtype:silent-capture", "type:buffer-kit"]),
        ("BCM", "Rifle Buffer Kit", "BCM-BUF-RIF", 4200, 6.1,
         "Rifle-weight buffer with a standard-rate spring.",
         ["weight:rifle", "springtype:standard", "type:buffer-kit"]),
        ("Geissele Automatics", "Super 42 Braided Buffer Spring Kit", "GEI-BUF-S42", 5900, 5.6,
         "Braided wire buffer spring for reduced buffer bounce.",
         ["weight:h2", "springtype:braided", "type:buffer-kit"]),
        ("VLTOR", "A5 Buffer Kit", "VLT-BUF-A5", 5400, 6.4,
         "Extended-length buffer and spring for the A5 receiver extension.",
         ["weight:a5h2", "springtype:a5", "type:buffer-kit"]),
        ("Odin Works", "Buffer Kit H3", "ODIN-BUF-H3", 4600, 6.6,
         "Heavier H3-weight buffer for suppressed or gas-heavy builds.",
         ["weight:h3", "springtype:standard", "type:buffer-kit"]),
    ],
    "optic": [
        ("Trijicon", "MRO Red Dot Sight", "TRI-OPT-MRO", 44900, 4.0,
         "Rugged 2 MOA red dot sight with a wide field of view.",
         ["type:red-dot", "magnification:1x"]),
        ("Aimpoint", "PRO Red Dot Sight", "AIM-OPT-PRO", 44900, 11.8,
         "Patrol rifle optic red dot with a multi-year battery life.",
         ["type:red-dot", "magnification:1x"]),
        ("Holosun", "507C X2 Red Dot", "HOL-OPT-507C", 32900, 2.4,
         "Multi-reticle red dot with solar failsafe and shake-awake.",
         ["type:red-dot", "magnification:1x"]),
        ("Vortex Optics", "Strike Eagle 1-6x24", "VTX-OPT-SE16", 39900, 19.9,
         "First-focal-plane low-power variable optic with an illuminated reticle.",
         ["type:lpvo", "magnification:1-6x"]),
        ("EOTech", "EXPS3 Holographic Sight", "EOT-OPT-EXPS3", 69900, 11.2,
         "Holographic weapon sight with a circle-dot reticle.",
         ["type:holographic", "magnification:1x"]),
        ("Leupold", "Mark 4HD 4.5-18x40", "LEU-OPT-M4HD", 129900, 26.5,
         "Precision rifle scope with a first-focal-plane reticle.",
         ["type:scope", "magnification:4.5-18x"]),
        ("American Defense Manufacturing", "QD Mount", "ADM-MNT-QD", 12900, 3.2,
         "Quick-detach optic mount with a repeatable return-to-zero.",
         ["type:mount", "mounttype:qd", "height:lower-1-3"]),
        ("LaRue Tactical", "LT104 QD Mount", "LAR-MNT-104", 16900, 4.6,
         "Quick-detach absolute co-witness height mount.",
         ["type:mount", "mounttype:qd", "height:absolute-co-witness"]),
        ("Geissele Automatics", "Super Precision Mount", "GEI-MNT-SP", 21900, 3.6,
         "Precision-machined quick-detach mount for red dot sights.",
         ["type:mount", "mounttype:qd", "height:lower-1-3"]),
        ("Scalarworks", "LEAP Mount", "SCL-MNT-LEAP", 24900, 2.9,
         "Ultra-lightweight direct-mount optic riser.",
         ["type:mount", "mounttype:direct", "height:lower-1-3"]),
        ("Vortex Optics", "Precision Matched Riser", "VTX-MNT-PMR", 8900, 3.8,
         "Direct-mount riser matched to absolute co-witness height.",
         ["type:mount", "mounttype:direct", "height:absolute-co-witness"]),
        ("Unity Tactical", "FAST Mount", "UNI-MNT-FAST", 17900, 2.1,
         "Low-profile direct-mount optic riser.",
         ["type:mount", "mounttype:direct", "height:lower-1-3"]),
    ],
    "muzzle-device": [
        ("SureFire", "WARCOMP Muzzle Brake", "SF-MZL-WARC", 15900, 3.8,
         "Muzzle brake and flash suppressor for 5.56 NATO, 1/2x28 threads.",
         ["thread:1-2x28", "type:brake"]),
        ("Precision Armament", "M4-72 Severe-Duty Compensator", "PA-MZL-M472", 9900, 2.8,
         "Recoil-reducing compensator for 5.56 NATO, 1/2x28 threads.",
         ["thread:1-2x28", "type:compensator"]),
        ("VG6 Precision", "Gamma 556 Muzzle Brake", "VG6-MZL-G556", 8900, 3.0,
         "Three-chamber muzzle brake for 5.56 NATO, 1/2x28 threads.",
         ["thread:1-2x28", "type:brake"]),
        ("Griffin Armament", "Taper Mount Flash Comp", "GRF-MZL-TMFC", 6900, 2.6,
         "Flash-suppressing compensator for 5.56 NATO, 1/2x28 threads.",
         ["thread:1-2x28", "type:flash-hider"]),
        ("SureFire", "SOCOM MB .300 Blackout", "SF-MZL-SOCOM", 17900, 4.2,
         "Muzzle brake for .300 Blackout, 5/8x24 threads.",
         ["thread:5-8x24", "type:brake"]),
        ("Odin Works", "Boar Muzzle Brake 6.5", "ODIN-MZL-BOAR", 7900, 3.4,
         "Muzzle brake for 6.5 Grendel, 5/8x24 threads.",
         ["thread:5-8x24", "type:brake"]),
    ],
}


async def main() -> None:
    settings = Settings()
    database = Database(settings.database_url)

    async with database.session() as session:
        category_ids: dict[str, object] = {}

        print("Seeding catalog categories...")
        for slug, name, section, sort_order in CATEGORIES:
            existing = await session.execute(
                select(PartCategoryRecord).where(PartCategoryRecord.slug == slug)
            )
            record = existing.scalar_one_or_none()
            if record is None:
                record = PartCategoryRecord(
                    id=uuid4(), slug=slug, name=name, section=section, sort_order=sort_order
                )
                session.add(record)
                await session.flush()
                print(f"  created category: {name}")
            else:
                record.name = name
                record.section = section
                record.sort_order = sort_order
                print(f"  synced category: {name}")
            category_ids[slug] = record.id

        print("\nSeeding catalog products...")
        for category_slug, products in PRODUCTS.items():
            category_id = category_ids[category_slug]
            for brand, name, sku, price_cents, weight_oz, description, tags in products:
                slug = slugify(f"{brand} {name}")
                existing = await session.execute(
                    select(ProductRecord.id).where(ProductRecord.slug == slug)
                )
                if existing.scalar_one_or_none() is not None:
                    print(f"  already exists: {brand} {name}")
                    continue

                session.add(
                    ProductRecord(
                        id=uuid4(),
                        category_id=category_id,
                        brand=brand,
                        name=name,
                        slug=slug,
                        sku=sku,
                        description=description,
                        price_cents=price_cents,
                        weight_oz=weight_oz,
                        image_url=None,
                        affiliate_url="#",
                        affiliate_retailer_name=None,
                        stock_status="in_stock",
                        attribute_tags=tags,
                        is_active=True,
                    )
                )
                print(f"  created: {brand} {name}")

        await session.flush()

    await database.dispose()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
