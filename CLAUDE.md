# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A React + Vite SPA that serves as an **interactive design document** — it compares 4 architectural approaches for augmenting Philippine BIR SLSP and QAP tax reports with journal entry data from Odoo Online (across multiple client databases). This is a documentation/prototyping tool, not a production app.

## Commands

```bash
npm run dev       # Start Vite dev server at http://localhost:5173
```

PR validation runs automatically via `cloudbuild-pr.yaml` (ruff check + format).

## Architecture

**Entry point chain:** `index.html` → `src/main.jsx` → `slsp-approaches.jsx`

Nearly all code lives in `slsp-approaches.jsx` (one large component). It is structured as a data-driven UI:

- `APPROACHES` array — static data for each of the 4 approaches (Cloud Run Job, MCP Server Tool, Google Sheets, Local CLI Script). Each entry contains architecture description, embedded code samples as strings, pros, cons, and a "fit" summary.
- `COMPARISON_ROWS` array — drives the side-by-side comparison table.
- `SLSPApproaches` component — top-level component with 3 `useState` values: `active` (selected approach tab), `tab` (architecture vs code view), `showComparison` (toggle comparison table).
- `CodeBlock` sub-component — renders code samples with a copy-to-clipboard button.

**Styling:** All inline styles — no CSS files, no Tailwind, no CSS modules. Primary palette: `#293750` (dark blue), `#406EEA` (accent blue), `#fafaf8` (background). Font: IBM Plex Sans.

**No routing, no API calls, no external state management.** Navigation is purely `useState`-based tab switching.

## Deployment (Canary)

This service uses **canary deployments** with traffic splitting:

1. Push to `master` → Cloud Build deploys with `--no-traffic`
2. New revision gets 0% traffic; a canary preview URL is created
3. Test via the canary URL
4. Promote to 100% traffic:
```bash
./promote.sh
```

### Smoke test
```bash
./smoke-test.sh https://slsp-qap-helper-njiacix2yq-as.a.run.app
```

### Lint and format
```bash
ruff check .
ruff format .
```

## Deployment Setup (Post-Build)

Once code is ready to deploy, follow these steps in order:

### 1. Create GitHub Repository

```bash
# Initialize git if not already done
git init
git add .
git commit -m "feat: initial commit"

# Create repo and push (requires gh CLI authenticated)
gh repo create <repo-name> --public --source=. --remote=origin --push
```

- Use `--private` instead of `--public` if the repo should be private.
- Confirm the remote is set: `git remote -v`

### 2. Connect to Google Cloud Build (2nd Gen)

2nd gen triggers use **GitHub App** connections (not OAuth tokens). Steps:

1. Go to **Cloud Build → Repositories (2nd gen)** in GCP Console.
2. Click **Link Repository** → select **GitHub** as the provider.
3. Authenticate with GitHub and install/authorize the **Google Cloud Build** GitHub App on the target repo.
4. Select the repo and click **Link**.

> Note: 2nd gen connections are region-scoped. Use `asia-southeast1` to match existing Cloud Run services.

### 3. Create a Cloud Build Trigger (Push to master)

```bash
# Via gcloud CLI
gcloud builds triggers create github \
  --name="deploy-on-master" \
  --region="asia-southeast1" \
  --repository="projects/<PROJECT_ID>/locations/asia-southeast1/connections/<CONNECTION_NAME>/repositories/<REPO_NAME>" \
  --branch-pattern="^master$" \
  --build-config="cloudbuild.yaml" \
  --generation=2
```

Replace `<PROJECT_ID>`, `<CONNECTION_NAME>`, and `<REPO_NAME>` with actual values.

Or via Console: **Cloud Build → Triggers → Create Trigger** → set:
- **Event:** Push to a branch
- **Branch:** `^master$`
- **Config:** `cloudbuild.yaml` (autodetected)
- **Generation:** 2nd gen
- **Repository:** the linked repo from step 2

### 4. Verify `cloudbuild.yaml` Exists

Ensure `cloudbuild.yaml` is at the repo root and covers build + deploy steps. The trigger will fail silently if the file is missing.

### 5. Test the Pipeline

```bash
git checkout -b test/trigger-check
git commit --allow-empty -m "chore: test CI trigger"
git push -u origin test/trigger-check
# Merge PR into master to fire the trigger
```

Check **Cloud Build → History** in the GCP Console to confirm the build runs.

---

## Related Work

`docs/superpowers/plans/2026-03-21-enhanced-slsp-qap-service.md` contains the implementation plan for the actual **backend Cloud Run service** that this UI describes. That service is a separate Python project (not in this repo).
