# Setup: AI Functions Cost Toolkit

Use this project in **your** Databricks workspace. Clone the folder, set `catalog`, deploy the bundle, and run the demo job.

## Prerequisites

| Requirement | How to check |
|---|---|
| Databricks CLI 0.292 or later | `databricks -v` |
| OAuth login to your workspace | `databricks auth login --host <your-workspace-url>` (do not use a PAT) |
| Foundation Model APIs | Serving UI lists pay-per-token endpoints such as `databricks-meta-llama-3-3-70b-instruct` |
| `CREATE SCHEMA` on the target catalog | The job creates a schema, not a catalog, if the catalog already exists |
| Read on `system.billing.usage` and `system.billing.list_prices` | `SELECT COUNT(*) FROM system.billing.usage WHERE usage_date = current_date() - 1`. See [enable system tables](https://docs.databricks.com/aws/en/admin/system-tables/). |

The CLI profile must match **your** workspace URL. This repo does not pin a host.

## Configure

Edit nothing in notebooks for catalog or schema. Pass values at deploy time:

```bash
cd ai-functions-cost-toolkit

databricks bundle validate --strict -t dev \
  --var catalog=<catalog>
```

| Variable | Default | What to change |
|---|---|---|
| `catalog` | `main` | Catalog where you can create a schema |
| `schema` | `ai_functions_cost_demo` | Any schema name; created if missing |
| `sample_size` | `100` | Start small; raise to match your own volume |
| `team_tag` | `ai-cost-demo` | Value for `custom_tags.team` |
| `owner_email` | deploying user | Value for `custom_tags.Owner` |
| `model_name` | `databricks-meta-llama-3-3-70b-instruct` | Any Foundation Model endpoint in your workspace |

## Deploy and run

```bash
databricks bundle deploy -t dev --var catalog=<catalog>
databricks bundle run ai_functions_cost_demo -t dev --var catalog=<catalog>
```

Reconcile later, after billing lag, with no extra inference:

```bash
databricks bundle run ai_functions_cost_reconcile_hourly -t dev --var catalog=<catalog>
```

To poll automatically, unpause `ai-functions-cost-reconcile-hourly` in the Jobs UI. It is paused on deploy.

## Customize

- Transcript style: `gen()` in `src/notebooks/02_generate_data.ipynb`
- Extracted fields: `ARRAY(...)` in `03a_run_ai_extract.ipynb` and the JSON prompt in `03b_run_ai_query.ipynb`
- Model: `--var model_name=<endpoint>` and, if needed, the `MODEL_RATES` dict in `03b`

## Known limitations

| Limitation | What to do |
|---|---|
| `system.billing.usage` lags real usage by 1 to 4 hours ([docs](https://docs.databricks.com/aws/en/admin/system-tables/billing)) | Treat null actuals as "not yet billed," not $0. Re-run notebook 04 later. |
| `custom_tags` on billing rows is best-effort | Reconciliation also filters by Owner and the run-time window. |
| The 50% AI Functions promotion ended 2026-06-30 | List-price prediction is the authoritative estimate after that date. |
| Per-token lookup in `03b` covers a small set of popular models | Unlisted models fall back to Llama 70B rates. Edit `MODEL_RATES` from the [pricing page](https://www.databricks.com/product/pricing/foundation-model-serving). |
| Hourly job is paused | Unpause only if you want automatic refreshes. |
| Attribution in 2026 billing often lands under Model Serving | Notebook 04 keys off `usage_metadata.endpoint_name`, not `billing_origin_product` alone. |

## Cleanup

```bash
databricks bundle destroy -t dev
```

Then drop demo data if you no longer need it:

```sql
DROP SCHEMA IF EXISTS <catalog>.<schema> CASCADE;
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Deploy permission denied on `/Workspace/Users/...` | CLI user does not own that path | Authenticate as the user who will own the bundle |
| Notebook 01 prints `system.billing.usage: NOT ACCESSIBLE` | System tables not enabled or not granted | See [enable system tables](https://docs.databricks.com/aws/en/admin/system-tables/) |
| Notebook 04 always shows `NO BILLING DATA YET` after 6+ hours | Window or Owner filter mismatch | Query `system.billing.usage` for the `run_log` window without the Owner filter |
| `run_ai_query` fails with `RESOURCE_DOES_NOT_EXIST` | `model_name` is not provisioned | Pick an endpoint from the Serving UI |
