"use strict";
// I can't get annotationPlugin to work with setup below. For now kept global import in html file.
//import { Chart as ChartJS, registerables } from "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/+esm";
//import ChartDataLabels from "https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/+esm";
//import annotationPlugin from "https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.1.0/+esm";

const ChartJS = window.Chart;
import { DATASET_MAP } from "./config.js";
import * as state from "./state.js";

//ChartJS.register(
//    ...registerables,
//    ChartDataLabels,
//    annotationPlugin
//);

let defaultDuration;
let chart;

// Initialize chart
export function initializeChart() {
    const ctx = document.getElementById("capacity_chart");

    // Set chart font
    Chart.defaults.font.family = "Trebuchet MS";

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

    // Settings for projection lines
    let projectionLineSettings = {
        type: "line",
        borderColor: annotationColour,
        borderWidth: 1,
        borderDash: [5, 5],
        display: true,
        xMin: 0,
        yMin: 0,
        xMax: 1,
        yMax: 1,
    }

    // Settings for dimension lines
    let dimensionLineSettings = {
        type: "line",
        borderColor: annotationColour,
        borderWidth: 1,
        display: true,
        xMin: 0,
        yMin: 0,
        xMax: 1,
        yMax: 1,
        label: {
            display: true,
            position: "center",
            backgroundColor: backgroundColour,
            color: annotationColour,
            content: "",
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
    }

	// initialize empty chart
	chart = new ChartJS(ctx, {
		type: "scatter",
	    data: data,
		options: {
            animation: {
                duration: 1000,
            },
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
                        weight_margin_1: JSON.parse(JSON.stringify(projectionLineSettings)), //needed to create a copy of the settings
                        weight_margin_2: JSON.parse(JSON.stringify(projectionLineSettings)),
                        weight_margin_3: JSON.parse(JSON.stringify(dimensionLineSettings)),

                        // weight margin at CoG envelope
                        weight_margin_env_1: JSON.parse(JSON.stringify(projectionLineSettings)),
                        weight_margin_env_2: JSON.parse(JSON.stringify(projectionLineSettings)),
                        weight_margin_env_3: JSON.parse(JSON.stringify(dimensionLineSettings)),

                        // CoG limits at current weight
                        cog_limit1_1: JSON.parse(JSON.stringify(projectionLineSettings)),
                        cog_limit1_2: JSON.parse(JSON.stringify(projectionLineSettings)),
                        cog_limit1_3: JSON.parse(JSON.stringify(dimensionLineSettings)),

                        cog_limit2_1: JSON.parse(JSON.stringify(projectionLineSettings)),
                        cog_limit2_2: JSON.parse(JSON.stringify(projectionLineSettings)),
                        cog_limit2_3: JSON.parse(JSON.stringify(dimensionLineSettings)),

                        // CoG offset from peak
                        cog_peak_offset_1: JSON.parse(JSON.stringify(projectionLineSettings)),
                        cog_peak_offset_2: JSON.parse(JSON.stringify(projectionLineSettings)),
                        cog_peak_offset_3: JSON.parse(JSON.stringify(dimensionLineSettings)),
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

    // Capture the default duration for animations (will be zero'ed when exporting reports)
    defaultDuration = chart.options.animation?.duration ?? 1000;

//    return chart;
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
        lift_capacity_at_cog_and_env: [{x: cog, y: lift_capacity_at_cog}, {x: cog_env[idx], y: lift_capacity_at_cog_envelope[idx]}],
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

function updateAnnotation(annotation, p1, p2, dimx, dimy) {
    // Update an annotation.
    // 3 components involved - one dim line, and two projection lines
    // dimx, dimy: if dimx provided, then the dim line is vertical, else horizontal
    const visible = p1.x != null && p1.y != null && p2.x != null && p2.y != null;

    if(dimx) {
        updateAnnotationComponent(annotation+"_1", p1.x, dimx, p1.y, p1.y, visible);
        updateAnnotationComponent(annotation+"_2", p2.x, dimx, p2.y, p2.y, visible);
        updateAnnotationComponent(annotation+"_3", dimx, dimx, p1.y, p2.y, visible, true);
    } else {
        updateAnnotationComponent(annotation+"_1", p1.x, p1.x, p1.y, dimy, visible);
        updateAnnotationComponent(annotation+"_2", p2.x, p2.x, p2.y, dimy, visible);
        updateAnnotationComponent(annotation+"_3", p1.x, p2.x, dimy, dimy, visible, true);
    }
}

function updateAnnotationComponent(annotation, xmin, xmax, ymin, ymax, visible=true, label=null) {
    const annotations = chart.options.plugins.annotation.annotations;

    if (!annotations[annotation]) {
        console.warn("Missing annotation:", annotation);
        return;
    }

    annotations[annotation].display = visible;

    if(!visible) return;

    annotations[annotation].xMin = xmin;
    annotations[annotation].xMax = xmax;
    annotations[annotation].yMin = ymin;
    annotations[annotation].yMax = ymax;

    if(label) {
        let labelval = null;
        if(xmin != xmax) {
            labelval = Math.abs(xmax - xmin).toFixed(3);
        } else {
            labelval = (ymax - ymin).toFixed(0);
        }
        annotations[annotation].label.content = labelval;
    }
}

export function updateChart() {
    // Update chart to reflect current entries.

    // Remove existing data
    chart.data.datasets.forEach((dataset) => {
        dataset.data = [];
    });

    // Add new data
    const caseData = state.liftcasesJson[state.caseIdx];
    const resultData = state.resultsJson[state.caseIdx];

    // Gather required data for charts
    const chartData = buildChartData(caseData, resultData);

    // Update chart data sets
    updateDatasets(chartData);

    // Update chart title
    chart.options.plugins.title.text = caseData.case + " - " + caseData.crane_curve_a;

    // Update annotations - projection lines and dimension lines
    const annotations = chart.options.plugins.annotation.annotations;

    const xmin = chartData.crane_capacity_curve_pt1[0].x;
    const xmax = chartData.crane_capacity_curve_pt2.slice(-1)[0].x;
    const ymin = Math.min(chartData.crane_capacity_curve_pt1[0].y, chartData.crane_capacity_curve_pt2.slice(-1)[0].y);
    const ymax = chartData.crane_capacity_curve_pt2[0].y;
    const x1 = xmin - 0.06 * (xmax - xmin);
    const x2 = xmax + 0.06 * (xmax - xmin);
    const y1 = ymin + 0.02 * (ymax - ymin);
    const y2 = ymax + 0.06 * (ymax - ymin);

    //      Update dim lines - weight margin at CoG
    updateAnnotation("weight_margin", chartData.cog_limit_at_given_weight[1], chartData.lift_capacity_at_cog_and_env[0], x2, null);

    //      Update dim lines - weight margin at CoG env
//    updateAnnotation("weight_margin_env", chartData.cog_limit_at_given_weight[0], chartData.lift_capacity_at_cog[1], x1, null);
    updateAnnotation("weight_margin_env", chartData.cog_limit_at_given_weight[0], chartData.lift_capacity_at_cog_and_env[1], x1, null);

    //      Update dim lines - CoG limits at current weight
    updateAnnotation("cog_limit1", chartData.cog_limit_at_given_weight[0], chartData.cog[0], null, y1);
    updateAnnotation("cog_limit2", chartData.cog_limit_at_given_weight[1], chartData.cog[0], null, y1);

    //      Update dim lines - CoG offset from peak
    updateAnnotation("cog_peak_offset", chartData.cog[0], chartData.crane_capacity_curve_pt2[0], null, y2);

    // Update chart
    chart.update();
};

export function disableChartAnimation() {
    if (!chart) return;

    chart.options.animation.duration = 0;
}

export function enableChartAnimation() {
    if (!chart) return;

    chart.options.animation.duration = defaultDuration;
}

