from pathlib import Path


def test_migrations_are_unique_and_ordered():
    paths = sorted((Path(__file__).parents[1] / "migrations" / "versions").glob("*.sql"))
    names = [path.name for path in paths]
    assert names == [
        "0001_market_foundation.sql",
        "0002_user_features.sql",
        "0003_portfolio_holdings.sql",
        "0004_portfolio_valuation.sql",
        "0005_portfolio_valuation_provenance.sql",
        "0006_alert_notification_delivery.sql",
    ]
    assert len(names) == len(set(names))


def test_migrations_have_sql():
    for path in (Path(__file__).parents[1] / "migrations" / "versions").glob("*.sql"):
        assert path.read_text(encoding="utf-8").strip()
