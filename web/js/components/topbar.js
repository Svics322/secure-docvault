import { getTemplate } from "../core/templates.js";
import { refs, setText, toggleHidden } from "../core/dom.js";

const ROLE_LABELS = {
  admin: "Адміністратор",
  user: "Користувач",
};

export async function createTopbar({ onLogout }) {
  const root = await getTemplate("topbar.html");
  const ui = refs(root);

  ui.logoutButton.addEventListener("click", () => onLogout?.());

  return {
    element: root,
    showUser(user) {
      const username = user.username || "";
      setText(ui.userInitial, username.slice(0, 1).toUpperCase(), "?");
      setText(ui.userName, username, "");
      setText(ui.userRole, ROLE_LABELS[user.role] || user.role || "", "");
      toggleHidden(ui.userChip, false);
      toggleHidden(ui.logoutButton, false);
    },
    hideUser() {
      toggleHidden(ui.userChip, true);
      toggleHidden(ui.logoutButton, true);
    },
  };
}
