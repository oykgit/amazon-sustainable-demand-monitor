# V2.0 dashboard integration — Stage 2B

The existing **Overview** workspace automatically reads current stored Neon observations and applies the Stage 2B evidence gate when a visitor opens the dashboard. No manual upload or refresh button is required.

- Adds `dashboard_commercial.py` and a test.
- Updates `app.py` only to display the assessment.
- Preserves 24 navigation buttons and all other workspaces.
- No database writes, new API calls, paid services, orders, or scheduled email sending.
- The existing GitHub scheduled assessment remains separate. This dashboard recomputes its view from Neon on opening, rather than reading GitHub Actions artifacts.
- Commercial product discovery, fresh authorized Amazon data, historical demand and scheduled email delivery are **not** complete.

To test, deploy to Render, open **Overview** and check that the table lists the same stored products and scenario profitability as Stage 2B. Do not share secrets.
