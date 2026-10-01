from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VisitStatsDTO:
    total_visits: int
    today_visits: int
    unique_visitors: int
    today_unique_visitors: int
