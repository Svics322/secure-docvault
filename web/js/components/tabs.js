import { getTemplate } from "../core/templates.js";

export async function createTabs({ items, onChange }) {
  const root = await getTemplate("tabs.html");
  const buttons = items.map((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tab";
    button.dataset.tab = item.id;
    button.setAttribute("role", "tab");
    button.textContent = item.label;
    button.addEventListener("click", () => onChange?.(item.id));
    root.appendChild(button);
    return button;
  });

  function setActive(id) {
    buttons.forEach((button) => {
      const active = button.dataset.tab === id;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", active ? "true" : "false");
    });
  }

  return { element: root, setActive };
}
