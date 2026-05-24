"use strict";

import { VERSION } from "../version.js";
import * as state from "./state.js";

export async function initializePyodide(pyodide) {
    // Set up pyodide, install and load packages, configure logging etc. for future use.

    // Load micropip - required to load non-standard packages
    await pyodide.loadPackage("micropip");
    const micropip = pyodide.pyimport("micropip");
    await micropip.install("requests");
    await micropip.install("simplejson");

    // Get the URL for package wheel, and install it
    const wheelUrl = getWheelUrl();
    await micropip.install(wheelUrl);

    // Get the URL for the crane curves, and make it available to pyodide
    const craneCurvesYml = await getCraneCurves();
    console.log(craneCurvesYml);
    pyodide.globals.set("crane_curves_yml", craneCurvesYml);

    // Configure logging to developer's console, and get crane curves
    await pyodide.runPythonAsync(`
        import logging
        import os
        import sys

        import requests
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
        #        response = requests.get("http://localhost:5000/static/crane_curves.yaml")
        # logger.debug("Raw crane curve content found: %s", response.content)

        # Path("/crane_curves.yaml").write_bytes(response.content)
        Path("/crane_curves.yaml").write_text(crane_curves_yml)
        os.environ["CRANE_CURVE_FILENAME"] = "/crane_curves.yaml"

        crane_curves = list(CraneCurves.crane_curve_ids())
        # logger.info("Crane curves found: %s", list(crane_curves))
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
            logger.debug(cases_json_str)
            liftcases = LiftCases().from_json(cases_json_str)
        liftcases_json = liftcases.to_json()

        # Calculate results
        dualcranelift = DualCraneLiftCapacity(liftcases)
        logger.debug("Produced python output: %s", dualcranelift)

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

    console.log("Liftcases returned from python:");
    console.log(state.liftcasesJson);

    console.log("Results returned from python:");
    console.log(state.resultsJson);
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
