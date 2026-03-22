# SLSP & QAP Helper

A Cloud Run service that generates BIR-compliant SLSP (Summary List of Sales/Purchases) and QAP (Quarterly Alphalist of Payees) reports from Odoo Online, exported as XLSX or DAT files.

## What it does

- Connects to multiple Odoo client databases via a central registry (source Odoo `project.task` records)
- Pulls posted vendor bills, customer invoices, and journal entries with withholding taxes
- Generates BIR-format DAT files that pass the BIR Validation Module:
  - **SLP** (Summary List of Purchases) — H/D records, grouped by TIN
  - **SLS** (Summary List of Sales) — H/D records, grouped by TIN
  - **QAP** (Quarterly Alphalist of Payees, 1601EQ) — HQAP/D1/C1 records

## Architecture

```
main.py            FastAPI app — routes, export orchestration
odoo_client.py     Odoo XML-RPC client — fetches bills, JEs, partners, taxes
bir_format.py      Pure functions — DAT line formatting, name sanitization, TIN cleaning
slsp_builder.py    SLSP report builder — aggregation, XLSX/DAT output
qap_builder.py     QAP report builder — merge, XLSX/DAT output
templates/         Jinja2 HTML (Odoo 19-themed UI)
```

## Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/{token}/` | Export form UI |
| GET | `/{token}/companies` | AJAX — company list for selected database |
| POST | `/{token}/export` | Generate and download XLSX or DAT |

All routes are guarded by `ACCESS_TOKEN` in the URL path.

## DAT file specs (BIR)

| Report | Header | Detail | Control | Filename |
|--------|--------|--------|---------|----------|
| SLP | `H,P,...` (20 fields) | `D,P,...` (17 fields) | — | `{TIN}P{MMYYYY}.dat` |
| SLS | `H,S,...` (16 fields) | `D,S,...` (15 fields) | — | `{TIN}S{MMYYYY}.dat` |
| QAP | `HQAP,...` (7 fields) | `D1,...` (14 fields) | `C1,...` (7 fields) | `{TIN}{BC}{MMYYYY}1601EQ.DAT` |

Name sanitization: uppercase, remove `.,'`, replace `&` with `AND`, replace `ñ` with `N`, max 50 chars.

## Local development

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in credentials
python main.py         # http://localhost:8080
```

## Environment variables

| Variable | Description |
|----------|-------------|
| `SOURCE_BASE_URL` | Source Odoo URL (service registry) |
| `SOURCE_DB` | Source Odoo database name |
| `SOURCE_LOGIN` | Source Odoo login |
| `SOURCE_PASSWORD` | Source Odoo API key |
| `ACCESS_TOKEN` | URL path secret for route protection |

## Deployment

Push to `master` triggers Cloud Build (`cloudbuild.yaml`):
1. Builds Docker image
2. Deploys to Cloud Run (`asia-southeast1`)
3. Secrets injected from Google Secret Manager

## Testing

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```
