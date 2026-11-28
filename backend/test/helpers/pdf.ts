// Builds small PDFs for tests, so no binary fixtures or real CVs are committed.
import { PDFDocument, StandardFonts } from "pdf-lib";

// A made-up Finnish/English CV.
export const fictional_cv_lines = [
  "Maija Esimerkki",
  "Ohjelmistokehittäjä / Software Developer, Jyväskylä",
  "",
  "Kokemus / Experience",
  "Junior-kehittäjä, Esimerkki Oy (2024–2026)",
  "Built REST APIs with Node.js and PostgreSQL.",
  "",
  "Kielitaito: suomi (äidinkieli), englanti (sujuva), ruotsi (perustaso)",
];

// One PDF page per string; each "\n" starts a new line.
export async function make_pdf(pages: string[]): Promise<Buffer> {
  const doc = await PDFDocument.create();
  const font = await doc.embedFont(StandardFonts.Helvetica);
  for (const text of pages) {
    const page = doc.addPage([595, 842]);
    if (text) page.drawText(text, { x: 40, y: 800, size: 9, font, lineHeight: 11 });
  }
  return Buffer.from(await doc.save());
}

// A valid PDF with a drawing but no text, like a scanned document.
export async function make_pdf_without_text(): Promise<Buffer> {
  const doc = await PDFDocument.create();
  doc.addPage().drawRectangle({ x: 50, y: 50, width: 200, height: 100 });
  return Buffer.from(await doc.save());
}

// About `chars` characters of text spread over pages of 70 lines.
export async function make_long_pdf(chars: number): Promise<Buffer> {
  const line = "Lorem ipsum ohjelmistokehitys TypeScript PostgreSQL ".repeat(2).trim();
  const lines_needed = Math.ceil(chars / (line.length + 1));
  const pages: string[] = [];
  for (let i = 0; i < lines_needed; i += 70) {
    pages.push(Array(Math.min(70, lines_needed - i)).fill(line).join("\n"));
  }
  return make_pdf(pages);
}
