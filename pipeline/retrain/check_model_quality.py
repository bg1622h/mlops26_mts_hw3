import pandas as pd
from airflow.exceptions import AirflowSkipException
from catboost import CatBoostClassifier
from sklearn.metrics import f1_score, roc_auc_score
from pipeline.settings import MODELS_DIR

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def model_metrics(path: Path, frame: pd.DataFrame) -> dict:
    model = CatBoostClassifier()
    model.load_model(str(path))
    missing = [name for name in model.feature_names_ if name not in frame.columns]
    if missing:
        raise ValueError(f"Missing features required by the current model: {missing}")
    features = frame[model.feature_names_].copy()
    for index in model.get_cat_feature_indices():
        column = model.feature_names_[index]
        features[column] = features[column].astype(str)
    labels = frame["target"].astype(int)
    probabilities = model.predict_proba(features)[:, 1]
    return {
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "f1": float(f1_score(labels, probabilities > 0.5, zero_division=0)),
    }


def check_model_quality(train_info: dict) -> dict:
    frame = pd.read_parquet(train_info["test_proc_path"])
    candidate_path = Path(train_info["staging_model"])
    if not candidate_path.exists():
        candidate_path = MODELS_DIR / f"my_catboost_{train_info['version']}.cbm"
    latest = MODELS_DIR / "latest.txt"
    if latest.exists():
        previous_version = latest.read_text(encoding="utf-8").strip()
        previous_path = MODELS_DIR / f"my_catboost_{previous_version}.cbm"
    else:
        previous_version = "initial"
        previous_path = Path(os.getenv("INITIAL_MODEL_PATH", "/opt/airflow/initial_model.cbm"))
    report = {
        "version": train_info["version"],
        "previous_version": previous_version,
        "test_month": train_info["test_month"],
        "test_rows": len(frame),
        "approved": False,
    }
    if frame["target"].nunique() < 2:
        report["reason"] = "The test set must have both classes to compute ROC-AUC"
    else:
        candidate = model_metrics(candidate_path, frame)
        previous = model_metrics(previous_path, frame)
        report.update(candidate=candidate, previous=previous)
        report["approved"] = all(candidate[metric] >= previous[metric] for metric in ("roc_auc", "f1"))
        report["reason"] = (
            "Publishing approved"
            if report["approved"]
            else "ROC-AUC or F1 decreased"
        )
    path = MODELS_DIR / f"model_quality_{train_info['version']}.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
    logger.info("Model comparison: %s", report)
    if not report["approved"]:
        raise AirflowSkipException(report["reason"])
    return train_info