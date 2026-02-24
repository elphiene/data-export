/**
 * runner.jsx — Ink Density Tool ExtendScript template
 *
 * Python generates a filled copy of this file per dot shape, replacing the
 * two special tokens below before calling:
 *   Illustrator.exe /b <filled_script.jsx>
 *
 * Tokens replaced by Python:
 *   <<REPLACEMENTS_DICT>>  — injected as a complete JSX object literal:
 *                            { "<<CUSTOMER>>": "Andrew Kohn", "<<DATE>>": "24-02-2026", … }
 *                            Keys are the placeholder strings in the master .ai template.
 *                            Values are the actual job data.
 *   <<TEMPLATE_PATH>>      — absolute path to the master .ai template (forward slashes)
 *   <<OUTPUT_PDF>>         — absolute path where the PDF should be saved (forward slashes)
 *
 * ============================================================
 * ILLUSTRATOR TEMPLATE SETUP GUIDE
 * ============================================================
 * In the master .ai file, each variable text frame must contain
 * exactly one of the placeholder strings listed below as its ENTIRE content.
 *
 * Artboard: set to A4 (210 × 297 mm) so PDF exports at A4 size.
 *
 * Page-level (same on every page):
 *   <<CUSTOMER>>   Customer name          e.g. "Andrew Kohn"
 *   <<STOCK>>      Stock description      e.g. "CRS XPS CBW SP"
 *   <<CRS>>        CRS reference code     e.g. "CRS 502"
 *   <<DATE>>       Job date               e.g. "11-09-2019"
 *   <<SHAPE>>      Dot shape name         e.g. "HD 16"
 *
 * Per weight (W1=120#, W2=150#, W3=200#):
 *   <<W1_LABEL>>   Weight label           e.g. "120#"
 *   <<W1_DC>>      C max density          e.g. "2.11"
 *   <<W1_DM>>      M max density          e.g. "1.80"
 *   <<W1_DY>>      Y max density          e.g. "1.66"
 *   <<W1_DK>>      K max density          e.g. "1.79"
 *
 * Per weight, per step (R01=100%, R02=95% … R14=1%, R15=0.8%, R16=0.4%):
 *   <<W1_R01_C>>  through  <<W3_R16_K>>
 *
 * Total variable text frames — 14-step job: 5 + (3 × 5) + (3 × 14 × 4) = 188
 * Total variable text frames — 16-step job: 5 + (3 × 5) + (3 × 16 × 4) = 212
 * ============================================================
 */

#target illustrator

(function () {

    // ---------------------------------------------------------------------------
    // 1. Open the master template as a new document (non-destructive)
    // ---------------------------------------------------------------------------
    var templateFile = new File("<<TEMPLATE_PATH>>");
    if (!templateFile.exists) {
        throw new Error("Template file not found: <<TEMPLATE_PATH>>");
    }

    var doc = app.open(templateFile);

    // ---------------------------------------------------------------------------
    // 2. Replacement dictionary — generated and injected by Python.
    //    Keys are the placeholder strings in the template text frames.
    //    Values are the actual job data for this export.
    // ---------------------------------------------------------------------------
    var replacements = <<REPLACEMENTS_DICT>>;

    // ---------------------------------------------------------------------------
    // 3. Walk all text frames and replace placeholder text
    // ---------------------------------------------------------------------------
    var items = doc.textFrames;
    for (var i = 0; i < items.length; i++) {
        var tf = items[i];
        var content = tf.contents;
        for (var key in replacements) {
            if (replacements.hasOwnProperty(key)) {
                if (content.indexOf(key) !== -1) {
                    tf.contents = content.split(key).join(replacements[key]);
                    content = tf.contents; // refresh after replace
                }
            }
        }
    }

    // ---------------------------------------------------------------------------
    // 4. Export as PDF
    // ---------------------------------------------------------------------------
    var pdfFile = new File("<<OUTPUT_PDF>>");
    var pdfOptions = new PDFSaveOptions();
    pdfOptions.pDFPreset = "[PDF/X-4:2008]"; // adjust preset as needed
    pdfOptions.useArtboardFrame = true;       // export at artboard size (A4)

    doc.saveAs(pdfFile, pdfOptions);

    // ---------------------------------------------------------------------------
    // 5. Close without saving the .ai document
    // ---------------------------------------------------------------------------
    doc.close(SaveOptions.DONOTSAVECHANGES);

})();
