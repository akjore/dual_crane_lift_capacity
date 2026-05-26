// Import required methods
/* global loadPyodide */ //Workaround for pyodide until imported here
import { populateCraneDropdown, setupMenu, updateInputs, updateResults, showLoadingOverlay, hideLoadingOverlay,
         enablePrintMode, disablePrintMode, setupYamlHandlers, setupUI, showVersion, setLoadingText } from "./ui.js";
import { initializePyodide, performCalcs, setPythonLogLevel } from "./api.js";
import { initializeChart, updateChart } from "./chart.js";
import { beginReport, addReportPage, finalizeReport } from "./pdf.js";
import { VALUE_FIELDS } from "./config.js";
import { log, setLogLevelJS } from "../logger.js";
import * as state from "./state.js";

let pyodide;

async function initialize() {
    showLoadingOverlay();

    showVersion();

    // Load Pyodide - required to run python code in browser
    setLoadingText("Initializing Python runtime ...");
    pyodide = await loadPyodide();

    // Initialize pyodide, and get the available crane curves
    const craneCurves = await initializePyodide(pyodide, (msg) => {
        setLoadingText(msg);
    });

    // Populate the select box with crane curves
    populateCraneDropdown(craneCurves);

    initializeChart();

    setupUI();
    registerEventListeners();

    hideLoadingOverlay();

    await handleCalculation();

    log.info("Ready.");
}

function registerEventListeners() {
    setupMenu(generatePdfWithCases);

    setupYamlHandlers(onYamlLoaded);

    // JS hook: add listener to form for any changes to input fields
    const form = document.getElementById("form_dualcranelift");
    form.addEventListener("change", handleFormChange);
}

async function handleFormChange(evnt) {
    updateStateFromEvent(evnt);

    // If user changes case, no need to recompute everything
    if (evnt.target.id === "case") {
        updateGUI();
        return;
    }

    await handleCalculation(evnt);
}

function updateStateFromEvent(evnt) {
    const id = evnt.target.id;
    const isSelect = evnt.target.tagName === "SELECT";
    const val = isSelect ? evnt.target.value : Number(evnt.target.value);

    // case selection
    if (id === "case") {
        state.setCaseIdx(Number(val));
        return;
    }

    const data = state.liftcasesJson?.[state.caseIdx];
    if (!data) { return };

    // generic value fields
    if (VALUE_FIELDS.includes(id)) {
        data[id].value = val;
    }

    // special cases
    switch (id) {
        case "crane_curve_a":
            data.crane_curve_a = val;
            data.crane_curve_b = val;
            break;

        case "cog":
            data.cog.value = val;
            data.cog_envelope.value[0] = data.cog.value - data.cog_offset_a.value;
            data.cog_envelope.value[1] = data.cog.value + data.cog_offset_b.value;
            break;

        case "cog_offset_a":
            data.cog_envelope.value[0] = data.cog.value - val;
            break;

        case "cog_offset_b":
            data.cog_envelope.value[1] = data.cog.value + val;
            break;
    }
}

async function handleCalculation(event) {
    await performCalcs(pyodide, event);
    updateGUI(event);
}

function updateGUI(evnt) {
    if (!evnt) {
        updateInputs();
    }
    updateResults();
    updateChart();
}

async function onYamlLoaded() {
    await handleCalculation();
}

async function generatePdfWithCases() {
    const element = document.querySelector(".container");

    // Preliminaries
    enablePrintMode();
    beginReport();

    // Print each page
    for (let i = 0; i < state.liftcasesJson.length; i++) {
        // Update GUI with the correct case
        state.setCaseIdx(i);

        updateGUI();

        // allow DOM + chart to update
        await new Promise(resolve => setTimeout(resolve, 50));

        await addReportPage(element);
    }

    finalizeReport();
    disablePrintMode();
}

window.setLogLevel = async function (level) {
    const VALID = ["DEBUG", "INFO", "WARNING", "ERROR"];

    if (!level) {
        log.info("[APP] Usage: setLogLevel(level)");
        log.info("[APP] Valid levels:", VALID);
        return;
    }

    const normalized = String(level).toUpperCase();

    if (VALID.indexOf(normalized) === -1) {
        log.warn("[APP] Invalid level:", level);
        log.info("[APP] Valid levels:", VALID);
        return;
    }

    setLogLevelJS(normalized);

    await setPythonLogLevel(pyodide, normalized);
};

initialize();
