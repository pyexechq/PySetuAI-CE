const backendUrl = document.getElementById("backend-url");
const apiKey = document.getElementById("api-key");
const save = document.getElementById("save");
const status = document.getElementById("status");

async function load() {
  const settings = await chrome.storage.local.get({ backendUrl: "http://localhost:8001", apiKey: "" });
  backendUrl.value = settings.backendUrl;
  apiKey.value = settings.apiKey;
}

async function requestBackendPermission(url) {
  const origin = new URL(url).origin;
  if (origin === "http://localhost:8001") return true;
  return chrome.permissions.request({ origins: [`${origin}/*`] });
}

save.addEventListener("click", async () => {
  status.textContent = "Verifying...";
  try {
    const url = backendUrl.value.trim().replace(/\/$/, "");
    const key = apiKey.value.trim();
    if (!url || !key) throw new Error("Backend URL and API key are required.");
    if (!(await requestBackendPermission(url))) throw new Error("Backend permission was not granted.");
    await chrome.storage.local.set({ backendUrl: url, apiKey: key, config: null, configFetchedAt: 0 });
    const response = await new Promise((resolve) => chrome.runtime.sendMessage({ type: "extension-config", force: true }, resolve));
    if (!response?.ok) throw new Error(response?.error || "Backend verification failed.");
    const domains = response.data.target_domains.length ? response.data.target_domains.join(", ") : "no domains configured";
    status.textContent = `Connected. Protected sites: ${domains}.`;
  } catch (error) {
    status.textContent = error.message;
  }
});

load();
