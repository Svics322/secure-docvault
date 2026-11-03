import { getTemplate } from "../core/templates.js";
import { refs, setErrors, toggleHidden } from "../core/dom.js";
import { showApiError } from "../core/errors.js";
import { attachPasswordToggle } from "./password-toggle.js";

export async function createLoginForm({ onSubmit }) {
  const root = await getTemplate("login-form.html");
  const ui = refs(root);
  const passwordToggle = attachPasswordToggle(
    ui.loginPassword,
    ui.loginPasswordToggle
  );
  const fields = {
    username: ui.loginUsernameErrors,
    password: ui.loginPasswordErrors,
  };

  function clearErrors() {
    setErrors(ui.loginErrors);
    Object.values(fields).forEach((node) => setErrors(node));
  }

  ui.loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors();

    const username = ui.loginUsername.value.trim();
    const password = ui.loginPassword.value;

    try {
      await onSubmit?.({ username, password });
      ui.loginPassword.value = "";
      passwordToggle.reset();
    } catch (error) {
      showApiError(error, { fields, general: ui.loginErrors });
    }
  });

  return {
    element: root,
    show(username = "") {
      clearErrors();
      passwordToggle.reset();
      if (username) {
        ui.loginUsername.value = username;
      }
      toggleHidden(root, false);
    },
    hide() {
      toggleHidden(root, true);
    },
  };
}
