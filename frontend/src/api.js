/**
 * Thin API client for the FastAPI backend.
 *
 * The base URL can be overridden at build time via REACT_APP_API_BASE_URL;
 * during development the CRA dev-server proxy (see package.json) forwards
 * relative requests to the backend on :8000, so the default empty string works.
 */
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "";

/**
 * Parse a fetch Response, throwing a useful Error on non-2xx responses.
 * @param {Response} response
 * @returns {Promise<any>} the parsed JSON body
 */
async function parseResponse(response) {
  let body = null;
  try {
    body = await response.json();
  } catch (err) {
    // Body was not JSON; leave it null and fall through to status handling.
  }

  if (!response.ok) {
    const detail =
      (body && (body.detail || body.message)) ||
      `Request failed with status ${response.status}`;
    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail)
    );
  }
  return body;
}

/**
 * Fetch the list of languages the dropdown should offer.
 * @returns {Promise<Array<{value: string, label: string}>>}
 */
export async function fetchLanguages() {
  const response = await fetch(`${API_BASE_URL}/api/languages`);
  return parseResponse(response);
}

/**
 * Run the multi-agent pipeline.
 * @param {string} language  selected language value
 * @param {string} problemStatement  the user's problem description
 * @returns {Promise<object>} the generation result
 */
export async function generateCode(language, problemStatement) {
  const response = await fetch(`${API_BASE_URL}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      language,
      problem_statement: problemStatement,
    }),
  });
  return parseResponse(response);
}
