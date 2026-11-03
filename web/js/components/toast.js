import { getTemplate } from "../core/templates.js";

export async function createToast() {
  const root = await getTemplate("toast.html");
  let timer = 0;

  return {
    element: root,
    show(message, kind = "ok") {
      root.textContent = message;
      root.className = `toast ${kind}`;
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        root.className = "toast hidden";
      }, 4200);
    },
  };
}
