"""Step 2: scenarios. Metrics (TTC, required deceleration), mining braking events from the logs, and the physics
frontier that separates 'no planner could have avoided this' from 'this planner failed'."""
import numpy as np

from . import config as C


def ttc(gap, closing):
    """Time to collision [s] = gap / closing speed (inf when the gap is not closing)."""
    gap = np.asarray(gap, dtype=float)
    closing = np.asarray(closing, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        res = np.where(closing > 0, gap / closing, np.inf)
    return float(res) if res.ndim == 0 else res


def required_decel(gap, closing):
    """Deceleration [m/s^2] needed to remove the closing speed exactly at contact: closing^2 / (2 gap)."""
    gap = np.asarray(gap, dtype=float)
    closing = np.asarray(closing, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        res = np.where(closing > 0, (closing ** 2) / (2 * gap), 0.0)
    return float(res) if res.ndim == 0 else res


def unavoidable(gaps, dvs, t_react=0.0, b_max=C.B_MAX):
    """Boolean grid (len(dvs), len(gaps)): True where NO planner can avoid contact, even braking at b_max after the
    reaction delay: gap < dv * t_react + dv^2 / (2 b_max)  (lead keeps its speed)."""
    gaps = np.asarray(gaps, dtype=float)
    dvs = np.asarray(dvs, dtype=float)
    G, DV = np.meshgrid(gaps, dvs)
    limit = DV * t_react + (DV ** 2) / (2 * b_max)
    return (DV > 0) & (G < limit)


def mine_braking(logs, threshold=C.BRAKE_THRESHOLD, min_steps=5):
    """Find trajectories where the lead brakes: smoothed deceleration below `threshold` for at least `min_steps`
    consecutive steps (0.5 s). Returns a list of event dicts (one per trajectory, first event only)."""
    events = []
    for i in range(len(logs)):
        n_i = logs.n[i]
        a = logs.a_lead[i, :n_i]
        is_brake = a < threshold

        onset = None
        end_run = None
        k = 0
        while k < len(is_brake):
            if is_brake[k]:
                run_start = k
                while k < len(is_brake) and is_brake[k]:
                    k += 1
                run_len = k - run_start
                if run_len >= min_steps:
                    onset = run_start
                    end_run = k
                    break
            else:
                k += 1

        if onset is not None:
            peak = float(np.min(a[onset:end_run]))
            gap_m = float(logs.gap[i, onset])
            closing_m_s = float(logs.v_ego[i, onset] - logs.v_lead_s[i, onset])
            ego_speed = float(logs.v_ego[i, onset])
            events.append({
                "traj": int(i),
                "onset_step": int(onset),
                "peak_decel": peak,
                "gap_m": gap_m,
                "closing_m_s": closing_m_s,
                "ego_speed": ego_speed,
            })
    return events


def human_brake_limit(logs, q=0.1):
    """Hardest braking [m/s^2, positive number] that the logged human followers ever applied (the q-th percentile of
    their acceleration, from the speed differences). Learned planners cannot have seen anything harder."""
    a = np.diff(logs.v_ego, axis=1) / C.DT
    return float(-np.nanpercentile(a, q))


def grid_from_logs(logs, v_ego, n_gap=60, n_dv=45):
    """Scenario grid. Gap limits come from what the logs contain (p2 .. p98 of the logged gaps). Closing speed runs
    from 0 to v_ego: dv = v_ego means the cutter is standing still, the most extreme case (never faster than that,
    otherwise the cutter would drive backwards)."""
    g_lo, g_hi = np.nanpercentile(logs.gap, [2, 98])
    return np.linspace(g_lo, g_hi, n_gap), np.linspace(0.0, v_ego, n_dv)
