# Cloud Resource Cleanup Automation

A Python automation tool for identifying stale, unattached, and stopped resources across Azure and Google Cloud Platform. The project supports provider-specific cleanup types and can run locally or from Azure DevOps.

## What it does

- Azure: stopped/deallocated VMs, unattached managed disks, public IPs, NICs, SSH public-key resources, empty VNets, and unused NSGs.
- GCP: terminated VM instances, unattached zonal disks, unused regional addresses, empty zonal network endpoint groups, and project SSH metadata cleanup.
- Shared CLI controls for provider selection, cleanup type selection, and age thresholds.
- Azure and GCP SDK authentication through the host environment, Azure CLI/managed identity, or Google Application Default Credentials.

## Safety first

The command is a dry run by default. It does not load cloud credentials or contact either provider until `--execute` is supplied. Review the selected resource types and thresholds before enabling deletion, and test with a non-production project or subscription first.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python run.py --cloud-providers azure,gcp --cleanup-types vm,disk
```

The last command prints the plan without making cloud changes. To execute cleanup, configure the appropriate provider credentials and run:

```powershell
python run.py --cloud-providers azure --cleanup-types vm,disk --hours 720 --disk-hours 720 --execute
python run.py --cloud-providers gcp --cleanup-types vm,disk --hours 720 --disk-hours 720 --execute
```

## Authentication

### Azure

Set `AZURE_SUBSCRIPTION_ID`. Optionally set `AZURE_RESOURCE_GROUP` and `AZURE_MANAGED_IDENTITY_CLIENT_ID`. The Azure SDK uses `DefaultAzureCredential`, so local development can use `az login`, while CI can use a managed identity or service connection.

### Google Cloud

Set `GCP_PROJECT_ID`, then authenticate with Google Application Default Credentials:

```powershell
gcloud auth application-default login
```

For CI, set `GOOGLE_APPLICATION_CREDENTIALS` to a securely injected service-account JSON path. Do not commit that file.

## CLI reference

```text
--cloud-providers azure,gcp
--cleanup-types vm,disk,ip,nic,ssh,vnet,nsg,neg
--hours 4
--disk-hours 4
--execute
```

Cleanup types are provider-specific. Unsupported types are logged and skipped. Age thresholds are expressed in hours.

## CI/CD

`pipeline/cleanUp_pipeline.yaml` installs dependencies in the same job that runs cleanup and invokes `run.py` directly. Configure the Azure DevOps variable group `cloud-credentials` with provider-specific values and set `AZURE_SERVICE_CONNECTION` to an Azure DevOps service connection name. Keep execution credentials in secret variables or workload identity configuration.

## Project layout

```text
run.py                 CLI and configuration entry point
azu/                   Azure cleanup implementations
gcp/                   GCP cleanup implementations
pipeline/              Azure DevOps pipeline definition
requirements.txt       Python dependencies
```

## Validation without cloud access

```powershell
python run.py --help
python run.py --cloud-providers azure,gcp
python -m compileall -q .
```

This repository is intended as an automation portfolio project. Any cloud account, subscription, project, credential, or identity used with it belongs to the operator and must be supplied through local or CI configuration.
