"""
istation_live_actions.py
========================
Live/on-demand report downloader for secure.istation.com.
Mirrors the production istation_actions.py but targets the Istation domain
and uses the Istation SSO login flow (domain = "Istation").

Report types:
  assessment          — AssessmentResultExport (Executive Summary)
  usage               — UsageSummaryExport
  usage_trend         — UsageTrendExport
  level_movement      — AssessmentResultExport (no Period param, AllResults=False)
  assessment_completion — ISIPCompletionExport
"""

import time
from pathlib import Path

import requests as _requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

ISTATION_LOGIN_URL    = "https://secure.istation.com/?DefaultDomain=istation"
BASE_ASSESSMENT_URL   = "https://secure.istation.com/Report/AssessmentResultExport"
BASE_USAGE_URL        = "https://secure.istation.com/Report/UsageSummaryExport"
BASE_USAGE_TREND_URL  = "https://secure.istation.com/Report/UsageTrendExport"
BASE_COMPLETION_URL   = "https://secure.istation.com/Report/ISIPCompletionExport"

SCHOOL_YEAR_LABELS = {y: f"{y}-{str(y+1)[-2:]}" for y in range(2017, 2027)}

PRODUCTS = {
    "Reading": {"pid": "ISIPEN",   "product_key": "EN",   "lexile": True},
    "Lectura": {"pid": "ISIPES",   "product_key": "SP",   "lexile": True},
    "Math":    {"pid": "ISIPMath", "product_key": "Math", "lexile": False},
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

SKILLS = {
    "Reading": {
        "Overall":                  "Overall",
        "Letter Knowledge":         "LK",
        "Phonemic Awareness":       "PA",
        "Alphabetic Decoding":      "AD",
        "Reading Comprehension":    "CMP",
        "Listening Comprehension":  "LC2",
        "Vocabulary":               "VOC",
        "Spelling":                 "SPL",
        "Text Fluency":             "TF",
        "Oral Reading Fluency":     "ORF",
    },
    "Lectura": {
        "Overall":                         "Overall",
        "Written Communications":          "ESC",
        "Phonemic/Phonological Awareness": "FON",
        "Reading Comprehension":           "CMP",
        "Listening Comprehension":         "COMP_AU",
        "Vocabulary":                      "VOC",
        "Word Analysis":                   "SPL",
        "Text Fluency":                    "TF",
        "Oral Reading Fluency":            "ORF",
    },
    "Math": {
        "Overall":                           "Math",
        "Number Sense":                      "NS",
        "Number System":                     "NSY",
        "Computations & Algebraic Thinking": "CA",
        "Measurement & Data Analysis":       "MD",
        "Statistics & Data Analysis":        "SDA",
        "Geometry":                          "G",
        "Geometry & Measurement":            "GM",
    },
}

MONTHS = {
    0: "August",   1: "September", 2: "October",  3: "November",
    4: "December", 5: "January",   6: "February",  7: "March",
    8: "April",    9: "May",      10: "June",      11: "July",
}

GRADES = {
    "All": None, "PK": -1, "K": 0,
    "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5, "6th": 6,
    "7th": 7, "8th": 8, "9th": 9, "10th": 10, "11th": 11, "12th": 12,
}


# ── Auth ───────────────────────────────────────────────────────────────────────

def login_to_istation(driver, email: str, log_fn=None) -> None:
    from selenium.common.exceptions import TimeoutException as _TEx

    def log(msg):
        if log_fn: log_fn(msg)
        else: print(msg)

    log("🔐 Opening Istation login page...")
    driver.get(ISTATION_LOGIN_URL)

    WebDriverWait(driver, 15).until(
        lambda d: "idsrv.istation.com" in d.current_url or "secure.istation.com" in d.current_url
    )
    time.sleep(2)

    # Type "Istation" into the domain field
    domain_field = None
    for by, sel in [
        (By.ID, "Domain"),
        (By.NAME, "Domain"),
        (By.XPATH, "//input[@type='text']"),
    ]:
        try:
            domain_field = WebDriverWait(driver, 5).until(EC.presence_of_element_located((by, sel)))
            break
        except _TEx:
            continue

    if domain_field:
        domain_field.clear()
        domain_field.send_keys("Istation")
        time.sleep(0.5)
        driver.find_element(By.TAG_NAME, "body").click()
        time.sleep(1.5)
        log("   Typed 'Istation' — waiting for SSO button...")

    # Click SSO button
    sso_clicked = False
    for by, sel in [
        (By.ID, "samlButton"),
        (By.XPATH, "//button[contains(@class,'login-btn-saml')]"),
        (By.XPATH, "//button[contains(@class,'saml')]"),
        (By.XPATH, "//a[contains(@class,'saml')]"),
        (By.XPATH, "//*[contains(@href,'saml') or contains(@href,'google')]"),
    ]:
        try:
            el = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((by, sel)))
            el.click()
            sso_clicked = True
            log("   Clicked SSO button")
            break
        except _TEx:
            continue

    if not sso_clicked:
        log("⚠️  Could not find SSO button — click it manually in the browser")

    # Wait for Google login
    WebDriverWait(driver, 30).until(lambda d: "accounts.google.com" in d.current_url)
    log("   Google login page reached")
    time.sleep(0.5)

    # Case 1: account chooser
    account_selected = False
    try:
        acct = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.XPATH, f"//*[@data-email='{email}']"))
        )
        acct.click()
        log("   Selected account from Google account chooser")
        account_selected = True
    except _TEx:
        pass

    # Case 2: email input
    if not account_selected:
        email_field = None
        for xpath in [
            "//input[@type='email']",
            "//input[@name='identifier']",
            "//input[@autocomplete='username']",
        ]:
            try:
                email_field = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                break
            except _TEx:
                continue

        if email_field:
            email_field.clear()
            email_field.send_keys(email)
            time.sleep(0.5)
            try:
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Next']]"))
                ).click()
            except _TEx:
                log("⚠️  Could not click Next — complete sign-in manually")
            log("   Google email entered — complete password/2FA in the browser...")
        else:
            log("⚠️  Could not find email field — enter your email manually")

    log("⏳ Waiting for login to complete...")

    WebDriverWait(driver, 180).until(
        lambda d: (
            "secure.istation.com" in d.current_url
            and "Account" not in d.current_url
            and "idsrv" not in d.current_url
        )
    )
    log("✅ Login successful")


