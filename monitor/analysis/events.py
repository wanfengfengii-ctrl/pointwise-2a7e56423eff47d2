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


def selection_flags(event, values):
    """严格高于某站的站点数少于名额k即入选，并列全部保留。"""
    return tuple(sum(1 for other in values if other > value) < event.request.k
                 for value in values)


def selected_at_point(event, u, v):
    flags = selection_flags(event, [s.at(u, v) for s in event.frame.scores])
    return tuple(flags[i] for i in event.request.coordinates)


def comparison_probability(first, second, support):
    a = first.a - second.a
    b = first.b - second.b
    c = first.c - second.c
    if b == c == 0:
        return Fraction(int(a > 0))
    area = polygon_area(support)
    return polygon_area(clip_halfplane(support, HalfPlane(a, b, c))) / area


def iter_event_regions(event, support):
    """有限枚举支撑集上排名恒定的事件区域，产出(面积, 各站入选标志)。

    用全部成对评分差半平面裁剪支撑多边形；每一切片内排名不变，
    分割线测度为零，恒等评分及并列在切片内部完整保留。
    """
    cells = [list(support)]
    for i, first in enumerate(event.frame.scores):
        for second in event.frame.scores[i + 1:]:
            a = first.a - second.a
            b = first.b - second.b
            c = first.c - second.c
            if b == 0 and c == 0:
                continue
            plane = HalfPlane(a, b, c)
            mirror = HalfPlane(-a, -b, -c)
            cells = [piece for cell in cells
                     for piece in (clip_halfplane(cell, plane),
                                   clip_halfplane(cell, mirror))
                     if polygon_area(piece) > 0]
    for cell in cells:
        area = polygon_area(cell)
        if area <= 0:
            continue
        u = sum((p[0] for p in cell), Fraction(0)) / len(cell)
        v = sum((p[1] for p in cell), Fraction(0)) / len(cell)
        yield area, selection_flags(event, [s.at(u, v) for s in event.frame.scores])


def rank_probability(event, coordinate, support):
    total = polygon_area(support)
    selected = sum((area for area, flags in iter_event_regions(event, support)
                    if flags[coordinate]), Fraction(0))
    return selected / total
