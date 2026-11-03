export const $ = (selector, root = document) => root.querySelector(selector);

export const $$ = (selector, root = document) =>
  Array.from(root.querySelectorAll(selector));

export function refs(root) {
  const nodes = root.matches?.("[data-ref]") ? [root] : [];
  nodes.push(...$$("[data-ref]", root));
  return nodes.reduce((mapped, node) => {
    mapped[node.dataset.ref] = node;
    return mapped;
  }, {});
}

export function setText(node, value, fallback = "—") {
  if (node) {
    node.textContent = value ?? fallback;
  }
}

export function setError(node, message = "") {
  if (node) {
    node.textContent = message;
  }
}

export function setErrors(node, messages) {
  if (!node) {
    return;
  }

  const list = (Array.isArray(messages) ? messages : messages ? [messages] : [])
    .map((message) => String(message).trim())
    .filter(Boolean);

  node.replaceChildren();
  list.forEach((message) => {
    const item = document.createElement("li");
    item.textContent = message;
    node.appendChild(item);
  });

  node.classList.toggle("hidden", list.length === 0);
}

export function toggleHidden(node, hidden) {
  if (node) {
    node.classList.toggle("hidden", hidden);
  }
}
