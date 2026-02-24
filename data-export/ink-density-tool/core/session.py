"""JSON session save/load for JobConfig."""
from __future__ import annotations

import json
from pathlib import Path

from core.models import JobConfig, ShapeData, WeightData


def _weight_to_dict(w: WeightData) -> dict:
    return {
        "label": w.label,
        "density": w.density,
        "steps": w.steps,
    }


def _shape_to_dict(s: ShapeData) -> dict:
    return {
        "name": s.name,
        "weights": [_weight_to_dict(w) for w in s.weights],
    }


def job_to_dict(job: JobConfig) -> dict:
    return {
        "customer": job.customer,
        "print_type": job.print_type,
        "stock_desc": job.stock_desc,
        "finish": job.finish,
        "dot_shape_type": job.dot_shape_type,
        "dot_shape_number": job.dot_shape_number,
        "date": job.date,
        "weight_labels": job.weight_labels,
        "step_labels": job.step_labels,
        "colour_names": job.colour_names,
        "shapes": [_shape_to_dict(s) for s in job.shapes],
    }


def _pad_or_trim(lst: list[float], length: int) -> list[float]:
    """Ensure list has exactly `length` elements, padding with 0.0 or trimming."""
    if len(lst) < length:
        return lst + [0.0] * (length - len(lst))
    return lst[:length]


def _weight_from_dict(d: dict) -> WeightData:
    raw_density = [float(v) for v in d.get("density", [0.0, 0.0, 0.0, 0.0])]
    density = _pad_or_trim(raw_density, 4)
    raw_steps = d.get("steps", [])
    steps = [
        _pad_or_trim([float(v) for v in row], 4) if row else [0.0, 0.0, 0.0, 0.0]
        for row in raw_steps
    ]
    if not steps:
        steps = [[0.0, 0.0, 0.0, 0.0]]
    return WeightData(label=d.get("label", ""), density=density, steps=steps)


def _shape_from_dict(d: dict) -> ShapeData:
    return ShapeData(
        name=d.get("name", ""),
        weights=[_weight_from_dict(w) for w in d.get("weights", [])],
    )


def job_from_dict(d: dict) -> JobConfig:
    return JobConfig(
        customer=d.get("customer", ""),
        print_type=d.get("print_type", "CRS"),
        stock_desc=d.get("stock_desc", ""),
        finish=d.get("finish", "RP"),
        dot_shape_type=d.get("dot_shape_type", "CRS"),
        dot_shape_number=d.get("dot_shape_number", ""),
        date=d.get("date", ""),
        weight_labels=d.get("weight_labels", ["120#", "150#", "200#"]),
        step_labels=d.get("step_labels", [
            "100", "95", "90", "80", "70", "60", "50", "40", "30", "20", "10", "5", "3", "1"
        ]),
        colour_names=d.get("colour_names", ["C", "M", "Y", "K"]),
        shapes=[_shape_from_dict(s) for s in d.get("shapes", [])],
    )


def save_session(job: JobConfig, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(job_to_dict(job), f, indent=2)


def load_session(path: str | Path) -> JobConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return job_from_dict(data)
