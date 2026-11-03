import { setErrors } from "./dom.js";

export function showApiError(error, { fields = {}, general } = {}) {
  Object.values(fields).forEach((node) => setErrors(node, []));

  const fieldErrors = error?.fieldErrors || {};
  const shown = new Set();

  Object.entries(fields).forEach(([field, node]) => {
    const messages = Array.isArray(fieldErrors[field]) ? fieldErrors[field] : [];
    setErrors(node, messages);
    messages.forEach((message) => shown.add(message));
  });

  let messages = [];
  if (Array.isArray(error?.errors) && error.errors.length) {
    messages = error.errors;
  } else if (error?.message) {
    messages = [error.message];
  } else {
    messages = ["Невідома помилка"];
  }

  setErrors(
    general,
    messages.filter((message) => !shown.has(message))
  );
}
