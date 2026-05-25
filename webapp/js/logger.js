"use strict";

let LOG_LEVEL = detectDebugMode() ? "DEBUG" : "WARNING";

function detectDebugMode() {
    // Auto-set to debug mode if running locally
    const isLocalhost = window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1";

    const urlDebug = window.location.search.includes("debug=true");

    return isLocalhost || urlDebug;
}

export function setLogLevelJS(level) {
    LOG_LEVEL = level;
    console.info("[APP] JS log level set to:", level);
}

function getCaller() {
    const err = new Error();
    const stack = err.stack ? err.stack.split("\n") : [];

    for (let i = 1; i < stack.length; i++) {
        const line = stack[i];

        if (
            line.indexOf("getCaller") !== -1 ||
            line.indexOf("logger.js") !== -1
        ) continue;

        // Extract just "file.js:line"
        const match = line.match(/([^\/]+\.\w+:\d+):\d+/);

        if (match) {
            return match[1];   // e.g. "main.js:42"
        }

        // fallback: remove "at " safely
        return line.replace("at ", "").trim();
    }

    return "";
}

export const log = {
    debug: function () {
        if (LOG_LEVEL === "DEBUG") {
            console.debug("[APP] " + getCaller() + ":", ...arguments);
        }
    },

    info: function () {
        if (LOG_LEVEL === "DEBUG" || LOG_LEVEL === "INFO") {
            console.info("[APP] " + getCaller() + ":", ...arguments);
        }
    },

    warn: function () {
        console.warn("[APP] " + getCaller() + ":", ...arguments);
    },

    error: function () {
        console.error("[APP] " + getCaller() + ":", ...arguments);
    }
};
