from app.budget import BudgetTracker


def test_iteration_cap():
    b = BudgetTracker(max_iterations=2, max_usd_cost=100)
    assert not b.should_stop()
    b.start_iteration()
    assert not b.iteration_cap_reached()
    b.start_iteration()
    assert b.iteration_cap_reached()
    assert b.should_stop()
    assert "iteration cap" in b.stop_reason()


def test_cost_cap():
    b = BudgetTracker(max_iterations=100, max_usd_cost=0.01)
    b.record_llm("claude-sonnet-5", 1_000_000, 1_000_000)  # $3 + $15
    assert b.cost_cap_reached()
    assert "cost cap" in b.stop_reason()


def test_llm_cost_accumulates_by_model():
    b = BudgetTracker()
    b.record_llm("claude-haiku-4-5-20251001", 1_000_000, 0)  # $1
    assert abs(b.llm_cost - 1.0) < 1e-6
    b.record_llm("claude-sonnet-5", 0, 1_000_000)  # +$15
    assert abs(b.llm_cost - 16.0) < 1e-6


def test_unknown_model_uses_conservative_default():
    b = BudgetTracker()
    b.record_llm("mystery-model", 1_000_000, 0)  # default input price 5.0
    assert abs(b.llm_cost - 5.0) < 1e-6


def test_search_cost():
    b = BudgetTracker()
    b.record_searches(10)
    assert b.search_calls == 10
    assert b.search_cost > 0


def test_remaining_budget_fraction():
    b = BudgetTracker(max_usd_cost=10.0)
    assert b.remaining_budget_fraction() == 1.0
    b.record_llm("claude-sonnet-5", 0, 333_333)  # ~$5
    frac = b.remaining_budget_fraction()
    assert 0.4 < frac < 0.6
