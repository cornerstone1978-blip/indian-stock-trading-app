import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch
from build_static import BUILD_DIR, build
from demo_data import seed_demo_data


class TestBuildStatic:
    def setup_method(self):
        with patch("demo_data._fetch_real_closes", return_value=[100.0] * 40):
            seed_demo_data()

    def test_build_creates_index_html(self):
        path = build()
        assert os.path.exists(path)
        assert path.endswith("index.html")

    def test_html_contains_key_sections(self):
        path = build()
        with open(path) as f:
            html = f.read()
        assert "Market Status" in html
        assert "Positions" in html
        assert "Trade History" in html
        assert "Strategy Visualisation" in html
        assert "Watchlist Overview" in html
        assert "API Key" in html
        assert "plotly" in html.lower()

    def test_html_contains_demo_symbols(self):
        path = build()
        with open(path) as f:
            html = f.read()
        assert "INFY" in html
        assert "RELIANCE" in html
        assert "TCS" in html

    def test_html_contains_timezone(self):
        path = build()
        with open(path) as f:
            html = f.read()
        assert "Asia/Kolkata" in html

    def test_html_has_credential_inputs(self):
        path = build()
        with open(path) as f:
            html = f.read()
        assert 'id="apiKey"' in html
        assert 'id="apiSecret"' in html
        assert 'id="accessToken"' in html

    def test_html_contains_search_bar(self):
        path = build()
        with open(path) as f:
            html = f.read()
        assert 'id="stockSearch"' in html
        assert "Stock Search" in html

    def test_html_contains_yfinance_reference(self):
        path = build()
        with open(path) as f:
            html = f.read()
        assert "yfinance" in html
