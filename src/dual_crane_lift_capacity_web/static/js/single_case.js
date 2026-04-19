"use strict";

function populateFields(obj) {
    // Assumptions:
    // obj is a dictionary, with keys matching html-fields that will be populated
    // Additionally, if class is "distance", the number will be formatted to
    // 3 decimals, otherwise 0 decimals.
    for (const [key, val] of Object.entries(obj)) {
        let elmn = document.getElementById(key);
        var noOfDecimals = 0;
        if (elmn.className.includes("distance")) {
            var noOfDecimals = 3;
        }
        elmn.textContent = val.toFixed(noOfDecimals);
    };
};

async function updateCalcs() {
    // Function aquires all the parameters from the form field, processes them,
    // obtains the results, and then processes the results for displaying in the
    // chart and in the various fields.

    // Get form input fields
    const formData = new FormData(document.getElementById("form_dualcranelift"));
    const formDataObj = Object.fromEntries(formData);
    console.log("Received input from html:")
    console.log(formDataObj);
    window.formDataObj = formDataObj;

    // Perform calcs
    await pyodide.runPythonAsync(`
        import os

        import js
        import json
        import numpy as np

        from dual_crane_lift_capacity.dual_crane_lift import DualCraneLift

        # create yaml input based on form data
        case = f"""
            { js.formDataObj.case }:
                crane_curve_a: { js.formDataObj.crane_curve_a }
                crane_curve_b: { js.formDataObj.crane_curve_a }
                crane_radius_a: { js.formDataObj.crane_radius_a } m
                crane_radius_b: { js.formDataObj.crane_radius_b } m
                rigging_weight_a: { js.formDataObj.rigging_weight_a } t
                rigging_weight_b: { js.formDataObj.rigging_weight_b } t
                weight_uncertainty_factor: { js.formDataObj.weight_uncertainty_factor }
                cog_uncertainty_factor: { js.formDataObj.cog_uncertainty_factor }
                tilt_factor: { js.formDataObj.tilt_factor }
                lift_point_a:
                  - ({ js.formDataObj.lift_point_a } - { js.formDataObj.float_a }) m
                  - ({ js.formDataObj.lift_point_a } + { js.formDataObj.float_a }) m
                lift_point_b:
                  - ({ js.formDataObj.lift_point_b } - { js.formDataObj.float_b }) m
                  - ({ js.formDataObj.lift_point_b } + { js.formDataObj.float_b }) m
                weight: { js.formDataObj.weight } t
                cog:
                  - ({ js.formDataObj.cog } - { js.formDataObj.module_cog_offset_a }) m
                  - { js.formDataObj.cog } m
                  - ({ js.formDataObj.cog } + { js.formDataObj.module_cog_offset_b }) m
        """

        # Calculate results
        dualcranelift = DualCraneLift(data=case)
        logger.debug("Produced python output: %s", dualcranelift)

        # Helper variables to improve readability
        res = dualcranelift.dual_crane_lift_capacity_results
        inp = dualcranelift.lift_cases

        # Set variables to be returned and displayed
        ret = {}
        ret["crane_capacity_a"] = res.crane_capacity_a[0].to("metric_ton").magnitude
        ret["crane_capacity_b"] = res.crane_capacity_b[0].to("metric_ton").magnitude

        cog = inp.cog[0][1].to("meters").magnitude
        lpa = np.average(inp.lift_point_a[0]).to("meter").magnitude
        lpb = np.average(inp.lift_point_b[0]).to("meter").magnitude
        ret["distance_cog_a"] = cog - lpa
        ret["distance_cog_b"] = lpb - cog
        ret["distance_cog_ab"] = lpb - lpa

        ret["factored_lift_weight"] = res.factored_lift_weight[0].to("metric_ton").magnitude

        ret["combined_rigging_weight"] = (inp.rigging_weight_a + inp.rigging_weight_b)[0].to("metric_ton").magnitude

        # edge of CoG envelope towards edges a and b of envelope
        lpa = np.average(inp.lift_point_a[0]).to("meter").magnitude
        lpb = np.average(inp.lift_point_b[0]).to("meter").magnitude
        cog = inp.cog[0].to("meters").magnitude
        dist_a = cog - lpa
        dist_b = lpb - cog
        dist_ab = lpb - lpa

        ret["distance_coga_a"] = dist_a[0]
        ret["distance_coga_b"] = dist_b[0]
        ret["distance_coga_ab"] = dist_ab

        ret["distance_cogb_a"] = dist_a[2]
        ret["distance_cogb_b"] = dist_b[2]
        ret["distance_cogb_ab"] = dist_ab

        # true hook load - edge of CoG envelope towards a and b
        total = res.true_hook_load_a + res.true_hook_load_b

        ret["true_hook_load_a_cog_a"] = res.true_hook_load_a[0][0].to("metric_ton").magnitude
        ret["true_hook_load_b_cog_a"] = res.true_hook_load_b[0][0].to("metric_ton").magnitude
        ret["total_true_hook_load_cog_a"] = total[0][0].to("metric_ton").magnitude

        ret["true_hook_load_a_cog_b"] = res.true_hook_load_a[0][1].to("metric_ton").magnitude
        ret["true_hook_load_b_cog_b"] = res.true_hook_load_b[0][1].to("metric_ton").magnitude
        ret["total_true_hook_load_cog_b"] = total[0][1].to("metric_ton").magnitude

        # factored hook load - edge of CoG envelope towards a and b
        total = res.factored_hook_load_a + res.factored_hook_load_b

        ret["factored_hook_load_a_cog_a"] = res.factored_hook_load_a[0][0].to("metric_ton").magnitude
        ret["factored_hook_load_b_cog_a"] = res.factored_hook_load_b[0][0].to("metric_ton").magnitude
        ret["total_factored_hook_load_cog_a"] = total[0][0].to("metric_ton").magnitude

        ret["factored_hook_load_a_cog_b"] = res.factored_hook_load_a[0][1].to("metric_ton").magnitude
        ret["factored_hook_load_b_cog_b"] = res.factored_hook_load_b[0][1].to("metric_ton").magnitude
        ret["total_factored_hook_load_cog_b"] = total[0][1].to("metric_ton").magnitude

        # spare capacity - difference between the crane capacity and the largest factored hook load
        ret["spare_capacity_a"] = res.spare_capacity_a[0].to("metric_ton").magnitude
        ret["spare_capacity_b"] = res.spare_capacity_b[0].to("metric_ton").magnitude

        # module weight margin
        ret["module_weight_margin"] = res.weight_margin[0].to("metric_ton").magnitude
        ret_json = json.dumps(ret)

        # Prepare data for plotting
        chart_data = {}
        #   capacity curve
        x = res.lift_capacity_curve_x[0].to("meter").magnitude.tolist()
        y = res.lift_capacity_curve_y[0].to("metric_ton").magnitude.tolist()
        l = len(x) // 2
        chart_data["crane_capacity_curve_pt1"] = [{"x": x1, "y": y1} for x1, y1 in zip(x[:l],y[:l])]
        chart_data["crane_capacity_curve_pt2"] = [{"x": x1, "y": y1} for x1, y1 in zip(x[l:],y[l:])]

        #   cogs
        cog = inp.cog[0].to("meter").magnitude.tolist()
        weight = inp.weight[0].to("metric_ton").magnitude.tolist()
        chart_data["cog"] = [{"x": cog[1], "y": weight}]
        chart_data["cog_envelope"] = [{"x": cog[0], "y": weight}, {"x": cog[2], "y": weight}]

        #   intercepts
        x = res.cog_limit_at_given_weight[0].to("meters").magnitude.tolist()
        chart_data["cog_limit_at_given_weight"] = [{"x": x[0], "y": weight}, {"x": x[1], "y": weight}]

        y = res.lift_capacity_at_cog[0].to("metric_ton").magnitude.tolist()
        idx = np.argmin(y, axis=0)
        chart_data["lift_capacity_at_cog"] = [{"x": cog[1], "y": y[1]}, {"x": cog[idx], "y": y[idx]}]

        ret_chart_json = json.dumps(chart_data)
    `);

    // Get computed values from python, and populate html page
    const ret = JSON.parse(pyodide.globals.get("ret_json"));
    console.log(ret);
    populateFields(ret);

    // Set module weight margin background colour according to value (positive, negative)
    let elmn = document.getElementById("module_weight_margin");
    elmn.classList.add('weight_margin', 'computed');

    const isPositive = ret.module_weight_margin >= 0;
    elmn.classList.toggle('weight_margin--positive', isPositive);
    elmn.classList.toggle('weight_margin--negative', !isPositive);

    updateChart();
};

