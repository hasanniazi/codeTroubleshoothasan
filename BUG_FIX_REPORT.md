# Bug Identification & Fix Report

## Scope and evidence

This report covers the Node.js book-catalog application and the Python handwriting-recognition application in this repository. It is based on the implementation and automated tests in the current checkout.

The repository history available for review contains only an initial commit, so it does not preserve earlier faulty versions or a per-file change history. The file lists below identify the current implementation and tests associated with each fix; they should not be read as a claim that Git can independently confirm each historical edit.

## Bugs identified and fixes applied

### 1. Book catalog: invalid or incomplete book data and IDs

- **Root cause:** Request values could be missing, blank, malformed, or outside valid ranges, and ID parsing needed to distinguish invalid identifiers from valid database lookups.
- **Fix:** Centralized checks require non-empty text, an integer published year in range, a finite non-negative price, a non-negative integer quantity, and a 10- or 13-digit ISBN. Invalid IDs are rejected before database operations. Validation errors return client errors rather than being treated as successful operations.
- **Relevant files:** `CodeTroubleshoot-main/nodejs/src/middleware/validate.js`, `CodeTroubleshoot-main/nodejs/src/services/bookService.js`, `CodeTroubleshoot-main/nodejs/src/controllers/bookController.js`.
- **Verification:** Tests cover required fields, creation, retrieval of missing records, and updates.

### 2. Book catalog: duplicate ISBNs and database query handling

- **Root cause:** ISBN uniqueness is enforced by the database; without translating that constraint into an expected API response, duplicate submissions could become opaque server errors. User-provided filters also need to be kept separate from SQL syntax.
- **Fix:** Duplicate ISBN constraint failures are mapped to HTTP 409. Search and category filters use bound SQL parameters, and database failures not explicitly recognized are rethrown.
- **Relevant files:** `CodeTroubleshoot-main/nodejs/src/repositories/bookRepository.js`, `CodeTroubleshoot-main/nodejs/src/controllers/bookController.js`, `CodeTroubleshoot-main/nodejs/src/middleware/errorHandler.js`.
- **Verification:** Tests cover duplicate ISBN rejection, category filtering, and search.

### 3. Book catalog: stock could become negative

- **Root cause:** Applying a negative inventory adjustment without checking the resulting quantity permits stock to fall below zero.
- **Fix:** Stock adjustments must be non-zero integers, and a decrease that would produce negative stock is rejected. Missing books are reported as not found.
- **Relevant files:** `CodeTroubleshoot-main/nodejs/src/services/stockService.js`, `CodeTroubleshoot-main/nodejs/src/middleware/validate.js`.
- **Verification:** Tests cover increasing and decreasing stock.

### 4. Book catalog: unreliable initial database contents

- **Root cause:** Initial seed inserts need to behave as a unit; a partial seed can leave an incomplete catalog, and an already-populated database should not be seeded again.
- **Fix:** The schema is created before use, seeding occurs only when the table is empty, and the seed inserts run in a transaction that rolls back on failure.
- **Relevant files:** `CodeTroubleshoot-main/nodejs/src/database/init.js`, `CodeTroubleshoot-main/nodejs/src/database/seed.js`.
- **Verification:** The API test suite confirms seeded records are available and checks dashboard totals.

### 5. Handwriting app: invalid, misleading, oversized, or unsafe uploads

- **Root cause:** A filename or client-supplied content type alone does not establish that an upload is a supported image; unbounded or path-like filenames also need to be rejected.
- **Fix:** Uploads are limited to JPG/JPEG and PNG, checked against expected media type and file signatures, rejected when empty or over 5 MiB, and checked for path-like filenames. The route reads at most one byte beyond the limit before validation.
- **Relevant files:** `CodeTroubleshoot-main/python/app/utils/validation.py`, `CodeTroubleshoot-main/python/app/routes/recognize.py`.
- **Verification:** Tests reject PDF, invalid image bytes, oversized uploads, and a path-like filename; valid PNG and JPEG uploads are accepted.

### 6. Handwriting app: image decoding and scaling failures

- **Root cause:** Invalid image bytes can fail during decoding, while resizing without a maximum bound or correct aspect-ratio calculation can distort images or waste processing resources.
- **Fix:** Decode failures are surfaced as invalid-image errors. Images are resized proportionally to fit within 800 by 600 pixels and are not enlarged when already smaller. Preprocessing normalizes the image to grayscale and applies thresholding for OCR.
- **Relevant files:** `CodeTroubleshoot-main/python/app/preprocessing/image_ops.py`, `CodeTroubleshoot-main/python/app/services/pipeline.py`, `CodeTroubleshoot-main/python/app/routes/recognize.py`.
- **Verification:** Tests verify invalid image rejection, OCR request handling, and resizing an image to 800 by 200 without changing the dimensions of a smaller image.

### 7. Handwriting app: saved-result access and text persistence

- **Root cause:** Result identifiers used in file paths must not be allowed to contain path components, and saved text should be read without being consumed or corrupted.
- **Fix:** Result IDs are generated as UUID hex strings and validated against a strict 32-character lowercase hexadecimal format before result files are accessed. Text is written and read as UTF-8; processed images are stored separately.
- **Relevant files:** `CodeTroubleshoot-main/python/app/utils/files.py`, `CodeTroubleshoot-main/python/app/routes/recognize.py`.
- **Verification:** Tests confirm saved text can be read repeatedly and that a successful recognition response exposes downloadable text and a processed PNG.

## Files implementing the fixes and their tests

**Node.js**

- `CodeTroubleshoot-main/nodejs/src/middleware/validate.js`
- `CodeTroubleshoot-main/nodejs/src/services/bookService.js`
- `CodeTroubleshoot-main/nodejs/src/services/stockService.js`
- `CodeTroubleshoot-main/nodejs/src/repositories/bookRepository.js`
- `CodeTroubleshoot-main/nodejs/src/database/init.js`
- `CodeTroubleshoot-main/nodejs/src/database/seed.js`
- `CodeTroubleshoot-main/nodejs/src/controllers/bookController.js`
- `CodeTroubleshoot-main/nodejs/src/middleware/errorHandler.js`
- `CodeTroubleshoot-main/nodejs/tests/books.test.js`

**Python**

- `CodeTroubleshoot-main/python/app/utils/validation.py`
- `CodeTroubleshoot-main/python/app/routes/recognize.py`
- `CodeTroubleshoot-main/python/app/preprocessing/image_ops.py`
- `CodeTroubleshoot-main/python/app/services/pipeline.py`
- `CodeTroubleshoot-main/python/app/utils/files.py`
- `CodeTroubleshoot-main/python/tests/test_recognize.py`

## Testing and verification

- **Node.js:** `npm.cmd test -- --runInBand` from `CodeTroubleshoot-main/nodejs` — **1 test suite passed; 16 tests passed**.
- **Python:** `.\.venv\Scripts\python.exe -m pytest CodeTroubleshoot-main\python\tests -q` from the repository root — **10 tests passed**.
- The Python test run emitted one deprecation warning from the installed Starlette/AnyIO test-client dependency; no test failed.

## Unresolved issues and limitations

- No known failures remain in the automated tests listed above.
- End-to-end OCR against an installed Tesseract executable was not verified in the test run; the OCR unit path is tested with a stub. A deployment must install Tesseract and, if it is not at the documented default Windows path, set `TESSERACT_CMD`.
- Because the available Git history contains only the initial commit, the original symptoms and exact before/after source changes cannot be independently reconstructed from version history.
