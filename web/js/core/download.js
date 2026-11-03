import { ApiError, formatError } from "./api.js";

export async function downloadFile(path, filename = "document") {
  const response = await fetch(path, { credentials: "same-origin" });
  if (!response.ok) {
    let message = `Помилка ${response.status}`;
    try {
      message = formatError(await response.json());
    } catch (error) {
      /* тіло не JSON — залишаємо статус */
    }
    throw new ApiError(message, response.status);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