def extract_session(driver) -> _requests.Session:
    session = _requests.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie["name"], cookie["value"], domain=cookie.get("domain", ""))
    ua = driver.execute_script("return navigator.userAgent")
    session.headers.update({"User-Agent": ua, "Referer": "https://secure.istation.com/"})
    return session


# ── URL builders ───────────────────────────────────────────────────────────────

def _grade_param(grade: str) -> list[str]:
    if not grade or grade == "All":
        return []
    val = GRADES.get(grade)
    return [f"Grade={val}"] if val is not None else []


def _period_param(assessment_mode: str, period: int | None = None) -> list[str]:
    if assessment_mode == "current":
        return ["Period=-1"]
    if assessment_mode == "per_month" and period is not None:
        return [f"Period={period}"]
    return []


def build_assessment_url(
    org_oid: str, product: dict, year: int,
    assessment_mode: str = "ytd", period: int | None = None,
    grade: str = "All", skill_code: str = "Overall",
) -> str:
    params = (
        _period_param(assessment_mode, period)
        + [f"Skill={skill_code}", f"Pid={product['pid']}"]
    )
    if product["product_key"]:
        params.append(f"ProductKey={product['product_key']}")
    params += _grade_param(grade)
    params += ["FilterByLocation=Any", "FilterType=students", "WgOid=0", "AllResults=True", f"Year={year}"]
    if product.get("lexile"):
        params.append("Lexile=True")
    return f"{BASE_ASSESSMENT_URL}/d{org_oid}?{'&'.join(params)}"


def build_usage_url(org_oid: str, product: dict, year: int, grade: str = "All") -> str:
    params = (
        ["weeks=0", f"Pid={product['pid']}", f"ProductKey={product['product_key']}"]
        + _grade_param(grade)
        + ["FilterType=students", "WgOid=0", "AllResults=True", f"Year={year}"]
    )
    return f"{BASE_USAGE_URL}/d{org_oid}?{'&'.join(params)}"


def build_usage_trend_url(org_oid: str, product: dict, year: int, grade: str = "All") -> str:
    params = (
        [f"Pid={product['pid']}", f"ProductKey={product['product_key']}"]
        + _grade_param(grade)
        + ["FilterType=students", "WgOid=0", "AllResults=True", f"Year={year}"]
    )
    return f"{BASE_USAGE_TREND_URL}/d{org_oid}?{'&'.join(params)}"


def build_level_movement_url(
    org_oid: str, product: dict, year: int,
    grade: str = "All", skill_code: str | None = None,
) -> str:
    if skill_code is None:
        _name = next((k for k, v in PRODUCTS.items() if v["pid"] == product["pid"]), "Reading")
        _skill = LEVEL_MOVEMENT_PRODUCTS.get(_name, {}).get("skill", "Overall")
    else:
        _skill = skill_code
    params = (
        [f"Skill={_skill}", f"Pid={product['pid']}", f"ProductKey={product['product_key']}"]
        + _grade_param(grade)
        + ["FilterType=students", "WgOid=0", "AllResults=False", f"Year={year}"]
    )
    return f"{BASE_ASSESSMENT_URL}/d{org_oid}?{'&'.join(params)}"


