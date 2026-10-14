# AI Functions Cost Toolkit

Fork this repository, point it at your Databricks workspace, and run a predicted-versus-actual cost comparison of `ai_extract` and `ai_query` on the same synthetic transcripts. No customer data is included.

This README is the GitHub source of truth. `databricks bundle deploy` uploads the notebooks and jobs. It does **not** publish this README into the workspace. Read here first, then deploy.

## What this proves

Two AI Functions paths price differently. This bundle runs both on the same rows, writes a predicted cost into `run_log`, then joins [`system.billing.usage`](https://docs.databricks.com/aws/en/admin/system-tables/billing) after the documented lag.

| Path | Function | Typical billing | Pricing model |
|---|---|---|---|
| A | `ai_extract` | AI Functions or Model Serving endpoint `databricks-ai-extract` | Per-input DBU rate ([AI Functions pricing](https://www.databricks.com/product/pricing/ai-functions)) |
| B | `ai_query` | Model Serving on the configured Foundation Model endpoint | Compute-time DBUs ([Foundation Model serving pricing](https://www.databricks.com/product/pricing/foundation-model-serving)) |

The first run usually shows predicted cost only. Actual dollars appear after billing lag (typically 1 to 4 hours). Do not treat a null actual as a $0 result.

## What the job does

1. Creates the target schema if it is missing.
2. Generates `sample_size` synthetic call transcripts (default 100).
3. Runs `ai_extract` and `ai_query` in parallel on those transcripts.
4. Reconciles predicted versus actual from `system.billing.usage` when rows exist.
5. Opens an account-wide ad-hoc cost notebook (filters via widgets).

## Use in your workspace

| Value | Where | Example |
|---|---|---|
| Databricks CLI profile | `-p <profile>` after `databricks auth login` | your profile name |
| `catalog` | bundle `--var` | any catalog where you can create a schema |
| `schema` | optional `--var` | `ai_functions_cost_demo` (default) |
| `sample_size` | optional `--var` | `100` (default) |
| `model_name` | optional `--var` | `databricks-meta-llama-3-3-70b-instruct` (default) |
| `team_tag` | optional `--var` | `ai-cost-demo` (default). Appears in `custom_tags.team`. |
| `owner_email` | optional `--var` | deploying user (default). Appears in `custom_tags.Owner`. |

```bash
git clone https://github.com/archana986/ai-functions-cost-toolkit.git
cd ai-functions-cost-toolkit

databricks auth login --host <your-workspace-url> -p <profile>

databricks bundle validate --strict -t dev -p <profile> \
  --var catalog=<your_catalog>

databricks bundle deploy -t dev -p <profile> \
  --var catalog=<your_catalog>

databricks bundle run ai_functions_cost_demo -t dev -p <profile> \
  --var catalog=<your_catalog>
```

Optional: after billing lag, run reconciliation only (no inference):

```bash
databricks bundle run ai_functions_cost_reconcile_hourly -t dev -p <profile> \
  --var catalog=<your_catalog>
```

The hourly job is **paused** on deploy. Unpause it in the Jobs UI if you want it to poll automatically.

## Tables this run writes

| Table | Notebook | Contents |
|---|---|---|
| `transcripts` | `02_generate_data` | Synthetic transcripts |
| `extract_results` | `03a_run_ai_extract` | `ai_extract` fields |
| `query_results` | `03b_run_ai_query` | `ai_query` JSON |
| `run_log` | `03a` and `03b` | Predicted cost and run window per path |

Notebook `04_reconcile_costs` reads those tables plus `system.billing.usage`. When billing has not landed yet, it prints `NO BILLING DATA YET` and exits cleanly.

## Cost of a demo run

At default `sample_size = 100`, expect well under one US dollar of inference plus a few cents of SQL. Actual billed dollars are the source of truth once `system.billing.usage` catches up. Do not quote predicted dollars as spend.

Scale with `--var sample_size=<n>` or job parameters. Multiply the measured per-row cost by your own daily volume. This pack does not include a customer volume or a customer invoice.

## Files

| Path | Use |
|---|---|
| `src/notebooks/` | Setup, generate, extract, query, reconcile, ad-hoc cost |
| `resources/demo.job.yml` | Full pipeline job |
| `resources/reconcile.job.yml` | Optional paused hourly reconcile |
| `databricks.yml` | Bundle name, variables, targets |
| `SETUP.md` | Prerequisites, customization, limitations, cleanup |

See `SETUP.md` for known limitations (billing lag, tag propagation, list-price lookup coverage).
