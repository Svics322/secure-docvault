import { readCookie } from "./cookies.js";

export class ApiError extends Error {
  constructor(message, status, { errors = [], fieldErrors = {} } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errors = errors;
    this.fieldErrors = fieldErrors;
  }
}

function normalizeMessage(item) {
  if (typeof item === "string") {
    return item;
  }
  if (item && typeof item.msg === "string") {
    return item.msg;
  }
  return JSON.stringify(item);
}

export function describeError(payload) {
  if (payload === null || payload === undefined || payload === "") {
    return {
      message: "Невідома помилка",
      errors: ["Невідома помилка"],
      fieldErrors: {},
    };
  }

  if (typeof payload === "string") {
    return { message: payload, errors: [payload], fieldErrors: {} };
  }

  if (Array.isArray(payload)) {
    const errors = payload.map(normalizeMessage).filter(Boolean);
    const finalErrors = errors.length ? errors : ["Невідома помилка"];
    return {
      message: finalErrors.join("\n"),
      errors: finalErrors,
      fieldErrors: {},
    };
  }

  if (typeof payload !== "object") {
    const text = String(payload);
    return { message: text, errors: [text], fieldErrors: {} };
  }

  if (payload.detail !== undefined) {
    return describeError(payload.detail);
  }

  const fieldErrors = {};
  if (payload.field_errors && typeof payload.field_errors === "object") {
    Object.entries(payload.field_errors).forEach(([field, messages]) => {
      if (Array.isArray(messages) && messages.length) {
        fieldErrors[field] = messages.map(normalizeMessage).filter(Boolean);
      }
    });
  }

  let errors = Array.isArray(payload.errors)
    ? payload.errors.map(normalizeMessage).filter(Boolean)
    : [];
  const message = typeof payload.message === "string" ? payload.message : "";

  if (!errors.length) {
    if (message) {
      errors = [message];
    } else if (typeof payload.error === "string") {
      errors = [payload.error];
    }
  }

  if (!errors.length) {
    const fieldMessages = Object.values(fieldErrors).flat();
    errors = fieldMessages.length ? fieldMessages : ["Невідома помилка"];
  }

  return {
    message: message || errors.join("\n"),
    errors,
    fieldErrors,
  };
}

export function formatError(payload) {
  return describeError(payload).message;
}

export async function api(path, options = {}) {
  const request = {
    credentials: "same-origin",
    ...options,
    headers: new Headers(options.headers || {}),
  };

  const method = (request.method || "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    request.headers.set("X-CSRF-Token", readCookie("csrf_token"));
  }

  if (
    request.body &&
    !(request.body instanceof FormData) &&
    typeof request.body !== "string"
  ) {
    request.headers.set("Content-Type", "application/json");
    request.body = JSON.stringify(request.body);
  }

  const response = await fetch(path, request);
  const contentType = response.headers.get("content-type") || "";
  let payload = null;

  if (contentType.includes("application/json")) {
    try {
      payload = await response.json();
    } catch (error) {
      payload = null;
    }
  } else {
    payload = await response.text();
  }

  if (!response.ok) {
    const description = describeError(payload);
    throw new ApiError(description.message, response.status, description);
  }
  return payload;
}
