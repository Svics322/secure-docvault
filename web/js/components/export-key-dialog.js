import { getTemplate } from "../core/templates.js";
import { refs, setErrors } from "../core/dom.js";
import { showApiError } from "../core/errors.js";
import { attachPasswordToggle } from "./password-toggle.js";

export async function createExportKeyDialog() {
  const root = await getTemplate("export-key-dialog.html");
  const ui = refs(root);
  const passwordToggle = attachPasswordToggle(ui.passphrase, ui.toggle);

  let resolver = null;
  let lastFocused = null;
  let handler = null;

  const focusable = () => [ui.passphrase, ui.toggle, ui.cancel, ui.submit];

  function reset() {
    ui.passphrase.value = "";
    passwordToggle.reset();
    setErrors(ui.errors);
    setErrors(ui.general);
    ui.submit.disabled = false;
    ui.submit.textContent = "Завантажити ключ";
  }

  function close(result) {
    if (!resolver) {
      return;
    }

    root.classList.remove("is-open");
    root.setAttribute("aria-hidden", "true");
    document.body.classList.remove("dialog-open");

    const resolve = resolver;
    resolver = null;

    if (lastFocused && document.contains(lastFocused)) {
      lastFocused.focus({ preventScroll: true });
    }

    resolve(result);
  }

  function onKeydown(event) {
    if (!resolver) {
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      close(false);
      return;
    }

    if (event.key !== "Tab") {
      return;
    }

    const elements = focusable();
    const current = elements.indexOf(document.activeElement);
    event.preventDefault();

    if (event.shiftKey) {
      elements[(current <= 0 ? elements.length : current) - 1].focus();
    } else {
      elements[(current + 1) % elements.length].focus();
    }
  }

  ui.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setErrors(ui.errors);
    setErrors(ui.general);

    if (!handler) {
      return;
    }

    ui.submit.disabled = true;
    ui.submit.textContent = "Готуємо…";

    try {
      await handler(ui.passphrase.value);
      close(true);
    } catch (error) {
      showApiError(error, {
        fields: { passphrase: ui.errors },
        general: ui.general,
      });
    } finally {
      ui.submit.disabled = false;
      ui.submit.textContent = "Завантажити ключ";
    }
  });

  ui.cancel.addEventListener("click", () => close(false));
  ui.overlay.addEventListener("click", (event) => {
    if (event.target === ui.overlay) {
      close(false);
    }
  });
  document.addEventListener("keydown", onKeydown);

  function open({ onExport } = {}) {
    if (resolver) {
      close(false);
    }

    handler = onExport || null;
    lastFocused = document.activeElement;
    reset();

    root.classList.add("is-open");
    root.setAttribute("aria-hidden", "false");
    document.body.classList.add("dialog-open");

    root.getBoundingClientRect();
    ui.passphrase.focus({ preventScroll: true });
    window.setTimeout(() => {
      if (resolver) {
        ui.passphrase.focus({ preventScroll: true });
      }
    }, 0);

    return new Promise((resolve) => {
      resolver = resolve;
    });
  }

  return { element: root, open, close };
}
