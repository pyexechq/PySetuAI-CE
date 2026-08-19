import { CONFIG_TTL_MS, DEFAULT_BACKEND_URL, MESSAGE_TYPES } from "../shared/constants.js";

async function getSettings() {
  const stored = await chrome.storage.local.get({
    backendUrl: DEFAULT_BACKEND_URL,
    apiKey: "",
    config: null,
    configFetchedAt: 0,
  });
  return { ...stored, backendUrl: stored.backendUrl.replace(/\/$/, "") };
}

async function apiRequest(path, options = {}) {
  const settings = await getSettings();
  if (!settings.apiKey) {
    throw new Error("Configure a PySetu API key in the extension settings.");
  }

  const response = await fetch(`${settings.backendUrl}/api/v1${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${settings.apiKey}`,
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || `Backend request failed (${response.status})`);
  }
  return body;
}

async function getConfig(force = false) {
  const settings = await getSettings();
  if (!force && settings.config && Date.now() - settings.configFetchedAt < CONFIG_TTL_MS) {
    return settings.config;
  }
  const config = await apiRequest("/extension/config");
  await chrome.storage.local.set({ config, configFetchedAt: Date.now() });
  return config;
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  const operation = message?.type;
  if (![MESSAGE_TYPES.CONFIG, MESSAGE_TYPES.SCAN, MESSAGE_TYPES.INCIDENT].includes(operation)) {
    return false;
  }

  (async () => {
    if (operation === MESSAGE_TYPES.CONFIG) {
      return { ok: true, data: await getConfig(Boolean(message.force)) };
    }
    if (operation === MESSAGE_TYPES.SCAN) {
      return { ok: true, data: await apiRequest("/extension/scan", {
        method: "POST",
        body: JSON.stringify(message.payload),
      }) };
    }
    return { ok: true, data: await apiRequest("/extension/incidents", {
      method: "POST",
      body: JSON.stringify(message.payload),
    }) };
  })().then(sendResponse).catch((error) => sendResponse({ ok: false, error: error.message }));

  return true;
});

chrome.runtime.onInstalled.addListener(() => {
  getConfig(true).catch(() => undefined);
});
