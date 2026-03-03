//! Excel export using rust_xlsxwriter.
//!
//! Since rust_xlsxwriter creates new workbooks (can't modify templates like openpyxl),
//! we recreate the template structure programmatically. The layout matches the Python
//! export exactly.

use std::path::Path;

use anyhow::{Context, Result};
use rust_xlsxwriter::{Format, Workbook, Worksheet};

use crate::core::models::JobConfig;

/// Row where step data starts (first table, both sheet types)
const STEP_START_ROW_T1: u32 = 3; // 0-indexed (row 4 in Excel)
/// Gap (in rows) between the T1 label row and the T2 step-start row
const GAP_T1_TO_T2: u32 = 7;
/// CMYK data columns: B=1, C=2, D=3, E=4 (0-indexed)
const DATA_COLS: [u16; 4] = [1, 2, 3, 4];

fn row_constants(num_steps: u32) -> (u32, u32, u32) {
    let label_t1 = STEP_START_ROW_T1 + num_steps;
    let step_start_t2 = label_t1 + GAP_T1_TO_T2;
    let label_t2 = step_start_t2 + num_steps;
    (label_t1, step_start_t2, label_t2)
}

pub fn export_excel(job: &JobConfig, output_path: &Path) -> Result<()> {
    let num_steps = job.num_steps() as u32;
    let (label_t1, step_start_t2, label_t2) = row_constants(num_steps);

    let title = job.heading();
    let dot_shape = job.dot_shape();

    let mut workbook = Workbook::new();

    let header_fmt = Format::new().set_bold();
    let step_labels = &job.step_labels;

    for (shape_idx, shape) in job.shapes.iter().enumerate() {
        // --- Single-weight sheet: weight[0] ---
        let ws_name = if shape_idx == 0 {
            "Sheet1".to_string()
        } else {
            format!("Sheet{}", shape_idx * 2 + 1)
        };

        let ws = workbook.add_worksheet();
        ws.set_name(&ws_name)?;

        // Metadata
        ws.write_string_with_format(0, 0, &title, &header_fmt)?;
        ws.write_string(0, 8, &job.date)?;

        // Step labels in column A
        for (i, label) in step_labels.iter().enumerate() {
            ws.write_string(STEP_START_ROW_T1 + i as u32, 0, label)?;
        }

        if !shape.weights.is_empty() {
            let w0 = &shape.weights[0];
            write_steps(ws, &w0.steps, STEP_START_ROW_T1, num_steps)?;
            ws.write_string(label_t1, 0, &w0.label)?;
            ws.write_string(label_t1, 8, &dot_shape)?;
        }

        // --- Dual-weight sheet: weight[1] + weight[2] ---
        let ws_name2 = if shape_idx == 0 {
            "Sheet2".to_string()
        } else {
            format!("Sheet{}", shape_idx * 2 + 2)
        };

        let ws2 = workbook.add_worksheet();
        ws2.set_name(&ws_name2)?;

        ws2.write_string_with_format(0, 0, &title, &header_fmt)?;
        ws2.write_string(0, 8, &job.date)?;

        // Step labels for first table
        for (i, label) in step_labels.iter().enumerate() {
            ws2.write_string(STEP_START_ROW_T1 + i as u32, 0, label)?;
        }

        // weight[1] — first table
        if shape.weights.len() > 1 {
            let w1 = &shape.weights[1];
            write_steps(ws2, &w1.steps, STEP_START_ROW_T1, num_steps)?;
            ws2.write_string(label_t1, 0, &w1.label)?;
            ws2.write_string(label_t1, 8, &dot_shape)?;
        }

        // Step labels for second table
        for (i, label) in step_labels.iter().enumerate() {
            ws2.write_string(step_start_t2 + i as u32, 0, label)?;
        }

        // weight[2] — second table
        if shape.weights.len() > 2 {
            let w2 = &shape.weights[2];
            write_steps(ws2, &w2.steps, step_start_t2, num_steps)?;
            ws2.write_string(label_t2, 0, &w2.label)?;
            ws2.write_string(label_t2, 8, &dot_shape)?;

            // Fix second table formulas (F column)
            for i in 0..num_steps {
                let r = step_start_t2 + i;
                // 0-indexed: F = col 5, B = col 1, E = col 4
                let formula = format!(
                    "=SUM(B{}:E{})/4",
                    r + 1, // Excel 1-indexed for formula references
                    r + 1
                );
                ws2.write_formula(r, 5, rust_xlsxwriter::Formula::new(formula))?;
            }
        }
    }

    // Set up page layout for all sheets (A4, portrait, fit-to-width)
    // Note: rust_xlsxwriter handles this per-worksheet during creation

    if let Some(parent) = output_path.parent() {
        std::fs::create_dir_all(parent)
            .with_context(|| format!("Failed to create dir: {}", parent.display()))?;
    }

    workbook
        .save(output_path)
        .with_context(|| format!("Failed to save Excel: {}", output_path.display()))?;

    Ok(())
}

fn write_steps(
    ws: &mut Worksheet,
    steps: &[[f64; 4]],
    start_row: u32,
    num_steps: u32,
) -> Result<()> {
    for ri in 0..num_steps as usize {
        if ri >= steps.len() {
            break;
        }
        let row_data = &steps[ri];
        let excel_row = start_row + ri as u32;
        for (ci, &col) in DATA_COLS.iter().enumerate() {
            let value = if ci < 4 { row_data[ci] } else { 0.0 };
            if value != 0.0 {
                ws.write_number(excel_row, col, value)?;
            }
            // Write nothing (blank) for zero values so formulas read as empty
        }
    }
    Ok(())
}
