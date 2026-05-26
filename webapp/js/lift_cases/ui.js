import feather from "https://cdn.jsdelivr.net/npm/feather-icons/+esm";

import { INPUT_FIELDS } from "./config.js";
import { VERSION } from "../version.js";
import { log } from "../logger.js";
import * as state from "./state.js";


// --------------- Show version ---------------
export function showVersion() {
    const el = document.getElementById("app-version");
    if (el) {
        el.textContent = `v${VERSION}`;
    }
}

// --------------- Crane curve select box ---------------
export function populateCraneDropdown(craneCurves) {
    const select = document.getElementById("crane_curve_a");

    craneCurves.forEach(curve => {
        const opt = document.createElement("option");
        opt.value = curve;
        opt.textContent = curve;
        select.appendChild(opt);
    });
}

// --------------- Setup ---------------
export function setupUI() {
    feather.replace();
    setupDetailsSection();
}

function setupDetailsSection() {
    const toggle = document.getElementById('detailsToggle');
    const section = document.getElementById('detailsSection');

    function toggleDetails() {
        const isHidden = section.hidden;
        section.hidden = !isHidden;
        toggle.classList.toggle('expanded', isHidden);
    }

    toggle.addEventListener('click', toggleDetails);

    toggle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            toggleDetails();
        }
    });
}

// --------------- Menu ---------------
// Setup menu
export function setupMenu(generateReport) {
    setupYamlMenu();
    setupDownloadReport(generateReport);
}

// Yaml-part of menu
function setupYamlMenu() {
    // Hooks for menu
    const btn = document.getElementById("yamlMenuBtn");
    const menu = document.getElementById("yamlMenu");

    btn.addEventListener("click", () => {
        menu.hidden = !menu.hidden;
    });

    //  close on click elsewhere
    document.addEventListener("click", (e) => {
        if (!btn.contains(e.target) && !menu.contains(e.target)) {
            menu.hidden = true;
        }
    });

    // Downloading the lift case input data as yaml
    document.getElementById("downloadYamlBtn").addEventListener("click", downloadYaml);

    // Downloading a sample for the user to modify
    document.getElementById("downloadSampleBtn").addEventListener("click", downloadSample);
}

// Report-part of menu
function setupDownloadReport(generateReport) {
    document
        .getElementById("downloadReportBtn")
        .addEventListener("click", generateReport);
}

// --------------- Upload yaml-file ---------------
export function setupYamlHandlers(onYamlLoaded) {
    // File upload / drag and drop drop zone
    const loadBtn   = document.getElementById('loadYamlBtn');
    const dropZone  = document.getElementById('loadYamlDropZone');
    const fileInput = document.getElementById('yamlFileInput');

    // Click: open file picker
    loadBtn.addEventListener('click', () => {
        fileInput.click();
    });

    // File chosen via picker
    fileInput.addEventListener('change', async () => {
        const file = fileInput.files[0];
        if (!file) { return };

        await handleYamlFile(file);
        await onYamlLoaded();

        fileInput.value = '';
    });

    // Drag & drop
    dropZone.addEventListener('dragover', e => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', async e => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');

        const file = e.dataTransfer.files[0];
        if (!file) { return };

        await handleYamlFile(file);
        await onYamlLoaded();   // ✅ now valid
    });
}

// Handle loading of yaml-file
export async function handleYamlFile(file) {
    if (!file.name.match(/\.ya?ml$/i)) {
        alert('Please select a .yaml or .yml file');
        return;
    }

    state.setCasesYamlStr(await file.text());
    state.setCasesJsonStr(null);
}

// --------------- Update inputs and result fields ---------------
function updateField(id, data) {
    // Update GUI
    const el = document.getElementById(id);

    if (!el) { return };

    if (!data || typeof data.value !== "number") {
        // clear input field
        el.value = "";
        return;
    }

    const decimals =
        el.classList.contains("distance") ||
        el.classList.contains("factor")
            ? 3 : 0;

    const value = data.value.toFixed(decimals);

    // update value - either input box or calculated field
    if (el.tagName === "SPAN") {
        el.textContent = value;
    } else {
        el.value = value;
    };

    // update unit
    const unitEl = document.getElementById(id + "_unit");
    if (unitEl) {
        unitEl.textContent = data.unit;
    };
}

export function updateInputs() {
    // This lists the input html fields to be updated. Requires that the
    // JSON object with the lift cases uses the same field names.
    const data = state.liftcasesJson[state.caseIdx];

    INPUT_FIELDS.forEach(f => updateField(f, data[f]));

    // Populate case dropdown box and select based on caseIdx
    let select = document.getElementById("case");
    select.innerHTML = "";
    state.liftcasesJson.forEach((c, i) => {
        const opt = document.createElement("option");
        opt.textContent = c.case;
        opt.value = i;
        select.appendChild(opt);
    });
    select.value = state.caseIdx;

    // Select crane curve
    select = document.getElementById("crane_curve_a");
    select.value = data.crane_curve_a;
}

