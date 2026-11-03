const cache = new Map();

async function fetchTemplate(name) {
  const response = await fetch(`/static/templates/${name}`, {
    credentials: "same-origin",
  });
  if (!response.ok) {
    throw new Error(`Не вдалося завантажити шаблон: ${name}`);
  }
  return response.text();
}

export async function getTemplate(name) {
  if (!cache.has(name)) {
    cache.set(name, fetchTemplate(name));
  }

  const html = await cache.get(name);
  const template = document.createElement("template");
  template.innerHTML = html.trim();

  const node = template.content.firstElementChild;
  if (!node) {
    throw new Error(`Порожній шаблон: ${name}`);
  }
  return node.cloneNode(true);
}
