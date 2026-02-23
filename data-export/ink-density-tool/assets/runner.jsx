/**
 * runner.jsx — Ink Density Tool ExtendScript template
 *
 * Python generates a filled copy of this file per dot shape, replacing every
 * <<PLACEHOLDER>> with a real value before calling:
 *   Illustrator.exe /b <filled_script.jsx>
 *
 * Special tokens replaced by Python (not data placeholders):
 *   <<TEMPLATE_PATH>>   — absolute path to the master .ai template
 *   <<OUTPUT_PDF>>      — absolute path where the PDF should be saved
 *
 * Data placeholders replaced by Python before the script runs — all of the
 * <<CUSTOMER>>, <<W1_R01_C>>, etc. tokens below are already substituted by
 * the time Illustrator sees this file.
 *
 * ============================================================
 * ILLUSTRATOR TEMPLATE SETUP GUIDE
 * ============================================================
 * In the master .ai file, each variable text frame must contain
 * exactly one of the placeholder strings below as its content.
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
    // 2. Build the replacement dictionary
    //    All values are pre-substituted by Python; this object is just a map
    //    of what is still in the document as placeholder text.
    // ---------------------------------------------------------------------------
    var replacements = {
        // Metadata
        "<<CUSTOMER>>": "<<CUSTOMER>>",
        "<<STOCK>>":    "<<STOCK>>",
        "<<CRS>>":      "<<CRS>>",
        "<<DATE>>":     "<<DATE>>",
        "<<SHAPE>>":    "<<SHAPE>>",

        // Weight labels
        "<<W1_LABEL>>": "<<W1_LABEL>>",
        "<<W2_LABEL>>": "<<W2_LABEL>>",
        "<<W3_LABEL>>": "<<W3_LABEL>>",

        // Density rows
        "<<W1_DC>>": "<<W1_DC>>", "<<W1_DM>>": "<<W1_DM>>", "<<W1_DY>>": "<<W1_DY>>", "<<W1_DK>>": "<<W1_DK>>",
        "<<W2_DC>>": "<<W2_DC>>", "<<W2_DM>>": "<<W2_DM>>", "<<W2_DY>>": "<<W2_DY>>", "<<W2_DK>>": "<<W2_DK>>",
        "<<W3_DC>>": "<<W3_DC>>", "<<W3_DM>>": "<<W3_DM>>", "<<W3_DY>>": "<<W3_DY>>", "<<W3_DK>>": "<<W3_DK>>",

        // Step rows W1 R01–R16
        "<<W1_R01_C>>": "<<W1_R01_C>>", "<<W1_R01_M>>": "<<W1_R01_M>>", "<<W1_R01_Y>>": "<<W1_R01_Y>>", "<<W1_R01_K>>": "<<W1_R01_K>>",
        "<<W1_R02_C>>": "<<W1_R02_C>>", "<<W1_R02_M>>": "<<W1_R02_M>>", "<<W1_R02_Y>>": "<<W1_R02_Y>>", "<<W1_R02_K>>": "<<W1_R02_K>>",
        "<<W1_R03_C>>": "<<W1_R03_C>>", "<<W1_R03_M>>": "<<W1_R03_M>>", "<<W1_R03_Y>>": "<<W1_R03_Y>>", "<<W1_R03_K>>": "<<W1_R03_K>>",
        "<<W1_R04_C>>": "<<W1_R04_C>>", "<<W1_R04_M>>": "<<W1_R04_M>>", "<<W1_R04_Y>>": "<<W1_R04_Y>>", "<<W1_R04_K>>": "<<W1_R04_K>>",
        "<<W1_R05_C>>": "<<W1_R05_C>>", "<<W1_R05_M>>": "<<W1_R05_M>>", "<<W1_R05_Y>>": "<<W1_R05_Y>>", "<<W1_R05_K>>": "<<W1_R05_K>>",
        "<<W1_R06_C>>": "<<W1_R06_C>>", "<<W1_R06_M>>": "<<W1_R06_M>>", "<<W1_R06_Y>>": "<<W1_R06_Y>>", "<<W1_R06_K>>": "<<W1_R06_K>>",
        "<<W1_R07_C>>": "<<W1_R07_C>>", "<<W1_R07_M>>": "<<W1_R07_M>>", "<<W1_R07_Y>>": "<<W1_R07_Y>>", "<<W1_R07_K>>": "<<W1_R07_K>>",
        "<<W1_R08_C>>": "<<W1_R08_C>>", "<<W1_R08_M>>": "<<W1_R08_M>>", "<<W1_R08_Y>>": "<<W1_R08_Y>>", "<<W1_R08_K>>": "<<W1_R08_K>>",
        "<<W1_R09_C>>": "<<W1_R09_C>>", "<<W1_R09_M>>": "<<W1_R09_M>>", "<<W1_R09_Y>>": "<<W1_R09_Y>>", "<<W1_R09_K>>": "<<W1_R09_K>>",
        "<<W1_R10_C>>": "<<W1_R10_C>>", "<<W1_R10_M>>": "<<W1_R10_M>>", "<<W1_R10_Y>>": "<<W1_R10_Y>>", "<<W1_R10_K>>": "<<W1_R10_K>>",
        "<<W1_R11_C>>": "<<W1_R11_C>>", "<<W1_R11_M>>": "<<W1_R11_M>>", "<<W1_R11_Y>>": "<<W1_R11_Y>>", "<<W1_R11_K>>": "<<W1_R11_K>>",
        "<<W1_R12_C>>": "<<W1_R12_C>>", "<<W1_R12_M>>": "<<W1_R12_M>>", "<<W1_R12_Y>>": "<<W1_R12_Y>>", "<<W1_R12_K>>": "<<W1_R12_K>>",
        "<<W1_R13_C>>": "<<W1_R13_C>>", "<<W1_R13_M>>": "<<W1_R13_M>>", "<<W1_R13_Y>>": "<<W1_R13_Y>>", "<<W1_R13_K>>": "<<W1_R13_K>>",
        "<<W1_R14_C>>": "<<W1_R14_C>>", "<<W1_R14_M>>": "<<W1_R14_M>>", "<<W1_R14_Y>>": "<<W1_R14_Y>>", "<<W1_R14_K>>": "<<W1_R14_K>>",
        "<<W1_R15_C>>": "<<W1_R15_C>>", "<<W1_R15_M>>": "<<W1_R15_M>>", "<<W1_R15_Y>>": "<<W1_R15_Y>>", "<<W1_R15_K>>": "<<W1_R15_K>>",
        "<<W1_R16_C>>": "<<W1_R16_C>>", "<<W1_R16_M>>": "<<W1_R16_M>>", "<<W1_R16_Y>>": "<<W1_R16_Y>>", "<<W1_R16_K>>": "<<W1_R16_K>>",

        // Step rows W2 R01–R16
        "<<W2_R01_C>>": "<<W2_R01_C>>", "<<W2_R01_M>>": "<<W2_R01_M>>", "<<W2_R01_Y>>": "<<W2_R01_Y>>", "<<W2_R01_K>>": "<<W2_R01_K>>",
        "<<W2_R02_C>>": "<<W2_R02_C>>", "<<W2_R02_M>>": "<<W2_R02_M>>", "<<W2_R02_Y>>": "<<W2_R02_Y>>", "<<W2_R02_K>>": "<<W2_R02_K>>",
        "<<W2_R03_C>>": "<<W2_R03_C>>", "<<W2_R03_M>>": "<<W2_R03_M>>", "<<W2_R03_Y>>": "<<W2_R03_Y>>", "<<W2_R03_K>>": "<<W2_R03_K>>",
        "<<W2_R04_C>>": "<<W2_R04_C>>", "<<W2_R04_M>>": "<<W2_R04_M>>", "<<W2_R04_Y>>": "<<W2_R04_Y>>", "<<W2_R04_K>>": "<<W2_R04_K>>",
        "<<W2_R05_C>>": "<<W2_R05_C>>", "<<W2_R05_M>>": "<<W2_R05_M>>", "<<W2_R05_Y>>": "<<W2_R05_Y>>", "<<W2_R05_K>>": "<<W2_R05_K>>",
        "<<W2_R06_C>>": "<<W2_R06_C>>", "<<W2_R06_M>>": "<<W2_R06_M>>", "<<W2_R06_Y>>": "<<W2_R06_Y>>", "<<W2_R06_K>>": "<<W2_R06_K>>",
        "<<W2_R07_C>>": "<<W2_R07_C>>", "<<W2_R07_M>>": "<<W2_R07_M>>", "<<W2_R07_Y>>": "<<W2_R07_Y>>", "<<W2_R07_K>>": "<<W2_R07_K>>",
        "<<W2_R08_C>>": "<<W2_R08_C>>", "<<W2_R08_M>>": "<<W2_R08_M>>", "<<W2_R08_Y>>": "<<W2_R08_Y>>", "<<W2_R08_K>>": "<<W2_R08_K>>",
        "<<W2_R09_C>>": "<<W2_R09_C>>", "<<W2_R09_M>>": "<<W2_R09_M>>", "<<W2_R09_Y>>": "<<W2_R09_Y>>", "<<W2_R09_K>>": "<<W2_R09_K>>",
        "<<W2_R10_C>>": "<<W2_R10_C>>", "<<W2_R10_M>>": "<<W2_R10_M>>", "<<W2_R10_Y>>": "<<W2_R10_Y>>", "<<W2_R10_K>>": "<<W2_R10_K>>",
        "<<W2_R11_C>>": "<<W2_R11_C>>", "<<W2_R11_M>>": "<<W2_R11_M>>", "<<W2_R11_Y>>": "<<W2_R11_Y>>", "<<W2_R11_K>>": "<<W2_R11_K>>",
        "<<W2_R12_C>>": "<<W2_R12_C>>", "<<W2_R12_M>>": "<<W2_R12_M>>", "<<W2_R12_Y>>": "<<W2_R12_Y>>", "<<W2_R12_K>>": "<<W2_R12_K>>",
        "<<W2_R13_C>>": "<<W2_R13_C>>", "<<W2_R13_M>>": "<<W2_R13_M>>", "<<W2_R13_Y>>": "<<W2_R13_Y>>", "<<W2_R13_K>>": "<<W2_R13_K>>",
        "<<W2_R14_C>>": "<<W2_R14_C>>", "<<W2_R14_M>>": "<<W2_R14_M>>", "<<W2_R14_Y>>": "<<W2_R14_Y>>", "<<W2_R14_K>>": "<<W2_R14_K>>",
        "<<W2_R15_C>>": "<<W2_R15_C>>", "<<W2_R15_M>>": "<<W2_R15_M>>", "<<W2_R15_Y>>": "<<W2_R15_Y>>", "<<W2_R15_K>>": "<<W2_R15_K>>",
        "<<W2_R16_C>>": "<<W2_R16_C>>", "<<W2_R16_M>>": "<<W2_R16_M>>", "<<W2_R16_Y>>": "<<W2_R16_Y>>", "<<W2_R16_K>>": "<<W2_R16_K>>",

        // Step rows W3 R01–R16
        "<<W3_R01_C>>": "<<W3_R01_C>>", "<<W3_R01_M>>": "<<W3_R01_M>>", "<<W3_R01_Y>>": "<<W3_R01_Y>>", "<<W3_R01_K>>": "<<W3_R01_K>>",
        "<<W3_R02_C>>": "<<W3_R02_C>>", "<<W3_R02_M>>": "<<W3_R02_M>>", "<<W3_R02_Y>>": "<<W3_R02_Y>>", "<<W3_R02_K>>": "<<W3_R02_K>>",
        "<<W3_R03_C>>": "<<W3_R03_C>>", "<<W3_R03_M>>": "<<W3_R03_M>>", "<<W3_R03_Y>>": "<<W3_R03_Y>>", "<<W3_R03_K>>": "<<W3_R03_K>>",
        "<<W3_R04_C>>": "<<W3_R04_C>>", "<<W3_R04_M>>": "<<W3_R04_M>>", "<<W3_R04_Y>>": "<<W3_R04_Y>>", "<<W3_R04_K>>": "<<W3_R04_K>>",
        "<<W3_R05_C>>": "<<W3_R05_C>>", "<<W3_R05_M>>": "<<W3_R05_M>>", "<<W3_R05_Y>>": "<<W3_R05_Y>>", "<<W3_R05_K>>": "<<W3_R05_K>>",
        "<<W3_R06_C>>": "<<W3_R06_C>>", "<<W3_R06_M>>": "<<W3_R06_M>>", "<<W3_R06_Y>>": "<<W3_R06_Y>>", "<<W3_R06_K>>": "<<W3_R06_K>>",
        "<<W3_R07_C>>": "<<W3_R07_C>>", "<<W3_R07_M>>": "<<W3_R07_M>>", "<<W3_R07_Y>>": "<<W3_R07_Y>>", "<<W3_R07_K>>": "<<W3_R07_K>>",
        "<<W3_R08_C>>": "<<W3_R08_C>>", "<<W3_R08_M>>": "<<W3_R08_M>>", "<<W3_R08_Y>>": "<<W3_R08_Y>>", "<<W3_R08_K>>": "<<W3_R08_K>>",
        "<<W3_R09_C>>": "<<W3_R09_C>>", "<<W3_R09_M>>": "<<W3_R09_M>>", "<<W3_R09_Y>>": "<<W3_R09_Y>>", "<<W3_R09_K>>": "<<W3_R09_K>>",
        "<<W3_R10_C>>": "<<W3_R10_C>>", "<<W3_R10_M>>": "<<W3_R10_M>>", "<<W3_R10_Y>>": "<<W3_R10_Y>>", "<<W3_R10_K>>": "<<W3_R10_K>>",
        "<<W3_R11_C>>": "<<W3_R11_C>>", "<<W3_R11_M>>": "<<W3_R11_M>>", "<<W3_R11_Y>>": "<<W3_R11_Y>>", "<<W3_R11_K>>": "<<W3_R11_K>>",
        "<<W3_R12_C>>": "<<W3_R12_C>>", "<<W3_R12_M>>": "<<W3_R12_M>>", "<<W3_R12_Y>>": "<<W3_R12_Y>>", "<<W3_R12_K>>": "<<W3_R12_K>>",
        "<<W3_R13_C>>": "<<W3_R13_C>>", "<<W3_R13_M>>": "<<W3_R13_M>>", "<<W3_R13_Y>>": "<<W3_R13_Y>>", "<<W3_R13_K>>": "<<W3_R13_K>>",
        "<<W3_R14_C>>": "<<W3_R14_C>>", "<<W3_R14_M>>": "<<W3_R14_M>>", "<<W3_R14_Y>>": "<<W3_R14_Y>>", "<<W3_R14_K>>": "<<W3_R14_K>>",
        "<<W3_R15_C>>": "<<W3_R15_C>>", "<<W3_R15_M>>": "<<W3_R15_M>>", "<<W3_R15_Y>>": "<<W3_R15_Y>>", "<<W3_R15_K>>": "<<W3_R15_K>>",
        "<<W3_R16_C>>": "<<W3_R16_C>>", "<<W3_R16_M>>": "<<W3_R16_M>>", "<<W3_R16_Y>>": "<<W3_R16_Y>>", "<<W3_R16_K>>": "<<W3_R16_K>>"
    };

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
