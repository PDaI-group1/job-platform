import { Router, type RequestHandler } from "express";
import multer from "multer";
import { delete_cv, find_cv, insert_cv, type cv_row } from "../cvs/cv_repository.ts";
import { extract_cv_text } from "../cvs/cv_text.ts";
import {
  create_access_token,
  hash_access_token,
  read_access_token_hash,
} from "../cvs/cv_token.ts";
import type { db_client } from "../db.ts";
import { api_error, invalid_parameter, not_found } from "../errors.ts";
// Same BIGINT id rules as for jobs.
import { parse_job_id as parse_id } from "../jobs/job_query.ts";

export const max_pdf_bytes = 5 * 1024 * 1024;

// Shown to the user when the worker could not build the profile. The worker's
// own profile_error is technical and stays in the database.
export const cv_failed_message =
  "We could not analyse this CV. Please try again later or upload a different file.";

// The PDF stays in memory only for the request; it is never written to disk.
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: max_pdf_bytes, files: 1, fields: 0, parts: 1 },
}).single("file");

// Runs multer and turns its errors into the API error format.
const receive_pdf: RequestHandler = (req, res, next) => {
  upload(req, res, (error: unknown) => {
    if (!error) return next();
    if (error instanceof multer.MulterError) {
      if (error.code === "LIMIT_FILE_SIZE") {
        return next(
          new api_error(413, "file_too_large", "The PDF may be at most 5 MB.", {
            max_bytes: max_pdf_bytes,
          }),
        );
      }
      return next(
        invalid_parameter("file", 'Send exactly one PDF in the multipart field "file".'),
      );
    }
    // Broken multipart body.
    next(new api_error(400, "bad_request", "Malformed upload request"));
  });
};

function to_response(cv: cv_row) {
  return {
    id: cv.id,
    status: cv.profile_status,
    // The profile is only shown when processing has finished.
    profile: cv.profile_status === "done" ? cv.profile : null,
    error: cv.profile_status === "failed" ? cv_failed_message : null,
    text_length: cv.text_length,
    created_at: cv.created_at,
    updated_at: cv.updated_at,
  };
}

export type cv_router_options = {
  db: db_client;
  upload_enabled: boolean;
};

export function create_cv_router({ db, upload_enabled }: cv_router_options): Router {
  const router = Router();

  router.post(
    "/cvs",
    (_req, _res, next) => {
      if (!upload_enabled) {
        return next(
          new api_error(503, "feature_disabled", "CV upload is not enabled yet."),
        );
      }
      next();
    },
    receive_pdf,
    async (req, res) => {
      if (!req.file) {
        throw invalid_parameter("file", 'Send the PDF in the multipart field "file".');
      }

      // The file name and the PDF are deliberately not kept.
      const text = await extract_cv_text(req.file.buffer);
      const access_token = create_access_token();
      const cv = await insert_cv(db, text, hash_access_token(access_token));

      res.status(201).json({
        id: cv.id,
        access_token,
        status: "pending",
        text_length: cv.text_length,
        created_at: cv.created_at,
      });
    },
  );

  router.get("/cvs/:id", async (req, res) => {
    const id = parse_id(req.params.id);
    const cv = await find_cv(db, id, read_access_token_hash(req));
    if (!cv) throw not_found(`CV ${id} not found`);
    res.json(to_response(cv));
  });

  router.delete("/cvs/:id", async (req, res) => {
    const id = parse_id(req.params.id);
    const deleted = await delete_cv(db, id, read_access_token_hash(req));
    if (!deleted) throw not_found(`CV ${id} not found`);
    res.status(204).end();
  });

  return router;
}