def build_completion_url(org_oid: str, product: dict, year: int, grade: str = "All") -> str:
    params = (
        [f"Pid={product['pid']}", f"ProductKey={product['product_key']}"]
        + _grade_param(grade)
        + ["FilterType=students", "WgOid=0", "AllResults=True", f"Year={year}"]
    )
    return f"{BASE_COMPLETION_URL}/d{org_oid}?{'&'.join(params)}"


# ── Downloader ─────────────────────────────────────────────────────────────────

def download_csv(session: _requests.Session, url: str, save_path: Path) -> bool:
    resp = session.get(url, timeout=90)
    if "/Account/" in resp.url or "idsrv" in resp.url:
        raise RuntimeError("Istation session expired — please re-run")
    resp.raise_for_status()
    content = resp.content
    if len(content) < 50 or content.lstrip()[:1] in (b"<", b" "):
        return False
    save_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = save_path.with_suffix(".tmp")
    tmp.write_bytes(content)
    tmp.rename(save_path)
    return True


def _download_one(session, url, save_path, log):
    if save_path.exists() and save_path.stat().st_size > 50:
        log(f"⏭️  {save_path.name} — already exists, skipping")
        return
    try:
        if download_csv(session, url, save_path):
            log(f"✅ {save_path.name}")
        else:
            log(f"⚠️  {save_path.name} — no data returned")
    except RuntimeError:
        raise
    except Exception as e:
        log(f"❌ {save_path.name} — {e}")
    time.sleep(0.3)


# ── Orchestrator ───────────────────────────────────────────────────────────────

def run_istation_reports(
    driver,
    org_oid: str,
    products: list[str],
    year: int,
    report_types: list[str],
    assessment_mode: str = "ytd",
    grade: str = "All",
    skill: str = "Overall",
    selected_months: list[int] | None = None,
    base_dir: str | None = None,
    email: str = "",
    log_fn=None,
) -> None:
    def log(msg):
        if log_fn: log_fn(msg)
        else: print(msg)

    sy_label  = SCHOOL_YEAR_LABELS.get(year, f"{year}-{str(year+1)[-2:]}")
    if base_dir is None:
        base_dir = str(Path.home() / "Documents" / "Istation Reports")
    out_base  = Path(base_dir).expanduser() / sy_label
    grade_tag = f"_{grade}" if grade != "All" else ""

    login_to_istation(driver, email, log_fn=log_fn)
    session = extract_session(driver)
    try:
        driver.minimize_window()
    except Exception:
        pass

    log(f"\n📊 Reports — OID: {org_oid} | Year: {sy_label} | Products: {', '.join(products)}")

    for product_name in products:
        prod       = PRODUCTS[product_name]
        usage_prod = USAGE_PRODUCTS[product_name]

        skill_map  = SKILLS.get(product_name, {})
        skill_code = skill_map.get(skill, "Overall")
        skill_tag  = f"_{skill}" if skill != "Overall" else ""

        if "assessment" in report_types:
            if assessment_mode == "per_month":
                periods = selected_months if selected_months is not None else list(MONTHS.keys())
                for period in periods:
                    month_name = MONTHS[period]
                    url = build_assessment_url(org_oid, prod, year, assessment_mode, period, grade, skill_code)
                    fname = f"ExecutiveSummary_{product_name}_{sy_label}_{month_name}{grade_tag}{skill_tag}.csv"
                    _download_one(session, url, out_base / "Executive Summary" / product_name / fname, log)
            else:
                mode_tag = "CurrentMonth" if assessment_mode == "current" else "YTD"
                url = build_assessment_url(org_oid, prod, year, assessment_mode, None, grade, skill_code)
                fname = f"ExecutiveSummary_{product_name}_{sy_label}_{mode_tag}{grade_tag}{skill_tag}.csv"
                _download_one(session, url, out_base / "Executive Summary" / fname, log)

        if "usage" in report_types:
            url = build_usage_url(org_oid, usage_prod, year, grade)
            fname = f"Usage_{product_name}_{sy_label}{grade_tag}.csv"
            _download_one(session, url, out_base / "Usage" / fname, log)

        if "usage_trend" in report_types:
            url = build_usage_trend_url(org_oid, usage_prod, year, grade)
            fname = f"UsageTrend_{product_name}_{sy_label}{grade_tag}.csv"
            _download_one(session, url, out_base / "Usage Trend" / fname, log)

        if "level_movement" in report_types:
            url = build_level_movement_url(org_oid, prod, year, grade, skill_code)
            fname = f"LevelMovement_{product_name}_{sy_label}{grade_tag}{skill_tag}.csv"
            _download_one(session, url, out_base / "Level Movement" / fname, log)

        if "assessment_completion" in report_types:
            url = build_completion_url(org_oid, usage_prod, year, grade)
            fname = f"AssessmentCompletion_{product_name}_{sy_label}{grade_tag}.csv"
            _download_one(session, url, out_base / "Assessment Completion" / fname, log)

    log("\n✅ All reports complete")
