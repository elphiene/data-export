use std::collections::HashMap;

use crate::core::models::{JobConfig, ShapeData, WeightData};

const COLOUR_SUFFIXES: &[&str] = &["C", "M", "Y", "K"];

/// Format a float for insertion into templates (strip trailing zeros, blank for 0).
pub fn fmt_value(v: f64) -> String {
    if v == 0.0 {
        return String::new();
    }
    // Equivalent to Python's f"{v:.4g}"
    let s = format!("{:.4}", v);
    // Trim trailing zeros after decimal point
    if s.contains('.') {
        let trimmed = s.trim_end_matches('0').trim_end_matches('.');
        // But if we trimmed everything, use the 4g-style format
        if trimmed.is_empty() || trimmed == "-" {
            String::new()
        } else {
            trimmed.to_string()
        }
    } else {
        s
    }
}

/// Build the <<PLACEHOLDER>> → value mapping for one chunk of weights.
pub fn build_placeholders(
    job: &JobConfig,
    shape: &ShapeData,
    chunk: &[&WeightData],
) -> HashMap<String, String> {
    let heading = job.heading();
    let dot_shape = job.dot_shape();

    let mut ph = HashMap::new();
    ph.insert("<<CUSTOMER>>".into(), heading);
    ph.insert("<<STOCK>>".into(), String::new());
    ph.insert("<<CRS>>".into(), dot_shape);
    ph.insert("<<DATE>>".into(), job.date.clone());
    ph.insert(
        "<<SET>>".into(),
        if job.set_number.is_empty() {
            String::new()
        } else {
            format!("SET {}", job.set_number)
        },
    );
    ph.insert(
        "<<JOB>>".into(),
        if job.job_number.is_empty() {
            String::new()
        } else {
            format!("JN {}", job.job_number)
        },
    );
    ph.insert("<<SHAPE>>".into(), shape.name.clone());

    for (wi, weight) in chunk.iter().enumerate() {
        let wn = wi + 1; // 1-indexed
        ph.insert(format!("<<W{wn}_LABEL>>"), weight.label.clone());

        // Density row
        for (ci, suffix) in COLOUR_SUFFIXES.iter().enumerate() {
            let val = if ci < 4 { weight.density[ci] } else { 0.0 };
            ph.insert(format!("<<W{wn}_D{suffix}>>"), fmt_value(val));
        }

        // Step rows (R01 … R16)
        for (ri, row) in weight.steps.iter().enumerate() {
            let rn = ri + 1;
            for (ci, suffix) in COLOUR_SUFFIXES.iter().enumerate() {
                let val = if ci < 4 { row[ci] } else { 0.0 };
                ph.insert(format!("<<W{wn}_R{rn:02}_{suffix}>>"), fmt_value(val));
            }
        }
    }

    ph
}

/// Split weights into groups of up to `size`.
pub fn chunk_weights(weights: &[WeightData], size: usize) -> Vec<Vec<&WeightData>> {
    weights.chunks(size).map(|c| c.iter().collect()).collect()
}
