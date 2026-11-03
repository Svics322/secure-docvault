import { getTemplate } from "../core/templates.js";
import { refs } from "../core/dom.js";

export async function createConfirmDialog() {
  const root = await getTemplate("confirm-dialog.html");
  const ui = refs(root);

  let resolver = null;
  let lastFocused = null;

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

    // У діалозі лише дві кнопки — циклічно перемикаємо фокус між ними.
    event.preventDefault();
    const next = document.activeElement === ui.cancel ? ui.confirm : ui.cancel;
    next.focus();
  }

  function open({
    title,
    message,
    confirmLabel = "Видалити",
    cancelLabel = "Скасувати",
    trigger,
  } = {}) {
    if (resolver) {
      close(false);
    }

    lastFocused = trigger || document.activeElement;
    ui.title.textContent = title || "";
    ui.message.textContent = message || "";
    ui.confirm.textContent = confirmLabel;
    ui.cancel.textContent = cancelLabel;

    root.classList.add("is-open");
    root.setAttribute("aria-hidden", "false");
    document.body.classList.add("dialog-open");

    // Гарантуємо, що елемент уже видимий, і повторюємо фокус після
    // перерахунку стилів (у фоновій вкладці rAF може бути призупинений).
    root.getBoundingClientRect();
    ui.cancel.focus({ preventScroll: true });
    window.setTimeout(() => {
      if (resolver) {
        ui.cancel.focus({ preventScroll: true });
      }
    }, 0);

    return new Promise((resolve) => {
      resolver = resolve;
    });
  }

  ui.cancel.addEventListener("click", () => close(false));
  ui.confirm.addEventListener("click", () => close(true));
  ui.overlay.addEventListener("click", (event) => {
    if (event.target === ui.overlay) {
      close(false);
    }
  });
  document.addEventListener("keydown", onKeydown);

  return {
    element: root,
    open,
    close,
  };
}
