import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const WORKSPACE_DIR = "C:/Users/01diy/OneDrive/Documents/TAPMI";
const BUILD_DIR = path.join(WORKSPACE_DIR, ".presentation-build");
const OUTPUT_DIR = path.join(WORKSPACE_DIR, "deliverables");
const CANDIDATE_PATH = path.join(BUILD_DIR, "committee-demo-candidate-v3.pptx");
const FINAL_PPTX = path.join(OUTPUT_DIR, "TAPMI_Committee_Allocation_Demo.pptx");
const SKILL_DIR = "C:/Users/01diy/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations";
const {
  applyPresentationChartFont,
  finalizePresentation,
  resolvePresentationFont,
} = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);

const FONT = resolvePresentationFont();
const ORANGE = "#E8752E";
const DARK = "#242424";
const MUTED = "#6B6B6B";
const BORDER = "#E7E5E2";
const SUBTLE = "#F7F7F5";
const WHITE = "#FFFFFF";

const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

function addText(slide, { name, text, x, y, w, h, size = 24, color = DARK, bold = false, align = "left", valign = "top" }) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    fontSize: size,
    typeface: FONT,
    color,
    bold,
    alignment: align,
    verticalAlignment: valign,
    wrap: "square",
    autoFit: "shrinkText",
    insets: 0,
  };
  return shape;
}

function addSlide(title) {
  const slide = presentation.slides.add();
  slide.background.fill = WHITE;
  addText(slide, { name: "slide-title", text: title, x: 80, y: 54, w: 1120, h: 88, size: 48, bold: true });
  return slide;
}

function addNotes(slide, text) {
  slide.speakerNotes.text = text;
}

// 1. Cover
{
  const slide = presentation.slides.add();
  slide.background.fill = WHITE;
  addText(slide, { name: "institution", text: "TAPMI CULTURAL COMMITTEE", x: 84, y: 88, w: 760, h: 36, size: 21, color: ORANGE, bold: true });
  addText(slide, { name: "cover-title", text: "Kala Fest staffing allocation", x: 84, y: 202, w: 1080, h: 108, size: 64, bold: true });
  addText(slide, { name: "cover-subtitle", text: "Committee demo and technical brief", x: 84, y: 332, w: 950, h: 52, size: 30, color: MUTED });
  addText(slide, { name: "cover-date", text: "25 October 2026", x: 84, y: 545, w: 380, h: 34, size: 22, color: MUTED });
  addText(slide, { name: "cover-version", text: "Published roster version 7", x: 84, y: 590, w: 520, h: 36, size: 24, bold: true });
  addNotes(slide, "Source: TAPMI application and README.md. Live data checked on 25 October 2026 (Asia/Kolkata). The deck summarizes the published Kala Fest roster and the current implementation.");
}

// 2. Staffing snapshot
{
  const slide = addSlide("Six published positions remain open");
  addText(slide, { name: "filled-metric", text: "19 / 25", x: 84, y: 170, w: 300, h: 82, size: 66, color: ORANGE, bold: true });
  addText(slide, { name: "filled-label", text: "positions assigned", x: 84, y: 255, w: 300, h: 38, size: 23, color: MUTED });
  addText(slide, { name: "coverage-metric", text: "76%", x: 472, y: 170, w: 240, h: 82, size: 66, bold: true });
  addText(slide, { name: "coverage-label", text: "overall coverage", x: 472, y: 255, w: 300, h: 38, size: 23, color: MUTED });
  addText(slide, { name: "unassigned-metric", text: "82", x: 850, y: 170, w: 180, h: 82, size: 66, bold: true });
  addText(slide, { name: "unassigned-label", text: "active volunteers unassigned", x: 850, y: 255, w: 320, h: 60, size: 23, color: MUTED });

  const chart = slide.charts.add("bar", {
    position: { left: 78, top: 348, width: 1110, height: 260 },
    categories: ["Stage & Backstage Management", "IT & Technical Support"],
    series: [{ name: "Open positions", values: [4, 2], fill: ORANGE }],
    hasLegend: false,
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 100 },
    xAxis: {
      visible: true,
      textStyle: { fill: MUTED, fontSize: 17 },
      majorGridlines: null,
    },
    yAxis: { visible: false, majorGridlines: null },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { fill: DARK, fontSize: 20, bold: true } },
    chartFill: WHITE,
    chartLine: { style: "solid", fill: "none", width: 0 },
    plotAreaFill: WHITE,
    plotAreaLine: { style: "solid", fill: "none", width: 0 },
  });
  applyPresentationChartFont(chart, { fontFamily: FONT });
  addNotes(slide, "Source: live Reports page and the published_allocations pointer in backend/cultural_committee.db. Version 7 has 19 assignments against 25 required roles. The 6 vacancies are 4 in Stage & Backstage Management (Critical) and 2 in IT & Technical Support (High). The same version has 82 active volunteers without an assignment.");
}

