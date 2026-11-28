import { getDocumentProxy } from "unpdf";
import { api_error } from "../errors.ts";

// Same limit as _MAX_TEXT_LEN in matching/cv_extract.py. Longer CVs are
// rejected, not cut: the worker would reject them too.
export const max_cv_text_length = 30_000;

// Unicode characters (code points), the way Python len() and PostgreSQL
// char_length() count them. String.length counts UTF-16 units instead, so an
// emoji would count as 2 here and as 1 in the worker.
export function count_chars(text: string): number {
  let count = 0;
  for (const _ of text) count++;
  return count;
}

// Control characters except tab (\t) and line feed (\n). PostgreSQL cannot store
// \u0000 in TEXT, and the others carry no meaning for the worker.
// eslint-disable-next-line no-control-regex -- matching them is the point
const control_chars = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g;

// Makes extracted text stable for storage and for the worker: NFC, LF line
// breaks, no trailing spaces, at most one empty line in a row.
export function normalize_cv_text(raw: string): string {
  return raw
    .normalize("NFC")
    .replace(/\r\n?/g, "\n")
    .replace(control_chars, "")
    .split("\n")
    .map((line) => line.trimEnd())
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

// PDFs start with "%PDF-"; the spec allows some bytes before it.
export function looks_like_pdf(data: Uint8Array): boolean {
  const head = Buffer.from(data.subarray(0, 1024)).toString("latin1");
  return head.includes("%PDF-");
}

export const cv_errors = {
  unsupported_file_type: () =>
    new api_error(415, "unsupported_file_type", "The file must be a PDF."),
  invalid_pdf: () =>
    new api_error(
      422,
      "invalid_pdf",
      "The PDF could not be read. It may be damaged or password-protected.",
    ),
  no_text: () =>
    new api_error(
      422,
      "cv_no_text",
      "No text was found in the PDF. Scanned documents are not supported; please upload a PDF with selectable text.",
    ),
  too_long: () =>
    new api_error(
      422,
      "cv_text_too_long",
      `The CV is too long. It may contain at most ${max_cv_text_length.toLocaleString("en-US")} characters of text.`,
      { max_length: max_cv_text_length },
    ),
};

// Extracts plain text from a PDF held in memory. Text items keep the line breaks
// PDF.js detects (hasEOL); pages are separated by an empty line. Throws api_error
// for anything the user should fix; the PDF and its text are never logged.
export async function extract_cv_text(data: Uint8Array): Promise<string> {
  if (!looks_like_pdf(data)) throw cv_errors.unsupported_file_type();

  let raw = "";
  try {
    // verbosity 0: PDF.js warnings go to the console otherwise.
    // A copy is passed because PDF.js takes ownership of (detaches) the buffer.
    const pdf = await getDocumentProxy(new Uint8Array(data), { verbosity: 0 });
    try {
      for (let page_number = 1; page_number <= pdf.numPages; page_number++) {
        const page = await pdf.getPage(page_number);
        const content = await page.getTextContent();
        for (const item of content.items) {
          if ("str" in item) {
            raw += item.str;
            if (item.hasEOL) raw += "\n";
          }
        }
        raw += "\n\n";
      }
    } finally {
      // Frees the document and its worker resources.
      await pdf.loadingTask.destroy();
    }
  } catch {
    throw cv_errors.invalid_pdf();
  }

  const text = normalize_cv_text(raw);
  if (text === "") throw cv_errors.no_text();
  if (count_chars(text) > max_cv_text_length) throw cv_errors.too_long();
  return text;
}
