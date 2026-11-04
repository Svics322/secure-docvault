import { getTemplate } from "../core/templates.js";
import { refs, setText, toggleHidden } from "../core/dom.js";
import { formatDateTime } from "../core/format.js";

function shortFingerprint(fingerprint) {
  if (!fingerprint) {
    return "—";
  }
  if (fingerprint.length <= 24) {
    return fingerprint;
  }
  return `${fingerprint.slice(0, 12)}…${fingerprint.slice(-8)}`;
}

export async function createSignatureCard({
  onGenerate,
  onPublicKey,
  onExportKey,
}) {
  const root = await getTemplate("signature-card.html");
  const ui = refs(root);

  ui.generate.addEventListener("click", () => onGenerate?.());
  ui.publicKey.addEventListener("click", () => onPublicKey?.());
  ui.exportKey.addEventListener("click", () => onExportKey?.());

  function update(key) {
    ui.state.classList.remove("is-active", "is-missing");

    if (!key) {
      ui.state.classList.add("is-missing");
      ui.state.textContent = "Ключ не створено";
      setText(ui.fingerprint, "—");
      setText(ui.created, "—");
      ui.fingerprint.removeAttribute("title");
      ui.hint.textContent = "Створіть ключі, щоб підписувати завантажені документи.";
      toggleHidden(ui.generate, false);
      toggleHidden(ui.publicKey, true);
      toggleHidden(ui.exportKey, true);
      return;
    }

    ui.state.classList.add("is-active");
    ui.state.textContent = "Ключ створено";
    setText(ui.fingerprint, shortFingerprint(key.fingerprint));
    ui.fingerprint.title = key.fingerprint || "";
    setText(ui.created, formatDateTime(key.created_at));
    ui.hint.textContent =
      "Документи підписуються автоматично під час завантаження. " +
      "Підпис перевіряється під час скачування.";
    toggleHidden(ui.generate, true);
    toggleHidden(ui.publicKey, false);
    toggleHidden(ui.exportKey, false);
  }

  function setBusy(busy) {
    ui.generate.disabled = busy;
    ui.generate.textContent = busy ? "Створюємо…" : "Створити ключі";
  }

  update(null);

  return { element: root, update, setBusy };
}
