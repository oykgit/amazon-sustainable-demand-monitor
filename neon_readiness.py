"""Read-only Neon search-interest status, separate from repository CSV audit."""
import os
from persistent_store import storage_transaction

def _connection(url):
    return storage_transaction("reader", url)

def read_interest_summary(url=None):
    url = url or os.environ.get('DATABASE_URL', '')
    with _connection(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.search_interest_observations')")
            if cur.fetchone()[0] is None:
                return {'rows': 0, 'keywords': 0, 'series': []}
            cur.execute("""SELECT market, keyword, COUNT(*) AS months,
                                  ROUND(AVG(search_interest)::numeric, 1) AS mean_interest
                           FROM public.search_interest_observations
                           GROUP BY market, keyword ORDER BY market, keyword""")
            series = [{'market': market, 'keyword': keyword, 'months': int(months),
                       'mean_interest': float(mean)}
                      for market, keyword, months, mean in cur.fetchall()]
            return {'rows': sum(item['months'] for item in series),
                    'keywords': len(series), 'series': series}
