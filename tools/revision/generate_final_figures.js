#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const sharp = require("sharp");

const root = path.resolve(__dirname, "..", "..");
const sourceDir = process.env.SHM_EM_SUBMITTED_FIGURES;
if (!sourceDir) {
  throw new Error("Set SHM_EM_SUBMITTED_FIGURES to the directory containing the submitted figure assets.");
}
const outputDir = path.join(root, "artifacts", "revision", "final-submission", "figures");
fs.mkdirSync(outputDir, { recursive: true });

const C = {
  navy: "#0b3c82",
  blue: "#1769e8",
  teal: "#087f83",
  green: "#169b62",
  orange: "#d66a00",
  red: "#c62828",
  ink: "#172033",
  muted: "#5e6b80",
  line: "#a9bfd9",
  paleBlue: "#f2f7fd",
  paleTeal: "#f1fbfa",
  paleOrange: "#fff8ef",
  paleRed: "#fff4f4",
  white: "#ffffff",
};

const esc = (value) => String(value)
  .replace(/&/g, "&amp;")
  .replace(/</g, "&lt;")
  .replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;");

function svgText(x, y, lines, options = {}) {
  const {
    size = 42,
    weight = 500,
    fill = C.ink,
    anchor = "start",
    lineHeight = Math.round(size * 1.25),
    family = "Arial, Helvetica, sans-serif",
  } = options;
  const items = Array.isArray(lines) ? lines : [lines];
  const tspans = items.map((line, index) =>
    `<tspan x="${x}" dy="${index === 0 ? 0 : lineHeight}">${esc(line)}</tspan>`
  ).join("");
  return `<text x="${x}" y="${y}" font-family="${family}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}">${tspans}</text>`;
}

function roundedRect(x, y, w, h, options = {}) {
  const { fill = C.white, stroke = C.line, strokeWidth = 4, radius = 18, dash = "" } = options;
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"${dash ? ` stroke-dasharray="${dash}"` : ""}/>`;
}

function circleLabel(x, y, label, fill = C.navy) {
  return `<circle cx="${x}" cy="${y}" r="50" fill="${fill}"/>${svgText(x, y + 16, label, { size: 50, weight: 700, fill: C.white, anchor: "middle" })}`;
}

function arrow(x1, y1, x2, y2, color = C.navy, dashed = false) {
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="10"${dashed ? ' stroke-dasharray="24 18"' : ""} marker-end="url(#arrow)"/>`;
}

function defs() {
  return `<defs>
    <marker id="arrow" markerWidth="16" markerHeight="16" refX="13" refY="6" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,12 L14,6 z" fill="context-stroke"/>
    </marker>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="130%">
      <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#23344d" flood-opacity="0.12"/>
    </filter>
  </defs>`;
}

function frame(width, height, body) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
    ${defs()}
    <rect width="${width}" height="${height}" fill="#ffffff"/>
    ${body}
  </svg>`;
}

async function saveSvgAndPng(baseName, svg, density = 600) {
  const svgPath = path.join(outputDir, `${baseName}.svg`);
  const pngPath = path.join(outputDir, `${baseName}.png`);
  fs.writeFileSync(svgPath, svg, "utf8");
  await sharp(Buffer.from(svg)).png({ compressionLevel: 9 }).withMetadata({ density }).toFile(pngPath);
}

function flowBox(x, y, w, h, title, detail, options = {}) {
  const { stroke = C.line, fill = C.white, titleFill = C.ink, detailFill = C.muted } = options;
  return `${roundedRect(x, y, w, h, { fill, stroke, strokeWidth: 5, radius: 20 })}
    ${svgText(x + 30, y + 58, title, { size: 40, weight: 700, fill: titleFill })}
    ${detail ? svgText(x + 30, y + 112, detail, { size: 31, weight: 400, fill: detailFill, lineHeight: 40 }) : ""}`;
}

