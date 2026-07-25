import os
import json
import uuid
from datetime import datetime
from pathlib import Path

from faker import Faker
from google import genai

fake = Faker()

AFRICAN_FIRST_NAMES = [
    "Wanjiku", "Kamau", "Achieng", "Omondi", "Njoki", "Kiprop",
    "Akinyi", "Barasa", "Juma", "Makena", "Njeru", "Ochieng",
    "Adisa", "Chimwemwe", "Dlamini", "Ekene", "Farai", "Gumbo",
    "Ikenna", "Kwame", "Lungile", "Mwangi", "Nkechi", "Okonkwo",
    "Ayanda", "Bhekisisa", "Chidi", "Dineo", "Esi", "Folami",
]
AFRICAN_LAST_NAMES = [
    "Kamau", "Odinga", "Mbeki", "Adeyemi", "Okonkwo", "Nkosi",
    "Mensah", "Osei", "Diop", "Keita", "Toure", "Kone",
    "Mutua", "Kiprono", "Wanjiku", "Mwangi", "Njoroge", "Ochieng",
    "Sang", "Kiplagat", "Chemweno", "Rotich", "Kosgei", "Bett",
]


def african_name():
    first = fake.random_element(AFRICAN_FIRST_NAMES)
    last = fake.random_element(AFRICAN_LAST_NAMES)
    return f"{first} {last}"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


def _get_client():
    if not GEMINI_API_KEY:
        return None
    return genai.Client(api_key=GEMINI_API_KEY)

DEPARTMENT_PROMPTS = {
    "Finance": """You are a senior financial analyst at {company_name}, a fast-growing African enterprise headquartered in Nairobi, Kenya.

Write a highly realistic internal CONFIDENTIAL financial document. Date: {date}.

Include ALL of the following elements:
1. Document title: "Q3 2026 Budget Allocation & Payroll Review — CONFIDENTIAL"
2. A table of executive salaries including:
   - Columns: Employee Name | Employee ID | Position | Monthly Salary (KES) | Bank Account
   - {employee_name} as the CFO with Employee ID {employee_id}
   - Generate 5-6 other realistic African executive names (e.g., Wanjiku Kamau, Ola Adeyemi, Thabo Mbeki)
   - Use Kenya Shillings (KES) for salary amounts between 250,000 and 1,500,000
   - Include the bank account {bank_account} for the CFO entry
3. Department budget allocations for Q3 2026 across at least 4 departments
4. A section titled "Tax Withholding & Compliance" mentioning KRA (Kenya Revenue Authority)
5. A "Board Approval Status: Pending — Awaiting Q2 Audit Sign-Off" footnote
6. Use corporate jargon: "strategic realignment", "cost optimization initiatives", "quarterly burn-rate adjustments"

Format professionally with clear sections, numbered items, bullet points, and a CFO signature block at the end.""",

    "Human Resources": """You are the HR Director at {company_name}, an African enterprise with offices in Nairobi, Lagos, and Johannesburg.

Write a CONFIDENTIAL internal HR document. Date: {date}.

Include ALL of the following elements:
1. Title: "Confidential Employee Records & Performance Review — {company_name}"
2. A personnel table with columns:
   - Employee Name | Employee ID | Department | ID/Passport Number | Position | Salary Grade
   - {employee_name} as the Senior HR Officer, Employee ID {employee_id}, ID Number {id_number}
   - 5-6 other realistic African employee names across Finance, IT, and Operations departments
3. A section titled "Disciplinary Matters" with 2 vague but suggestive entries (e.g., "Ongoing investigation — Code of Conduct violation — Legal advised confidentiality")
4. "Salary Review Recommendations" for the upcoming fiscal year
5. A mention of "Pending labour board case — external counsel engaged"
6. Compliance notes referencing the Kenyan Employment Act 2007
7. Use standard HR jargon: "performance improvement plan", "retention risk", "organisational restructuring"

Use a formal, bureaucratic tone throughout.""",

    "IT / Engineering": """You are the CTO (Chief Technology Officer) at {company_name}, a growing African tech-enabled enterprise with hybrid cloud infrastructure.

Write a CONFIDENTIAL internal IT security document. Date: {date}.

Include ALL of the following elements:
1. Title: "IT Infrastructure Audit & Security Posture Report — CONFIDENTIAL"
2. A "Network Infrastructure Overview" section listing:
   - Primary Domain Controller: DC-01 (10.0.10.10)
   - Backup Domain Controller: DC-02 (10.0.10.11)
   - Mail Server: MAIL-01 (10.0.20.5)
   - Database Server: DB-01 (10.0.30.15)
   - File Server: FS-01 (10.0.40.20)
3. A table of "Privileged Access Credentials (Rotated Quarterly)":
   - System | Internal URL / IP | Username | Access Level | Last Rotation
   - Include {employee_name} as the System Administrator with ID {employee_id}
4. "Software Inventory & Licensing" — mention Windows Server 2022, Microsoft 365 Business Premium, AWS EC2 instances in the af-south-1 region
5. A "Critical Security Vulnerabilities" section with 3 realistic-sounding but fictional CVEs (e.g., CVE-2026-0381: SAML authentication bypass on internal IdP)
6. "Cloud Infrastructure" notes mentioning AWS Cape Town region, Azure South Africa North
7. "Pending Security Audit Recommendations" — at least 5 items

Use technical IT jargon throughout. Include a CTO digital signature block.""",

    "Operations": """You are the Operations Director at {company_name}, a growing African enterprise with supply chain operations across East Africa.

Write a CONFIDENTIAL internal operations document. Date: {date}.

Include ALL of the following elements:
1. Title: "Operations & Logistics Status Report — CONFIDENTIAL"
2. A supply chain vendor table:
   - Vendor Name | Service | Contract Value (USD) | Contract Value (KES) | Renewal Date
   - At least 6 vendors with realistic African company names
3. A "Logistics Route" section describing the Mombasa–Nairobi–Kampala corridor
4. A table of "Current Inventory Stock Levels" for at least 8 SKU items
5. A "Supply Chain Disruptions" section mentioning border delays at Busia and Malaba
6. "Mitigation Strategies" — at least 3 concrete actions
7. "Pending Vendor Negotiations" — mention 2 vendors under renegotiation
8. Include {employee_name} as the Supply Chain Lead, Employee ID {employee_id}

Use professional operations management language throughout. Include a signature block.""",
}


