import { spawnSync } from "node:child_process";
import { describe, expect, it } from "vitest";
import { api_error } from "../src/errors.ts";
import {
  count_chars,
  extract_cv_text,
  looks_like_pdf,
  max_cv_text_length,
  normalize_cv_text,
} from "../src/cvs/cv_text.ts";
import {
  fictional_cv_lines,
  make_long_pdf,
  make_pdf,
  make_pdf_without_text,
} from "./helpers/pdf.ts";

async function expect_api_error(promise: Promise<unknown>, status: number, code: string) {
  const error = await promise.then(
    () => null,
    (e: unknown) => e,
  );
  expect(error).toBeInstanceOf(api_error);
  expect((error as api_error).status).toBe(status);
  expect((error as api_error).code).toBe(code);
  return error as api_error;
}

// Python 3 from PATH, if any: used to check that lengths match the worker.
function python_len(text: string): number | null {
  for (const cmd of ["python3", "python"]) {
    const run = spawnSync(
      cmd,
      ["-c", "import sys; print(len(sys.stdin.buffer.read().decode('utf-8')))"],
      { input: Buffer.from(text, "utf8") },
    );
    if (run.status === 0) return Number(run.stdout.toString().trim());
  }
  return null;
}

describe("count_chars", () => {
  it("counts Unicode characters, not UTF-16 units", () => {
    expect(count_chars("abc")).toBe(3);
    expect(count_chars("äöå")).toBe(3);
    expect("🚀".length).toBe(2);
    expect(count_chars("🚀")).toBe(1);
    // A letter plus a combining mark is two characters, as in Python.
    expect(count_chars("ä")).toBe(2);
  });

  const python_available = python_len("x") === 1;
  it.skipIf(!python_available)("matches Python len() used by the worker", () => {
    const text = normalize_cv_text("Äiti 🚀 naïve ä\r\nrivi 2 \u{1F600}– end");
    expect(count_chars(text)).toBe(python_len(text));
  });
});

describe("normalize_cv_text", () => {
  it("turns CRLF and CR into LF", () => {
    expect(normalize_cv_text("a\r\nb\rc\nd")).toBe("a\nb\nc\nd");
  });

  it("removes NUL and other control characters but keeps tabs", () => {
    expect(normalize_cv_text("a\u0000b\u0007c\td")).toBe("abc\td");
  });

  it("trims trailing spaces and keeps at most one empty line", () => {
    expect(normalize_cv_text("  Title   \n\n\n\nText  \n")).toBe("Title\n\nText");
  });

  it("uses NFC, so ä is one character", () => {
    const text = normalize_cv_text("äiti");
    expect(text).toBe("äiti");
    expect(count_chars(text)).toBe(4);
  });
});

describe("looks_like_pdf", () => {
  it("accepts a PDF header and rejects other files", () => {
    expect(looks_like_pdf(Buffer.from("%PDF-1.7\n..."))).toBe(true);
    expect(looks_like_pdf(Buffer.from("\u0089PNG\r\n\u001a\n"))).toBe(false);
  });
});

describe("extract_cv_text", () => {
  it("keeps line breaks and Finnish letters of a mixed fi/en CV", async () => {
    const pdf = await make_pdf([fictional_cv_lines.join("\n"), "Sivu 2 / Page 2: Åbo"]);

    const text = await extract_cv_text(pdf);

    for (const line of fictional_cv_lines.filter(Boolean)) {
      expect(text.split("\n")).toContain(line);
    }
    expect(text).toContain("Kielitaito: suomi (äidinkieli)");
    expect(text).not.toContain("\r");
    // Pages are separated by an empty line.
    expect(text.endsWith("perustaso)\n\nSivu 2 / Page 2: Åbo")).toBe(true);
  });

  it("rejects a PDF without text (e.g. a scan)", async () => {
    await expect_api_error(extract_cv_text(await make_pdf_without_text()), 422, "cv_no_text");
  });

  it("rejects text over 30 000 characters instead of cutting it", async () => {
    const error = await expect_api_error(
      extract_cv_text(await make_long_pdf(max_cv_text_length + 2000)),
      422,
      "cv_text_too_long",
    );
    expect(error.details).toEqual({ max_length: max_cv_text_length });
  });

  it("accepts text just under the limit", async () => {
    const text = await extract_cv_text(await make_long_pdf(max_cv_text_length - 1000));
    expect(count_chars(text)).toBeLessThanOrEqual(max_cv_text_length);
    expect(count_chars(text)).toBeGreaterThan(max_cv_text_length - 2000);
  });

  it("rejects files that are not PDFs", async () => {
    await expect_api_error(
      extract_cv_text(Buffer.from("\u0089PNG\r\n\u001a\nnot a pdf")),
      415,
      "unsupported_file_type",
    );
  });

  it("rejects a broken PDF", async () => {
    await expect_api_error(
      extract_cv_text(Buffer.from("%PDF-1.7\nthis is not really a pdf")),
      422,
      "invalid_pdf",
    );
  });
});