// 3. Observed algorithm comparison
{
  const slide = addSlide("Greedy and ILP fill the same number in this run");
  addText(slide, { name: "comparison-subtitle", text: "Both methods use the current requirements and the same hard eligibility checks.", x: 82, y: 150, w: 1100, h: 46, size: 25, color: MUTED });
  const values = [
    ["Method", "Filled", "Coverage", "Top-two preferences", "Observed runtime"],
    ["Greedy baseline", "19 / 25", "76%", "2 volunteers", "0.0062 seconds"],
    ["PuLP ILP", "19 / 25", "76%", "1 volunteer", "0.168 seconds"],
  ];
  const table = slide.tables.add({
    rows: values.length,
    columns: values[0].length,
    left: 80,
    top: 244,
    width: 1120,
    height: 174,
    columnWidths: [220, 165, 145, 280, 310],
    values,
  });
  table.borders.assign({ style: "solid", fill: BORDER, width: 1 });
  for (let row = 0; row < values.length; row += 1) {
    table.rows[row].height = row === 0 ? 52 : 61;
    for (let column = 0; column < values[0].length; column += 1) {
      const cell = table.getCell(row, column);
      cell.fill = row === 0 ? ORANGE : (row === 1 ? WHITE : SUBTLE);
      cell.text.style = {
        fontSize: row === 0 ? 19 : 22,
        typeface: FONT,
        color: row === 0 ? WHITE : DARK,
        bold: row === 0 || column === 0,
        alignment: column === 0 ? "left" : "center",
        verticalAlignment: "middle",
        wrap: "square",
        autoFit: "shrinkText",
        insets: { left: 12, right: 12, top: 5, bottom: 5 },
      };
    }
  }
  addText(slide, { name: "comparison-takeaway", text: "No fill gain under ILP in this run. Greedy matched one more top-two preference.", x: 82, y: 478, w: 1080, h: 54, size: 25, bold: true });
  addText(slide, { name: "comparison-caveat", text: "Runtime varies by request. These timings describe one live run, not a general speed guarantee.", x: 82, y: 555, w: 1080, h: 48, size: 21, color: MUTED });
  addNotes(slide, "Source: Reports & Allocation in the live app on 25 October 2026. The observed snapshot showed 19/25 and 76% for both algorithms, 2 versus 1 assignments within volunteers' top-two department preferences, and runtimes 0.0062s versus 0.168s. The numbers are request-level timings and vary on rerun.");
}

// 4. Allocation logic
{
  const slide = addSlide("How the two methods make assignments");
  addText(slide, { name: "greedy-heading", text: "Priority-first Greedy", x: 82, y: 166, w: 500, h: 42, size: 30, color: ORANGE, bold: true });
  addText(slide, {
    name: "greedy-explanation",
    text: "Critical roles come first, then High, then Normal.\n\nWithin each tier, +10 per preferred-skill match. Department preference adds +15 / +10 / +5; experience adds +1 per year.\n\nClear and fast. Earlier choices can limit later matches.",
    x: 82, y: 222, w: 500, h: 242, size: 23,
  });
  addText(slide, { name: "ilp-heading", text: "PuLP ILP with CBC", x: 672, y: 166, w: 520, h: 42, size: 30, color: ORANGE, bold: true });
  addText(slide, {
    name: "ilp-explanation",
    text: "A binary choice represents each eligible person and role slot.\n\nPer filled slot: +100 base; priority adds +50 / +25 / +10. Fit adds up to +10 for preferred skills, +8 / +4 / +2 for department preference, and +0.5 per experience year.\n\nAt most one person per slot and one role per volunteer.",
    x: 672, y: 222, w: 520, h: 242, size: 22,
  });
  addText(slide, { name: "eligibility-heading", text: "Shared eligibility rules", x: 82, y: 492, w: 420, h: 38, size: 26, bold: true });
  addText(slide, { name: "eligibility-copy", text: "Active account, mandatory skills, event availability, and maximum hours. Vacancies remain open when no eligible person can take them.", x: 82, y: 539, w: 1100, h: 64, size: 22 });
  addText(slide, { name: "fairness-gap", text: "Current code has no explicit fairness score, and its weights are not centralized.", x: 82, y: 625, w: 1100, h: 34, size: 19, color: MUTED, bold: true });
  addNotes(slide, "Sources: backend/app/allocation/greedy.py, ilp_optimizer.py, eligibility.py, and ALLOCATION_ALGORITHM.md. The code currently hard-codes the stated score additions. The algorithm specification says exact objective weights and a measurable fairness metric remain open; the current ILP objective does not include an explicit fairness term. These implementation weights should not be represented as committee-approved policy.");
}