def _next_tracking_id():
    return uuid.uuid4().hex[:12]


def _build_pixel_url(tracker_host, tracker_port, filename):
    nonce = uuid.uuid4().hex[:8]
    return f"http://{tracker_host}:{tracker_port}/track?file={filename}&_={nonce}"


def _generate_fake_data():
    return {
        "employee_name": african_name(),
        "employee_id": f"{fake.random_int(min=1000, max=9999)}/{fake.random_int(min=10, max=99)}",
        "bank_account": fake.iban(),
        "id_number": f"{fake.random_int(min=10000000, max=99999999)}{fake.random_int(min=100, max=999)}",
        "date": datetime.now().strftime("%d %B %Y"),
    }


MOCK_DOCUMENTS = {
    "Finance": """CONFIDENTIAL — Q3 2026 Budget Allocation & Payroll Review
================================================================
Date: {date}
Prepared by: {employee_name}, CFO
Employee ID: {employee_id}

1. EXECUTIVE SALARY TABLE
----------------------------------------------------------------
Employee Name           | ID        | Position              | Monthly (KES)  | Bank Account
------------------------|-----------|-----------------------|----------------|-----------------------
{employee_name}         | {employee_id} | Chief Financial Officer | 1,250,000     | {bank_account}
Wanjiku Kamau           | 4501/22   | CEO                   | 1,500,000     | KE74 1000 2000 3000 4000 5001
Ola Adeyemi             | 4502/18   | CTO                   | 1,100,000     | KE63 1000 2000 3000 4000 5002
Thabo Mbeki             | 4503/15   | COO                   | 950,000       | KE52 1000 2000 3000 4000 5003
Achieng Omondi          | 4504/20   | Head of Sales         | 850,000       | KE41 1000 2000 3000 4000 5004
Kiprop Barasa           | 4505/12   | Legal Counsel         | 780,000       | KE30 1000 2000 3000 4000 5005
Makena Njeru            | 4506/08   | HR Director           | 720,000       | KE29 1000 2000 3000 4000 5006

2. DEPARTMENT BUDGET ALLOCATIONS (KES)
----------------------------------------------------------------
Department              | Q3 Budget    | Q2 Actual    | Variance
------------------------|--------------|--------------|-----------
Finance & Accounting    | 18,500,000   | 17,200,000   | +7.6%
IT Operations           | 22,000,000   | 21,500,000   | +2.3%
Human Resources         | 9,800,000    | 9,400,000    | +4.3%
Operations & Logistics  | 14,200,000   | 13,800,000   | +2.9%
Sales & Marketing       | 16,500,000   | 15,900,000   | +3.8%

3. TAX WITHHOLDING & COMPLIANCE
----------------------------------------------------------------
All salaries processed through the KRA (Kenya Revenue Authority) PAYE
system. Withholding tax applied at the statutory rate of 30% for highest
bracket earners. NHIF and NSSF deductions remitted monthly. Q3 compliance
audit scheduled for 15 August 2026.

4. STRATEGIC NOTES
----------------------------------------------------------------
• Strategic realignment of Finance division underway — 3 new analyst
  positions approved for Q4 2026
• Cost optimization initiatives targeting 12% reduction in external
  consultancy spend
• Quarterly burn-rate adjustments factored into revised cash flow
  projections
• Board approval status: PENDING — Awaiting Q2 audit sign-off from
  Ernst & Young Nairobi

Signed,
{employee_name}
Chief Financial Officer
{date}""",

    "Human Resources": """CONFIDENTIAL — Employee Records & Performance Review
================================================================
Date: {date}
Prepared by: {employee_name}, Senior HR Officer
Employee ID: {employee_id}

1. PERSONNEL REGISTER
----------------------------------------------------------------
Employee Name           | ID        | Department   | ID/Passport      | Position
------------------------|-----------|--------------|------------------|--------------------
{employee_name}         | {employee_id} | HR          | {id_number}      | Senior HR Officer
Wanjiku Kamau           | 4501/22   | Executive    | AQ 4521 8732     | Chief Executive Officer
Ola Adeyemi             | 4502/18   | IT           | AQ 4521 8733     | Chief Technology Officer
Grace Akinyi            | 4507/11   | Finance      | AQ 4521 8734     | Senior Accountant
Samuel Ochieng          | 4508/09   | Operations   | AQ 4521 8735     | Logistics Manager
Fatima Adisa            | 4509/14   | IT           | AQ 4521 8736     | Systems Administrator
Paul Mwangi             | 4510/07   | Operations   | AQ 4521 8737     | Procurement Officer

2. DISCIPLINARY MATTERS (CONFIDENTIAL)
----------------------------------------------------------------
• Employee #4508/09 — Ongoing investigation regarding Code of Conduct
  violation. Legal advised strict confidentiality. External counsel
  engaged. Next hearing: 5 August 2026.
• Employee #4505/12 — Formal written warning issued for failure to
  disclose conflict of interest in vendor procurement process.

3. SALARY REVIEW RECOMMENDATIONS
----------------------------------------------------------------
Across-the-board adjustment of 7% recommended for Q4 2026 to account
for current inflation (5.9% YoY as of June 2026). High performers
identified for additional merit-based increments of 3-5%.

4. COMPLIANCE NOTES
----------------------------------------------------------------
• Full compliance with Kenyan Employment Act 2007, Part VI on fair
  termination procedures
• Performance improvement plans active for 2 employees (IT, Operations)
• Retention risk flagged for 3 key personnel — counteroffer strategy
  under review
• Organisational restructuring proposal submitted for board review

Signed,
{employee_name}
Senior HR Officer
{date}""",

    "IT / Engineering": """CONFIDENTIAL — IT Infrastructure Audit & Security Posture Report
================================================================
Date: {date}
Prepared by: {employee_name}, System Administrator
Employee ID: {employee_id}

1. NETWORK INFRASTRUCTURE OVERVIEW
----------------------------------------------------------------
Hostname              | IP Address    | Role                  | Status
----------------------|---------------|-----------------------|---------
DC-01                 | 10.0.10.10    | Primary Domain Ctrl   | Online
DC-02                 | 10.0.10.11    | Backup Domain Ctrl    | Online
MAIL-01               | 10.0.20.5     | Exchange Mail Server  | Online
DB-01                 | 10.0.30.15    | PostgreSQL Database   | Online
FS-01                 | 10.0.40.20    | File Server (Honeypot)| Online
WEB-01                | 10.0.50.10    | IIS Web Server        | Online

2. PRIVILEGED ACCESS CREDENTIALS (Rotated Quarterly)
----------------------------------------------------------------
System       | URL/IP        | Username      | Access Level   | Last Rotation
-------------|---------------|---------------|----------------|--------------
Active Dir   | dc-01.intra   | {employee_name}  | Domain Admin   | 2026-06-01
SQL Server   | db-01:5432    | sa_admin      | DB Owner       | 2026-06-15
AWS Console  | 12.34.56.78   | {employee_id}    | Full Access    | 2026-05-20
Firewall     | 10.0.0.1      | net_admin     | Super Admin    | 2026-06-10

3. CRITICAL SECURITY VULNERABILITIES
----------------------------------------------------------------
• CVE-2026-0381 — SAML authentication bypass on internal IdP (PATCH
  PENDING — vendor ETA 14 Aug)
• CVE-2026-0412 — SMBv1 still enabled on FS-01 (legacy app dependency)
• CVE-2026-0398 — Outdated TLS 1.0 on mail gateway (migration to 1.3
  scheduled Q3 2026)

4. REMEDIATION ROADMAP
----------------------------------------------------------------
All critical patches to be applied within 30 days. Network segmentation
review in progress for Finance and HR VLANs. EDR deployment scheduled
for all servers by 1 September 2026.

Signed,
{employee_name}
System Administrator
{date}""",

    "Operations": """CONFIDENTIAL — Operations & Logistics Status Report
================================================================
Date: {date}
Prepared by: {employee_name}, Supply Chain Lead
Employee ID: {employee_id}

1. SUPPLY CHAIN VENDOR TABLE
----------------------------------------------------------------
Vendor Name            | Service             | Contract USD   | KES            | Renewal
-----------------------|---------------------|----------------|----------------|----------
Mombasa Logistics Ltd  | Freight Forwarding  | 120,000        | 15,600,000     | 2026-10-01
Kampala Hauliers Co    | Road Transport      | 85,000         | 11,050,000     | 2026-11-15
Nairobi Warehouse PLC  | Storage & Dist.     | 95,000         | 12,350,000     | 2026-09-30
E.A. Packaging Ltd     | Supplies & Packing  | 45,000         | 5,850,000      | 2027-01-15
Jubilee Insurers       | Cargo Insurance     | 28,000         | 3,640,000      | 2027-03-01
Tema Port Services     | Customs Clearance   | 62,000         | 8,060,000      | 2026-12-01

2. LOGISTICS ROUTE: MOMBASA–NAIROBI–KAMPALA CORRIDOR
----------------------------------------------------------------
• Mombasa Port (discharge) → Container Freight Station (48hr clearance)
• Mombasa–Nairobi via A109 (450km, ~8hrs transit)
• Nairobi–Busia via A104 (400km, ~6hrs)
• Busia border crossing (avg 4hr delay on peak days)
• Busia–Kampala via B1 (200km, ~3hrs)
Total transit time: 4-6 days door-to-door

3. CURRENT INVENTORY STOCK LEVELS
----------------------------------------------------------------
SKU Code       | Item                 | Qty on Hand | Reorder Level | Status
---------------|----------------------|-------------|---------------|---------
RM-001         | Raw Material A       | 12,500      | 8,000         | Adequate
RM-002         | Raw Material B       | 3,200       | 5,000         | REORDER
PK-001         | Packaging Crate L    | 890         | 1,200         | REORDER
FG-001         | Finished Good Alpha  | 4,100       | 2,000         | Adequate
FG-002         | Finished Good Beta   | 1,800       | 2,500         | LOW
SP-001         | Spare Part X         | 670         | 400           | Adequate
SP-002         | Spare Part Y         | 120         | 300           | REORDER
OF-001         | Office Supplies      | 2,300       | 1,000         | Adequate

4. DISRUPTIONS & MITIGATION
----------------------------------------------------------------
• Border delays at Busia (avg 4hr) and Malaba (avg 6hr) impacting
  Kampala-bound shipments
• Mitigation: Pre-clearance documentation submitted 24hr before arrival;
  alternative route via Namanga under evaluation
• Fuel surcharge increase of 8% from Kenya Pipeline Company — budget
  revision flagged

Signed,
{employee_name}
Supply Chain Lead
{date}""",
}