async function buildFigure3() {
  const width = 4200;
  const height = 2550;
  let body = "";

  const panels = [
    { x: 70, y: 70, w: 4060, h: 690, label: "A", title: "Persisted forecast and optional Project Future State", color: C.navy, fill: C.paleBlue },
    { x: 70, y: 810, w: 4060, h: 650, label: "B", title: "Evaluate: candidate calculation with no formal business side effects", color: C.blue, fill: C.paleBlue },
    { x: 70, y: 1510, w: 4060, h: 970, label: "C", title: "Execute: independent Gate recheck, formal transaction, and provenance", color: C.teal, fill: C.paleTeal },
  ];
  for (const panel of panels) {
    body += roundedRect(panel.x, panel.y, panel.w, panel.h, { fill: panel.fill, stroke: panel.color, strokeWidth: 5, radius: 26 });
    body += circleLabel(panel.x + 70, panel.y + 70, panel.label, panel.color);
    body += svgText(panel.x + 145, panel.y + 87, panel.title, { size: 48, weight: 700, fill: panel.color });
  }

  const aY = 280;
  body += flowBox(150, aY, 650, 300, "1  Registered batch", ["PIT_PRE reads the active", "observation/model contract"], { stroke: C.navy });
  body += arrow(800, aY + 150, 920, aY + 150, C.navy);
  body += flowBox(930, aY, 720, 300, "2  Persisted prediction state", ["Batch, runs, point forecasts,", "bundle and result hashes"], { stroke: C.navy });
  body += arrow(1650, aY + 150, 1770, aY + 150, C.navy);
  body += flowBox(1780, aY, 760, 300, "3  Gate inspection", ["Contract, model/feature sets,", "40-step timeline, quality, hashes"], { stroke: C.navy });
  body += arrow(2540, aY + 150, 2660, aY + 150, C.navy);
  body += flowBox(2670, aY, 720, 300, "4  Future-state read", ["Target -> station -> project", "state; deterministic state hash"], { stroke: C.teal, fill: C.white });
  body += arrow(3390, aY + 150, 3510, aY + 150, C.teal);
  body += flowBox(3520, aY, 520, 300, "5  View", ["Eligibility, blockers,", "risk timeline"], { stroke: C.teal, fill: C.white });
  body += svgText(1780, 655, "Optional independent read path: Project Future State is not consumed by Execute.", { size: 34, weight: 600, fill: C.teal });

  const bY = 1010;
  body += flowBox(150, bY, 620, 280, "6  Evaluate request", ["Rule + batch", "mode = REPLAY"], { stroke: C.blue });
  body += arrow(770, bY + 140, 910, bY + 140, C.blue);
  body += flowBox(920, bY, 740, 280, "7  Canonical series", ["Load rule and engineering-valued", "observation/forecast series"], { stroke: C.blue });
  body += arrow(1660, bY + 140, 1800, bY + 140, C.blue);
  body += flowBox(1810, bY, 700, 280, "8  Gate inspect", ["Re-read persisted prediction state", "without a persisted Gate record"], { stroke: C.blue });
  body += arrow(2510, bY + 140, 2650, bY + 140, C.blue);
  body += flowBox(2660, bY, 700, 280, "9  Rule calculation", ["Validate unit and semantics;", "compute simulated candidates"], { stroke: C.blue });
  body += arrow(3360, bY + 140, 3500, bY + 140, C.blue);
  body += flowBox(3510, bY, 530, 280, "10  Result", ["Candidate + calculation snapshot", "Evaluation/audit run only"], { stroke: C.blue });
  body += svgText(3510, 1375, "No formal event, Gate record, workflow, response, report, notification, or prediction link.", { size: 29, weight: 600, fill: C.red, anchor: "end" });

  const cY = 1710;
  body += flowBox(150, cY, 570, 280, "11  Execute request", ["Rule + batch + mode", "OPERATIONAL or REPRODUCTION"], { stroke: C.teal });
  body += arrow(720, cY + 140, 840, cY + 140, C.teal);
  body += flowBox(850, cY, 670, 280, "12  Reload state", ["Rule and canonical series", "read again"], { stroke: C.teal });
  body += arrow(1520, cY + 140, 1640, cY + 140, C.teal);
  body += flowBox(1650, cY, 690, 280, "13  Gate evaluate", ["Revalidate persisted state", "and persist a new Gate record"], { stroke: C.teal });
  body += arrow(2340, cY + 140, 2460, cY + 140, C.teal);
  body += flowBox(2470, cY, 700, 280, "14  Rule calculation", ["Validate units and semantics;", "compute formal event candidate"], { stroke: C.teal });
  body += arrow(3170, cY + 140, 3290, cY + 140, C.teal);
  body += flowBox(3300, cY, 740, 280, "15  Formal transaction", ["Event + batch/run/model/Gate link", "Response workflow + report state"], { stroke: C.green, fill: C.white });

  body += roundedRect(150, 2070, 2190, 300, { fill: C.paleRed, stroke: C.red, strokeWidth: 5, radius: 20 });
  body += svgText(190, 2140, "Blocked path", { size: 40, weight: 700, fill: C.red });
  body += svgText(190, 2200, ["If executionEligible = false, return typed blockers before", "any formal-event side effect."], { size: 34, fill: C.ink, lineHeight: 44 });
  body += roundedRect(2470, 2070, 1570, 300, { fill: C.white, stroke: C.teal, strokeWidth: 5, radius: 20 });
  body += svgText(2510, 2140, "16  Auditable trace", { size: 40, weight: 700, fill: C.teal });
  body += svgText(2510, 2200, ["Resolve rule, Gate, batch, run, model/hash, input window,", "forecast snapshot, event, and response records."], { size: 32, fill: C.ink, lineHeight: 42 });
  body += arrow(3670, 1995, 3670, 2050, C.teal);

  await saveSvgAndPng("Fig3_Forecast_to_Event_Sequence", frame(width, height, body));
}

