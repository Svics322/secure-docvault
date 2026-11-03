import { getTemplate } from "../core/templates.js";
import { refs, toggleHidden } from "../core/dom.js";
import { createLoginForm } from "../components/login-form.js";
import { createRegisterForm } from "../components/register-form.js";
import { createTabs } from "../components/tabs.js";

export async function createAuthView({ onLogin, onRegister }) {
  const root = await getTemplate("auth-view.html");
  const ui = refs(root);

  const login = await createLoginForm({ onSubmit: onLogin });
  const register = await createRegisterForm({
    onSubmit: onRegister,
    onSuccess: (username) => switchTo("login", username),
  });
  const tabs = await createTabs({
    items: [
      { id: "login", label: "Вхід" },
      { id: "register", label: "Реєстрація" },
    ],
    onChange: (id) => switchTo(id),
  });

  ui.tabsHost.append(tabs.element);
  ui.loginHost.append(login.element);
  ui.registerHost.append(register.element);

  function switchTo(name, username = "") {
    tabs.setActive(name);
    if (name === "login") {
      login.show(username);
      register.hide();
    } else {
      login.hide();
      register.show();
    }
  }

  switchTo("login");

  return {
    element: root,
    show() {
      toggleHidden(root, false);
    },
    hide() {
      toggleHidden(root, true);
    },
    showLogin(username = "") {
      switchTo("login", username);
    },
  };
}