def _call_gemini(prompt, department):
    client = _get_client()
    if client is None:
        return MOCK_DOCUMENTS.get(department, MOCK_DOCUMENTS["Finance"])
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text
    except Exception:
        return MOCK_DOCUMENTS.get(department, MOCK_DOCUMENTS["Finance"])


def _build_html(content, company_name, department, pixel_url):
    safe_name = company_name.replace("&", "&amp;").replace("<", "&lt;")
    safe_dept = department.replace("&", "&amp;").replace("<", "&lt;")
    safe_content = content.replace("&", "&amp;").replace("<", "&lt;")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{safe_name} — {safe_dept} — Confidential</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; padding: 2.5em; max-width: 900px; margin: auto; background: #fafafa; color: #222; line-height: 1.7; }}
  .confidential-banner {{ background: #d32f2f; color: #fff; text-align: center; padding: 12px; font-weight: 700; font-size: 1.1em; letter-spacing: 2px; margin-bottom: 2em; border-radius: 4px; }}
  .content {{ background: #fff; padding: 2em; border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.12); white-space: pre-wrap; font-family: 'Courier New', monospace; font-size: 0.95em; }}
  .footer {{ margin-top: 2em; font-size: 0.8em; color: #888; text-align: center; border-top: 1px solid #ddd; padding-top: 1em; }}
</style>
</head>
<body>
<div class="confidential-banner">CONFIDENTIAL — {safe_name} Internal Use Only</div>
<div class="content">{safe_content}</div>
<div class="footer">Document generated by Project Ember — AI HoneyToken Factory &copy; {datetime.now().year}</div>
<img src="{pixel_url}" width="1" height="1" alt="" style="display:none;" />
</body>
</html>"""


def _build_markdown(content, company_name, department, pixel_url):
    return f"""# {company_name} – {department}

> **⚠️ CONFIDENTIAL — Internal Use Only**

---

{content}

---

*Document generated by Project Ember — AI HoneyToken Factory*

<img src="{pixel_url}" width="1" height="1" alt="" style="display:none;" />
"""


def _build_txt(content, company_name, department):
    sep = "=" * 72
    return f"""{sep}
CONFIDENTIAL — {company_name} — {department}
{sep}

{content}

{sep}
END OF DOCUMENT — Project Ember HoneyToken
{sep}
"""


def generate_honeytokens(
    company_name,
    department,
    output_dir,
    tracker_host="localhost",
    tracker_port=8765,
):
    os.makedirs(output_dir, exist_ok=True)

    fake_data = _generate_fake_data()
    prompt = DEPARTMENT_PROMPTS[department].format(company_name=company_name, **fake_data)
    corporate_text = _call_gemini(prompt, department)

    safe_company = company_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    safe_dept = department.replace(" ", "_").replace("/", "_").replace("\\", "_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{safe_company}_{safe_dept}_{ts}"

    pixel_url = _build_pixel_url(tracker_host, tracker_port, base_name)
    tracking_id = _next_tracking_id()

    manifest = []

    # --- .txt ---
    txt_path = os.path.join(output_dir, f"{base_name}.txt")
    txt_content = _build_txt(corporate_text, company_name, department)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content)
    manifest.append({
        "file": f"{base_name}.txt",
        "format": "txt",
        "department": department,
        "company": company_name,
        "tracking_id": tracking_id,
        "pixel_url": pixel_url,
        "created_at": datetime.now().isoformat(),
    })

    # --- .md ---
    md_path = os.path.join(output_dir, f"{base_name}.md")
    md_content = _build_markdown(corporate_text, company_name, department, pixel_url)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    manifest.append({
        "file": f"{base_name}.md",
        "format": "md",
        "department": department,
        "company": company_name,
        "tracking_id": tracking_id,
        "pixel_url": pixel_url,
        "created_at": datetime.now().isoformat(),
    })

    # --- .html ---
    html_path = os.path.join(output_dir, f"{base_name}.html")
    html_content = _build_html(corporate_text, company_name, department, pixel_url)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    manifest.append({
        "file": f"{base_name}.html",
        "format": "html",
        "department": department,
        "company": company_name,
        "tracking_id": tracking_id,
        "pixel_url": pixel_url,
        "created_at": datetime.now().isoformat(),
    })

    manifest_path = os.path.join(output_dir, "manifest.json")
    existing = []
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            existing = json.load(f)
    existing.extend(manifest)
    with open(manifest_path, "w") as f:
        json.dump(existing, f, indent=2)

    return manifest


if __name__ == "__main__":
    import sys
    company = sys.argv[1] if len(sys.argv) > 1 else "Acme Kenya Ltd"
    dept = sys.argv[2] if len(sys.argv) > 2 else "Finance"
    out = sys.argv[3] if len(sys.argv) > 3 else "./honeytokens"
    m = generate_honeytokens(company, dept, out)
    print(f"Deployed {len(m)} honeytokens to {out}/")
    for entry in m:
        print(f"  -> {entry['file']}  [{entry['tracking_id']}]")
