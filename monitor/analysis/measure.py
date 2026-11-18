from fractions import Fraction
from monitor.calibration.scenarios import (PointScenario, RectangleScenario,
                                           validate_distribution)
from monitor.analysis.geometry import rectangle_polygon
from monitor.analysis.events import rank_probability, selected_at_point
from monitor.analysis.results import make_probability_result, AnalysisError


def measure_scenario(event, scenario):
    if not event.request.targets:
        return (), Fraction(0), Fraction(0)
    if isinstance(scenario, PointScenario):
        marginal = tuple(Fraction(int(v)) for v in
                         selected_at_point(event, scenario.u, scenario.v))
    elif isinstance(scenario, RectangleScenario):
        support = rectangle_polygon(scenario.u_lo, scenario.u_hi,
                                    scenario.v_lo, scenario.v_hi)
        marginal = tuple(rank_probability(event, i, support)
                         for i in event.request.coordinates)
    else:
        raise AnalysisError("unsupported scenario measure")
    joint = Fraction(1)
    complement = Fraction(1)
    for value in marginal:
        joint *= value
        complement *= 1 - value
    return marginal, joint, 1 - complement


def combine_scenario_measures(event, weighted):
    marginal = [Fraction(0)] * len(event.request.targets)
    joint = union = Fraction(0)
    for weight, (values, both, either) in weighted:
        for i, value in enumerate(values):
            marginal[i] += weight * value
        joint += weight * both
        union += weight * either
    return make_probability_result(event.request, marginal, joint, union)


def integrate_ranking_event(event, model):
    if (event.frame.model_id != model.id or
            event.frame.axes != tuple(model.axes.to_payload())):
        raise AnalysisError("ranking event uses a different shared model")
    scenarios = validate_distribution(model.scenarios)
    return combine_scenario_measures(
        event, ((s.weight, measure_scenario(event, s)) for s in scenarios))
