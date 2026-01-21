import os
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")
DEFAULT_DATE_RANGE = "last_30_days"
PAGE_TITLE = "NIGINart Analytics"
PAGE_ICON = "📊"
LAYOUT = "wide"
CACHE_TTL = 300
LOGS_CACHE_TTL = 60
DEFAULT_METRICS_LIMIT = 1000
DEFAULT_LOGS_LIMIT = 10
CHART_HEIGHT = 400
CHART_THEME = "plotly_white"
