import js from "@eslint/js";
import globals from "globals";
import { defineConfig } from "eslint/config";

globals: globals.browser

export default [
    {
        ignores: ["node_modules/**"],

        files: ["webapp/**/*.js"],

        ignores: ["node_modules/"],

        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
//            globals: {
//                fetch: "readonly",
//                window: "readonly",
//                document: "readonly"
//            }
            globals: globals.browser
        },

        rules: {
            "no-unused-vars": "warn",
            "no-undef": "error",
            "no-console": "off",
            "no-debugger": "warn",

            "eqeqeq": "warn",
            "curly": "warn"
        }
    }
];
