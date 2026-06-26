#!/usr/bin/env python3
"""
istation_extractor.py
=====================
Istation Historical Data Extractor — writes directly to Google Drive for Desktop

What this does:
  1. Opens Chrome and walks through the Istation SSO login (you finish the
     Google auth step manually in the browser window that appears).
  2. Grabs your session cookies and hands them to a requests.Session so all
     subsequent downloads happen quietly in the background.
  3. Iterates every district × product × school-year × month, builds the
     correct export URL, downloads the CSV, and saves it directly into your
     local Google Drive folder — Drive for Desktop syncs it automatically.

Setup (run once):
  pip install -r requirements.txt

ChromeDriver:
  Make sure ChromeDriver matches your Chrome version.
  https://googlechromelabs.github.io/chrome-for-testing/

Usage:
  python istation_extractor.py
"""

import csv
import sys
import time
from datetime import datetime
from pathlib import Path

import requests as http_lib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

ISTATION_LOGIN_URL = "https://secure.istation.com/?DefaultDomain=istation"
BASE_EXPORT_URL    = "https://secure.istation.com/Report/AssessmentResultExport"
BASE_USAGE_URL     = "https://secure.istation.com/Report/UsageSummaryExport"

# Local Google Drive for Desktop sync path — files written here upload automatically
DRIVE_BASE = Path.home() / (
    "Library/CloudStorage/"
    "GoogleDrive-derek.armesto@amiralearning.com/"
    "My Drive"
)
PROJECT_LABEL = "Historical Data Request (Istation) - April 2026 Pull"

# ── Product definitions ───────────────────────────────────────────────────────
PRODUCTS = {
    "Reading": {"pid": "ISIPEN",   "product_key": "EN", "lexile": True},
    "Lectura": {"pid": "ISIPES",   "product_key": "SP", "lexile": True},
    "Math":    {"pid": "ISIPMath", "product_key": None,  "lexile": False},
}

USAGE_PRODUCTS = {
    "Reading": {"pid": "ISIPEN",         "product_key": "EN"},
    "Lectura": {"pid": "SpanishReading", "product_key": "SP"},
    "Math":    {"pid": "ISIPMath",       "product_key": "Math"},
}

LEVEL_MOVEMENT_PRODUCTS = {
    "Reading": {"pid": "ISIPEN",   "product_key": "EN",   "skill": "Overall"},
    "Lectura": {"pid": "ISIPES",   "product_key": "SP",   "skill": "Overall"},
    "Math":    {"pid": "ISIPMath", "product_key": "Math", "skill": "Math"},
}

# ── Month mapping (Istation Period param) ────────────────────────────────────
MONTHS = {
    0:  "August",
    1:  "September",
    2:  "October",
    3:  "November",
    4:  "December",
    5:  "January",
    6:  "February",
    7:  "March",
    8:  "April",
    9:  "May",
    10: "June",
    11: "July",
}

