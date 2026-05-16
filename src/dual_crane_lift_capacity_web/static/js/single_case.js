"use strict";

const VALUE_FIELDS = [
    "crane_radius_a",
    "crane_radius_b",
    "weight_uncertainty_factor",
    "cog_uncertainty_factor",
    "tilt_factor",
    "weight",
    "rigging_weight_a",
    "rigging_weight_b",
    "lift_point_a",
    "lift_point_b",
    "float_a",
    "float_b",
    "cog_offset_a",
    "cog_offset_b",
];

const INPUT_FIELDS = [...VALUE_FIELDS, "cog"];

const DATASET_MAP = [
    "crane_capacity_curve_pt1",
    "crane_capacity_curve_pt2",
    null,       // connector
    "cog",
    "cog_envelope",
    "cog_limit_at_given_weight",
    "lift_capacity_at_cog"
];

function updateGUI(evnt) {
    if (!evnt) {
        updateInputs();
    }
    updateResults();
    updateChart();
}

function updateField(id, data) {
    // Update GUI
    const el = document.getElementById(id);
    if (!el || !data || typeof data.value !== "number") return;

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

function updateInputs() {
    // This lists the input html fields to be updated. Requires that the JSON object with the lift cases uses the same field names.
    const data = liftcasesJson[caseIdx];

    INPUT_FIELDS.forEach(f => updateField(f, data[f]));

    // Populate case dropdown box and select based on caseIdx
    let select = document.getElementById("case");
    select.innerHTML = "";
    liftcasesJson.forEach((c, i) => {
        const opt = document.createElement("option");
        opt.textContent = c.case;
        opt.value = i;
        select.appendChild(opt);
    });
    select.value = caseIdx;

    // Select crane curve
    select = document.getElementById("crane_curve_a");
    select.value = data.crane_curve_a;
}

function updateResults() {
    // This list the html fields to be updated. Requires that the JSON object with the results uses the same field names.
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

    const data = resultsJson[caseIdx];

    resultFields.forEach(f => updateField(f, data[f]));

    // Handle special cases
    updateField("distance_coga_ab", data.distance_lift_point_a_to_lift_point_b);
    updateField("distance_cogb_ab", data.distance_lift_point_a_to_lift_point_b);

    updateField("crane_capacity_a", liftcasesJson[caseIdx].crane_capacity_a);
    updateField("crane_capacity_b", liftcasesJson[caseIdx].crane_capacity_b);

    // Set module weight margin background colour according to value (positive, negative)
    let elmn = document.getElementById("weight_margin");
    elmn.classList.add('weight_margin', 'computed');

    const isPositive = data.weight_margin.value >= 0;
    elmn.classList.toggle('weight_margin--positive', isPositive);
    elmn.classList.toggle('weight_margin--negative', !isPositive);
};

async function runPython() {
    // Perform calcs
    await pyodide.runPythonAsync(`
        import os

        import js
        import json
        import numpy as np

        import pint

        # from dual_crane_lift_capacity.dual_crane_lift import DualCraneLift
        from dual_crane_lift_capacity.lift_cases import LiftCases
        from dual_crane_lift_capacity.dual_crane_lift_capacity import DualCraneLiftCapacity

        # Create an input object
        if js.casesYamlStr:
            logger.debug("Loading yaml")
            liftcases = LiftCases().from_yaml(js.casesYamlStr)
        else:
            logger.debug("Loading json")
            logger.debug(js.casesJsonStr)
            liftcases = LiftCases().from_json(js.casesJsonStr)
        liftcases_json = liftcases.to_json()

        # Calculate results
        dualcranelift = DualCraneLiftCapacity(liftcases)
        logger.debug("Produced python output: %s", dualcranelift)

        # Return input and results
        results_json = dualcranelift.to_json()
    `);
};

function extractResults() {
    // Get the lift cases from python, create JSON object, and populate html page if required
    let ret = pyodide.globals.get("liftcases_json");
    if (ret) liftcasesJson = JSON.parse(ret);
    console.log("Lift cases returned from python:");
    console.log(liftcasesJson);

    // Get computed values from python, create a JSON object, and populate html page
    ret = pyodide.globals.get("results_json");
    if (ret) resultsJson = JSON.parse(ret);
    console.log("Results returned from python:");
    console.log(resultsJson);
};

async function performCalcs(evnt) {
    // Function aquires either a serialised yaml file or a json object, performs the calculations, and returns results

    // Get the serialized yaml/json input describing the cases
//    if(evnt && (evnt.target.tagName == "INPUT" || evnt.target.tagName == "SELECT")) {
    if (evnt && ["INPUT", "SELECT"].includes(evnt.target.tagName)) {
        // If an input box was modified, then process the json
        window.casesJsonStr = JSON.stringify(liftcasesJson);
        window.casesYamlStr = null;
    } else {
        // otherwise, process the yaml-string
        window.casesJsonStr = null;
        window.casesYamlStr = casesYamlStr;
    };

    // Run the python code
    await runPython();

    // Populate the js variables with updated results
    extractResults();

    // Update GUI with results
    updateGUI(evnt);
};

async function initialize() {
    // Set up pyodide, install and load packages, configure logging etc. for future use.

    // Load micropip - required to load non-standard packages
    await pyodide.loadPackage("micropip");
    const micropip = pyodide.pyimport("micropip");
    await micropip.install("requests");
    await micropip.install("simplejson");

    // Load dual crane lift capacity lib
    //wheel_url = "https://github.com/akjore/dual_crane_lift_capacity.whl";
    //wheel_url = "https://github.com/akjore/dual_crane_lift_capacity/dist/dual_crane_lift_capacity-0.0.1-py3-none-any.whl";
    // wheel_url = "file:///dual_crane_lift_capacity-0.0.1-py3-none-any.whl";
    // const wheel_url = "file:///dual_crane_lift_capacity-0.1.1.post45+git.f3b0c79e.dirty-py3-none-any.whl";
    // const wheel_url = "http://localhost:8000/dual_crane_lift_capacity-0.1.1.post45+git.f3b0c79e.dirty-py3-none-any.whl";
    // const wheel_url = "http://localhost:5000/dual_crane_lift_capacity-0.1.1.post45+git.f3b0c79e.dirty-py3-none-any.whl";
    // const wheel_url = "{{ url_for('static', filename='dual_crane_lift_capacity-0.1.1.post45+git.f3b0c79e.dirty-py3-none-any.whl') }}"
    const wheel_url = "http://localhost:5000/static/dual_crane_lift_capacity-0.1.1.post45+git.f3b0c79e.dirty-py3-none-any.whl";

    await micropip.install(wheel_url);

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
        # response = requests.get("http://localhost:8000/crane_curves.yaml")
        response = requests.get("http://localhost:5000/static/crane_curves.yaml")
        logger.debug("Raw crane curve content found: %s", response.content)

        Path("/crane_curves.yaml").write_bytes(response.content)
        os.environ["CRANE_CURVE_FILENAME"] = "/crane_curves.yaml"

        crane_curves = CraneCurves.crane_curve_ids()
        logger.info("Crane curves found: %s", list(crane_curves))
    `);

    // Populate select box
    let crane_curves = document.getElementById("crane_curve_a");
    let crane_curves_lst = pyodide.globals.get("crane_curves");

    for (let crane_curve of crane_curves_lst) {
        let opt = document.createElement("option");
        opt.value = crane_curve;
        opt.innerHTML = crane_curve;
        crane_curves.append(opt);
    };

    // Wrap up initialisation
    ready();
};

function initializeChart() {
    let gridColour = "#e5e7ef";
    let annotationColour = "#999";
    let accentColour = "#f5a623";
    let accentColour_border = "#e28c00";
    let backgroundColour = "#f4f4f9";

    // Prepare the chart area with all lines, dimensions, etc., but without actual data.
    // Configure datasets
	let data = {
		datasets: [{
			label: "Dual crane lift capacity1",
			borderColor: "black",
			borderWidth: 1,
			pointBackgroundColor: ["#000"],
         	pointBorderColor: ["#000"],
         	pointRadius: 2,
         	pointHoverRadius: 2,
         	fill: false,
         	tension: 0,
         	showLine: true,
            datalabels: {
                anchor: "end",
                align: "left",
                color: "#000",
                formatter: (val) => {
                    return Math.round(val.y);
                },
                font: {
                    weight: "normal",
                    size: 12
                }
            }
		}, {
			label: "Dual crane lift capacity2",
			borderColor: "black",
			borderWidth: 1,
			pointBackgroundColor: ["#000"],
         	pointBorderColor: ["#000"],
         	pointRadius: 2,
         	pointHoverRadius: 2,
         	fill: false,
         	tension: 0,
         	showLine: true,
            datalabels: {
                anchor: "end",
                align: "right",
                color: "#000",
                formatter: (val) => {
                    return Math.round(val.y);
                },
                font: {
                    weight: "normal",
                    size: 12
                }
            }
		}, {
			label: "Dual crane lift capacity3",
			borderColor: "black",
			borderWidth: 1,
			pointBackgroundColor: ["#000"],
         	pointBorderColor: ["#000"],
         	pointRadius: 2,
         	pointHoverRadius: 2,
         	fill: false,
         	tension: 0,
         	showLine: true,
            datalabels: {
                display: false
            }
		}, {
			label: "CoG",
        	pointBackgroundColor: accentColour,
        	pointBorderColor: accentColour_border,
        	pointRadius: 10,
        	pointHoverRadius: 10,
            pointStyle: "rectRot",
            datalabels: {
                anchor: "center",
                align: "bottom",
                formatter: (val) => {
                    return "CoG";
                }
            }
		}, {
			label: "CoG envelope",
        	pointBackgroundColor: accentColour,
        	pointBorderColor: accentColour_border,
        	pointRadius: 5,
        	pointHoverRadius: 5,
            pointStyle: "rectRot",
            datalabels: {
                display: false,
            }
		}, {
			label: "Weight intercepts",
        	pointBorderColor: "black",
        	pointRadius: 5,
        	pointHoverRadius: 5,
            datalabels: {
                display: false,
            }
		}, {
			label: "CoG intercepts",
        	pointBorderColor: "black",
        	pointRadius: 5,
        	pointHoverRadius: 5,
            datalabels: {
                display: false,
            }
		}]
	};

	// initialize empty chart
	let chart = new Chart(ctx, {
		type: "scatter",
	    data: data,
		options: {
            maintainAspectRatio: false,
			responsive: true,
			plugins: {
                legend: {
                    display: false
                },
				title: {
	        		display: true,
                    font: {
                        weight: "bold",
                        size: 20,
                    },
	        		text: ""
	      		},
                annotation: {
                    annotations: {
                        // weight margin at CoG
                        weight_margin_1: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                            display: true,
                        },
                        weight_margin_2: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                            display: true,
                        },
                        weight_margin_3: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            display: true,
                            label: {
                                display: true,
                                position: "center",
                                backgroundColor: backgroundColour,
                                color: annotationColour,
                            },
                            arrowHeads: {
                                end: {
                                    display: true,
                                    fill: true,
                                    length: 6,
                                    width: 4
                                },
                                start: {
                                    display: true,
                                    fill: true,
                                    length: 6,
                                    width: 4
                                }
                            }
                        },
                        // weight margin at CoG envelope
                        weight_margin_env_1: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                            display: true,
                        },
                        weight_margin_env_2: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                            display: true,
                        },
                        weight_margin_env_3: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            display: true,
                            label: {
                                display: true,
                                position: "center",
                                backgroundColor: backgroundColour,
                                color: annotationColour,
                            },
                            arrowHeads: {
                                end: {
                                    display: true,
                                    fill: true,
                                    length: 6,
                                    width: 4
                                },
                                start: {
                                    display: true,
                                    fill: true,
                                    length: 6,
                                    width: 4
                                }
                            }
                        },
                        // CoG limits at current weight
                        cog_limit_1: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                            display: true,
                        },
                        cog_limit_2: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                            display: true,
                        },
                        cog_limit_3: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                            display: true,
                        },
                        cog_limit_4: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            display: true,
                            label: {
                                display: true,
                                position: "center",
                                backgroundColor: backgroundColour,
                                color: annotationColour,
                            },
                            arrowHeads: {
                                end: {
                                    display: true,
                                    fill: true,
                                    length: 6,
                                    width: 4
                                },
                                start: {
                                    display: true,
                                    fill: true,
                                    length: 6,
                                    width: 4
                                }
                            }
                        },
                        cog_limit_5: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            display: true,
                            label: {
                                display: true,
                                position: "center",
                                backgroundColor: backgroundColour,
                                color: annotationColour,
                            },
                            arrowHeads: {
                                end: {
                                    display: true,
                                    fill: true,
                                    length: 6,
                                    width: 4
                                },
                                start: {
                                    display: true,
                                    fill: true,
                                    length: 6,
                                    width: 4
                                }
                            }
                        },
                        // CoG offset from peak
                        cog_peak_offset_1: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                        },
                        cog_peak_offset_2: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                        },
                        cog_peak_offset_3: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            label: {
                                display: true,
                                position: "center",
                                backgroundColor: backgroundColour,
                                color: annotationColour,
                            },
                            arrowHeads: {
                                end: {
                                    display: true,
                                    fill: true,
                                    length: 6,
                                    width: 4
                                },
                                start: {
                                    display: true,
                                    fill: true,
                                    length: 6,
                                    width: 4
                                }
                            }
                        },


                    }
                }
			},
			scales: {
            	y: {
					title: {
						display: true,
						text: "Weight [t]"
					},
                    grid: {
                        color: gridColour
                    }
            	},
            	x: {
					title: {
						display: true,
						text: "Centre of Gravity [m]"
					},
                    grid: {
                        color: gridColour
                    }
            	}
        	}
		}
  	});

    return chart;
};

function buildChartData(caseData, resultData) {
    const x_coord = resultData.lift_capacity_curve_x.value;
    const y_coord = resultData.lift_capacity_curve_y.value;
    const weight = caseData.weight.value;
    const cog = caseData.cog.value;
    const cog_env = caseData.cog_envelope.value;
    const cog_limit_at_weight = resultData.cog_limits_at_given_weight.value;
    const lift_capacity_at_cog = resultData.lift_capacity_at_cog.value;
    const lift_capacity_at_cog_envelope = resultData.lift_capacity_at_cog_envelope.value;
    const min = Math.min(... lift_capacity_at_cog_envelope);
    const idx = lift_capacity_at_cog_envelope.indexOf(min);
    const len = Math.floor(x_coord.length / 2)

    const coords = x_coord.map((x, i) => ({ x, y: y_coord[i] }));

    return {
        crane_capacity_curve_pt1: coords.slice(0, len),
        crane_capacity_curve_pt2: coords.slice(len),
        cog: [{x: cog, y: weight}],
        cog_envelope: [{x: cog_env[0], y: weight}, {x: cog_env[1], y: weight}],
        cog_limit_at_given_weight: [{x: cog_limit_at_weight[0], y: weight}, {x: cog_limit_at_weight[1], y: weight}],
        lift_capacity_at_cog: [{x: cog, y: lift_capacity_at_cog}, {x: cog_env[idx], y: lift_capacity_at_cog_envelope[idx]}],
    };
};

function updateDatasets(chartData) {
    DATASET_MAP.forEach((key, i) => {
        if (key) {
            chart.data.datasets[i].data = chartData[key];
        }
    });

    // special connector dataset
    chart.data.datasets[2].data = [
        chartData.crane_capacity_curve_pt1.at(-1),
        chartData.crane_capacity_curve_pt2[0]
    ];
}

function updateAnnotation(annotation, xmin, xmax, ymin, ymax, label=null) {
    const annotations = chart.options.plugins.annotation.annotations;

    annotations[annotation].xMin = xmin;
    annotations[annotation].xMax = xmax;
    annotations[annotation].yMin = ymin;
    annotations[annotation].yMax = ymax;

    if(label) {
        annotations[annotation].label.content = label;
    }

    annotations[annotation].display = xmin != null && xmax != null && ymin != null && ymax != null;
}

function updateChart() {
    // Update chart to reflect current entries.

    // Remove existing data
    chart.data.datasets.forEach((dataset) => {
        dataset.data = [];
    });

    // Add new data
    const caseData = liftcasesJson[caseIdx];
    const resultData = resultsJson[caseIdx];

    // Gather required data for charts
    const chartData = buildChartData(caseData, resultData);

    // Update chart data sets
    updateDatasets(chartData);

    // Update chart title
    chart.options.plugins.title.text = caseData.case + " - " + caseData.crane_curve_a;

    // Update dim lines - weight margin at CoG
    const annotations = chart.options.plugins.annotation.annotations;

    const xmin = chartData.crane_capacity_curve_pt1[0].x;
    const xmax = chartData.crane_capacity_curve_pt2.slice(-1)[0].x;
    const ymin = Math.min(chartData.crane_capacity_curve_pt1[0].y, chartData.crane_capacity_curve_pt2.slice(-1)[0].y);
    const ymax = chartData.crane_capacity_curve_pt2[0].y;
    const x1 = xmin - 0.1 * (xmax - xmin);
    const x2 = xmax + 0.1 * (xmax - xmin);
    const y1 = ymin;
    const y2 = ymax + 0.1 * (ymax - ymin);

    let xMin = chartData.cog_limit_at_given_weight[1].x;
    let xMax = x2;
    let yMin = chartData.cog[0].y;
    let yMax = yMin;
    updateAnnotation("weight_margin_1", xMin, xMax, yMin, yMax);

    xMin = chartData.lift_capacity_at_cog[0].x;
    xMax = x2;
    yMin = chartData.lift_capacity_at_cog[0].y;
    yMax = yMin;
    updateAnnotation("weight_margin_2", xMin, xMax, yMin, yMax);

    xMin = x2;
    xMax = x2;
    yMin = chartData.cog[0].y;
    yMax = chartData.lift_capacity_at_cog[0].y;
    let label = (chartData.lift_capacity_at_cog[0].y - chartData.cog[0].y).toFixed(0);
    updateAnnotation("weight_margin_3", xMin, xMax, yMin, yMax, label);

    // Update dim lines - weight margin at CoG env
    xMin = chartData.cog_limit_at_given_weight[0].x;
    xMax = x1;
    yMin = chartData.cog[0].y;
    yMax = yMin;
    updateAnnotation("weight_margin_env_1", xMin, xMax, yMin, yMax);

    xMin = chartData.lift_capacity_at_cog[1].x;
    xMax = x1;
    yMin = chartData.lift_capacity_at_cog[1].y;
    yMax = yMin;
    updateAnnotation("weight_margin_env_2", xMin, xMax, yMin, yMax);

    xMin = x1;
    xMax = x1;
    yMin = chartData.cog[0].y;
    yMax = chartData.lift_capacity_at_cog[1].y;
    label = (chartData.lift_capacity_at_cog[1].y - chartData.cog[0].y).toFixed(0);
    updateAnnotation("weight_margin_env_3", xMin, xMax, yMin, yMax, label);

    // Update dim lines - CoG limits at current weight
    xMin = chartData.cog_limit_at_given_weight[0].x;
    xMax = xMin;
    yMin = y1;
    yMax = chartData.cog[0].y;
    updateAnnotation("cog_limit_1", xMin, xMax, yMin, yMax);

    xMin = chartData.cog[0].x;
    xMax = xMin;
    yMin = y1;
    yMax = chartData.cog[0].y;
    updateAnnotation("cog_limit_2", xMin, xMax, yMin, yMax);

    xMin = chartData.cog_limit_at_given_weight[1].x;
    xMax = xMin;
    yMin = y1;
    yMax = chartData.cog[0].y;
    updateAnnotation("cog_limit_3", xMin, xMax, yMin, yMax);

    xMin = chartData.cog_limit_at_given_weight[0].x;
    xMax = chartData.cog[0].x;
    yMin = y1;
    yMax = y1;
    label = (chartData.cog[0].x - chartData.cog_limit_at_given_weight[0].x).toFixed(3);
    updateAnnotation("cog_limit_4", xMin, xMax, yMin, yMax, label);

    xMin = chartData.cog[0].x;
    xMax = chartData.cog_limit_at_given_weight[1].x;
    yMin = y1;
    yMax = y1;
    label = (chartData.cog_limit_at_given_weight[1].x - chartData.cog[0].x).toFixed(3);
    updateAnnotation("cog_limit_5", xMin, xMax, yMin, yMax, label);

    // Update dim lines - CoG offset from peak
    xMin = chartData.cog[0].x;
    xMax = xMin;
    yMin = chartData.lift_capacity_at_cog[0].y;
    yMax = y2;
    updateAnnotation("cog_peak_offset_1", xMin, xMax, yMin, yMax);

    xMin = chartData.crane_capacity_curve_pt2[0].x;
    xMax = xMin;
    yMin = chartData.crane_capacity_curve_pt2[0].y;
    yMax = y2;
    updateAnnotation("cog_peak_offset_2", xMin, xMax, yMin, yMax);

    xMin = chartData.crane_capacity_curve_pt2[0].x;
    xMax = chartData.cog[0].x;
    yMin = y2;
    yMax = y2;
    label = (Math.abs(chartData.cog[0].x - chartData.crane_capacity_curve_pt2[0].x)).toFixed(3);
    updateAnnotation("cog_peak_offset_3", xMin, xMax, yMin, yMax, label);

    // Update chart
    chart.update();
};

// JS hook: add listener to form for any changes to input fields
let form = document.getElementById('form_dualcranelift');
form.addEventListener('change', function(evt) {
    // Update liftcasesJson with the change
    // GUI only permits changes to values -> no changes to units

    // Capture new value, and convert to number if numeric field.
    const id = evt.target.id;
    const isSelect = evt.target.tagName === "SELECT";
    const val = isSelect ? evt.target.value : Number(evt.target.value);

    const data = liftcasesJson?.[caseIdx];
    if (!data) return;

    if (VALUE_FIELDS.includes(id)) {
        data[id].value = val;
    }

    // special cases
    if (id === "crane_curve_a") {
        data.crane_curve_a = val;
        data.crane_curve_b = val;
    }

    if (id === "cog") {
        data.cog.value = val;
        data.cog_envelope.value[0] = data.cog.value - data.cog_offset_a.value;
        data.cog_envelope.value[1] = data.cog.value + data.cog_offset_b.value;
    }

    if (id === "cog_offset_a") {
        data.cog_envelope.value[0] = data.cog.value - val;
    }

    if (id === "cog_offset_b") {
        data.cog_envelope.value[1] = data.cog.value + val;
    }

    if (window.performCalcs) performCalcs(evt);
});

// Show overlay when page starts loading
document.getElementById("overlay").style.visibility = "visible";

// When page has loaded, hide the overlay and write message to log
function ready() {
    document.getElementById("overlay").style.visibility = "hidden";

    // Allow form elements to update calcs
//    window.performCalcs = performCalcs();
    window.performCalcs = performCalcs;
    performCalcs();

    console.log("Ready.");
}

// Load Pyodide - required to run python code in browser
const pyodide = await loadPyodide();

// Initialize pyodide
initialize();

// Initialize chart
var Chart = window.Chart;

//      Register chart plug-ins
Chart.register(ChartDataLabels);

var ctx = document.getElementById("capacity_chart");
var chart = initializeChart();

//      Set chart font
Chart.defaults.font.family = "Trebuchet MS";

// 'Details' section is nominally hidden - toggle to display / hide
const toggle = document.getElementById('detailsToggle');
const section = document.getElementById('detailsSection');

function toggleDetails() {
    const isHidden = section.hidden;
    section.hidden = !isHidden;
    toggle.classList.toggle('expanded', isHidden);
}

toggle.addEventListener('click', toggleDetails);

//      keyboard accessibility
toggle.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleDetails();
    }
});

// File upload / drag and drop drop zone
const loadBtn   = document.getElementById('loadYamlBtn');
const dropZone  = document.getElementById('loadYamlDropZone');
const fileInput = document.getElementById('yamlFileInput');

//      Click: open file picker
loadBtn.addEventListener('click', () => {
    fileInput.click();
});

//      File chosen via picker
fileInput.addEventListener('change', async () => {
    const file = fileInput.files[0];
    if (!file) return;
    await handleYamlFile(file);
    fileInput.value = ''; // allow re-upload of same file
});

//      Drag & drop
dropZone.addEventListener('dragover', e => {
    e.preventDefault();           // required
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', async e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');

    const file = e.dataTransfer.files[0];
    if (!file) return;

    await handleYamlFile(file);
});

//      Handle loading of yaml-file
async function handleYamlFile(file) {
    if (!file.name.match(/\.ya?ml$/i)) {
        alert('Please select a .yaml or .yml file');
        return;
    }

    casesYamlStr = await file.text();
    await performCalcs();
}

// Add the feather icons to the web page
feather.replace();

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

// variables
let liftcasesJson = null;
let resultsJson = null;
let caseIdx = 0;

// Sample to get user going
let casesYamlStr = `
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
    # cog_envelope: [(61.668-0.5) m, (61.668+0.5) m]
    cog_envelope: [(62.750-1.500) m, (62.750+1.500) m]
`;
