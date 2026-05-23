"use strict";

export const VALUE_FIELDS = [
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

export const INPUT_FIELDS = [...VALUE_FIELDS, "cog"];

export const DATASET_MAP = [
    "crane_capacity_curve_pt1",
    "crane_capacity_curve_pt2",
    null,       // connector
    "cog",
    "cog_envelope",
    "cog_limit_at_given_weight",
    "lift_capacity_at_cog_and_env"
];
