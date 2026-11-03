import { getTemplate } from "../core/templates.js";
import { refs, setErrors, toggleHidden } from "../core/dom.js";
import { showApiError } from "../core/errors.js";
import { attachPasswordToggle } from "./password-toggle.js";

export async function createRegisterForm({ onSubmit, onSuccess }) {
  const root = await getTemplate("register-form.html");
  const ui = refs(root);
  const passwordToggle = attachPasswordToggle(
    ui.registerPassword,
    ui.registerPasswordToggle
  );
  const fields = {
    username: ui.registerUsernameErrors,
    email: ui.registerEmailErrors,
    password: ui.registerPasswordErrors,
  };

  function clearErrors() {
    setErrors(ui.registerErrors);
    Object.values(fields).forEach((node) => setErrors(node));
  }

  ui.registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors();

    const username = ui.registerUsername.value.trim();
    const email = ui.registerEmail.value.trim();
    const password = ui.registerPassword.value;

    try {
      await onSubmit?.({ username, email, password });
      ui.registerPassword.value = "";
      passwordToggle.reset();
      onSuccess?.(username);
    } catch (error) {
      showApiError(error, { fields, general: ui.registerErrors });
    }
  });

  return {
    element: root,
    show() {
      clearErrors();
      passwordToggle.reset();
      toggleHidden(root, false);
    },
    hide() {
      toggleHidden(root, true);
    },
  };
}
