from datetime import date
from unittest.mock import patch

from app.market import is_trading_day


def test_weekend_not_trading_day():
    sunday = date(2026, 9, 20)
    assert is_trading_day(sunday) is False


def test_holiday_not_trading_day():
    mock = {"stat": "很抱歉，沒有符合條件的資料!"}
    with patch("app.market.requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock
        assert is_trading_day(date(2026, 9, 18)) is False


def test_trading_day():
    mock = {"stat": "OK"}
    with patch("app.market.requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock
        assert is_trading_day(date(2026, 9, 18)) is True


def test_network_error_fails_open():
    with patch("app.market.requests.get", side_effect=Exception("timeout")):
        assert is_trading_day(date(2026, 9, 18)) is True