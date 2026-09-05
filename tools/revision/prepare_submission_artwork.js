#!/usr/bin/env node
"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const sharp = require("sharp");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..", "..");
const figures = path.join(root, "artifacts", "revision", "final-submission", "figures");
const finalWidthMm = 175;
const rasterDensity = 610;
const browserExecutable = process.env.SHM_EM_BROWSER_EXECUTABLE
  || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";

const vectorFigures = [
  "Fig1_Research_Gap_and_Workflow",
  "Fig2_Software_Architecture",
  "Fig3_Forecast_to_Event_Sequence",
];
const rasterFigures = [
  "Fig4_Task_Oriented_Interface_Composite",
  "Fig5_Public_Reference_Workflow",
];

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function svgDimensions(svg) {
  const viewBox = svg.match(/viewBox="0 0 ([0-9.]+) ([0-9.]+)"/);
  if (!viewBox) throw new Error("SVG is missing a numeric viewBox");
  return { width: Number(viewBox[1]), height: Number(viewBox[2]) };
}

async function svgToPdf(browser, baseName) {
  const source = path.join(figures, `${baseName}.svg`);
  const destination = path.join(figures, `${baseName}.pdf`);
  const svg = fs.readFileSync(source, "utf8");
  const dimensions = svgDimensions(svg);
  const heightMm = finalWidthMm * dimensions.height / dimensions.width;
  const page = await browser.newPage();
  await page.setContent(`<!doctype html><html><head><style>
    @page { size: ${finalWidthMm}mm ${heightMm.toFixed(4)}mm; margin: 0; }
    html, body { margin: 0; padding: 0; width: ${finalWidthMm}mm; height: ${heightMm.toFixed(4)}mm; overflow: hidden; }
    svg { display: block; width: ${finalWidthMm}mm; height: ${heightMm.toFixed(4)}mm; }
  </style></head><body>${svg}</body></html>`, { waitUntil: "load" });
  await page.pdf({
    path: destination,
    width: `${finalWidthMm}mm`,
    height: `${heightMm.toFixed(4)}mm`,
    margin: { top: "0", right: "0", bottom: "0", left: "0" },
    printBackground: true,
    preferCSSPageSize: true,
  });
  await page.close();
  return {
    name: baseName,
    submissionFormat: "PDF",
    path: path.relative(root, destination).replace(/\\/g, "/"),
    physicalWidthMm: finalWidthMm,
    physicalHeightMm: Number(heightMm.toFixed(3)),
    sha256: sha256(destination),
  };
}

async function pngToTiff(baseName) {
  const source = path.join(figures, `${baseName}.png`);
  const destination = path.join(figures, `${baseName}.tiff`);
  const metadata = await sharp(source).metadata();
  await sharp(source)
    .withMetadata({ density: rasterDensity })
    .tiff({ compression: "lzw", quality: 100 })
    .toFile(destination);
  const effectiveDpi = metadata.width / (finalWidthMm / 25.4);
  return {
    name: baseName,
    submissionFormat: "TIFF",
    path: path.relative(root, destination).replace(/\\/g, "/"),
    pixels: { width: metadata.width, height: metadata.height },
    physicalWidthMm: finalWidthMm,
    effectiveDpiAtFinalWidth: Number(effectiveDpi.toFixed(2)),
    embeddedDensityDpi: rasterDensity,
    sha256: sha256(destination),
  };
}

async function main() {
  for (const name of [...vectorFigures, ...rasterFigures]) {
    const source = path.join(figures, `${name}.${vectorFigures.includes(name) ? "svg" : "png"}`);
    if (!fs.existsSync(source)) throw new Error(`Missing artwork source: ${source}`);
  }

  if (!fs.existsSync(browserExecutable)) {
    throw new Error(`Browser executable not found: ${browserExecutable}`);
  }
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable });
  let artifacts;
  try {
    artifacts = [];
    for (const name of vectorFigures) artifacts.push(await svgToPdf(browser, name));
  } finally {
    await browser.close();
  }
  for (const name of rasterFigures) artifacts.push(await pngToTiff(name));

  const manifest = {
    schemaVersion: "shm-em-submission-artwork-v1",
    finalWidthMm,
    policy: {
      vector: "PDF generated from editable SVG source",
      hybridRaster: "TIFF at >=500 dpi at final physical width",
    },
    artifacts,
  };
  const manifestPath = path.join(figures, "submission-artwork-manifest.json");
  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify(manifest, null, 2)}\n`);
}

main().catch((error) => {
  console.error(error.stack || error.message || error);
  process.exit(1);
});