async function cropToDataUrl(imagePath, crop, width, height) {
  const buffer = await sharp(imagePath)
    .extract(crop)
    .resize(width, height, { fit: "contain", position: "centre", background: "#ffffff" })
    .png({ compressionLevel: 9 })
    .toBuffer();
  return `data:image/png;base64,${buffer.toString("base64")}`;
}

function imageTag(href, x, y, w, h) {
  return `<image href="${href}" x="${x}" y="${y}" width="${w}" height="${h}" preserveAspectRatio="xMidYMid slice"/>`;
}

async function buildFigure4() {
  const a = path.join(sourceDir, "Fig4_User_Interfaces_(a).png");
  const b = path.join(sourceDir, "Fig4_User_Interfaces_(b).png");
  const c = path.join(sourceDir, "Fig4_User_Interfaces_(c).png");
  for (const source of [a, b, c]) {
    if (!fs.existsSync(source)) throw new Error(`Missing Figure 4 source: ${source}`);
  }

  const aKpi = await cropToDataUrl(a, { left: 640, top: 175, width: 3850, height: 275 }, 1670, 150);
  const aMap = await cropToDataUrl(a, { left: 640, top: 455, width: 2600, height: 1600 }, 1670, 990);
  const aTrend = await cropToDataUrl(a, { left: 640, top: 2110, width: 2600, height: 1210 }, 1670, 690);
  const bKpi = await cropToDataUrl(b, { left: 550, top: 405, width: 3220, height: 215 }, 2000, 135);
  const bTrend = await cropToDataUrl(b, { left: 1130, top: 625, width: 2650, height: 850 }, 2000, 680);
  const cTop = await cropToDataUrl(c, { left: 590, top: 390, width: 3160, height: 540 }, 2000, 350);
  const cTable = await cropToDataUrl(c, { left: 590, top: 960, width: 2210, height: 550 }, 1320, 350);
  const cDetail = await cropToDataUrl(c, { left: 2820, top: 900, width: 850, height: 1280 }, 660, 730);

  const width = 4200;
  const height = 2400;
  let body = "";
  body += roundedRect(40, 40, 1790, 2320, { stroke: C.navy, strokeWidth: 5, radius: 20 });
  body += roundedRect(1870, 40, 2290, 1090, { stroke: C.blue, strokeWidth: 5, radius: 20 });
  body += roundedRect(1870, 1170, 2290, 1190, { stroke: C.teal, strokeWidth: 5, radius: 20 });

  body += circleLabel(105, 105, "a", C.navy);
  body += svgText(175, 120, "Project Workspace", { size: 48, weight: 700, fill: C.navy });
  body += imageTag(aKpi, 100, 165, 1670, 150);
  body += imageTag(aMap, 100, 345, 1670, 990);
  body += imageTag(aTrend, 100, 1370, 1670, 690);
  body += svgText(100, 2135, ["Observed and forecast risk are shown together with the", "earliest predicted exceedance and engineering-valued trend."], { size: 33, fill: C.muted, lineHeight: 42 });

  body += circleLabel(1935, 105, "b", C.blue);
  body += svgText(2005, 120, "Observation and Prediction", { size: 48, weight: 700, fill: C.blue });
  body += imageTag(bKpi, 1980, 185, 2060, 140);
  body += imageTag(bTrend, 1980, 350, 2060, 700);

  body += circleLabel(1935, 1235, "c", C.teal);
  body += svgText(2005, 1250, "Prediction Runs", { size: 48, weight: 700, fill: C.teal });
  body += imageTag(cTop, 1980, 1310, 2060, 350);
  body += imageTag(cTable, 1980, 1695, 1335, 350);
  body += imageTag(cDetail, 3345, 1695, 695, 610);
  body += svgText(1980, 2115, ["One batch records six model runs, 124 target channels,", "40 synchronized future steps, completeness, and Gate status."], { size: 32, fill: C.muted, lineHeight: 41 });

  await saveSvgAndPng("Fig4_Task_Oriented_Interface_Composite", frame(width, height, body), 600);
}

