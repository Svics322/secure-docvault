import { getTemplate } from "../core/templates.js";
import { refs, setErrors, setText } from "../core/dom.js";
import { showApiError } from "../core/errors.js";
import { formatDateTime } from "../core/format.js";

export async function createCommentsPanel({ onLoad, onSubmit }) {
  const root = await getTemplate("comments-panel.html");
  const itemTemplate = await getTemplate("comment-item.html");
  const ui = refs(root);
  const fields = {
    title: ui.commentTitleErrors,
    comment: ui.commentTextErrors,
  };
  let selectedId = "";

  function clearErrors() {
    setErrors(ui.commentErrors);
    Object.values(fields).forEach((node) => setErrors(node));
  }

  function setDocuments(documents) {
    ui.commentDocument.replaceChildren();

    documents.forEach((doc) => {
      const option = document.createElement("option");
      option.value = doc.document_id;
      option.textContent = doc.original_filename;
      ui.commentDocument.appendChild(option);
    });

    const ids = documents.map((doc) => doc.document_id);
    selectedId = ids.includes(selectedId) ? selectedId : ids[0] || "";
    ui.commentDocument.value = selectedId;
    return selectedId;
  }

  function render(comments) {
    ui.commentList.replaceChildren();

    comments.forEach((comment) => {
      const item = itemTemplate.cloneNode(true);
      const itemUi = refs(item);
      setText(itemUi.commentItemTitle, comment.title);
      setText(
        itemUi.commentItemMeta,
        `${comment.author || "—"} · ${formatDateTime(comment.created_at)}`
      );
      setText(itemUi.commentItemText, comment.comment);
      ui.commentList.appendChild(item);
    });
  }

  ui.commentDocument.addEventListener("change", () => {
    selectedId = ui.commentDocument.value;
    onLoad?.(selectedId);
  });

  ui.commentForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors();

    if (!selectedId) {
      setErrors(ui.commentErrors, ["Спочатку завантажте документ"]);
      return;
    }

    const title = ui.commentTitle.value.trim();
    const comment = ui.commentText.value.trim();

    try {
      await onSubmit?.({ documentId: selectedId, title, comment });
      ui.commentTitle.value = "";
      ui.commentText.value = "";
    } catch (error) {
      showApiError(error, { fields, general: ui.commentErrors });
    }
  });

  return {
    element: root,
    setDocuments,
    render,
    selectedDocumentId: () => selectedId,
  };
}
