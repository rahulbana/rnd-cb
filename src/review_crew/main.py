"""CLI entry point for the Review Authenticity Crew.

Usage:
    python -m review_crew.main "Bella Italia restaurant, Bandra Mumbai"
    python -m review_crew.main "Sony WH-1000XM5 headphones" --type product

Or just run it with no arguments and answer the prompts.
"""

import argparse
import sys

from dotenv import load_dotenv

from .crew import ReviewAuthenticityCrew
from .models import ReviewReport


def _check_env() -> None:
    import os

    missing = [k for k in ("OPENAI_API_KEY", "TAVILY_API_KEY") if not os.getenv(k)]
    if missing:
        print(
            f"\n[!] Missing environment variable(s): {', '.join(missing)}\n"
            f"    Copy .env.example to .env and fill them in.\n"
        )
        sys.exit(1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Research and verify reviews for a product, restaurant, hotel, etc."
    )
    parser.add_argument(
        "subject",
        nargs="?",
        help="What to research, e.g. 'Bella Italia restaurant Mumbai'.",
    )
    parser.add_argument(
        "--type",
        dest="subject_type",
        default="auto",
        help="Category hint: product / restaurant / hotel / app / service (default: auto).",
    )
    return parser.parse_args()


def _print_report(report: ReviewReport) -> None:
    line = "=" * 70
    print(f"\n{line}")
    print(f" REVIEW AUTHENTICITY REPORT: {report.subject} ({report.subject_type})")
    print(line)
    print(f" Total reviewers found : {report.total_reviews_found}")
    print(f" Overall sentiment     : {report.overall_sentiment}")
    print(f" Positivity score      : {report.sentiment_score}/100")
    print(f"\n CONCLUSION:\n  {report.conclusion}")

    print(f"\n TOP POSITIVE REVIEWS:")
    for i, r in enumerate(report.top_positive_reviews[:5], 1):
        print(f"  {i}. ({r.rating}) {r.text}\n     source: {r.source}")

    print(f"\n TOP NEGATIVE REVIEWS:")
    for i, r in enumerate(report.top_negative_reviews[:5], 1):
        print(f"  {i}. ({r.rating}) {r.text}\n     source: {r.source}")

    print(f"\n AUTHENTICITY ASSESSMENT (by verifier agent):\n  {report.authenticity_assessment}")

    print(f"\n SOURCES:")
    for s in report.sources:
        print(f"  - {s}")
    print(f"{line}\n")


def run() -> None:
    load_dotenv()
    _check_env()

    args = _parse_args()
    subject = args.subject or input("What do you want reviews for? ").strip()
    if not subject:
        print("No subject provided. Exiting.")
        sys.exit(1)

    subject_type = args.subject_type
    if subject_type == "auto":
        subject_type = (
            input("Category (product/restaurant/hotel/app/service) [auto]: ").strip()
            or "auto"
        )

    print(f"\nResearching reviews for: {subject} (type: {subject_type}) ...\n")

    result = ReviewAuthenticityCrew().crew().kickoff(
        inputs={"subject": subject, "subject_type": subject_type}
    )

    report = getattr(result, "pydantic", None)
    if isinstance(report, ReviewReport):
        _print_report(report)
    else:
        # Fallback: print whatever the crew returned.
        print("\n=== RAW RESULT ===\n")
        print(result)


if __name__ == "__main__":
    run()
