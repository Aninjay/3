import fs from "node:fs/promises";
import { Workbook } from "@oai/artifact-tool";

const sourcePath = "C:/Users/01diy/OneDrive/Documents/TAPMI/volunteers CSV.csv";
const outputPath = "C:/Users/01diy/OneDrive/Documents/TAPMI/deliverables/volunteer_interview_raw_data.csv";
const expectedHeaders = [
  "volunteer_id",
  "interviewed_by",
  "name",
  "skills",
  "availability_start",
  "availability_end",
  "max_hours",
  "experience_level",
  "department_preference",
];

const sourceCsv = await fs.readFile(sourcePath, "utf8");
const sourceWorkbook = await Workbook.fromCSV(sourceCsv, { sheetName: "Volunteer Raw Data" });
const sourceRows = sourceWorkbook
  .worksheets.getActiveWorksheet()
  .getRange("A1:I99")
  .values;

if (JSON.stringify(sourceRows[0]) !== JSON.stringify(expectedHeaders)) {
  throw new Error(`Unexpected source columns: ${JSON.stringify(sourceRows[0])}`);
}
if (sourceRows.length !== 99 || sourceRows.some((row) => row.length !== expectedHeaders.length)) {
  throw new Error(`Expected 98 data rows and 9 columns; found ${sourceRows.length - 1} rows.`);
}

const encodeCell = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
const outputCsv = sourceRows.map((row) => row.map(encodeCell).join(",")).join("\r\n") + "\r\n";
await fs.writeFile(outputPath, outputCsv, "utf8");

const savedWorkbook = await Workbook.fromCSV(await fs.readFile(outputPath, "utf8"), {
  sheetName: "Volunteer Raw Data",
});
const savedRows = savedWorkbook.worksheets.getActiveWorksheet().getRange("A1:I99").values;
if (JSON.stringify(savedRows) !== JSON.stringify(sourceRows)) {
  throw new Error("Saved CSV failed the row-by-row content check.");
}

process.stdout.write(JSON.stringify({ outputPath, dataRows: savedRows.length - 1, headers: savedRows[0] }));