# ── District list ─────────────────────────────────────────────────────────────
# years = list of school-year START years
#   e.g. 2022 → 2022-23 school year,  range(2022, 2025) → [2022, 2023, 2024]
DISTRICTS = [
    {
        "name": "Socorro ISD",
        "state": "Texas",
        "oid": "22327",
        "products": ["Reading"],
        "years": list(range(2022, 2025)),
    },
    {
        "name": "Ysleta ISD",
        "state": "Texas",
        "oid": "28870",
        "products": ["Reading", "Lectura"],
        "years": list(range(2022, 2025)),
    },
    {
        "name": "Lubbock ISD",
        "state": "Texas",
        "oid": "16827",
        "products": ["Reading", "Lectura"],
        "years": list(range(2022, 2025)),
    },
    {
        "name": "Amarillo ISD",
        "state": "Texas",
        "oid": "49410",
        "products": ["Reading", "Lectura", "Math"],
        "years": list(range(2022, 2025)),
    },
    {
        "name": "Lubbock-Cooper ISD",
        "state": "Texas",
        "oid": "19690",
        "products": ["Reading", "Lectura", "Math"],
        "years": list(range(2022, 2025)),
    },
    {
        "name": "Rockwall ISD",
        "state": "Texas",
        "oid": "43870",
        "products": ["Reading", "Lectura"],
        "years": list(range(2022, 2025)),
    },
    {
        "name": "Lockhart ISD",
        "state": "Texas",
        "oid": "56738",
        "products": ["Reading", "Lectura"],
        "years": list(range(2021, 2025)),
    },
    {
        "name": "Irving ISD",
        "state": "Texas",
        "oid": "18327",
        "products": ["Reading", "Lectura"],
        "years": list(range(2022, 2025)),
    },
    {
        "name": "Eagle Pass ISD",
        "state": "Texas",
        "oid": "9571",
        "products": ["Reading", "Lectura"],
        "years": list(range(2021, 2025)),
    },
    {
        "name": "Carrollton-Farmers Branch ISD",
        "state": "Texas",
        "oid": "47945",
        "products": ["Reading", "Lectura", "Math"],
        "years": list(range(2022, 2025)),
    },
    {
        "name": "La Porte ISD",
        "state": "Texas",
        "oid": "8447",
        "products": ["Reading", "Lectura"],
        "years": list(range(2023, 2025)),
    },
    {
        "name": "Carroll ISD",
        "state": "Texas",
        "oid": "61477",
        "products": ["Math"],
        "years": list(range(2022, 2025)),
    },
    {
        "name": "International Leadership of Texas",
        "state": "Texas",
        "oid": "67989",
        "products": ["Reading", "Lectura"],
        "years": list(range(2022, 2025)),
    },
    {
        "name": "Waller ISD",
        "state": "Texas",
        "oid": "17106",
        "products": ["Reading", "Lectura"],
        "years": list(range(2023, 2025)),
    },
    {
        "name": "Little Elm ISD",
        "state": "Texas",
        "oid": "44452",
        "products": ["Reading", "Lectura"],
        "years": list(range(2023, 2025)),
    },
    {
        "name": "Leander ISD",
        "state": "Texas",
        "oid": "49647",
        "products": ["Reading", "Lectura"],
        "years": list(range(2021, 2025)),
    },
    {
        "name": "Forney ISD",
        "state": "Texas",
        "oid": "12447",
        "products": ["Reading", "Lectura", "Math"],
        "years": list(range(2023, 2025)),
    },
    {
        "name": "Sharyland ISD",
        "state": "Texas",
        "oid": "41250",
        "products": ["Reading", "Lectura"],
        "years": list(range(2021, 2025)),
    },
    {
        "name": "Northside ISD",
        "state": "Texas",
        "oid": "51830",
        "products": ["Reading", "Lectura"],
        "years": list(range(2022, 2025)),
    },
    {
        "name": "Seguin ISD",
        "state": "Texas",
        "oid": "55593",
        "products": ["Reading", "Lectura"],
        "years": list(range(2021, 2025)),
    },
    {
        "name": "Liberty Hill ISD",
        "state": "Texas",
        "oid": "47750",
        "products": ["Reading", "Lectura"],
        "years": list(range(2023, 2025)),
    },
    {
        "name": "Manor ISD",
        "state": "Texas",
        "oid": "18607",
        "products": ["Reading", "Lectura"],
        "years": list(range(2023, 2025)),
    },
    {
        "name": "School District U-46",
        "state": "Illinois",
        "oid": "74722",
        "products": ["Reading", "Lectura"],
        "years": list(range(2018, 2025)),
    },
    {
        "name": "Milwaukee Public Schools",
        "state": "Wisconsin",
        "oid": "19485",
        "products": ["Lectura"],
        "years": list(range(2018, 2025)),
    },
    {"name": "Hidalgo ISD",             "state": "Texas",    "oid": "50563", "products": ["Reading", "Lectura"], "years": list(range(2022, 2025))},
    {"name": "Pinellas County Schools", "state": "Florida",  "oid": "35168", "products": ["Reading"],            "years": list(range(2018, 2025))},
    {"name": "Polk County",             "state": "Florida",  "oid": "4694",  "products": ["Reading"],            "years": list(range(2018, 2025))},
    {"name": "Palm Beach County SD",    "state": "Florida",  "oid": "34788", "products": ["Lectura"],            "years": list(range(2018, 2025))},
    {"name": "Broward County",          "state": "Florida",  "oid": "14441", "products": ["Lectura"],            "years": list(range(2018, 2025))},
    {"name": "Volusia County",          "state": "Florida",  "oid": "4704",  "products": ["Lectura"],            "years": list(range(2018, 2025))},
    {"name": "Manatee County",          "state": "Florida",  "oid": "74189", "products": ["Lectura"],            "years": list(range(2018, 2025))},
    {"name": "CUSD 300",                "state": "Illinois", "oid": "82377", "products": ["Reading", "Math"],     "years": [2024]},
]