async function buildFigure5() {
  const source = path.join(sourceDir, "Fig5_Reference_Workflow.png");
  if (!fs.existsSync(source)) throw new Error(`Missing Figure 5 source: ${source}`);
  const referencePanel = await cropToDataUrl(source, { left: 0, top: 0, width: 590, height: 1086 }, 1570, 2840);
  const width = 4200;
  const height = 3000;
  let body = "";

  body += roundedRect(35, 35, 1630, 2930, { stroke: C.navy, strokeWidth: 5, radius: 24 });
  body += imageTag(referencePanel, 65, 65, 1570, 2840);

  body += roundedRect(1695, 35, 1010, 2930, { fill: C.paleTeal, stroke: C.teal, strokeWidth: 5, radius: 24 });
  body += circleLabel(1770, 115, "B", C.teal);
  body += svgText(1850, 132, "Forecast contract", { size: 54, weight: 700, fill: C.teal });

  const contractRows = [
    ["9 field points", "registered engineering objects"],
    ["6 fixed-version models", "bundle and preprocessor hashes"],
    ["Input widths", "114 / 114 / 114 / 114 / 114 / 164"],
    ["Output widths", "42 / 42 / 14 / 14 / 2 / 10 = 124"],
    ["Feature mappings", "model-owned, ordered, and versioned"],
    ["16 historical steps", "aligned engineering-valued inputs"],
    ["40 future steps", "3-min interval; +120 min horizon"],
  ];
  let rowY = 245;
  for (let index = 0; index < contractRows.length; index += 1) {
    body += roundedRect(1750, rowY, 900, 255, { fill: C.white, stroke: C.line, strokeWidth: 4, radius: 18 });
    body += circleLabel(1815, rowY + 65, String(index + 1), C.teal);
    body += svgText(1890, rowY + 76, contractRows[index][0], { size: 39, weight: 700, fill: C.ink });
    body += svgText(1890, rowY + 137, contractRows[index][1], { size: 31, fill: C.muted });
    rowY += 285;
  }
  body += roundedRect(1750, 2265, 900, 580, { fill: C.white, stroke: C.teal, strokeWidth: 4, radius: 18 });
  body += svgText(1795, 2335, "Common temporal frame", { size: 40, weight: 700, fill: C.teal });
  body += svgText(1795, 2400, "History", { size: 32, weight: 600, fill: C.navy });
  body += svgText(2585, 2400, "Forecast", { size: 32, weight: 600, fill: C.teal, anchor: "end" });
  body += `<line x1="1810" y1="2520" x2="2590" y2="2520" stroke="${C.line}" stroke-width="10"/>`;
  for (let i = 0; i < 8; i += 1) body += `<circle cx="${1830 + i * 65}" cy="2520" r="18" fill="${C.navy}"/>`;
  body += `<circle cx="2355" cy="2520" r="28" fill="${C.white}" stroke="${C.ink}" stroke-width="6"/>`;
  for (let i = 0; i < 5; i += 1) body += `<circle cx="${2395 + i * 50}" cy="2520" r="18" fill="${C.teal}"/>`;
  body += svgText(1810, 2600, "h-15", { size: 30, fill: C.muted });
  body += svgText(2355, 2600, "h0", { size: 30, fill: C.ink, anchor: "middle" });
  body += svgText(2590, 2600, "h40", { size: 30, fill: C.muted, anchor: "end" });
  body += svgText(1795, 2715, ["Database contract is authoritative; runtime", "configuration supplies connection and work paths only."], { size: 30, fill: C.muted, lineHeight: 40 });

  body += roundedRect(2735, 35, 1430, 2930, { fill: C.paleBlue, stroke: C.navy, strokeWidth: 5, radius: 24 });
  body += circleLabel(2810, 115, "C", C.navy);
  body += svgText(2890, 132, "End-to-end reproduction", { size: 54, weight: 700, fill: C.navy });

  const steps = [
    ["Public sample", "2,464 observations; 9 points"],
    ["Six-model prediction", "124 channels x 40 steps"],
    ["Gate and Future State", "integrity + synchronized project risk"],
    ["Evaluate (REPLAY)", "candidate + audit; no formal side effects"],
    ["Execute (REPRODUCTION)", "independent Gate + formal transaction"],
    ["Provenance verification", "event-to-model/input/evidence trace"],
  ];
  let stepY = 240;
  for (let index = 0; index < steps.length; index += 1) {
    body += flowBox(2790, stepY, 780, 260, `${index + 1}  ${steps[index][0]}`, steps[index][1], { stroke: index < 2 ? C.navy : C.teal, fill: C.white });
    if (index < steps.length - 1) body += arrow(3180, stepY + 260, 3180, stepY + 330, index < 1 ? C.navy : C.teal);
    stepY += 390;
  }

  body += roundedRect(3610, 240, 500, 2265, { fill: C.white, stroke: C.line, strokeWidth: 4, radius: 18 });
  body += svgText(3860, 315, "Verified outputs", { size: 39, weight: 700, fill: C.navy, anchor: "middle" });
  const results = [
    ["Model runs", "6 / 6"],
    ["Target channels", "124 / 124"],
    ["Forecast records", "4,960"],
    ["Engineering conversion", "0 errors"],
    ["Referential integrity", "0 errors"],
    ["Failure matrix", "15 / 15"],
    ["Backend tests", "55 / 55"],
    ["Frontend checks", "2 / 2"],
    ["Formal provenance", "verified"],
  ];
  let resultY = 395;
  for (const [name, value] of results) {
    body += `<line x1="3640" y1="${resultY + 165}" x2="4080" y2="${resultY + 165}" stroke="#d8e3ef" stroke-width="3"/>`;
    body += svgText(3665, resultY + 55, name, { size: 31, weight: 600, fill: C.ink });
    body += svgText(4050, resultY + 115, value, { size: 34, weight: 700, fill: value.includes("errors") ? C.green : C.navy, anchor: "end" });
    resultY += 225;
  }
  body += roundedRect(3610, 2550, 500, 295, { fill: C.paleOrange, stroke: C.orange, strokeWidth: 4, radius: 18 });
  body += svgText(3860, 2620, "Runtime scope", { size: 36, weight: 700, fill: C.orange, anchor: "middle" });
  body += svgText(3860, 2680, ["software workflow latency;", "not forecast accuracy"], { size: 29, fill: C.ink, anchor: "middle", lineHeight: 39 });

  await saveSvgAndPng("Fig5_Public_Reference_Workflow", frame(width, height, body), 600);
}

async function main() {
  await buildFigure3();
  await buildFigure4();
  await buildFigure5();
  for (const name of [
    "Fig3_Forecast_to_Event_Sequence",
    "Fig4_Task_Oriented_Interface_Composite",
    "Fig5_Public_Reference_Workflow",
  ]) {
    const png = path.join(outputDir, `${name}.png`);
    const metadata = await sharp(png).metadata();
    process.stdout.write(`${name}: ${metadata.width}x${metadata.height}, density=${metadata.density || "n/a"}\n`);
  }
}

main().catch((error) => {
  console.error(error.stack || error.message || error);
  process.exit(1);
});
