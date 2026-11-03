import csv
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

BIS_LIMITS = {
    "arsenic": 10.0,   # ug/L (micrograms per litre)
    "fluoride": 1.5,   # mg/L
    "nitrate": 45.0,   # mg/L
    "uranium": 30.0    # ug/L
}

PARAM_LABELS = {
    "arsenic": ("As", "ug/L"),
    "fluoride": ("F", "mg/L"),
    "nitrate": ("NO3", "mg/L"),
    "uranium": ("U", "ug/L")
}

class AreaLockEngine:
    def __init__(self, risk_csv_path: str = "district_risk.csv"):
        self.risk_csv_path = risk_csv_path
        self.districts: Dict[str, Dict[str, Any]] = {}
        self.load_risk_table()

    def load_risk_table(self):
        self.districts.clear()
        try:
            with open(self.risk_csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    d_name = row["district"].strip()
                    self.districts[d_name.lower()] = {
                        "name": d_name,
                        "state": row.get("state", "").strip(),
                        "flags": {
                            "arsenic": int(row.get("arsenic", 0)),
                            "fluoride": int(row.get("fluoride", 0)),
                            "nitrate": int(row.get("nitrate", 0)),
                            "uranium": int(row.get("uranium", 0)),
                        },
                        "notes": row.get("notes", "")
                    }
        except Exception as e:
            print(f"Error loading {self.risk_csv_path}: {e}")

    def get_district_info(self, district_name: str) -> Optional[Dict[str, Any]]:
        return self.districts.get(district_name.strip().lower())

    def get_flagged_params(self, district_name: str) -> list[str]:
        info = self.get_district_info(district_name)
        if not info:
            return []
        return [k for k, v in info["flags"].items() if v == 1]

    def evaluate_lock(
        self,
        district_name: str,
        water_source: str, # "groundwater" or "piped"
        test_result: Optional[Dict[str, Any]] = None,
        current_date: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        Evaluates whether an area lock should be applied.
        Returns: (locked: bool, reason: str)
        """
        if current_date is None:
            current_date = datetime.now()

        # Rule 2: Lock applies only to groundwater
        if water_source.lower() != "groundwater":
            return False, f"Source is {water_source.title()} -> Area lock bypassed"

        info = self.get_district_info(district_name)
        # Rule 3: Unlisted district
        if not info:
            return False, f"District '{district_name}' has no CGWB flag found (never assume safe)"

        flagged = [k for k, v in info["flags"].items() if v == 1]
        if not flagged:
            return False, f"No chemical exceedance flagged for {info['name']}"

        flag_str = ", ".join(PARAM_LABELS[p][0] for p in flagged)

        # Rule 4: Check if test result is provided
        if not test_result:
            return True, f"District flag: {flag_str}; no test on file -> RO forced"

        test_source = test_result.get("source", "unknown").lower()
        test_date_raw = test_result.get("date")
        if isinstance(test_date_raw, str):
            try:
                test_date = datetime.strptime(test_date_raw, "%Y-%m-%d")
            except ValueError:
                test_date = current_date
        elif isinstance(test_date_raw, datetime):
            test_date = test_date_raw
        else:
            test_date = current_date

        # Rule 7: Test strips are advisory only and NEVER unlock arsenic
        if "arsenic" in flagged and "strip" in test_source:
            return True, f"Test strip advisory only: cannot unlock As (54% false negative risk) -> RO stays locked"

        # Rule 6: 6-month validity expiration
        days_old = (current_date - test_date).days
        if days_old > 180:
            expiry_str = (test_date + timedelta(days=180)).strftime("%Y-%m-%d")
            return True, f"Test {test_date.strftime('%Y-%m-%d')} expired on {expiry_str} (>6 mos) -> RO stays locked"

        # Rule 6: Nitrate re-locks post-monsoon
        # Monsoon in India is typically June to September (months 6 to 9).
        # Post-monsoon is October onwards. If test was before June and current date is Oct-Feb, re-lock.
        if "nitrate" in flagged:
            # Check if a monsoon season passed between test date and current date
            test_month = test_date.month
            curr_month = current_date.month
            # If tested pre-monsoon (month <= 5) and now it's post-monsoon (month >= 10 or next year)
            if (test_month <= 5 and curr_month >= 10) or (current_date.year > test_date.year and curr_month >= 10):
                return True, f"Nitrate flag re-locked post-monsoon (CGWB nitrate surge detected) -> RO forced"

        # Rule 5: Verify all flagged parameters meet BIS limits
        measured_values = test_result.get("values", {})
        param_summaries = []
        for param in flagged:
            val = measured_values.get(param)
            label, unit = PARAM_LABELS[param]
            limit = BIS_LIMITS[param]

            if val is None:
                return True, f"Missing test value for flagged contaminant {label} -> RO stays locked"

            if float(val) > limit:
                return True, f"Test {test_date.strftime('%Y-%m-%d')} ({test_result.get('source', 'lab')}) {label}={val}{unit} > {limit} -> RO stays locked"

            param_summaries.append(f"{label}={val}{unit}")

        expiry_date = (test_date + timedelta(days=180)).strftime("%Y-%m-%d")
        summary_str = ", ".join(param_summaries)
        return False, f"Unlocked: {test_result.get('source', 'lab')} {test_date.strftime('%Y-%m-%d')} {summary_str}; expires {expiry_date}"
