import { getTemplate } from "../core/templates.js";
import { refs, setText } from "../core/dom.js";
import { formatDateTime, formatSize } from "../core/format.js";

export async function createDocumentsTable({ onRefresh, onDownload, onDelete }) {
  const root = await getTemplate("documents-table.html");
  const rowTemplate = await getTemplate("document-row.html");
  const ui = refs(root);

  ui.refreshButton.addEventListener("click", () => onRefresh?.());

  function render(documents) {
    ui.documentsBody.replaceChildren();

    if (!documents.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 5;
      cell.className = "empty";
      cell.textContent = "Ще немає документів";
      row.appendChild(cell);
      ui.documentsBody.appendChild(row);
      return;
    }

    documents.forEach((doc) => {
      const row = rowTemplate.cloneNode(true);
      const rowUi = refs(row);

      const signature = doc.signature || {};
      const isSigned =
        signature.status === "signed" || signature.status === "verified";

      setText(rowUi.docName, doc.original_filename);
      setText(
        rowUi.docSignature,
        isSigned ? "Підписано" : "Без підпису",
        ""
      );
      rowUi.docSignature.classList.toggle("is-signed", isSigned);
      rowUi.docSignature.classList.toggle("is-unsigned", !isSigned);
      rowUi.docSignature.title = isSigned
        ? `${signature.algorithm || "ЕЦП"} · ${
            signature.signer || "—"
          } · перевіряється під час скачування`
        : "Документ без електронного підпису";
      setText(rowUi.docSize, formatSize(doc.size_bytes));
      setText(rowUi.docType, doc.content_type);
      setText(rowUi.docCreated, formatDateTime(doc.created_at));

      rowUi.docDownload.addEventListener("click", () => onDownload?.(doc));
      rowUi.docRemove.addEventListener("click", (event) =>
        onDelete?.(doc, event.currentTarget)
      );
      ui.documentsBody.appendChild(row);
    });
  }

  function setBusy(busy) {
    ui.refreshButton.disabled = busy;
  }

  return { element: root, render, setBusy };
}
