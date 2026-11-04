import { $ } from "./core/dom.js";
import { api } from "./core/api.js";
import { downloadFile, downloadText } from "./core/download.js";
import { createTopbar } from "./components/topbar.js";
import { createToast } from "./components/toast.js";
import { createConfirmDialog } from "./components/confirm-dialog.js";
import { createExportKeyDialog } from "./components/export-key-dialog.js";
import { createAuthView } from "./views/auth-view.js";
import { createVaultView } from "./views/vault-view.js";

let topbar;
let toast;
let confirmDialog;
let exportKeyDialog;
let authView;
let vaultView;

function showAuth() {
  authView.show();
  vaultView.hide();
  topbar.hideUser();
}

function showVault(user) {
  authView.hide();
  vaultView.show(user);
  topbar.showUser(user);
  refreshSigningKey();
}

async function loadProfile() {
  const data = await api("/api/v1/user/profile");
  showVault(data.user_data);
  return data.user_data;
}

async function loadComments(documentId) {
  try {
    const data = await api(
      `/api/v1/documents/${encodeURIComponent(documentId)}/comments`
    );
    vaultView.comments.render(data.comments || []);
  } catch (error) {
    toast.show(error.message, "error");
  }
}

async function refreshDocuments() {
  vaultView.table.setBusy(true);
  try {
    const data = await api("/api/v1/documents");
    const documents = data.documents || [];
    vaultView.table.render(documents);

    const selectedId = vaultView.comments.setDocuments(documents);
    if (selectedId) {
      await loadComments(selectedId);
    } else {
      vaultView.comments.render([]);
    }
  } finally {
    vaultView.table.setBusy(false);
  }
}

async function handleRefresh() {
  try {
    await refreshDocuments();
  } catch (error) {
    toast.show(error.message, "error");
  }
}

async function refreshSigningKey() {
  try {
    const data = await api("/api/v1/signing/keys");
    vaultView.signature.update(data.key);
  } catch (error) {
    if (error.status !== 401) {
      toast.show(error.message, "error");
    }
  }
}

async function handleGenerateKey() {
  vaultView.signature.setBusy(true);
  try {
    const data = await api("/api/v1/signing/keys", { method: "POST" });
    vaultView.signature.update(data.key);
    toast.show("Ключі ЕЦП створено", "ok");
  } catch (error) {
    toast.show(error.message, "error");
  } finally {
    vaultView.signature.setBusy(false);
  }
}

async function handlePublicKey() {
  try {
    const pem = await api("/api/v1/signing/keys/public");
    downloadText(pem, "docvault-public-key.pem", "application/x-pem-file");
    toast.show("Публічний ключ завантажено", "ok");
  } catch (error) {
    toast.show(error.message, "error");
  }
}

async function handleExportKey() {
  await exportKeyDialog.open({
    onExport: async (passphrase) => {
      const pem = await api("/api/v1/signing/keys/export", {
        method: "POST",
        body: { passphrase },
      });
      downloadText(pem, "docvault-private-key.pem", "application/x-pem-file");
      toast.show(
        "Приватний ключ завантажено. Збережіть його в безпечному місці.",
        "ok"
      );
    },
  });
}

async function handleLogin({ username, password }) {
  await api("/api/v1/auth/login", {
    method: "POST",
    body: { username, password },
  });
  await loadProfile();
  await refreshDocuments();
  toast.show(`Вітаємо, ${username}!`, "ok");
}

async function handleRegister({ username, email, password }) {
  await api("/api/v1/auth/register", {
    method: "POST",
    body: { username, email, password },
  });
  toast.show("Реєстрація успішна. Увійдіть у систему.", "ok");
}

async function handleLogout() {
  try {
    await api("/api/v1/auth/logout", { method: "POST" });
  } catch (error) {
    /* навіть якщо сервер недоступний, локально сесію закриваємо */
  }
  showAuth();
  toast.show("Ви вийшли з системи", "ok");
}

async function handleUpload(file) {
  const formData = new FormData();
  if (file) {
    formData.append("file", file);
  }

  await api("/api/v1/documents/upload", { method: "POST", body: formData });
  toast.show("Файл зашифровано, підписано та збережено", "ok");
  await refreshDocuments();
  await refreshSigningKey();
}

async function handleDownload(doc) {
  try {
    const result = await downloadFile(
      `/api/v1/documents/${encodeURIComponent(doc.document_id)}/download`,
      doc.original_filename
    );
    if (result.headers.get("X-Signature-Status") === "Signed & Verified") {
      toast.show("Файл розшифровано. Підпис перевірено.", "ok");
    } else {
      toast.show("Файл розшифровано та завантажено", "ok");
    }
  } catch (error) {
    toast.show(error.message, "error");
  }
}

async function handleDelete(doc, trigger) {
  const confirmed = await confirmDialog.open({
    title: "Видалити документ?",
    message: `«${doc.original_filename}» буде видалено назавжди. Відновити його не вдасться.`,
    confirmLabel: "Видалити",
    cancelLabel: "Скасувати",
    trigger,
  });

  if (!confirmed) {
    return;
  }

  try {
    await api(`/api/v1/documents/${encodeURIComponent(doc.document_id)}`, {
      method: "DELETE",
    });
    toast.show("Документ видалено", "ok");
    await refreshDocuments();
  } catch (error) {
    toast.show(error.message, "error");
  }
}

async function handleAddComment({ documentId, title, comment }) {
  await api(
    `/api/v1/documents/${encodeURIComponent(documentId)}/comments`,
    { method: "POST", body: { title, comment } }
  );
  await loadComments(documentId);
  toast.show("Коментар додано", "ok");
}

async function bootstrap() {
  [
    topbar,
    toast,
    confirmDialog,
    exportKeyDialog,
    authView,
    vaultView,
  ] = await Promise.all([
    createTopbar({ onLogout: handleLogout }),
    createToast(),
    createConfirmDialog(),
    createExportKeyDialog(),
    createAuthView({ onLogin: handleLogin, onRegister: handleRegister }),
    createVaultView({
      onUpload: handleUpload,
      onRefresh: handleRefresh,
      onDownload: handleDownload,
      onDelete: handleDelete,
      onLoadComments: loadComments,
      onAddComment: handleAddComment,
      onGenerateKey: handleGenerateKey,
      onPublicKey: handlePublicKey,
      onExportKey: handleExportKey,
    }),
  ]);

  $("#topbar-host").append(topbar.element);
  $("#toast-host").append(toast.element);
  $("#dialog-host").append(confirmDialog.element, exportKeyDialog.element);

  const viewHost = $("#view-host");
  viewHost.append(authView.element, vaultView.element);

  try {
    await loadProfile();
    await refreshDocuments();
  } catch (error) {
    showAuth();
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootstrap);
} else {
  bootstrap();
}
