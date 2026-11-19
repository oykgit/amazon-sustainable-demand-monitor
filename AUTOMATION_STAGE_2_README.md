# Automation Stage 2A: unattended public catalogue discovery

This is a limited but genuine **automatic discovery** integration. GitHub Actions queries the Open Library public search API on Mondays and Thursdays at approximately 08:00 UTC, or when run manually, and uploads a JSON report as a workflow artifact. The system does not require manual product entry or CSV upload to generate leads.

**Important limitations:** Open Library covers books, not general Amazon inventory. Its records do not verify Amazon UK/Ireland listing availability, historical demand, selling price, supplier cost, fees, competition or profit. Candidates are labelled `CATALOGUE_LEAD_ONLY`, not buy recommendations. This is a foundation for broader authorized providers, **not the requested full automatic Amazon opportunity monitor**. No Neon writes, scraping, email sending or purchases. Provider errors are recorded rather than replaced with invented data.

Add `automatic_candidate_discovery.py` at repository root, `.github/workflows/automatic-candidate-discovery.yml` at exact workflow path, and `tests/test_automatic_candidate_discovery.py` under tests. Run Actions → Automated catalogue candidate discovery (read-only) → Run workflow; download `automatic-catalogue-discovery` artifact. The workflow can be delayed by GitHub scheduling. `DISCOVERY_TOPICS` may optionally be set at job level as a comma-separated list, but defaults work without configuration.

Next development gates: verify live provider response; select an authorized Amazon UK/IE product data provider with historical pricing and permitted automation; implement cross-source evidence validation and non-misleading profitability ranking; connect durable dashboard storage and Brevo email once authenticated.
