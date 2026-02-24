from __future__ import annotations
from dataclasses import dataclass, field


STEP_LABELS_14: list[str] = [
    "100", "95", "90", "80", "70", "60", "50", "40", "30", "20", "10", "5", "3", "1"
]
STEP_LABELS_16: list[str] = STEP_LABELS_14 + ["0.8", "0.4"]

# Backward-compat alias
STEP_LABELS: list[str] = STEP_LABELS_14

COLOUR_NAMES: list[str] = ["C", "M", "Y", "K"]


@dataclass
class WeightData:
    label: str
    # 4 max-density readings: [C, M, Y, K]
    density: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    # [N rows][4 colours] — percentage readings at each step
    steps: list[list[float]] = field(
        default_factory=lambda: [[0.0, 0.0, 0.0, 0.0] for _ in range(len(STEP_LABELS_14))]
    )

    def __post_init__(self) -> None:
        if len(self.density) != 4:
            raise ValueError("density must have exactly 4 values (C, M, Y, K)")
        if len(self.steps) < 1:
            raise ValueError("steps must have at least 1 row")
        for row in self.steps:
            if len(row) != 4:
                raise ValueError("each step row must have exactly 4 values (C, M, Y, K)")


@dataclass
class ShapeData:
    name: str
    weights: list[WeightData] = field(default_factory=list)


@dataclass
class JobConfig:
    customer: str = ""
    print_type: str = "CRS"       # CRS or QUA
    stock_desc: str = ""          # free text, e.g. "XPS"
    finish: str = "RP"            # RP, SP, or CBW SP
    dot_shape_type: str = "CRS"   # CRS, CRY, HD, or ESXR
    dot_shape_number: str = ""    # e.g. "01", "502"
    date: str = ""
    weight_labels: list[str] = field(default_factory=lambda: ["120#", "150#", "200#"])
    step_labels: list[str] = field(default_factory=lambda: list(STEP_LABELS_14))
    colour_names: list[str] = field(default_factory=lambda: list(COLOUR_NAMES))
    shapes: list[ShapeData] = field(default_factory=list)
