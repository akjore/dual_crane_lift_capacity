export const COMPUTED_FIELDS = [
    "crane_capacity_a",
    "crane_capacity_b",
    "factored_lift_weight",
    "combined_rigging_weight",
    "distance_lift_point_a_to_cog",
    "distance_lift_point_b_to_cog",
    "distance_lift_point_a_to_cog_offset_towards_a",
    "distance_lift_point_b_to_cog_offset_towards_a",
    "distance_lift_point_a_to_cog_offset_towards_b",
    "distance_lift_point_b_to_cog_offset_towards_b",
    "distance_lift_point_a_to_lift_point_b",
];

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

export const RESULT_FIELDS = [
    "spare_capacity_a",
    "spare_capacity_b",
    "weight_margin",
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
];

export const DATASET_MAP = [
    "crane_capacity_curve_pt1",
    "crane_capacity_curve_pt2",
    null,       // connector
    "cog",
    "cog_envelope",
    "cog_limit_at_given_weight",
    "lift_capacity_at_cog_and_env"
];