async function initialize() {
    // Set up pyodide, install and load packages, configure logging etc. for future use.

    // Load micropip - required to load non-standard packages
    await pyodide.loadPackage("micropip");
    const micropip = pyodide.pyimport("micropip");

    await micropip.install("requests");

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

        crane_curves = CraneCurves().crane_curve_ids
        logger.info("Crane curves found: %s", list(crane_curves))
    `);

    // Populate select box, and select the option that matches the starting example
    let crane_curves = document.getElementById("crane_curve_a");
    let crane_curves_lst = pyodide.globals.get("crane_curves");

    for (let crane_curve of crane_curves_lst) {
        let opt = document.createElement("option");
        opt.value = crane_curve;
        opt.innerHTML = crane_curve;
        if (crane_curve == "S7000.main.fixed_1.5") {
            opt.selected = true;
        };
            crane_curves.append(opt);
    };

    // Copy the crane curve file to console
    let file = pyodide.FS.readFile("/crane_curves.yaml", { encoding: "utf8" });
    console.log(file);

    // Perform calculations for sample
    updateCalcs();
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
	        		text: "Sample"
	      		},
                annotation: {
                    annotations: {
                        // weight margin at CoG
                        weight_margin_1: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                        },
                        weight_margin_2: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                        },
                        weight_margin_3: {
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
                        // weight margin at CoG envelope
                        weight_margin_env_1: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                        },
                        weight_margin_env_2: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                        },
                        weight_margin_env_3: {
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
                        // CoG limits at current weight
                        cog_limit_1: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                        },
                        cog_limit_2: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                        },
                        cog_limit_3: {
                            type: "line",
                            borderColor: annotationColour,
                            borderWidth: 1,
                            borderDash: [5, 5],
                        },
                        cog_limit_4: {
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
                        cog_limit_5: {
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

function updateChart() {
    // Update chart to reflect current entries.

    // Get computed values from python
    const chart_data = JSON.parse(pyodide.globals.get("ret_chart_json"));
    console.log(chart_data);
    const formData = new FormData(document.getElementById("form_dualcranelift"));
    const formDataObj = Object.fromEntries(formData);

    // Remove existing data
    chart.data.labels.pop();
    chart.data.datasets.forEach((dataset) => {
        dataset.data.pop();
    });

    // Add new data
    chart.data.datasets[0].data = chart_data.crane_capacity_curve_pt1;
    chart.data.datasets[1].data = chart_data.crane_capacity_curve_pt2;
    chart.data.datasets[2].data = [chart_data.crane_capacity_curve_pt1.slice(-1)[0], chart_data.crane_capacity_curve_pt2[0]];
    chart.data.datasets[3].data = chart_data.cog;
    chart.data.datasets[4].data = chart_data.cog_envelope;
    chart.data.datasets[5].data = chart_data.cog_limit_at_given_weight;
    chart.data.datasets[6].data = chart_data.lift_capacity_at_cog;

    // Update title
    chart.options.plugins.title.text = formDataObj.case + " - " + formDataObj.crane_curve_a;

    // Update dim lines - weight margin at CoG
    let annotations = chart.options.plugins.annotation.annotations;

    let xmin = chart_data.crane_capacity_curve_pt1[0].x;
    let xmax = chart_data.crane_capacity_curve_pt2.slice(-1)[0].x;
    let ymin = Math.min(chart_data.crane_capacity_curve_pt1[0].y, chart_data.crane_capacity_curve_pt2.slice(-1)[0].y);
    let ymax = chart_data.crane_capacity_curve_pt2[0].y;
    let x1 = xmin - 0.1 * (xmax - xmin);
    let x2 = xmax + 0.1 * (xmax - xmin);
    let y1 = ymin;
    let y2 = ymax + 0.1 * (ymax - ymin);

    annotations.weight_margin_1.xMin = chart_data.cog_limit_at_given_weight[1].x;
    annotations.weight_margin_1.xMax = x2;
    annotations.weight_margin_1.yMin = chart_data.cog[0].y;
    annotations.weight_margin_1.yMax = chart_data.cog[0].y;

    annotations.weight_margin_2.xMin = chart_data.lift_capacity_at_cog[0].x;
    annotations.weight_margin_2.xMax = x2;
    annotations.weight_margin_2.yMin = chart_data.lift_capacity_at_cog[0].y;
    annotations.weight_margin_2.yMax = chart_data.lift_capacity_at_cog[0].y;

    annotations.weight_margin_3.xMin = x2;
    annotations.weight_margin_3.xMax = x2;
    annotations.weight_margin_3.yMin = chart_data.cog[0].y;
    annotations.weight_margin_3.yMax = chart_data.lift_capacity_at_cog[0].y;
    annotations.weight_margin_3.label.content = (chart_data.lift_capacity_at_cog[0].y - chart_data.cog[0].y).toFixed(0);

    // Update dim lines - weight margin at CoG env
    annotations.weight_margin_env_1.xMin = chart_data.cog_limit_at_given_weight[0].x;
    annotations.weight_margin_env_1.xMax = x1;
    annotations.weight_margin_env_1.yMin = chart_data.cog[0].y;
    annotations.weight_margin_env_1.yMax = chart_data.cog[0].y;

    annotations.weight_margin_env_2.xMin = chart_data.lift_capacity_at_cog[1].x;
    annotations.weight_margin_env_2.xMax = x1;
    annotations.weight_margin_env_2.yMin = chart_data.lift_capacity_at_cog[1].y;
    annotations.weight_margin_env_2.yMax = chart_data.lift_capacity_at_cog[1].y;

    annotations.weight_margin_env_3.xMin = x1;
    annotations.weight_margin_env_3.xMax = x1;
    annotations.weight_margin_env_3.yMin = chart_data.cog[0].y;
    annotations.weight_margin_env_3.yMax = chart_data.lift_capacity_at_cog[1].y;
    annotations.weight_margin_env_3.label.content = (chart_data.lift_capacity_at_cog[1].y - chart_data.cog[0].y).toFixed(0);

    // Update dim lines - CoG limits at current weight
    annotations.cog_limit_1.xMin = chart_data.cog_limit_at_given_weight[0].x;
    annotations.cog_limit_1.xMax = chart_data.cog_limit_at_given_weight[0].x;
    annotations.cog_limit_1.yMin = y1;
    annotations.cog_limit_1.yMax = chart_data.cog[0].y;

    annotations.cog_limit_2.xMin = chart_data.cog[0].x;
    annotations.cog_limit_2.xMax = chart_data.cog[0].x;
    annotations.cog_limit_2.yMin = y1;
    annotations.cog_limit_2.yMax = chart_data.cog[0].y;

    annotations.cog_limit_3.xMin = chart_data.cog_limit_at_given_weight[1].x;
    annotations.cog_limit_3.xMax = chart_data.cog_limit_at_given_weight[1].x;
    annotations.cog_limit_3.yMin = y1;
    annotations.cog_limit_3.yMax = chart_data.cog[0].y;

    annotations.cog_limit_4.xMin = chart_data.cog_limit_at_given_weight[0].x;
    annotations.cog_limit_4.xMax = chart_data.cog[0].x;
    annotations.cog_limit_4.yMin = y1;
    annotations.cog_limit_4.yMax = y1;
    annotations.cog_limit_4.label.content = (chart_data.cog[0].x - chart_data.cog_limit_at_given_weight[0].x).toFixed(3);

    annotations.cog_limit_5.xMin = chart_data.cog[0].x;
    annotations.cog_limit_5.xMax = chart_data.cog_limit_at_given_weight[1].x;
    annotations.cog_limit_5.yMin = y1;
    annotations.cog_limit_5.yMax = y1;
    annotations.cog_limit_5.label.content = (chart_data.cog_limit_at_given_weight[1].x - chart_data.cog[0].x).toFixed(3);

    // Update dim lines - CoG offset from peak
    annotations.cog_peak_offset_1.xMin = chart_data.cog[0].x;
    annotations.cog_peak_offset_1.xMax = chart_data.cog[0].x;
    annotations.cog_peak_offset_1.yMin = chart_data.lift_capacity_at_cog[0].y;
    annotations.cog_peak_offset_1.yMax = y2;

    annotations.cog_peak_offset_2.xMin = chart_data.crane_capacity_curve_pt2[0].x;
    annotations.cog_peak_offset_2.xMax = chart_data.crane_capacity_curve_pt2[0].x;
    annotations.cog_peak_offset_2.yMin = chart_data.crane_capacity_curve_pt2[0].y;
    annotations.cog_peak_offset_2.yMax = y2;

    annotations.cog_peak_offset_3.xMin = chart_data.crane_capacity_curve_pt2[0].x;
    annotations.cog_peak_offset_3.xMax = chart_data.cog[0].x;
    annotations.cog_peak_offset_3.yMin = y2;
    annotations.cog_peak_offset_3.yMax = y2;
    annotations.cog_peak_offset_3.label.content = (Math.abs(chart_data.cog[0].x - chart_data.crane_capacity_curve_pt2[0].x)).toFixed(3);

    // Update chart
    chart.update();

    // This is the last step - ready for new instructions
    ready();
    //console.log("Ready.");
};

// JS hook: add listener to form for any changes to input fields
let form = document.getElementById('form_dualcranelift');
form.addEventListener('change', function(evt) {
    console.log(evt.target.value);
    if (window.updateCalcs) updateCalcs();
});

document.getElementById("overlay").style.visibility = "visible"; // Show overlay when page starts loading

function ready() {
    document.getElementById("overlay").style.visibility = "hidden";
    console.log("Ready.");
}
//window.addEventListener('load', function () {
//  alert("It's loaded!")
//})

//window.addEventListener('load', function () {
//window.onload = function() {
//    document.getElementById("overlay").style.visibility = "hidden"; // Hide overlay when page is loaded
//});

//window.onload = function() {
//    document.getElementById('overlay').style.visibility = 'visible'; // Show overlay when page starts loading
//};

//HTMLInputElementObject.addEventListener('input', (evt) => {
//  console.log('run'); // Do something
//});

var Chart = window.Chart;

// Register plug-ins
Chart.register(ChartDataLabels);

// Set chart font
Chart.defaults.font.family = "Trebuchet MS";

// Load Pyodide - required to run python code in browser
const pyodide = await loadPyodide();

// Initialize pyodide
initialize();

// Initialize chart
var ctx = document.getElementById("capacity_chart");
var chart = initializeChart();

// Allow form elements to update calcs
window.updateCalcs = updateCalcs;

