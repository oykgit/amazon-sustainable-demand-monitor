# Authorized commercial feed: automatic diagnostic only

This adds a scheduled GitHub Actions invocation of the **existing** `authorized_provider.py` collector. It does not modify the Streamlit app, dashboard, Neon, or existing workflows.

## Configuration (only after obtaining a licensed feed)

GitHub repository **Settings > Secrets and variables > Actions**:

- Repository **secret** `AUTHORIZED_FEED_URL`: the full HTTPS JSON endpoint of a source you are contractually permitted to poll.
- Repository **variable** `AUTHORIZED_FEED_HOST`: exact host of that endpoint, without `https://`.
- Repository **variable** `AUTHORIZED_FEED_PROVIDER`: provider's name.
- Repository **variable** `AUTHORIZED_FEED_PERMISSION_REF`: your permission/license reference; do not put secrets here.

Without all four values, the workflow reports `NOT_CONFIGURED` and makes zero network requests. **Do not invent a feed URL or put a general Amazon product page here.** The expected provider response is a JSON object containing `observations` with fields required by `controlled_collection.COLUMNS`. Provider must be authorized for scheduled automated access. The feed is limited to 250 records / 1 MB, blocks redirects and nonpublic DNS addresses, and performs **no database writes**.

Run **Actions > Authorized commercial feed check (read-only) > Run workflow** to inspect status. A green run with `NOT_CONFIGURED` means the diagnostic ran, **not** that a data source is operational. `PREVIEW_COMPLETE` means schema checks passed; it does not establish Amazon demand or source truth. No API subscription, Keepa calls, email, or purchase actions are enabled.

## Current blocker

No verified, licensed commercial feed URL is present in the uploaded repository. Previous Open Food Facts (403) and UPCitemdb (429) responses do not establish viable unattended access. A provider with permitted access and sufficient price/history/fee information is still required before genuine automated resale recommendations are possible.
