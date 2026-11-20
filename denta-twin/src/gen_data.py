"""Generate a synthetic appointment dataset for a 3-chair dental clinic (one week)
and evaluate a transparent no-show risk rule. All data are SYNTHETIC."""
import json
import random
from datetime import date, timedelta

import pandas as pd

random.seed(42)

OUT = "data"
START = date(2026, 11, 2)  # Monday
DAYS = 6                   # Mon-Sat
HOURS = list(range(9, 17))  # 8 one-hour slots: 09:00..16:00

CHAIRS = [
    # chair, room, doctor, service, avg check KZT (assumption), booking prob, share of new patients
    ("CH-1", "Room 101", "Dr. Sultanova (therapist)", "Therapy / fillings", 18000, 0.82, 0.25),
    ("CH-2", "Room 102", "Dr. Omarov (hygienist)", "Hygiene / cleaning", 15000, 0.80, 0.60),
    ("CH-3", "Room 103", "Dr. Bekova (surgeon)", "Surgery / implant consult", 25000, 0.72, 0.35),
]
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

rows = []
rid = 1
for d in range(DAYS):
    day = START + timedelta(days=d)
    for h in HOURS:
        for chair, room, doctor, service, check, p_book, p_new in CHAIRS:
            booked = random.random() < p_book
            rec = {
                "Record_ID": f"R{rid:03d}",
                "Date": day.isoformat(),
                "Day": DAY_NAMES[d],
                "Time_Slot": f"{h:02d}:00",
                "Chair_ID": chair,
                "Room": room,
                "Doctor": doctor,
                "Service": service,
                "Slot_Status": "Booked" if booked else "Free",
                "Patient_Type": "",
                "Lead_Time_Days": "",
                "Confirmed": "",
                "Outcome": "Free slot",
            }
            if booked:
                new = random.random() < p_new
                # new patients (often from promo ads) tend to book further ahead
                lead = random.choice([1, 2, 3, 4, 5, 6, 8, 10, 12, 14]) if new else random.choice([0, 1, 1, 2, 3, 4, 5, 7, 9, 12])
                confirmed = random.random() < (0.55 if new else 0.85)
                # synthetic ground truth: no-show probability grows with the same risk factors + noise
                p_ns = 0.02 + 0.07 * new + 0.08 * (lead > 7) + 0.25 * (not confirmed)
                no_show = random.random() < p_ns
                rec.update({
                    "Patient_Type": "New" if new else "Returning",
                    "Lead_Time_Days": lead,
                    "Confirmed": "Yes" if confirmed else "No",
                    "Outcome": "No-show" if no_show else "Attended",
                })
            rows.append(rec)
            rid += 1

df = pd.DataFrame(rows)
check_map = {c[0]: c[4] for c in CHAIRS}

booked_mask = df["Slot_Status"] == "Booked"
df["Chair_Hours"] = 1
df["Booked_Flag"] = booked_mask.astype(int)
df["Attended_Flag"] = (df["Outcome"] == "Attended").astype(int)
df["NoShow_Flag"] = (df["Outcome"] == "No-show").astype(int)
df["Revenue_KZT"] = df.apply(lambda r: check_map[r["Chair_ID"]] if r["Outcome"] == "Attended" else 0, axis=1)
df["Lost_Revenue_KZT"] = df.apply(lambda r: check_map[r["Chair_ID"]] if r["Outcome"] == "No-show" else 0, axis=1)
# no-show flag only for booked slots (blank for free slots) so that AVG = no-show rate in the dashboard
df["NoShow_if_Booked"] = df.apply(lambda r: r["NoShow_Flag"] if r["Slot_Status"] == "Booked" else "", axis=1)


def risk_score(r):
    if r["Slot_Status"] != "Booked":
        return ""
    return int(r["Patient_Type"] == "New") + int(int(r["Lead_Time_Days"]) > 7) + int(r["Confirmed"] == "No")


df["Risk_Score"] = df.apply(risk_score, axis=1)
df["Risk_Level"] = df["Risk_Score"].apply(lambda s: "" if s == "" else ("High" if s >= 2 else "Low"))
df["Data_Status"] = "Synthetic"
df = df[["Record_ID","Date","Day","Time_Slot","Chair_ID","Room","Doctor","Service","Slot_Status","Patient_Type",
         "Lead_Time_Days","Confirmed","Outcome","Risk_Score","Risk_Level","Chair_Hours","Booked_Flag",
         "Attended_Flag","NoShow_Flag","NoShow_if_Booked","Revenue_KZT","Lost_Revenue_KZT","Data_Status"]]

df.to_csv(f"{OUT}/dental_clinic_appointments_synthetic.csv", index=False)

# ---------- KPIs ----------
b = df[booked_mask]
total_slots = len(df)
kpi = {
    "records": total_slots,
    "booked": int(b.shape[0]),
    "free": int((~booked_mask).sum()),
    "attended": int(df["Attended_Flag"].sum()),
    "no_shows": int(df["NoShow_Flag"].sum()),
    "chair_utilization_pct": round(100 * df["Attended_Flag"].sum() / df["Chair_Hours"].sum(), 1),
    "booking_rate_pct": round(100 * b.shape[0] / total_slots, 1),
    "no_show_rate_pct": round(100 * df["NoShow_Flag"].sum() / b.shape[0], 1),
    "revenue_kzt": int(df["Revenue_KZT"].sum()),
    "lost_revenue_kzt": int(df["Lost_Revenue_KZT"].sum()),
    "revenue_per_chair_hour_kzt": round(df["Revenue_KZT"].sum() / df["Chair_Hours"].sum()),
}

