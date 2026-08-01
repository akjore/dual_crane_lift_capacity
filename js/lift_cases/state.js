import { log } from "../logger.js";

// variables
export let liftcasesJson = [];
export let resultsJson = [];
export let caseIdx = 0;
export let casesJsonStr = null;
// Sample to get user going, and overridden if user uploads / drag 'n drops a new yaml file
export let casesYamlStr = `
cases:
  - case: Sample 1
    crane_curve_a: S7000.main.fixed_1.5
    crane_curve_b: S7000.main.fixed_1.5
    crane_radius_a: 50.0 m
    crane_radius_b: 50.0 m
    rigging_weight_a: 435 t
    rigging_weight_b: 360 t
    weight_uncertainty_factor: 1.03
    cog_uncertainty_factor: 1.02
    tilt_factor: 1.02
    lift_point_a: 43.230 m
    lift_point_b: 82.0 m
    weight: 9410 t
    float_a: 3.030 m
    # cog: 61.646 m
    cog: 62.750 m
    cog_envelope: [(62.750-2.000) m, (62.750+1.500) m]
`;

export function setCaseIdx(i) {
    caseIdx = i;
}

export function setCasesYamlStr(value) {
    if (value !== null && typeof value !== "string") {
        log.warn("setCasesYamlStr expected string/null, got:", value);
    }

    casesYamlStr = value;
}

export function setCasesJsonStr(value) {
    if (value !== null && typeof value !== "string") {
        log.warn("setCasesJsonStr expected string/null, got:", value);
    }

    casesJsonStr = value;
}

export function setResultsJson(newArray) {
    if (!Array.isArray(newArray)) {
        log.error("setResultsJson: expected array, got:", newArray);
        return;
    }

    resultsJson.length = 0;
    resultsJson.push(...newArray);
}

export function setLiftcasesJson(newArray) {
    if (!Array.isArray(newArray)) {
        log.error("setLiftcasesJson: expected array, got:", newArray);
        return;
    }

    // clear existing array
    liftcasesJson.length = 0;

    // replace contents
    liftcasesJson.push(...newArray);
}
