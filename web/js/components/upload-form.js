import { getTemplate } from "../core/templates.js";
import { refs, setErrors, toggleHidden } from "../core/dom.js";
import { showApiError } from "../core/errors.js";
import { formatSize } from "../core/format.js";

export async function createUploadForm({ onSubmit }) {
  const root = await getTemplate("upload-form.html");
  const ui = refs(root);

  function selectedFile() {
    return ui.uploadInput.files?.[0] || null;
  }

  function refreshFileState() {
    const file = selectedFile();
    const hasFile = Boolean(file);

    toggleHidden(ui.dropzoneIdle, hasFile);
    toggleHidden(ui.dropzoneFile, !hasFile);
    ui.dropZone.classList.toggle("has-file", hasFile);

    if (hasFile) {
      setErrors(ui.uploadErrors);
    }

    if (file) {
      ui.fileName.textContent = file.name;
      ui.fileSize.textContent = formatSize(file.size);
    }
  }

  ui.uploadInput.addEventListener("change", refreshFileState);

  ui.dropZone.addEventListener("click", (event) => {
    if (event.target.closest("[data-ref='fileClear']")) {
      return;
    }
    ui.uploadInput.click();
  });

  ui.dropZone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      ui.uploadInput.click();
    }
  });

  ["dragenter", "dragover"].forEach((name) => {
    ui.dropZone.addEventListener(name, (event) => {
      event.preventDefault();
      ui.dropZone.classList.add("is-dragover");
    });
  });

  ["dragleave", "dragend", "drop"].forEach((name) => {
    ui.dropZone.addEventListener(name, () => {
      ui.dropZone.classList.remove("is-dragover");
    });
  });

  ui.dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    const files = event.dataTransfer?.files;
    if (files?.length) {
      ui.uploadInput.files = files;
      refreshFileState();
    }
  });

  ui.fileClear.addEventListener("click", (event) => {
    event.stopPropagation();
    ui.uploadInput.value = "";
    refreshFileState();
  });

  ui.uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setErrors(ui.uploadErrors);

    try {
      await onSubmit?.(selectedFile());
      ui.uploadInput.value = "";
      refreshFileState();
    } catch (error) {
      showApiError(error, { general: ui.uploadErrors });
    }
  });

  refreshFileState();

  return { element: root };
}
