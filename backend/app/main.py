"""
GP's Assistant Diagnostician - FastAPI backend
Ports the original Streamlit pipeline (embeddings -> t-SNE -> logistic regression -> diagnosis)
into a clean REST API for a React frontend.

Runs fully offline by default using TF-IDF + Truncated SVD as the embedding engine,
so no API key is required for the demo. Optionally, a Mistral or OpenAI key can be
provided to use real LLM embeddings instead.
"""
from __future__ import annotations

import io
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.manifold import TSNE
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from . import pricing_corridor
from .medical_database import get_medical_info

app = FastAPI(title="GP's Assistant Diagnostician API", version="1.0.0")

# Allow overriding via ALLOWED_ORIGINS env var (comma-separated) in production,
# e.g. "https://your-app.vercel.app,https://your-app-git-main.vercel.app"
_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
_allow_origins = ["*"] if _origins_env.strip() == "*" else [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------------
# In-memory application state (single-user local demo, mirrors st.session_state)
# ----------------------------------------------------------------------------
STATE: Dict[str, Any] = {
    "df": None,  # pandas DataFrame with columns text, label
    "embeddings": None,  # np.ndarray [n, d]
    "encoded_labels": None,
    "label_encoder": LabelEncoder(),
    "vectorizer": None,
    "svd": None,
    "tsne_coords": None,  # np.ndarray [n, 3]
    "scaler": None,
    "clf": None,
    "model_metrics": {},
    "api_provider": "Local (offline)",
    "api_key": None,
    "search_history": [],
    "confidence_thresholds": {"green": [75, 100], "amber": [55, 74], "red": [0, 54]},
}

DEFAULT_DATASET_URL = "https://raw.githubusercontent.com/mistralai/cookbook/main/data/Symptom2Disease.csv"


# ----------------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------------
class ConfigureRequest(BaseModel):
    provider: str = "Local (offline)"
    api_key: Optional[str] = None


class LoadUrlRequest(BaseModel):
    url: Optional[str] = None


class DiagnoseRequest(BaseModel):
    symptoms: str


class ThresholdRequest(BaseModel):
    green: List[int]
    amber: List[int]
    red: List[int]


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _df_preview(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "rows": len(df),
        "columns": list(df.columns),
        "unique_labels": int(df["label"].nunique()) if "label" in df.columns else 0,
        "sample": df.head(25).to_dict(orient="records"),
    }


def _get_confidence_color(confidence_pct: float) -> str:
    t = STATE["confidence_thresholds"]
    if t["green"][0] <= confidence_pct <= t["green"][1]:
        return "green"
    if t["amber"][0] <= confidence_pct <= t["amber"][1]:
        return "amber"
    return "red"


def _embed_texts_offline(texts: List[str], fit: bool) -> np.ndarray:
    """TF-IDF + TruncatedSVD embedding pipeline. Fully offline, no API key needed."""
    n_components = min(64, max(2, len(texts) - 1))
    if fit or STATE["vectorizer"] is None:
        vectorizer = TfidfVectorizer(max_features=2000, stop_words="english", ngram_range=(1, 2))
        matrix = vectorizer.fit_transform(texts)
        svd = TruncatedSVD(n_components=n_components, random_state=42)
        reduced = svd.fit_transform(matrix)
        STATE["vectorizer"] = vectorizer
        STATE["svd"] = svd
    else:
        matrix = STATE["vectorizer"].transform(texts)
        reduced = STATE["svd"].transform(matrix)
    return reduced


def _embed_texts_provider(texts: List[str], provider: str, api_key: str) -> np.ndarray:
    """Call a real embeddings API (Mistral or OpenAI) if the user supplied a key."""
    vectors = []
    if provider == "Mistral":
        url = "https://api.mistral.ai/v1/embeddings"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        for i in range(0, len(texts), 50):
            chunk = texts[i : i + 50]
            resp = requests.post(url, headers=headers, json={"model": "mistral-embed", "input": chunk}, timeout=60)
            resp.raise_for_status()
            data = resp.json()["data"]
            vectors.extend([d["embedding"] for d in data])
    elif provider == "OpenAI":
        url = "https://api.openai.com/v1/embeddings"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        for text in texts:
            resp = requests.post(url, headers=headers, json={"model": "text-embedding-3-small", "input": text}, timeout=60)
            resp.raise_for_status()
            vectors.append(resp.json()["data"][0]["embedding"])
    else:
        raise HTTPException(400, f"Unsupported provider for embeddings: {provider}")
    return np.array(vectors)


def _embed(texts: List[str], fit: bool) -> np.ndarray:
    provider = STATE["api_provider"]
    if provider in ("Mistral", "OpenAI") and STATE["api_key"]:
        try:
            return _embed_texts_provider(texts, provider, STATE["api_key"])
        except Exception as exc:  # fall back gracefully
            raise HTTPException(502, f"Embedding provider error ({provider}): {exc}")
    return _embed_texts_offline(texts, fit=fit)


# ----------------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.post("/api/configure")
def configure(req: ConfigureRequest):
    STATE["api_provider"] = req.provider
    STATE["api_key"] = req.api_key
    return {"provider": STATE["api_provider"], "configured": True}


@app.get("/api/config")
def get_config():
    return {
        "provider": STATE["api_provider"],
        "has_key": bool(STATE["api_key"]),
        "processed": STATE["embeddings"] is not None,
        "trained": STATE["clf"] is not None,
        "has_clusters": STATE["tsne_coords"] is not None,
        "rows": int(len(STATE["df"])) if STATE["df"] is not None else 0,
    }


@app.post("/api/data/load-url")
def load_url(req: LoadUrlRequest):
    url = req.url or DEFAULT_DATASET_URL
    try:
        df = pd.read_csv(url, index_col=0)
    except Exception as exc:
        raise HTTPException(400, f"Failed to load CSV from URL: {exc}")
    if "text" not in df.columns or "label" not in df.columns:
        raise HTTPException(400, "CSV must contain 'text' and 'label' columns")
    STATE["df"] = df.reset_index(drop=True)
    return _df_preview(STATE["df"])


@app.post("/api/data/load-file")
async def load_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents), index_col=0)
    except Exception as exc:
        raise HTTPException(400, f"Failed to parse CSV: {exc}")
    if "text" not in df.columns or "label" not in df.columns:
        raise HTTPException(400, "CSV must contain 'text' and 'label' columns")
    STATE["df"] = df.reset_index(drop=True)
    return _df_preview(STATE["df"])