by_chair = df.groupby("Chair_ID").agg(
    slots=("Chair_Hours", "sum"), booked=("Booked_Flag", "sum"), attended=("Attended_Flag", "sum"),
    no_shows=("NoShow_Flag", "sum"), revenue=("Revenue_KZT", "sum"), lost=("Lost_Revenue_KZT", "sum"))
by_chair["utilization_pct"] = (100 * by_chair.attended / by_chair.slots).round(1)
by_chair["no_show_rate_pct"] = (100 * by_chair.no_shows / by_chair.booked).round(1)
by_chair["rev_per_chair_hour"] = (by_chair.revenue / by_chair.slots).round(0)

by_day = df.groupby("Day", sort=False).agg(
    booked=("Booked_Flag", "sum"), attended=("Attended_Flag", "sum"), no_shows=("NoShow_Flag", "sum"),
    revenue=("Revenue_KZT", "sum"))

by_type = b.groupby("Patient_Type").agg(booked=("Booked_Flag", "sum"), no_shows=("NoShow_Flag", "sum"))
by_type["rate"] = (100 * by_type.no_shows / by_type.booked).round(1)
by_conf = b.groupby("Confirmed").agg(booked=("Booked_Flag", "sum"), no_shows=("NoShow_Flag", "sum"))
by_conf["rate"] = (100 * by_conf.no_shows / by_conf.booked).round(1)
by_risk = b.groupby("Risk_Level").agg(booked=("Booked_Flag", "sum"), no_shows=("NoShow_Flag", "sum"))
by_risk["rate"] = (100 * by_risk.no_shows / by_risk.booked).round(1)

# ---------- Rule evaluation (confusion matrix on all booked, labelled records) ----------
pred = b["Risk_Level"] == "High"
act = b["Outcome"] == "No-show"
tp = int((pred & act).sum()); fp = int((pred & ~act).sum())
fn = int((~pred & act).sum()); tn = int((~pred & ~act).sum())
ev = {
    "TP": tp, "FP": fp, "FN": fn, "TN": tn,
    "accuracy_pct": round(100 * (tp + tn) / len(b), 1),
    "precision_pct": round(100 * tp / (tp + fp), 1) if tp + fp else None,
    "recall_pct": round(100 * tp / (tp + fn), 1) if tp + fn else None,
    "high_risk_bookings": int(pred.sum()),
    "baseline_accuracy_pct_all_attend": round(100 * (~act).sum() / len(b), 1),
}

# threshold sensitivity (score >=1, >=2, >=3)
sens = []
for t in (1, 2, 3):
    p = b["Risk_Score"].astype(int) >= t
    tp_ = int((p & act).sum()); fp_ = int((p & ~act).sum()); fn_ = int((~p & act).sum())
    sens.append({"threshold": t, "flagged": int(p.sum()), "caught": tp_,
                 "precision_pct": round(100 * tp_ / (tp_ + fp_), 1) if tp_ + fp_ else None,
                 "recall_pct": round(100 * tp_ / (tp_ + fn_), 1) if tp_ + fn_ else None})

# simple single-factor baseline: flag every unconfirmed booking
pu = b["Confirmed"] == "No"
tpu = int((pu & act).sum()); fpu = int((pu & ~act).sum())
baseline_unconfirmed = {"flagged": int(pu.sum()), "caught": tpu,
                        "precision_pct": round(100 * tpu / (tpu + fpu), 1),
                        "recall_pct": round(100 * tpu / int(act.sum()), 1)}

# ---------- Benefit estimates (assumptions, not measured) ----------
A = {"call_minutes": 3, "admin_cost_kzt_per_hour": 1800, "save_rate_after_call": 0.40, "weeks_per_month": 4}
avg_lost_check = df["Lost_Revenue_KZT"].sum() / max(1, df["NoShow_Flag"].sum())
recovered_visits_week = tp * A["save_rate_after_call"]
benefit = {
    "assumptions": A,
    "avg_check_of_missed_visit_kzt": round(avg_lost_check),
    "recovered_visits_per_week": round(recovered_visits_week, 1),
    "recovered_revenue_week_kzt": round(recovered_visits_week * avg_lost_check),
    "recovered_revenue_month_kzt": round(recovered_visits_week * avg_lost_check * A["weeks_per_month"]),
    "utilization_after_pct": round(100 * (df["Attended_Flag"].sum() + recovered_visits_week) / df["Chair_Hours"].sum(), 1),
    "calls_all_week": int(len(b)), "calls_high_risk_week": int(pred.sum()),
    "admin_minutes_saved_week": int((len(b) - pred.sum()) * A["call_minutes"]),
}
benefit["admin_hours_saved_month"] = round(benefit["admin_minutes_saved_week"] * A["weeks_per_month"] / 60, 1)
benefit["admin_cost_saved_month_kzt"] = round(benefit["admin_hours_saved_month"] * A["admin_cost_kzt_per_hour"])

summary = {
    "kpi": kpi,
    "by_chair": by_chair.reset_index().to_dict(orient="records"),
    "by_day": by_day.reset_index().to_dict(orient="records"),
    "by_patient_type": by_type.reset_index().to_dict(orient="records"),
    "by_confirmed": by_conf.reset_index().to_dict(orient="records"),
    "by_risk": by_risk.reset_index().to_dict(orient="records"),
    "rule_eval": ev,
    "threshold_sensitivity": sens,
    "baseline_unconfirmed_only": baseline_unconfirmed,
    "benefit": benefit,
}
with open(f"{OUT}/summary.json", "w") as f:
    json.dump(summary, f, indent=2, default=int)

print(json.dumps(summary, indent=2, default=int))