// 5. Architecture and governance
{
  const slide = addSlide("Application architecture and publication controls");
  const columns = [
    { x: 82, heading: "React + Vite", copy: "Organizer and volunteer portals. Flask serves the compiled frontend in deployment." },
    { x: 455, heading: "Flask + Python", copy: "Role-protected API, event workflows, reports, simulation, Greedy, and PuLP/CBC." },
    { x: 828, heading: "PostgreSQL", copy: "Stores profiles, skills, requirements, assignments, versions, and audit history. SQLite supports local setup." },
  ];
  for (const [index, column] of columns.entries()) {
    addText(slide, { name: `architecture-heading-${index}`, text: column.heading, x: column.x, y: 184, w: 330, h: 45, size: 30, color: ORANGE, bold: true });
    addText(slide, { name: `architecture-copy-${index}`, text: column.copy, x: column.x, y: 242, w: 325, h: 160, size: 23 });
  }
  addText(slide, { name: "publication-heading", text: "Draft, review, approval, publication", x: 82, y: 458, w: 940, h: 42, size: 27, bold: true });
  addText(slide, {
    name: "publication-copy",
    text: "The solver creates a draft. Organizers can review and edit it, then approve a specific version before publishing. Volunteers see their own published assignments only. Simulations use a copy of the inputs.",
    x: 82, y: 512, w: 1090, h: 112, size: 23,
  });
  addNotes(slide, "Sources: ARCHITECTURE.md, DATABASE_SCHEMA.md, backend/app/__init__.py, backend/app/auth_middleware.py, backend/app/routes/allocation_routes.py, and backend/app/routes/simulation_routes.py. Convener and Co-convener have organizer access; volunteer sessions are scoped to the signed-in volunteer.");
}

// 6. Department export formats
{
  const slide = addSlide("Department rosters come from the published version");
  addText(slide, { name: "csv-heading", text: "CSV", x: 84, y: 180, w: 420, h: 48, size: 34, color: ORANGE, bold: true });
  addText(slide, { name: "csv-copy", text: "One row per assigned volunteer.\n\nDepartment, role, priority, volunteer name, and student ID.\n\nEasy to filter or import into another sheet.", x: 84, y: 246, w: 480, h: 220, size: 24 });
  addText(slide, { name: "excel-heading", text: "Excel workbook", x: 672, y: 180, w: 480, h: 48, size: 34, color: ORANGE, bold: true });
  addText(slide, { name: "excel-copy", text: "A summary sheet shows required, assigned, vacant, and coverage totals.\n\nOne worksheet per department lists assigned volunteers.\n\nThe current workbook includes eight department sheets.", x: 672, y: 246, w: 510, h: 220, size: 24 });
  addText(slide, { name: "export-control", text: "Organizer login and a published allocation are required. Department heads receive files from the Convener or Co-convener; this build has no separate department-head login.", x: 84, y: 535, w: 1090, h: 90, size: 22, color: MUTED, bold: true });
  addNotes(slide, "Sources: backend/app/routes/report_routes.py and frontend/src/pages/ReportsPage.jsx. The roster endpoint uses the published allocation pointer, returns HTTP 409 when no version is published, and requires the Convener or Co-convener role. CSV includes all assigned records. The Excel workbook has a roster summary and one worksheet for each department with requirements.");
}

