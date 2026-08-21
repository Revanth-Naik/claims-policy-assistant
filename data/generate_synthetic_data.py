"""
Generates fully synthetic members, providers, and claims data for a fictional
health plan ("Meridian Health Plan"). None of this is real Cigna data or any
real person/provider -- it exists purely to give the dbt models and RAG layer
something realistic to run against.

Run: python data/generate_synthetic_data.py
Outputs CSVs into data/raw/.
"""
import os
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

OUT_DIR = os.path.join(os.path.dirname(__file__), "raw")
os.makedirs(OUT_DIR, exist_ok=True)

N_MEMBERS = 800
N_PROVIDERS = 120
N_CLAIMS = 6000

PLAN_TYPES = ["Bronze HMO", "Silver PPO", "Gold PPO", "Platinum HMO"]
REGIONS = ["Northeast", "Mid-Atlantic", "Southeast", "Midwest", "West"]
SPECIALTIES = [
    "Primary Care", "Cardiology", "Orthopedics", "Behavioral Health",
    "Dermatology", "Endocrinology", "Radiology", "Physical Therapy",
    "OB/GYN", "Pediatrics",
]
PROCEDURES = [
    ("99213", "Office visit, established patient"),
    ("99385", "Preventive visit, new patient"),
    ("70551", "MRI, brain"),
    ("93000", "Electrocardiogram"),
    ("97110", "Therapeutic exercise"),
    ("90837", "Psychotherapy, 60 min"),
    ("29881", "Knee arthroscopy"),
    ("80053", "Comprehensive metabolic panel"),
    ("71046", "Chest X-ray"),
    ("J3490", "Unclassified drug (specialty pharmacy)"),
]
DENIAL_REASONS = [
    ("CO-50", "Not deemed a medical necessity"),
    ("CO-97", "Service bundled into another paid service"),
    ("PR-1", "Deductible amount not yet met"),
    ("CO-197", "Precertification/prior authorization absent"),
    ("CO-29", "Time limit for claim submission has expired"),
]


def gen_members(n):
    rows = []
    for i in range(1, n + 1):
        effective = fake.date_between(start_date="-3y", end_date="-3m")
        plan = random.choice(PLAN_TYPES)
        # a slice of members had a mid-history plan change -> good SCD2 example
        changed = random.random() < 0.18
        rows.append({
            "member_id": f"M{i:06d}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "dob": fake.date_of_birth(minimum_age=1, maximum_age=85),
            "gender": random.choice(["F", "M"]),
            "region": random.choice(REGIONS),
            "plan_type": plan,
            "plan_effective_date": effective,
            "scd_change_flag": changed,
        })
    return pd.DataFrame(rows)


def explode_member_scd(members_df):
    """Turn each member into 1 or 2 dimension rows to simulate SCD Type 2 history."""
    out = []
    for _, m in members_df.iterrows():
        if not m["scd_change_flag"]:
            out.append({
                "member_id": m["member_id"], "first_name": m["first_name"],
                "last_name": m["last_name"], "dob": m["dob"], "gender": m["gender"],
                "region": m["region"], "plan_type": m["plan_type"],
                "valid_from": m["plan_effective_date"], "valid_to": None, "is_current": True,
            })
        else:
            change_date = m["plan_effective_date"] + timedelta(days=random.randint(120, 500))
            old_plan = random.choice([p for p in PLAN_TYPES if p != m["plan_type"]])
            out.append({
                "member_id": m["member_id"], "first_name": m["first_name"],
                "last_name": m["last_name"], "dob": m["dob"], "gender": m["gender"],
                "region": m["region"], "plan_type": old_plan,
                "valid_from": m["plan_effective_date"], "valid_to": change_date, "is_current": False,
            })
            out.append({
                "member_id": m["member_id"], "first_name": m["first_name"],
                "last_name": m["last_name"], "dob": m["dob"], "gender": m["gender"],
                "region": m["region"], "plan_type": m["plan_type"],
                "valid_from": change_date, "valid_to": None, "is_current": True,
            })
    return pd.DataFrame(out)


def gen_providers(n):
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "provider_id": f"P{i:05d}",
            "provider_name": f"Dr. {fake.last_name()}" if random.random() > 0.1 else fake.company() + " Clinic",
            "npi": fake.numerify("##########"),
            "specialty": random.choice(SPECIALTIES),
            "region": random.choice(REGIONS),
            "network_status": random.choices(["In-Network", "Out-of-Network"], weights=[0.85, 0.15])[0],
        })
    return pd.DataFrame(rows)


def gen_claims(n, members_df, providers_df):
    # members_df has one row per member (pre-SCD2-explode) with plan_effective_date --
    # a claim can only exist on or after the member's plan enrollment date, otherwise
    # it has no matching member dimension version for the point-in-time join.
    member_records = members_df[["member_id", "plan_effective_date"]].to_dict("records")
    provider_ids = providers_df["provider_id"].tolist()
    today = date.today()
    rows = []
    for i in range(1, n + 1):
        member = random.choice(member_records)
        earliest = max(member["plan_effective_date"], today - timedelta(days=730))
        if earliest >= today:
            earliest = today - timedelta(days=1)
        service_date = fake.date_between(start_date=earliest, end_date="today")
        submitted_date = service_date + timedelta(days=random.randint(0, 21))
        proc_code, proc_desc = random.choice(PROCEDURES)
        billed = round(random.uniform(80, 4500), 2)
        status = random.choices(["Paid", "Denied", "Pending"], weights=[0.78, 0.14, 0.08])[0]
        if status == "Paid":
            allowed = round(billed * random.uniform(0.55, 0.9), 2)
            paid = round(allowed * random.uniform(0.7, 1.0), 2)
            denial_code, denial_desc = None, None
        elif status == "Denied":
            allowed, paid = 0.0, 0.0
            denial_code, denial_desc = random.choice(DENIAL_REASONS)
        else:
            allowed, paid = None, None
            denial_code, denial_desc = None, None

        rows.append({
            "claim_id": f"C{i:07d}",
            "claim_line_id": 1,
            "member_id": member["member_id"],
            "provider_id": random.choice(provider_ids),
            "service_date": service_date,
            "submitted_date": submitted_date,
            "procedure_code": proc_code,
            "procedure_desc": proc_desc,
            "billed_amount": billed,
            "allowed_amount": allowed,
            "paid_amount": paid,
            "claim_status": status,
            "denial_reason_code": denial_code,
            "denial_reason_desc": denial_desc,
            "place_of_service": random.choice(["Office", "Outpatient Hospital", "Telehealth", "Inpatient Hospital"]),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    members_raw = gen_members(N_MEMBERS)
    members_scd = explode_member_scd(members_raw)
    providers = gen_providers(N_PROVIDERS)
    claims = gen_claims(N_CLAIMS, members_raw, providers)

    members_scd.to_csv(os.path.join(OUT_DIR, "members.csv"), index=False)
    providers.to_csv(os.path.join(OUT_DIR, "providers.csv"), index=False)
    claims.to_csv(os.path.join(OUT_DIR, "claims.csv"), index=False)

    print(f"members.csv  -> {len(members_scd)} rows ({members_scd['member_id'].nunique()} distinct members, "
          f"{(~members_scd['is_current']).sum()} historical SCD2 rows)")
    print(f"providers.csv -> {len(providers)} rows")
    print(f"claims.csv   -> {len(claims)} rows")
