"""Domain scenario templates.

Each template is a curated set of realistic feature specs for a business domain.
The planner matches keywords in the user prompt to a scenario and uses it as a
starting point, then overrides row counts, rates, and feature counts from the
prompt. This is what makes ``"telecom churn dataset"`` produce sensible columns
(tenure, monthly_charges, contract_type...) instead of anonymous ``feature_1``.
"""

from __future__ import annotations

from app.models.spec import (
    DType,
    Distribution,
    FeatureRole,
    FeatureSpec,
    TaskType,
)


def _num(name, dist, params, dtype=DType.FLOAT, desc="", low=None, high=None):
    return FeatureSpec(
        name=name,
        dtype=dtype,
        distribution=dist,
        params=params,
        description=desc,
        low=low,
        high=high,
    )


def _cat(name, categories, weights=None, desc=""):
    return FeatureSpec(
        name=name,
        dtype=DType.CATEGORY,
        categories=categories,
        weights=weights,
        description=desc,
    )


# Each entry: keyword triggers -> (task_type, domain, features, target hints).
SCENARIOS: dict[str, dict] = {
    "fraud": {
        "keywords": ["fraud", "fraudulent", "transaction fraud"],
        "task_type": TaskType.BINARY_CLASSIFICATION,
        "domain": "banking",
        "target_name": "is_fraud",
        "positive_rate": 0.02,
        "features": [
            _num("amount", Distribution.LOGNORMAL, {"mean": 3.5, "sigma": 1.2},
                 desc="Transaction amount"),
            _num("account_age_days", Distribution.GAMMA, {"shape": 2.0, "scale": 300},
                 dtype=DType.INTEGER, desc="Age of account in days"),
            _num("num_transactions_24h", Distribution.POISSON, {"lam": 4},
                 dtype=DType.INTEGER, desc="Transactions in last 24h"),
            _num("distance_from_home_km", Distribution.EXPONENTIAL, {"scale": 25},
                 desc="Distance of transaction from home"),
            _num("time_since_last_txn_min", Distribution.EXPONENTIAL, {"scale": 120},
                 desc="Minutes since previous transaction"),
            _cat("merchant_category",
                 ["grocery", "electronics", "travel", "gambling", "gas", "online"],
                 desc="Merchant category code"),
            _cat("channel", ["chip", "swipe", "online", "contactless"],
                 desc="Payment channel"),
            _cat("device_type", ["mobile", "desktop", "pos", "atm"],
                 desc="Originating device"),
        ],
    },
    "churn": {
        "keywords": ["churn", "attrition", "retention"],
        "task_type": TaskType.BINARY_CLASSIFICATION,
        "domain": "telecom",
        "target_name": "churned",
        "positive_rate": 0.15,
        "features": [
            _num("tenure_months", Distribution.GAMMA, {"shape": 2.0, "scale": 12},
                 dtype=DType.INTEGER, desc="Months as a customer"),
            _num("monthly_charges", Distribution.NORMAL, {"mean": 70, "std": 25},
                 desc="Monthly bill amount"),
            _num("total_charges", Distribution.GAMMA, {"shape": 2.0, "scale": 800},
                 desc="Lifetime charges"),
            _num("support_tickets", Distribution.POISSON, {"lam": 1.5},
                 dtype=DType.INTEGER, desc="Support tickets opened"),
            _num("data_usage_gb", Distribution.GAMMA, {"shape": 2.0, "scale": 15},
                 desc="Monthly data usage"),
            _cat("contract_type", ["month-to-month", "one-year", "two-year"],
                 weights=[0.55, 0.25, 0.20], desc="Contract length"),
            _cat("internet_service", ["dsl", "fiber", "none"],
                 desc="Internet service type"),
            _cat("payment_method",
                 ["credit_card", "bank_transfer", "electronic_check", "mailed_check"],
                 desc="Payment method"),
        ],
    },
    "loan": {
        "keywords": ["loan", "default", "credit risk", "credit default"],
        "task_type": TaskType.BINARY_CLASSIFICATION,
        "domain": "banking",
        "target_name": "defaulted",
        "positive_rate": 0.10,
        "features": [
            _num("annual_income", Distribution.LOGNORMAL, {"mean": 10.8, "sigma": 0.5},
                 desc="Applicant annual income"),
            _num("loan_amount", Distribution.GAMMA, {"shape": 2.0, "scale": 8000},
                 desc="Requested loan amount"),
            _num("credit_score", Distribution.NORMAL, {"mean": 680, "std": 70},
                 dtype=DType.INTEGER, low=300, high=850, desc="Credit score"),
            _num("debt_to_income", Distribution.BETA, {"a": 2, "b": 5},
                 desc="Debt-to-income ratio"),
            _num("employment_years", Distribution.GAMMA, {"shape": 2.0, "scale": 4},
                 desc="Years employed"),
            _cat("home_ownership", ["rent", "own", "mortgage"],
                 desc="Home ownership status"),
            _cat("loan_purpose",
                 ["debt_consolidation", "home", "car", "education", "business"],
                 desc="Purpose of loan"),
        ],
    },
    "house": {
        "keywords": ["house price", "home price", "housing", "real estate"],
        "task_type": TaskType.REGRESSION,
        "domain": "real_estate",
        "target_name": "sale_price",
        "features": [
            _num("area_sqft", Distribution.NORMAL, {"mean": 1800, "std": 600},
                 low=400, desc="Living area in square feet"),
            _num("bedrooms", Distribution.POISSON, {"lam": 3},
                 dtype=DType.INTEGER, low=1, desc="Number of bedrooms"),
            _num("bathrooms", Distribution.POISSON, {"lam": 2},
                 dtype=DType.INTEGER, low=1, desc="Number of bathrooms"),
            _num("age_years", Distribution.GAMMA, {"shape": 2.0, "scale": 15},
                 dtype=DType.INTEGER, desc="Age of the property"),
            _num("garage_spaces", Distribution.POISSON, {"lam": 1.5},
                 dtype=DType.INTEGER, desc="Garage capacity"),
            _num("distance_to_city_km", Distribution.EXPONENTIAL, {"scale": 12},
                 desc="Distance to city center"),
            _cat("condition", ["poor", "fair", "good", "excellent"],
                 weights=[0.1, 0.3, 0.4, 0.2], desc="Property condition"),
            _cat("neighborhood_tier", ["a", "b", "c", "d"],
                 desc="Neighborhood quality tier"),
        ],
    },
    "insurance": {
        "keywords": ["insurance", "premium"],
        "task_type": TaskType.REGRESSION,
        "domain": "insurance",
        "target_name": "premium",
        "features": [
            _num("age", Distribution.NORMAL, {"mean": 40, "std": 14},
                 dtype=DType.INTEGER, low=18, high=90, desc="Policyholder age"),
            _num("bmi", Distribution.NORMAL, {"mean": 27, "std": 5},
                 desc="Body mass index"),
            _num("num_dependents", Distribution.POISSON, {"lam": 1},
                 dtype=DType.INTEGER, desc="Number of dependents"),
            _cat("smoker", ["no", "yes"], weights=[0.8, 0.2], desc="Smoker flag"),
            _cat("region", ["north", "south", "east", "west"], desc="Region"),
            _cat("vehicle_type", ["sedan", "suv", "truck", "sports"],
                 desc="Insured vehicle type"),
        ],
    },
    "healthcare": {
        "keywords": ["disease", "diagnosis", "patient", "healthcare", "medical",
                     "clinical"],
        "task_type": TaskType.BINARY_CLASSIFICATION,
        "domain": "healthcare",
        "target_name": "diagnosis_positive",
        "positive_rate": 0.20,
        "features": [
            _num("age", Distribution.NORMAL, {"mean": 50, "std": 18},
                 dtype=DType.INTEGER, low=0, high=100, desc="Patient age"),
            _num("bmi", Distribution.NORMAL, {"mean": 27, "std": 6}, desc="BMI"),
            _num("blood_pressure", Distribution.NORMAL, {"mean": 120, "std": 18},
                 dtype=DType.INTEGER, desc="Systolic blood pressure"),
            _num("glucose", Distribution.NORMAL, {"mean": 100, "std": 25},
                 desc="Fasting glucose"),
            _num("cholesterol", Distribution.NORMAL, {"mean": 200, "std": 40},
                 desc="Total cholesterol"),
            _num("heart_rate", Distribution.NORMAL, {"mean": 72, "std": 11},
                 dtype=DType.INTEGER, desc="Resting heart rate"),
            _cat("sex", ["female", "male"], desc="Biological sex"),
            _cat("smoker", ["no", "former", "current"],
                 weights=[0.6, 0.25, 0.15], desc="Smoking status"),
        ],
    },
    "employee": {
        "keywords": ["employee attrition", "hr analytics", "workforce"],
        "task_type": TaskType.BINARY_CLASSIFICATION,
        "domain": "human_resources",
        "target_name": "left_company",
        "positive_rate": 0.16,
        "features": [
            _num("age", Distribution.NORMAL, {"mean": 37, "std": 9},
                 dtype=DType.INTEGER, low=18, high=65, desc="Employee age"),
            _num("years_at_company", Distribution.GAMMA, {"shape": 2.0, "scale": 3},
                 dtype=DType.INTEGER, desc="Tenure"),
            _num("monthly_income", Distribution.LOGNORMAL, {"mean": 8.6, "sigma": 0.4},
                 desc="Monthly income"),
            _num("distance_from_home_km", Distribution.EXPONENTIAL, {"scale": 10},
                 desc="Commute distance"),
            _num("satisfaction_score", Distribution.BETA, {"a": 5, "b": 2},
                 desc="Job satisfaction 0-1"),
            _cat("department", ["sales", "engineering", "hr", "support", "finance"],
                 desc="Department"),
            _cat("overtime", ["no", "yes"], weights=[0.7, 0.3], desc="Works overtime"),
        ],
    },
    "sales_forecast": {
        "keywords": ["sales forecast", "demand forecast", "revenue forecast"],
        "task_type": TaskType.REGRESSION,
        "domain": "retail",
        "target_name": "units_sold",
        "features": [
            _num("price", Distribution.GAMMA, {"shape": 2.0, "scale": 20},
                 desc="Unit price"),
            _num("discount_pct", Distribution.BETA, {"a": 2, "b": 6},
                 desc="Discount fraction"),
            _num("marketing_spend", Distribution.GAMMA, {"shape": 2.0, "scale": 500},
                 desc="Marketing spend"),
            _num("competitor_price", Distribution.GAMMA, {"shape": 2.0, "scale": 20},
                 desc="Competitor unit price"),
            _cat("season", ["winter", "spring", "summer", "fall"], desc="Season"),
            _cat("store_type", ["flagship", "mall", "outlet", "online"],
                 desc="Store type"),
        ],
    },
    "segmentation": {
        "keywords": ["segmentation", "customer segment", "clustering", "cluster"],
        "task_type": TaskType.CLUSTERING,
        "domain": "retail",
        "target_name": "segment",
        "features": [
            _num("recency_days", Distribution.EXPONENTIAL, {"scale": 40},
                 dtype=DType.INTEGER, desc="Days since last purchase"),
            _num("frequency", Distribution.POISSON, {"lam": 6},
                 dtype=DType.INTEGER, desc="Purchase frequency"),
            _num("monetary_value", Distribution.LOGNORMAL, {"mean": 5.5, "sigma": 0.8},
                 desc="Total spend"),
            _num("avg_basket_size", Distribution.GAMMA, {"shape": 2.0, "scale": 3},
                 desc="Average basket size"),
            _num("tenure_months", Distribution.GAMMA, {"shape": 2.0, "scale": 10},
                 dtype=DType.INTEGER, desc="Customer tenure"),
        ],
    },
}


def match_scenario(prompt: str) -> str | None:
    """Return the scenario key whose keywords best match the prompt."""

    lowered = prompt.lower()
    best_key = None
    best_score = 0
    for key, cfg in SCENARIOS.items():
        score = sum(1 for kw in cfg["keywords"] if kw in lowered)
        # Longer keyword phrases are stronger signals.
        score += sum(2 for kw in cfg["keywords"] if " " in kw and kw in lowered)
        if score > best_score:
            best_score = score
            best_key = key
    return best_key if best_score > 0 else None