// 7. Production-style Compose
{
  const slide = addSlide("Docker Compose runs the production web stack");
  const blocks = [
    ["PostgreSQL 16", "Persistent database volume and health check."],
    ["Python 3.12 + Gunicorn", "Flask API serves the built React app."],
    ["Startup sequence", "Wait for PostgreSQL, apply migrations, seed the catalog, then start Gunicorn."],
    ["Production data defaults", "Known demo accounts and sample records stay off. Bootstrap an organizer through .env; keep SEED_DEMO_DATA=false."],
  ];
  for (const [index, [heading, copy]] of blocks.entries()) {
    const y = 165 + index * 112;
    addText(slide, { name: `compose-heading-${index}`, text: heading, x: 84, y, w: 340, h: 42, size: 25, color: ORANGE, bold: true });
    addText(slide, { name: `compose-copy-${index}`, text: copy, x: 440, y, w: 730, h: 70, size: 24 });
  }
  addText(slide, { name: "compose-caveat", text: "Single-host deployment. Configure HTTPS, backups, and an approved OTP email provider before real committee use.", x: 84, y: 630, w: 1100, h: 38, size: 19, color: MUTED });
  addNotes(slide, "Sources: Dockerfile, docker-compose.yml, .env.compose.example, backend/app/db/seed.py, backend/app/db/connection.py, and README.md. SEED_DEMO_DATA defaults to false. With an organizer bootstrap email and password, startup seeds the department and skill catalog without demo users or sample volunteers/events. The current activation flow prints OTP codes to application logs and does not connect to an email provider.");
}

// 8. Demo runbook and decisions
{
  const slide = addSlide("Live demo and production decisions");
  addText(slide, { name: "demo-heading", text: "Live demo", x: 82, y: 165, w: 450, h: 42, size: 30, color: ORANGE, bold: true });
  addText(slide, {
    name: "demo-steps",
    text: "Open http://localhost:5000 and choose the Convener demo account.\n\nOpen Reports & Allocation to compare the current snapshot.\n\nReview six open positions, then download the published CSV or Excel roster.\n\nUse the volunteer account to show the personal published-assignment view.",
    x: 82, y: 222, w: 510, h: 370, size: 22,
  });
  addText(slide, { name: "decisions-heading", text: "Before live deployment", x: 682, y: 165, w: 500, h: 42, size: 30, color: ORANGE, bold: true });
  addText(slide, {
    name: "production-decisions",
    text: "Approve and centralize the score weights. Define a measurable fairness policy.\n\nConnect a vetted email provider for volunteer activation.\n\nUse unique secrets and organizer credentials. Keep demo seeding off.\n\nDecide whether department heads need their own authenticated access.",
    x: 682, y: 222, w: 510, h: 370, size: 22,
  });
  addNotes(slide, "Sources: README.md, PRD.md, ALLOCATION_ALGORITHM.md, backend/app/services/auth_service.py, and the current web app. Do not place demo passwords in a shareable deck. The login screen has quick demo buttons for the supplied test accounts. Production deployment should use unique organizer credentials, avoid demo seeding, approve the scoring policy, and integrate OTP delivery.");
}

await fs.mkdir(BUILD_DIR, { recursive: true });
await fs.mkdir(OUTPUT_DIR, { recursive: true });

// Export editable draft and previews before validation.
for (const [index, slide] of presentation.slides.items.entries()) {
  const preview = await presentation.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(path.join(BUILD_DIR, `slide-${String(index + 1).padStart(2, "0")}.png`), new Uint8Array(await preview.arrayBuffer()));
}
await (await PresentationFile.exportPptx(presentation)).save(CANDIDATE_PATH);

const integrityValidatorPath = path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py");
const layoutValidatorPath = path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py");
const runtimePython = "C:/Users/01diy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const receiptPath = path.join(BUILD_DIR, "committee-demo-validation-v3.json");
const result = await finalizePresentation({
  workspaceDir: WORKSPACE_DIR,
  candidatePath: CANDIDATE_PATH,
  finalPath: FINAL_PPTX,
  pythonExecutable: runtimePython,
  integrityValidatorPath,
  layoutValidatorPath,
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
    "--require-native-table-slide", "3",
  ],
  explicitTotalSlideCount: 8,
  requiredNativeTableOwnerSlides: [3],
  requiredNativeChartOwnerSlides: [2],
  materializeLiteralChartWorkbooks: true,
  fontPolicy: { basis: "design", families: [FONT] },
  expectedSlideSizeEmu: "12192000,6858000",
  verifyArtifactToolImport: true,
  receiptPath,
});

console.log(JSON.stringify({
  finalPptx: FINAL_PPTX,
  slideCount: presentation.slides.items.length,
  font: FONT,
  finalization: result,
}, null, 2));
