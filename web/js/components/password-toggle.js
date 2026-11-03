export function attachPasswordToggle(input, button) {
  if (!input || !button) {
    return { reset() {} };
  }

  function setVisible(visible) {
    input.type = visible ? "text" : "password";
    button.classList.toggle("is-visible", visible);
    button.setAttribute("aria-pressed", String(visible));
    button.setAttribute(
      "aria-label",
      visible ? "Приховати пароль" : "Показати пароль"
    );
  }

  button.addEventListener("click", () => {
    const visible = input.type === "password";
    setVisible(visible);
    input.focus({ preventScroll: true });
  });

  setVisible(false);

  return {
    reset() {
      setVisible(false);
    },
  };
}