# ─────────────────────────────────────────────────────────────────────────────
# ISTATION LOGIN  (Selenium — human completes the Google SSO step)
# ─────────────────────────────────────────────────────────────────────────────

def login_to_istation(driver: webdriver.Chrome) -> None:
    """
    Navigate to the Istation login page, type 'Istation' in the domain field
    to reveal the SSO button, click it, auto-fill the Google email, then wait
    for you to complete password/2FA.  Returns when the session is live.
    """
    print("\n🔐 Opening Istation login page...")
    driver.get(ISTATION_LOGIN_URL)

    # Wait for identity server redirect
    WebDriverWait(driver, 15).until(
        lambda d: "idsrv.istation.com" in d.current_url or "secure.istation.com" in d.current_url
    )
    time.sleep(2)

    # Type "Istation" in domain field and blur to reveal SSO button
    domain_field = None
    for by, selector in [
        (By.ID, "Domain"),
        (By.NAME, "Domain"),
        (By.XPATH, "//input[@type='text']"),
    ]:
        try:
            domain_field = WebDriverWait(driver, 5).until(EC.presence_of_element_located((by, selector)))
            break
        except Exception:
            continue

    if domain_field:
        domain_field.clear()
        domain_field.send_keys("Istation")
        time.sleep(0.5)
        driver.find_element(By.TAG_NAME, "body").click()
        print("   Typed 'Istation' — waiting for SSO button...")
        time.sleep(1.5)

    # Click the SSO button
    sso_clicked = False
    for by, selector in [
        (By.ID, "samlButton"),
        (By.XPATH, "//button[contains(@class,'login-btn-saml')]"),
        (By.XPATH, "//button[contains(@class,'saml')]"),
        (By.XPATH, "//a[contains(@class,'saml')]"),
        (By.XPATH, "//*[contains(@href,'saml') or contains(@href,'google') or contains(@href,'external')]"),
    ]:
        try:
            el = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((by, selector)))
            el.click()
            print("   Clicked SSO button")
            sso_clicked = True
            break
        except Exception:
            continue

    if not sso_clicked:
        input("\n⚠️  Could not find SSO button automatically.\n"
              "    Please click it in the browser, then press Enter here: ")

    # Auto-fill Google email (or select account if already signed in)
    WebDriverWait(driver, 30).until(lambda d: "accounts.google.com" in d.current_url)
    time.sleep(0.5)

    try:
        # Case 1: account chooser page (already signed into Google)
        account = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@data-email='derek.armesto@amiralearning.com']"))
        )
        account.click()
        print("   Selected Google account from chooser...")
    except Exception:
        # Case 2: standard email input page — try multiple selectors
        email_field = None
        for xpath in [
            "//input[@type='email']",
            "//input[@name='identifier']",
            "//input[@autocomplete='username']",
        ]:
            try:
                email_field = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                break
            except Exception:
                continue

        if email_field:
            email_field.clear()
            email_field.send_keys("derek.armesto@amiralearning.com")
            time.sleep(0.5)
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Next']]"))
            ).click()
            print("   Google email entered — please complete password/2FA in the browser...")
        else:
            input("\n⚠️  Could not auto-fill Google login.\n"
                  "    Please enter your email manually in the browser, then press Enter here: ")

    # Wait up to 3 minutes for full login to complete
    print("\n⏳ Waiting up to 3 minutes for login to complete...\n")
    WebDriverWait(driver, 180).until(
        lambda d: (
            "secure.istation.com" in d.current_url
            and "Account" not in d.current_url
            and "idsrv" not in d.current_url
        )
    )
    print("🎉 Login successful — session is live.")


def extract_requests_session(driver: webdriver.Chrome) -> http_lib.Session:
    """Copy cookies from Selenium into a requests.Session for headless downloads."""
    session = http_lib.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=cookie.get("domain", ""),
        )
    ua = driver.execute_script("return navigator.userAgent")
    session.headers.update({
        "User-Agent": ua,
        "Referer": "https://secure.istation.com/",
    })
    return session


