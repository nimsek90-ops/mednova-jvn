# Deployment target: Vercel

The current, complete procedure is [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md). It covers the official Django WSGI integration, Python version, private remote MySQL and S3 storage, environment names, static assets, migrations, cron, provider limitations, deployment verification, backups and rollback.

Status: **NOT DEPLOYED**. The connected account returned HTTP 403 when creating the project. No production database or storage account was configured or contacted. See [REPAIR_AND_VERCEL_REPORT.md](REPAIR_AND_VERCEL_REPORT.md) for local functional/browser evidence and exact remaining actions.

A persistent Django/Waitress host behind HTTPS remains a fallback if the target Vercel native MySQL build or required scanner integration cannot be supported; that fallback was not deployed. Preserve the existing application/database architecture and verify the actual blocker before changing hosts.
