// A short sample so the app is usable without hunting for text to paste.
export const SAMPLE_TEXT = `Quarterly Engineering Review — Q3

Overview
This quarter the platform team focused on reliability and cost. We migrated the
primary datastore to a managed service, reducing on-call incidents by 40% and
cutting infrastructure spend by roughly $18,000 per month. The migration ran two
weeks longer than planned due to an unexpected data-encoding issue in legacy
records, which required a one-off backfill job.

Key results
- API p99 latency dropped from 820ms to 310ms after connection-pool tuning.
- We shipped the new rate limiter, eliminating the three largest outage classes
  from last quarter.
- Test coverage on the billing service rose from 54% to 81%.
- The mobile release cadence moved from monthly to biweekly.

Decisions
- We will standardize on the managed datastore for all new services starting Q4.
- The legacy reporting pipeline will be deprecated; teams must migrate by end of
  Q1 next year.
- We approved hiring two additional SREs to support the expanded on-call rotation.

Risks and open questions
- The backfill job revealed data-quality gaps that may affect historical reports.
- Vendor lock-in is a growing concern; we should evaluate an exit strategy.
- Biweekly mobile releases increase QA load and may require more automation.

Next steps
- Finalize the Q4 migration plan and communicate deadlines to all teams.
- Draft an SRE onboarding guide before the new hires start.
- Investigate the historical data-quality issues and quantify their impact.
- Prototype automated QA for the mobile pipeline.`;
