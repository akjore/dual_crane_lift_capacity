"use strict";

// Report generation in pdf
import { jsPDF } from "https://cdn.jsdelivr.net/npm/jspdf@4.2.1/dist/jspdf.es.min.js/+esm";
import html2canvas from "https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js/+esm";
import { disableChartAnimation, enableChartAnimation } from "./chart.js";
import { VERSION } from "../version.js";
import { log } from "../logger.js";
import * as state from "./state.js";

let pdf;
let currentPage;
let margin;
let pageWidth;
let pageHeight;
let usableWidth;
let usableHeight;

// Initialize report
export function beginReport() {
    margin = 10;
    pageWidth = 297;
    pageHeight = 210;
    usableWidth = pageWidth - 2 * margin;
    usableHeight = pageHeight - 2 * margin;

    pdf = new jsPDF({
        orientation: "landscape",
        unit: "mm",
        format: "a4"
    });

    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(8);

    // Temporarily switch of chart transitions
    disableChartAnimation();

    // Reset page count
    currentPage = 0;
}

// Finalize report
export function finalizeReport() {
    const totalPages = pdf.getNumberOfPages();

    // Finalize report
    // --- Footer content ---
    const date = new Date().toISOString().slice(0, 10);

    for (let i = 1; i <= totalPages; i++) {
        pdf.setPage(i);

        // Add left footer
        pdf.text("v"+VERSION, margin, pageHeight - 5);

        // Add centre footer
        pdf.text(date, pageWidth / 2, pageHeight - 5, { align: "center" });

        // Add right footer
        pdf.text(`Page ${i} of ${totalPages}`, pageWidth - margin, pageHeight - 5, {align: "right"});
    }

    pdf.save("dual_crane_report.pdf");

    // restore chart transitions
    enableChartAnimation();
}

// Print pdf report page
export async function addReportPage(element) {
    const canvas = await html2canvas(element, {
        scale: 1.5,
        width: element.scrollWidth,
        height: element.scrollHeight
    });
    const img = canvas.toDataURL("image/jpeg");

    const imgProps = pdf.getImageProperties(img);

    const ratio = Math.min(
        usableWidth / imgProps.width,
        usableHeight / imgProps.height
    );

    const imgWidth = imgProps.width * ratio;
    const imgHeight = imgProps.height * ratio;

    const x = (pageWidth - imgWidth) / 2;
    const y = (pageHeight - imgHeight) / 2;

    if (currentPage > 0) {
        pdf.addPage();
    }
    pdf.addImage(img, "JPEG", x, y, imgWidth, imgHeight, undefined, "FAST");
}
