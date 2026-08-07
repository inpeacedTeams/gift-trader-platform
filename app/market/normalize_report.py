from dataclasses import asdict, dataclass
from .normalize import NormalizedSnapshot

@dataclass(frozen=True)
class NormalizationReport:
    marketplace: str
    input_count: int
    accepted_count: int
    duplicate_count: int
    rejected_count: int


def report(snapshot: NormalizedSnapshot) -> NormalizationReport:
    return NormalizationReport(
        marketplace=snapshot.marketplace,
        input_count=len(snapshot.listings) + snapshot.duplicate_count + snapshot.rejected_count,
        accepted_count=len(snapshot.listings),
        duplicate_count=snapshot.duplicate_count,
        rejected_count=snapshot.rejected_count,
    )


def report_dict(snapshot: NormalizedSnapshot) -> dict[str, int | str]:
    return asdict(report(snapshot))
