from app.db.repositories.liquidity import liquidity_label


def stats(hours, closed=5):
    return {"median_hours_to_sell": hours, "closed_listings": closed, "confident": closed >= 3}


def test_a_quick_turnover_reads_fast():
    assert liquidity_label(stats(4)) == "fast"


def test_a_few_days_reads_steady():
    assert liquidity_label(stats(48)) == "steady"


def test_a_week_reads_slow():
    assert liquidity_label(stats(200)) == "slow"


def test_thin_evidence_is_admitted_not_guessed():
    # Two closed listings is an anecdote, and calling it "fast" would be a lie.
    assert liquidity_label(stats(2, closed=2)) == "unknown"


def test_no_history_is_unknown():
    assert liquidity_label(stats(None, closed=9)) == "unknown"
