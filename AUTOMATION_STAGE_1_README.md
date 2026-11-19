# Automation stage 1: unattended read-only report

A GitHub Actions job runs daily at approximately 07:30 UTC (GitHub scheduled runs can be delayed or skipped). It reads existing Neon records and creates a JSON report as a GitHub Actions artifact. It does not discover products, fetch Amazon data, write to Neon, send emails, or buy anything.

## Required setup

In GitHub repository **Settings > Secrets and variables > Actions**, add a repository secret named `DATABASE_URL` containing the same Neon connection URL used by Render. Do not paste it into chat or commit it. Ensure the database user has only the minimum necessary permissions; existing store loader functions may issue `CREATE TABLE IF NOT EXISTS` and therefore the workflow is *logically read-only* for existing tables, not guaranteed SQL SELECT-only. For a strict read-only database account, database schema must already exist and loaders may need further refactoring.

To verify: GitHub **Actions > Automated research summary (read-only) > Run workflow**. After completion, open the run's artifact named `automated-research-summary` and inspect `automated_research_report.json`. This is a test of scheduled execution infrastructure and stored-data analysis, **not** automated sourcing or dashboard/email delivery. The workflow will fail clearly if the database secret is missing.

Do not remove the existing research-review workflow. Brevo 401 is still unresolved.
