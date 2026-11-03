import { getTemplate } from "../core/templates.js";
import { refs, setText } from "../core/dom.js";
import { formatDateTime } from "../core/format.js";

const ROLE_LABELS = {
  admin: "Адміністратор",
  user: "Користувач",
};

export async function createProfileCard() {
  const root = await getTemplate("profile-card.html");
  const ui = refs(root);

  return {
    element: root,
    update(user) {
      setText(ui.profileUsername, user.username);
      setText(ui.profileEmail, user.email);
      setText(ui.profileRole, ROLE_LABELS[user.role] || user.role);
      setText(ui.profileCreated, formatDateTime(user.created_at));
    },
  };
}
