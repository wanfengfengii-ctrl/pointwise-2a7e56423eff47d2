"""复测报告事故核账。

A、B、C在同一校准情景中参与排名。rectangle为[-1,1]的二维均匀
情景；mixture再混合一半零点质量。零点及恒等评分上的并列不截断。
planar使用A=U、B=V、C=0并给两个名额。每例通过正式接纳、固定、
评分、报告与自足包复算入口，对照精确手算值；不使用随机抽样。
"""
from copy import deepcopy
from fractions import Fraction as F
from monitor.archive.database import ArchiveDatabase
from monitor.archive.reading import read_result
from monitor.archive.delivery import build_bundle, verify_bundle
from monitor.archive.codec import canonical_json
from monitor.analysis.jobs import run_daily_manifest


def rectangle(weight=1):
    return dict(kind="rectangle", weight=weight,
                u_lo=-1, u_hi=1, v_lo=-1, v_hi=1)


def point(weight=1):
    return dict(kind="point", weight=weight, u=0, v=0)


def manifest(name, rows, scenarios, k=1):
    observations = [
        dict(source="station-lab", station=station, revision="r1",
             x=a, r_u=b, r_v=c, unit="ug/m3")
        for station, a, b, c in rows
    ]
    return dict(
        batch=name, observations=observations,
        cohort=[(r["source"], r["station"], r["revision"]) for r in observations],
        calibration=dict(
            source="calibration-lab", revision="c1", variables=["U", "V"],
            scenarios=deepcopy(scenarios),
            rule=dict(delta=0, alpha=1, beta=1, gamma=1,
                      version="affine-v1", input_unit="ug/m3", output_unit="score")),
        score_request=name + "-score", analysis_request=name + "-analysis",
        k=k, targets=["A", "B"])


def cases():
    opposed = [("A", 0, 1, 0), ("B", 0, -1, 0), ("C", 0, 0, 0)]
    yield "rectangle", manifest("rectangle", opposed, [rectangle()]), (
        [F(1, 2), F(1, 2)], F(0), F(1))
    yield "mixture", manifest("mixture", opposed,
                              [rectangle("1/2"), point("1/2")]), (
        [F(3, 4), F(3, 4)], F(1, 2), F(1))
    tied = [("A", 2, 1, -1), ("B", 2, 1, -1), ("C", 2, 1, -1)]
    yield "ties", manifest("ties", tied, [rectangle()]), (
        [F(1), F(1)], F(1), F(1))
    planar = [("A", 0, 1, 0), ("B", 0, 0, 1), ("C", 0, 0, 0)]
    yield "planar", manifest("planar", planar, [rectangle()], k=2), (
        [F(5, 8), F(5, 8)], F(1, 4), F(1))


def probabilities(payload):
    return payload["marginals"], payload["joint"], payload["union"]


def main():
    failed = []
    for name, inputs, expected in cases():
        with ArchiveDatabase() as db:
            ids = run_daily_manifest(db, inputs)
            report = read_result(db, ids["report"])["payload"]
            actual = probabilities(report)
            replayed = probabilities(verify_bundle(build_bundle(db, ids["report"])))
            print(canonical_json(dict(case=name, expected=expected,
                                      actual=actual, replayed=replayed)))
            if actual != expected or replayed != expected:
                failed.append(name)
    if failed:
        print("RANK_JOINT_MISMATCH " + ",".join(failed))
        return 1
    print("RANK_JOINT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
