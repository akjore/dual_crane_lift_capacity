import yaml from "https://cdn.jsdelivr.net/npm/js-yaml@4/+esm";
import { VERSION } from "../version.js";
import { log } from "../logger.js";
import * as state from "./state.js";

export async function initializePyodide(pyodide, onProgress) {
    // Set up pyodide, install and load packages, configure logging etc. for future use.

    // Load micropip - required to load non-standard packages
    if (onProgress) {onProgress("Initializing Python runtime ...")};
    await pyodide.loadPackage("micropip");
    const micropip = pyodide.pyimport("micropip");

    // Get the URL for package wheel, and install it
    if (onProgress) {onProgress("Installing application package ...")};
    const wheelUrl = getWheelUrl();
    await micropip.install(wheelUrl);

    // Get the crane curves, and make it available to pyodide
    if (onProgress) {onProgress("Loading crane curves ...")};
    const craneCurvesYml = await getCraneCurves();
    log.debug("Crane curves:", yaml.load(craneCurvesYml));
    pyodide.globals.set("crane_curves_yml", craneCurvesYml);

    // Configure logging to developer's console, and get crane curves
    if (onProgress) {onProgress("Preparing runtime environment ...")};
    await pyodide.runPythonAsync(`
        import logging
        import json
        import os
        import sys
        from pathlib import Path

        from dual_crane_lift_capacity.crane_curves import CraneCurves

        LOGGING_LEVEL = logging.DEBUG

        # Set up and configure logging
        logger = logging.getLogger(__name__)
        logger.setLevel(LOGGING_LEVEL)

        """
        Logging messages by default are sent to the developer console as stderr,
        and show up there as Warnings. Create a streamhandler that sends to stdout,
        and format the message to show level.
        """
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        logger.addHandler(console)

        # Get crane curves
        Path("/crane_curves.yaml").write_text(crane_curves_yml)
        os.environ["CRANE_CURVE_FILENAME"] = "/crane_curves.yaml"

        crane_curves = list(CraneCurves.crane_curve_ids())
    `);
    return pyodide.globals.get("crane_curves");
};

export async function runPython(pyodide) {
    // Share variables with pyodide
    pyodide.globals.set("cases_yaml_str", state.casesYamlStr);
    pyodide.globals.set("cases_json_str", state.casesJsonStr);

    // Perform calcs
    await pyodide.runPythonAsync(`
        from dual_crane_lift_capacity.lift_cases import LiftCases
        from dual_crane_lift_capacity.dual_crane_lift_capacity import DualCraneLiftCapacity

        # Create an input object
        if cases_yaml_str:
            logger.debug("Loading yaml")
            liftcases = LiftCases().from_yaml(cases_yaml_str)
        else:
            logger.debug("Loading json")
            liftcases = LiftCases().from_json(cases_json_str)
        liftcases_json = liftcases.to_json()

        # Calculate results
        dualcranelift = DualCraneLiftCapacity(liftcases)
        s = json.dumps(dualcranelift, default=str)
        logger.debug("Produced python output: %s", s)

        # Return input and results
        results_json = dualcranelift.to_json()
    `);
};

function extractResults(pyodide) {
    // Get the lift cases from python, create JSON object, and save to state
    let ret = JSON.parse(pyodide.globals.get("liftcases_json"));
    state.setLiftcasesJson(ret);

    // Get computed values from python, create a JSON object, and save to state
    ret = JSON.parse(pyodide.globals.get("results_json"));
    state.setResultsJson(ret);

    log.debug("Liftcases returned from python:", state.liftcasesJson);

    log.debug("Results returned from python:", state.resultsJson);
};

export async function performCalcs(pyodide, evnt) {
    // Function aquires either a serialised yaml file or a json object, performs the calculations, and returns results

    // Get the serialized yaml/json input describing the cases
    if (evnt && ["INPUT", "SELECT"].includes(evnt.target.tagName)) {
        // If an input box was modified, then process the json
        state.setCasesJsonStr(JSON.stringify(state.liftcasesJson));
        state.setCasesYamlStr(null);
    } else {
        // otherwise, process the yaml-string - null out JsonStr
        state.setCasesJsonStr(null);
    };

    // Run the python code
    await runPython(pyodide);

    // Populate the js variables with updated results
    extractResults(pyodide);
};

function getWheelUrl() {
    return `wheels/dual_crane_lift_capacity-${VERSION}-py3-none-any.whl`;
}

async function getCraneCurves() {
    const response = await fetch("data/crane_curves.yaml");

    if (!response.ok) {
        throw new Error("Failed to load crane curves");
    }

    return await response.text();
}

export async function setPythonLogLevel(pyodide, level) {
    try {
        pyodide.globals.set("log_level", level);

        await pyodide.runPythonAsync(`
            logger.info("Current log level is %s", logging.getLevelName(logger.getEffectiveLevel()))

            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
            }

            logger.setLevel(level_map.get(log_level, logging.WARNING))

            logger.info("Log level changed to %s", logging.getLevelName(logger.getEffectiveLevel()))
        `);
    } catch {
        log.warn("[APP] Failed to set Python log level");
    }
}