# ─────────────────────────────────────────────────────────────────────────────
# URL BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_export_url(org_oid: str, product: dict, year: int, period: int) -> str:
    """
    Build the AssessmentResultExport URL for one district/product/year/month.

    Pattern:
      /Report/AssessmentResultExport/d{OID}?Period=…&Pid=…&Year=…&AllResults=True
    """
    params = [
        f"Period={period}",
        "Skill=Overall",
        f"Pid={product['pid']}",
    ]
    if product["product_key"]:
        params.append(f"ProductKey={product['product_key']}")
    params += [
        "FilterByLocation=Any",
        "FilterType=students",
        "WgOid=0",
        "AllResults=True",
        f"Year={year}",
    ]
    if product["lexile"]:
        params.append("Lexile=True")

    return f"{BASE_EXPORT_URL}/d{org_oid}?{'&'.join(params)}"


def build_usage_url(org_oid: str, product: dict, year: int) -> str:
    """
    Build the UsageSummaryExport URL for one district/product/year.

    Pattern:
      /Report/UsageSummaryExport/d{OID}?weeks=0&Pid=…&ProductKey=…&FilterType=students&WgOid=0&AllResults=True&Year=…
    """
    params = [
        "weeks=0",
        f"Pid={product['pid']}",
        f"ProductKey={product['product_key']}",
        "FilterType=students",
        "WgOid=0",
        "AllResults=True",
        f"Year={year}",
    ]
    return f"{BASE_USAGE_URL}/d{org_oid}?{'&'.join(params)}"


def build_level_movement_url(org_oid: str, product: dict, year: int) -> str:
    """
    Build the Level Movement URL for one district/product/year.

    Pattern:
      /Report/AssessmentResultExport/d{OID}?Skill=Overall&Pid=…&ProductKey=…&FilterType=students&WgOid=0&AllResults=False&Year=…
    """
    params = [
        f"Skill={product['skill']}",
        f"Pid={product['pid']}",
    ]
    if product["product_key"]:
        params.append(f"ProductKey={product['product_key']}")
    params += [
        "FilterType=students",
        "WgOid=0",
        "AllResults=True",
        f"Year={year}",
    ]
    return f"{BASE_EXPORT_URL}/d{org_oid}?{'&'.join(params)}"


# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOADER
# ─────────────────────────────────────────────────────────────────────────────