@app.get("/api/data/preview")
def data_preview():
    if STATE["df"] is None:
        raise HTTPException(404, "No data loaded yet")
    return _df_preview(STATE["df"])


@app.post("/api/process")
def process_embeddings():
    if STATE["df"] is None:
        raise HTTPException(400, "Load data first")
    df = STATE["df"]
    texts = df["text"].astype(str).tolist()
    embeddings = _embed(texts, fit=True)
    STATE["embeddings"] = embeddings
    STATE["encoded_labels"] = STATE["label_encoder"].fit_transform(df["label"])
    return {
        "processed": True,
        "embedding_dim": int(embeddings.shape[1]),
        "total_samples": int(embeddings.shape[0]),
        "unique_diseases": int(df["label"].nunique()),
        "provider": STATE["api_provider"],
        "label_distribution": df["label"].value_counts().to_dict(),
    }


@app.post("/api/cluster")
def cluster():
    if STATE["embeddings"] is None:
        raise HTTPException(400, "Process embeddings first")
    embeddings = STATE["embeddings"]
    n = embeddings.shape[0]
    perplexity = min(30, max(2, n // 3))
    tsne = TSNE(n_components=3, random_state=0, perplexity=perplexity, init="pca")
    coords = tsne.fit_transform(embeddings)
    STATE["tsne_coords"] = coords
    df = STATE["df"]
    points = [
        {
            "x": float(coords[i, 0]),
            "y": float(coords[i, 1]),
            "z": float(coords[i, 2]),
            "label": str(df["label"].iloc[i]),
            "text": str(df["text"].iloc[i])[:160],
        }
        for i in range(n)
    ]
    return {
        "points": points,
        "total_clusters": int(df["label"].nunique()),
        "data_points": n,
        "original_dim": int(embeddings.shape[1]),
    }


@app.post("/api/train")
def train():
    if STATE["embeddings"] is None:
        raise HTTPException(400, "Process embeddings first")
    X = STATE["embeddings"]
    y = STATE["encoded_labels"]
    train_x, test_x, train_y, test_y = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler = StandardScaler()
    train_x = scaler.fit_transform(train_x)
    test_x = scaler.transform(test_x)
    STATE["scaler"] = scaler

    clf = LogisticRegression(random_state=0, max_iter=1000)
    clf.fit(train_x, train_y)
    STATE["clf"] = clf

    train_acc = clf.score(train_x, train_y)
    test_acc = clf.score(test_x, test_y)

    # Per-class metrics for a nice bar chart
    classes = STATE["label_encoder"].classes_
    proba_test = clf.predict_proba(test_x)
    preds_test = clf.predict(test_x)
    per_class = []
    for idx, cls in enumerate(classes):
        mask = test_y == idx
        support = int(mask.sum())
        if support == 0:
            continue
        acc = float((preds_test[mask] == idx).mean())
        per_class.append({"label": str(cls), "accuracy": acc, "support": support})

    STATE["model_metrics"] = {
        "training_accuracy": float(train_acc),
        "test_accuracy": float(test_acc),
        "total_classes": int(len(classes)),
        "per_class": per_class,
    }
    return STATE["model_metrics"]


@app.post("/api/diagnose")
def diagnose(req: DiagnoseRequest):
    if STATE["clf"] is None:
        raise HTTPException(400, "Train the model first")
    if not req.symptoms.strip():
        raise HTTPException(400, "Symptoms text is required")

    embedding = _embed([req.symptoms], fit=False)
    embedding_scaled = STATE["scaler"].transform(embedding)

    clf = STATE["clf"]
    pred_encoded = clf.predict(embedding_scaled)[0]
    prediction = STATE["label_encoder"].inverse_transform([pred_encoded])[0]

    proba = clf.predict_proba(embedding_scaled)[0]
    confidence = float(np.max(proba))
    classes = STATE["label_encoder"].classes_
    top_predictions = sorted(
        [{"label": str(c), "probability": float(p)} for c, p in zip(classes, proba)],
        key=lambda x: x["probability"],
        reverse=True,
    )[:5]

    medical_info = get_medical_info(str(prediction))

    entry = {
        "input_text": req.symptoms,
        "prediction": str(prediction),
        "confidence": confidence,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "color": _get_confidence_color(confidence * 100),
    }
    STATE["search_history"].append(entry)

    return {
        "diagnosis": str(prediction),
        "confidence": confidence,
        "confidence_color": entry["color"],
        "top_predictions": top_predictions,
        "medical_info": medical_info,
    }


@app.get("/api/history")
def history():
    return {"history": STATE["search_history"]}


@app.delete("/api/history")
def clear_history():
    STATE["search_history"] = []
    return {"cleared": True}


@app.get("/api/history/analysis")
def history_analysis():
    if not STATE["search_history"]:
        return {"analysis": []}
    df = pd.DataFrame(STATE["search_history"])
    t = STATE["confidence_thresholds"]
    analysis = []
    for condition in df["prediction"].unique():
        sub = df[df["prediction"] == condition]
        pct = sub["confidence"] * 100
        green = int((pct >= t["green"][0]).sum())
        amber = int(((pct >= t["amber"][0]) & (pct < t["green"][0])).sum())
        red = int((pct < t["amber"][0]).sum())
        total = len(sub)
        analysis.append(
            {
                "condition": condition,
                "green_pct": round(green / total * 100, 1) if total else 0,
                "amber_pct": round(amber / total * 100, 1) if total else 0,
                "red_pct": round(red / total * 100, 1) if total else 0,
                "count": total,
                "avg_confidence": round(float(sub["confidence"].mean()) * 100, 1),
            }
        )
    return {"analysis": analysis}


@app.get("/api/thresholds")
def get_thresholds():
    return STATE["confidence_thresholds"]


@app.put("/api/thresholds")
def set_thresholds(req: ThresholdRequest):
    STATE["confidence_thresholds"] = {"green": req.green, "amber": req.amber, "red": req.red}
    return STATE["confidence_thresholds"]


# ----------------------------------------------------------------------------
# Dynamic Pricing Corridor routes (aircraft parts pricing dashboard)
# ----------------------------------------------------------------------------
@app.get("/api/pricing/filters")
def pricing_filters():
    return pricing_corridor.get_filter_options()


@app.get("/api/pricing/kpis")
def pricing_kpis(
    part_class: Optional[List[str]] = Query(None),
    condition: Optional[List[str]] = Query(None),
    year: Optional[List[int]] = Query(None),
    part_number: Optional[List[str]] = Query(None),
):
    return pricing_corridor.get_kpis(part_class=part_class, condition=condition, year=year, part_number=part_number)


@app.get("/api/pricing/scatter")
def pricing_scatter(
    part_class: Optional[List[str]] = Query(None),
    condition: Optional[List[str]] = Query(None),
    year: Optional[List[int]] = Query(None),
    part_number: Optional[List[str]] = Query(None),
):
    return pricing_corridor.get_scatter_data(part_class=part_class, condition=condition, year=year, part_number=part_number)


@app.get("/api/pricing/table")
def pricing_table(
    part_class: Optional[List[str]] = Query(None),
    condition: Optional[List[str]] = Query(None),
    year: Optional[List[int]] = Query(None),
    part_number: Optional[List[str]] = Query(None),
):
    return pricing_corridor.get_corridor_table(part_class=part_class, condition=condition, year=year, part_number=part_number)


@app.get("/api/pricing/trend")
def pricing_trend(
    part_class: Optional[List[str]] = Query(None),
    condition: Optional[List[str]] = Query(None),
    year: Optional[List[int]] = Query(None),
    part_number: Optional[List[str]] = Query(None),
):
    return pricing_corridor.get_trend_data(part_class=part_class, condition=condition, year=year, part_number=part_number)


@app.get("/api/pricing/yearly-bar")
def pricing_yearly_bar(
    part_class: Optional[List[str]] = Query(None),
    condition: Optional[List[str]] = Query(None),
    year: Optional[List[int]] = Query(None),
    part_number: Optional[List[str]] = Query(None),
):
    return pricing_corridor.get_yearly_bar(part_class=part_class, condition=condition, year=year, part_number=part_number)


@app.get("/api/pricing/class-pie")
def pricing_class_pie(
    part_class: Optional[List[str]] = Query(None),
    condition: Optional[List[str]] = Query(None),
    year: Optional[List[int]] = Query(None),
    part_number: Optional[List[str]] = Query(None),
):
    return pricing_corridor.get_class_pie(part_class=part_class, condition=condition, year=year, part_number=part_number)


@app.post("/api/reset")
def reset():
    STATE.update(
        {
            "df": None,
            "embeddings": None,
            "encoded_labels": None,
            "label_encoder": LabelEncoder(),
            "vectorizer": None,
            "svd": None,
            "tsne_coords": None,
            "scaler": None,
            "clf": None,
            "model_metrics": {},
            "search_history": [],
        }
    )
    return {"reset": True}