export function updateResults() {
    // This lists the html fields to be updated. Requires that the
    // JSON object with the results uses the same field names.
    const resultFields = [
        "spare_capacity_a",
        "spare_capacity_b",
        "factored_lift_weight",
        "weight_margin",
        "combined_rigging_weight",
        "true_hookload_a_with_cog_offset_towards_a",
        "true_hookload_a_with_cog_offset_towards_b",
        "true_hookload_b_with_cog_offset_towards_a",
        "true_hookload_b_with_cog_offset_towards_b",
        "factored_hookload_a_with_cog_offset_towards_a",
        "factored_hookload_a_with_cog_offset_towards_b",
        "factored_hookload_b_with_cog_offset_towards_a",
        "factored_hookload_b_with_cog_offset_towards_b",
        "combined_true_hookload_cog_offset_towards_a",
        "combined_true_hookload_cog_offset_towards_b",
        "combined_factored_hookload_cog_offset_towards_a",
        "combined_factored_hookload_cog_offset_towards_b",
        "distance_lift_point_a_to_cog",
        "distance_lift_point_b_to_cog",
        "distance_lift_point_a_to_cog_offset_towards_a",
        "distance_lift_point_b_to_cog_offset_towards_a",
        "distance_lift_point_a_to_cog_offset_towards_b",
        "distance_lift_point_b_to_cog_offset_towards_b",
        "distance_lift_point_a_to_lift_point_b",
    ];

    const data = state.resultsJson[state.caseIdx];

    resultFields.forEach(f => updateField(f, data[f]));

    // Handle special cases
    updateField("distance_coga_ab", data.distance_lift_point_a_to_lift_point_b);
    updateField("distance_cogb_ab", data.distance_lift_point_a_to_lift_point_b);

    updateField("crane_capacity_a", state.liftcasesJson[state.caseIdx].crane_capacity_a);
    updateField("crane_capacity_b", state.liftcasesJson[state.caseIdx].crane_capacity_b);

    // Set module weight margin background colour according to value (positive, negative)
    let elmn = document.getElementById("weight_margin");
    elmn.classList.add('weight_margin', 'computed');

    const isPositive = data.weight_margin.value >= 0;
    elmn.classList.toggle('weight_margin--positive', isPositive);
    elmn.classList.toggle('weight_margin--negative', !isPositive);
}

// --------------- Provide user with a sample ---------------
export function downloadSample() {
    const url = "data/sample.yaml";

    log.info("Downloading sample YAML");

    // Trigger browser download
    const a = document.createElement("a");
    a.href = url;
    a.download = "sample.yaml";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// --------------- Download copy of lift cases as yaml ---------------
export function downloadYaml() {
    const yaml = buildYaml(state.liftcasesJson);

    const blob = new Blob([yaml], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "liftcases.yaml";
    a.click();

    URL.revokeObjectURL(url);
}

function buildYaml(cases) {
    let lines = [];
    lines.push("cases:");

    cases.forEach(c => {
        lines.push(`  - case: ${c.case}`);

        // simple fields
        lines.push(`    crane_curve_a: ${c.crane_curve_a}`);
        lines.push(`    crane_curve_b: ${c.crane_curve_b}`);

        // quantities
        addQuantity(lines, "crane_radius_a", c.crane_radius_a);
        addQuantity(lines, "crane_radius_b", c.crane_radius_b);
        addQuantity(lines, "rigging_weight_a", c.rigging_weight_a);
        addQuantity(lines, "rigging_weight_b", c.rigging_weight_b);
        addQuantity(lines, "lift_point_a", c.lift_point_a);
        addQuantity(lines, "lift_point_b", c.lift_point_b);
        addQuantity(lines, "weight", c.weight);
        addQuantity(lines, "cog", c.cog);

        // floats
        addQuantityOptional(lines, "float_a", c.float_a);
        addQuantityOptional(lines, "float_b", c.float_b);

        // factors (dimensionless)
        addScalar(lines, "weight_uncertainty_factor", c.weight_uncertainty_factor);
        addScalar(lines, "cog_uncertainty_factor", c.cog_uncertainty_factor);
        addScalar(lines, "tilt_factor", c.tilt_factor);

        // envelope
        if (c.cog_envelope?.value) {
            const [min, max] = c.cog_envelope.value;

            if (min !== null && max !== null) {
                lines.push(
                    `    cog_envelope: [${min} ${c.cog_envelope.unit}, ${max} ${c.cog_envelope.unit}]`
                );
            }
        }
    });

    return lines.join("\n");
}

//      Helper functions
function addQuantity(lines, name, q) {
    if (!q) { return };
    lines.push(`    ${name}: ${q.value} ${q.unit}`);
}

function addQuantityOptional(lines, name, q) {
    if (!q || q.value === null) { return };
    lines.push(`    ${name}: ${q.value} ${q.unit}`);
}

function addScalar(lines, name, q) {
    if (!q) { return };
    lines.push(`    ${name}: ${q.value}`);
}

// --------------- Misc helper functions ---------------
export function enablePrintMode() {
    document.body.classList.add("print-mode");
}

export function disablePrintMode() {
    document.body.classList.remove("print-mode");
}

// --------------- Loading overlay ---------------
export function setLoadingText(text) {
    const el = document.getElementById("loadingText");
    if (el) { el.textContent = text };
}

export function showLoadingOverlay() {
    const el = document.getElementById("loadingOverlay");
    if (!el) { return };

    requestAnimationFrame(() => {
        el.classList.add("active");
    });
}

export function hideLoadingOverlay() {
    const el = document.getElementById("loadingOverlay");
    if (!el) { return };

    el.classList.remove("active");

    setTimeout(() => {
    }, 300);
}
