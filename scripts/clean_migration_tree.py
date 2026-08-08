from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "migrations" / "versions"
LEGACY = (
    "0002_portfolio_holdings.sql",
    "0003_portfolio_valuation_alerts.sql",
    "0004_portfolio_valuation_provenance.sql",
    "0005_alert_notification_delivery.sql",
)

for filename in LEGACY:
    path = ROOT / filename
    if path.exists():
        path.unlink()
        print(f"removed {path}")
