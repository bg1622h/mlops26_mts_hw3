from datetime import datetime, timezone
from pipeline.db import LABELED_COLUMNS, get_conn
from pipeline.settings import CAT_FEATURES


def check_dataset(run_id=None) -> dict:
    result = {
        "run_id": run_id,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "rules": [],
    }
    conn = get_conn()
    try:
        conn.set_session(isolation_level="REPEATABLE READ", readonly=True)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='labeled_transactions'"
            )
            columns = {row[0] for row in cur.fetchall()}
            missing = sorted(set(LABELED_COLUMNS) - columns)
            if missing:
                result["rules"].append(
                    {
                        "name": "Schema and required values",
                        "passed": False,
                        "details": f"Missing columns: {missing}",
                    }
                )
                return result
            required = [
                "transaction_time",
                "target",
                "amount",
                "population_city",
                "lat",
                "lon",
                "merchant_lat",
                "merchant_lon",
                *CAT_FEATURES,
            ]
            conditions = [
                (
                    "Schema and required values",
                    " AND ".join(f"{column} IS NOT NULL" for column in required),
                ),
                ("Finite transaction time", "isfinite(transaction_time)"),
                (
                    "Finite nonnegative amount",
                    "amount >= 0 AND amount < 'Infinity'::double precision",
                ),
                (
                    "Geographic coordinates within valid ranges",
                    "lat BETWEEN -90 AND 90 AND merchant_lat BETWEEN -90 AND 90 AND lon BETWEEN -180 AND 180 AND merchant_lon BETWEEN -180 AND 180",
                ),
                ("Binary target with both classes", "target IN (0,1)"),
            ]
            expressions = [
                f"COUNT(*) FILTER (WHERE ({condition}) IS NOT TRUE)"
                for _, condition in conditions
            ]
            cur.execute(
                "SELECT COUNT(*), COUNT(DISTINCT target), "
                + ", ".join(expressions)
                + " FROM labeled_transactions"
            )
            row = cur.fetchone()
            result["rows"] = row[0]
            for index, ((name, _), invalid) in enumerate(zip(conditions, row[2:])):
                passed = invalid == 0 and row[0] > 0
                if index == 4:
                    passed = passed and row[1] == 2
                result["rules"].append(
                    {
                        "name": name,
                        "passed": passed,
                        "details": f"Rows: {row[0]}, violations: {invalid}, distinct labels: {row[1]}",
                    }
                )
        return result
    finally:
        conn.close()