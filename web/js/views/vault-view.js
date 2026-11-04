import { getTemplate } from "../core/templates.js";
import { refs, toggleHidden } from "../core/dom.js";
import { createProfileCard } from "../components/profile-card.js";
import { createUploadForm } from "../components/upload-form.js";
import { createDocumentsTable } from "../components/documents-table.js";
import { createCommentsPanel } from "../components/comments-panel.js";
import { createSignatureCard } from "../components/signature-card.js";

export async function createVaultView({
  onUpload,
  onRefresh,
  onDownload,
  onDelete,
  onLoadComments,
  onAddComment,
  onGenerateKey,
  onPublicKey,
  onExportKey,
}) {
  const root = await getTemplate("vault-view.html");
  const ui = refs(root);

  const profile = await createProfileCard();
  const upload = await createUploadForm({ onSubmit: onUpload });
  const signature = await createSignatureCard({
    onGenerate: onGenerateKey,
    onPublicKey,
    onExportKey,
  });
  const table = await createDocumentsTable({
    onRefresh,
    onDownload,
    onDelete,
  });
  const comments = await createCommentsPanel({
    onLoad: onLoadComments,
    onSubmit: onAddComment,
  });

  ui.summaryHost.append(profile.element, upload.element);
  ui.signatureHost.append(signature.element);
  ui.documentsHost.append(table.element);
  ui.commentsHost.append(comments.element);

  return {
    element: root,
    show(user) {
      profile.update(user);
      toggleHidden(root, false);
    },
    hide() {
      toggleHidden(root, true);
    },
    table,
    comments,
    signature,
  };
}