def download_and_save(
    session: http_lib.Session,
    url: str,
    save_path: Path,
) -> bool:
    """
    Download one CSV and write it to save_path.
    Returns True if real data was written, False if the response was empty.
    Raises RuntimeError if the session has expired.
    """
    try:
        resp = session.get(url, timeout=90)

        # Redirect to login page = session expired
        if "/Account/LogOn" in resp.url or "/Account/" in resp.url:
            raise RuntimeError("Session expired — please re-run the script to log in again.")

        resp.raise_for_status()
        content = resp.content

        # Skip empty responses or HTML error pages
        if len(content) < 50 or content.lstrip()[:1] in (b"<", b" "):
            return False

        save_path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file first — only rename once complete so a
        # interrupted write never leaves a corrupt file that resume skips
        tmp_path = save_path.with_suffix(".tmp")
        tmp_path.write_bytes(content)
        tmp_path.rename(save_path)
        return True

    except RuntimeError:
        raise
    except Exception as exc:
        print(f"\n    ⚠️  Error: {exc}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST SHEET LOADER
# ─────────────────────────────────────────────────────────────────────────────

# Maps product names used in the request sheet → internal PRODUCTS keys
PRODUCT_NAME_MAP = {
    "reading":  "Reading",
    "math":     "Math",
    "lectura":  "Lectura",
    "spanish":  "Lectura",
}

SCRIPT_DIR = Path(__file__).parent


def parse_year_range(year_range: str) -> set[int]:
    """
    Parse the School Year(s) field into a set of school-year start years.

    Formats supported:
      "2022-23"   → {2022}          single year, abbreviated end
      "2022-2023" → {2022}          single year, full end
      "2021-2025" → {2021,2022,2023,2024}  range (end year > start + 1)
    """
    parts = year_range.strip().split("-")
    start = int(parts[0])
    if len(parts) == 2 and len(parts[1]) == 4:
        end = int(parts[1])
        if end > start + 1:
            return set(range(start, end))
    return {start}


def load_districts_from_request_sheet() -> list:
    """
    Reads 'Historical Data Request - Sheet1.csv' and builds a districts list
    in the same format as the hardcoded DISTRICTS constant, looking up OIDs
    from 'District name and organization oid.csv'.
    Skips rows where Completed == TRUE.
    Every district is exported for both assessment and usage.
    """
    request_csv  = SCRIPT_DIR / "Historical Data Request - Sheet1.csv"
    oid_csv      = SCRIPT_DIR / "District name and organization oid.csv"

    if not request_csv.exists():
        print(f"❌ Request sheet not found: {request_csv}")
        return []
    if not oid_csv.exists():
        print(f"❌ OID lookup not found: {oid_csv}")
        return []

    # Build OID lookup: district name (lowercase) → organization OID
    oid_lookup: dict[str, str] = {}
    with open(oid_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = row["DISTRICT NAME"].strip().lower()
            oid_lookup[key] = row["ORGANIZATION OID"].strip()

    # Group request rows by district name
    from collections import defaultdict
    grouped: dict[str, dict] = defaultdict(lambda: {"state": "", "oid": "", "products": set(), "years": set()})

    with open(request_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("Completed", "").strip().upper() == "TRUE":
                continue

            name       = row["District"].strip()
            state      = row["State"].strip()
            year_range   = row["School Year(s)"].strip()
            raw_products = [p.strip() for p in row["Product"].split(",")]

            grouped[name]["state"] = state
            grouped[name]["years"].update(parse_year_range(year_range))

            for raw in raw_products:
                product = PRODUCT_NAME_MAP.get(raw.lower())
                if not product:
                    print(f"⚠️  Unknown product '{raw}' for {name} — skipping")
                    continue
                grouped[name]["products"].add(product)

            if not grouped[name]["oid"]:
                oid = oid_lookup.get(name.lower(), "")
                if not oid:
                    print(f"⚠️  OID not found for '{name}' — check district name spelling")
                grouped[name]["oid"] = oid

    return [
        {
            "name":     name,
            "state":    info["state"],
            "oid":      info["oid"],
            "products": sorted(info["products"]),
            "years":    sorted(info["years"]),
        }
        for name, info in grouped.items()
    ]


def mark_district_completed(district_name: str) -> None:
    """Rewrites the request sheet setting Completed=TRUE for all rows matching district_name."""
    request_csv = SCRIPT_DIR / "Historical Data Request - Sheet1.csv"
    rows = []
    fieldnames = None
    with open(request_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        for row in reader:
            if row["District"].strip() == district_name:
                row["Completed"] = "TRUE"
            rows.append(row)
    with open(request_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def count_total_files(districts: list) -> int:
    assessment_count = sum(
        len(d["years"]) * len(d["products"]) * len(MONTHS)
        for d in districts if d["years"]
    )
    usage_count = sum(
        len(d["years"]) * len(d["products"])
        for d in districts if d["years"]
    )
    level_movement_count = sum(
        len(d["years"]) * len(d["products"])
        for d in districts if d["years"]
    )
    return assessment_count + usage_count + level_movement_count


def main():
    # Optional --test flag: only run Socorro ISD
    test_mode = "--test" in sys.argv

    if test_mode:
        districts = [d for d in DISTRICTS if d["name"] == "Socorro ISD"]
    else:
        districts = load_districts_from_request_sheet()
        if not districts:
            print("❌ No districts found in the request sheet. Nothing to do.")
            return

    if test_mode:
        print("🧪 TEST MODE — Socorro ISD only\n")

    # Verify the Drive base folder exists before we start
    if not DRIVE_BASE.exists():
        print(f"❌ Google Drive folder not found at:\n   {DRIVE_BASE}")
        print("   Make sure Google Drive for Desktop is running and signed in.")
        return

    print(f"✅ Google Drive confirmed:\n   {DRIVE_BASE}\n")

    # ── Step 1: Istation SSO Login ────────────────────────────────────────────
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        login_to_istation(driver)
        session = extract_requests_session(driver)
    finally:
        driver.quit()

    print("✅ Browser closed — proceeding with downloads.\n")

    # ── Step 2: Download + Save Loop ──────────────────────────────────────────
    total   = count_total_files(districts)
    done    = 0
    skipped = 0
    errors  = 0

    # Manifest log — written inside the project folder alongside the data
    project_dir = DRIVE_BASE / PROJECT_LABEL
    project_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / f"_manifest{'_test' if test_mode else ''}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    manifest_file = open(manifest_path, "w", newline="", encoding="utf-8")
    manifest = csv.writer(manifest_file)
    manifest.writerow(["district", "oid", "year", "product", "period", "status", "bytes", "file_path"])

    print(f"📦 Total export URLs to process: {total}")
    print(f"📋 Manifest: {manifest_path.name}")
    print("=" * 70)

    run_start = time.time()

    try:
        for district in districts:
            if not district["years"]:
                print(f"\n⏭️  Skipping {district['name']} ({district['state']}) — no years configured yet")
                manifest.writerow([district["name"], district["oid"], "", "", "", "skipped_no_years", 0, ""])
                manifest_file.flush()
                continue

            assessment_files = len(district["years"]) * len(district["products"]) * len(MONTHS)
            usage_files      = len(district["years"]) * len(district["products"])
            print(f"\n📂 {district['name']}  (OID: {district['oid']}) — {assessment_files} assessment + {usage_files} usage files")
            district_start = time.time()
            dist_done = dist_skipped = dist_errors = 0

            # ── Assessment (year × product × month) ──────────────────────────
            for year in district["years"]:
                sy_label = f"{year}-{str(year + 1)[-2:]}"

                for product_name in district["products"]:
                    product_cfg = PRODUCTS[product_name]

                    for period, month_name in MONTHS.items():
                        url = build_export_url(district["oid"], product_cfg, year, period)

                        save_path = (
                            DRIVE_BASE
                            / PROJECT_LABEL
                            / district["state"]
                            / district["name"]
                            / sy_label
                            / product_name
                            / "Assessment"
                            / f"{district['name']}_{product_name}_{sy_label}_{month_name}.csv"
                        )

                        if save_path.exists() and save_path.stat().st_size > 50:
                            print(f"  ⏭️  {save_path.name} ... already exists, skipping")
                            manifest.writerow([district["name"], district["oid"], sy_label, product_name, month_name, "already_exists", save_path.stat().st_size, str(save_path)])
                            done += 1
                            dist_done += 1
                            manifest_file.flush()
                            continue

                        print(f"  ↓  {save_path.name} ... ", end="", flush=True)

                        try:
                            saved = download_and_save(session, url, save_path)
                        except RuntimeError as exc:
                            print(f"\n\n❌ {exc}")
                            manifest.writerow([district["name"], district["oid"], sy_label, product_name, month_name, "session_expired", 0, ""])
                            manifest_file.flush()
                            return

                        if saved:
                            byte_count = save_path.stat().st_size
                            print(f"✅  ({byte_count:,} bytes)")
                            manifest.writerow([district["name"], district["oid"], sy_label, product_name, month_name, "saved", byte_count, str(save_path)])
                            done += 1
                            dist_done += 1
                        else:
                            print("no data — skipped")
                            manifest.writerow([district["name"], district["oid"], sy_label, product_name, month_name, "no_data", 0, ""])
                            skipped += 1
                            dist_skipped += 1

                        manifest_file.flush()
                        time.sleep(0.4)

            # ── Usage (year × product, one file each) ────────────────────────
            for year in district["years"]:
                sy_label = f"{year}-{str(year + 1)[-2:]}"

                for product_name in district["products"]:
                    usage_cfg = USAGE_PRODUCTS[product_name]
                    url = build_usage_url(district["oid"], usage_cfg, year)

                    save_path = (
                        DRIVE_BASE
                        / PROJECT_LABEL
                        / district["state"]
                        / district["name"]
                        / sy_label
                        / product_name
                        / "Usage"
                        / f"{district['name']}_{product_name}_{sy_label}_Usage.csv"
                    )

                    if save_path.exists() and save_path.stat().st_size > 50:
                        print(f"  ⏭️  {save_path.name} ... already exists, skipping")
                        manifest.writerow([district["name"], district["oid"], sy_label, product_name, "Usage", "already_exists", save_path.stat().st_size, str(save_path)])
                        done += 1
                        dist_done += 1
                        manifest_file.flush()
                        continue

                    print(f"  ↓  {save_path.name} ... ", end="", flush=True)

                    try:
                        saved = download_and_save(session, url, save_path)
                    except RuntimeError as exc:
                        print(f"\n\n❌ {exc}")
                        manifest.writerow([district["name"], district["oid"], sy_label, product_name, "Usage", "session_expired", 0, ""])
                        manifest_file.flush()
                        return

                    if saved:
                        byte_count = save_path.stat().st_size
                        print(f"✅  ({byte_count:,} bytes)")
                        manifest.writerow([district["name"], district["oid"], sy_label, product_name, "Usage", "saved", byte_count, str(save_path)])
                        done += 1
                        dist_done += 1
                    else:
                        print("no data — skipped")
                        manifest.writerow([district["name"], district["oid"], sy_label, product_name, "Usage", "no_data", 0, ""])
                        skipped += 1
                        dist_skipped += 1

                    manifest_file.flush()
                    time.sleep(0.4)

            # ── Level Movement (year × product, one file each) ───────────────
            for year in district["years"]:
                sy_label = f"{year}-{str(year + 1)[-2:]}"

                for product_name in district["products"]:
                    product_cfg = LEVEL_MOVEMENT_PRODUCTS[product_name]
                    url = build_level_movement_url(district["oid"], product_cfg, year)

                    save_path = (
                        DRIVE_BASE
                        / PROJECT_LABEL
                        / district["state"]
                        / district["name"]
                        / sy_label
                        / product_name
                        / "Level Movement"
                        / f"{district['name']}_{product_name}_{sy_label}_LevelMovement.csv"
                    )

                    if save_path.exists() and save_path.stat().st_size > 50:
                        print(f"  ⏭️  {save_path.name} ... already exists, skipping")
                        manifest.writerow([district["name"], district["oid"], sy_label, product_name, "Level Movement", "already_exists", save_path.stat().st_size, str(save_path)])
                        done += 1
                        dist_done += 1
                        manifest_file.flush()
                        continue

                    print(f"  ↓  {save_path.name} ... ", end="", flush=True)

                    try:
                        saved = download_and_save(session, url, save_path)
                    except RuntimeError as exc:
                        print(f"\n\n❌ {exc}")
                        manifest.writerow([district["name"], district["oid"], sy_label, product_name, "Level Movement", "session_expired", 0, ""])
                        manifest_file.flush()
                        return

                    if saved:
                        byte_count = save_path.stat().st_size
                        print(f"✅  ({byte_count:,} bytes)")
                        manifest.writerow([district["name"], district["oid"], sy_label, product_name, "Level Movement", "saved", byte_count, str(save_path)])
                        done += 1
                        dist_done += 1
                    else:
                        print("no data — skipped")
                        manifest.writerow([district["name"], district["oid"], sy_label, product_name, "Level Movement", "no_data", 0, ""])
                        skipped += 1
                        dist_skipped += 1

                    manifest_file.flush()
                    time.sleep(0.4)

            dist_elapsed = time.time() - district_start
            dist_mins, dist_secs = divmod(int(dist_elapsed), 60)
            print(f"\n   ✔ {district['name']} complete — saved: {dist_done}, no data: {dist_skipped}, errors: {dist_errors}  ⏱ {dist_mins}m {dist_secs}s")

            if dist_errors == 0 and not test_mode:
                mark_district_completed(district["name"])
                print(f"   📝 Marked complete in request sheet")

    finally:
        manifest_file.close()

    total_elapsed = time.time() - run_start
    total_mins, total_secs = divmod(int(total_elapsed), 60)
    total_hrs, total_mins = divmod(total_mins, 60)

    print("\n" + "=" * 70)
    print(f"🏁  Complete!")
    print(f"    Saved    : {done}")
    print(f"    No data  : {skipped}")
    print(f"    Errors   : {errors}")
    print(f"    Total time: {total_hrs}h {total_mins}m {total_secs}s")
    print(f"\n📁 Files written to:\n   {DRIVE_BASE}")
    print(f"📋 Manifest saved to:\n   {manifest_path}")


if __name__ == "__main__":
    main()
