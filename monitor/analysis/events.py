from dataclasses import dataclass
from fractions import Fraction
from monitor.analysis.geometry import HalfPlane, clip_halfplane, polygon_area
from monitor.scoring.representation import validate_score_frame
from monitor.analysis.results import parse_analysis_request, AnalysisError


@dataclass(frozen=True)
class RankingEvent:
    frame: object
    request: object


def build_ranking_event(frame, request):
    validate_score_frame(frame)
    checked = parse_analysis_request(frame, request.score_id, request.k, request.targets)
    if checked != request:
        raise AnalysisError("request coordinates differ from frame")
    return RankingEvent(frame, request)


def selected_at_point(event, u, v):
    ordered = sorted(event.frame.scores,
                     key=lambda s: (-s.at(u, v), s.station))
    selected = {s.coordinate for s in ordered[:event.request.k]}
    return tuple(i in selected for i in event.request.coordinates)


def comparison_probability(first, second, support):
    a = first.a - second.a
    b = first.b - second.b
    c = first.c - second.c
    if b == c == 0:
        return Fraction(int(a > 0 or (a == 0 and first.station < second.station)))
    area = polygon_area(support)
    return polygon_area(clip_halfplane(support, HalfPlane(a, b, c))) / area


def rank_probability(event, coordinate, support):
    target = event.frame.scores[coordinate]
    counts = [Fraction(1)]
    for other in event.frame.scores:
        if other.coordinate == coordinate:
            continue
        probability = comparison_probability(other, target, support)
        updated = [Fraction(0)] * (len(counts) + 1)
        for count, mass in enumerate(counts):
            updated[count] += mass * (1 - probability)
            updated[count + 1] += mass * probability
        counts = updated
    return sum(counts[:event.request.k], Fraction(0))
