const MESSAGE_TYPES = {
  CONFIG: "extension-config",
  SCAN: "extension-scan",
  INCIDENT: "extension-incident",
};

const DEBOUNCE_MS = 500;
const ADAPTERS = [
  {
    domains: ["chatgpt.com", "chat.openai.com"],
    composer: "textarea, [contenteditable='true'][role='textbox'], [contenteditable='true']",
    send: "button[data-testid*='send'], button[data-testid*='submit'], button[aria-label*='Send'], button[aria-label*='send']",
  },
  {
    domains: ["gemini.google.com"],
    composer: "rich-textarea, textarea, [contenteditable='true']",
    send: "button[aria-label*='Send'], button[aria-label*='send']",
  },
  {
    domains: ["claude.ai"],
    composer: "textarea, [contenteditable='true']",
    send: "button[aria-label*='Send'], button[aria-label*='send']",
  },
];

let activeConfig = null;
let latestVerdict = null;
let scanTimer = null;
let guardedSubmit = false;

function currentAdapter() {
  return ADAPTERS.find((adapter) => adapter.domains.some((domain) => location.hostname === domain || location.hostname.endsWith(`.${domain}`)));
}

function domainMatches(hostname, domains) {
  return domains.some((domain) => {
    const normalized = domain.trim().toLowerCase().replace(/^https?:\/\//, "").replace(/^www\./, "");
    const host = hostname.toLowerCase().replace(/^www\./, "");
    return host === normalized || host.endsWith(`.${normalized}`);
  });
}

function sendMessage(message) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage(message, (response) => {
        const runtimeError = chrome.runtime.lastError;
        resolve(runtimeError ? { ok: false, error: runtimeError.message } : response);
      });
    } catch (error) {
      resolve({ ok: false, error: error instanceof Error ? error.message : "Extension context unavailable" });
    }
  });
}

function readComposer(element) {
  return element.matches("textarea") ? element.value : element.innerText;
}

function findComposer(selector) {
  const active = document.activeElement instanceof Element ? document.activeElement.closest(selector) : null;
  if (active) return active;
  return [...document.querySelectorAll(selector)].find((element) => readComposer(element).trim());
}

async function writeComposer(element, content) {
  if (element.matches("textarea")) {
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set;
    setter?.call(element, content);
    element.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertReplacementText", data: content }));
  } else {
    element.focus();
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(element);
    selection?.removeAllRanges();
    selection?.addRange(range);
    if (!document.execCommand("insertText", false, content)) {
      element.textContent = content;
    }
    element.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: content }));
  }
  await new Promise((resolve) => window.requestAnimationFrame(resolve));
}

function showBanner(text, blocked = false) {
  let banner = document.getElementById("pysetu-browser-protection");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "pysetu-browser-protection";
    banner.style.cssText = "position:fixed;z-index:2147483647;right:16px;bottom:16px;max-width:360px;padding:12px 16px;border:1px solid #d97706;border-radius:8px;background:#fffbeb;color:#78350f;font:14px/1.4 sans-serif;box-shadow:0 4px 16px #0002";
    document.documentElement.appendChild(banner);
  }
  banner.textContent = text;
  banner.style.display = "block";
  if (!blocked) window.setTimeout(() => { banner.style.display = "none"; }, 2500);
}

async function scan(content) {
  const result = await sendMessage({
    type: MESSAGE_TYPES.SCAN,
    payload: { content, site: location.hostname, url: location.href },
  });
  if (!result?.ok) {
    showBanner(`PySetu protection unavailable: ${result?.error || "scan failed"}`);
    return null;
  }
  latestVerdict = { content, verdict: result.data };
  if (result.data.action === "redact") {
    showBanner(result.data.reason || "Sensitive values will be redacted before sending");
  } else if (!result.data.allowed) {
    showBanner(`Message blocked: ${result.data.reason || result.data.matched_rule || "policy violation"}`, true);
  }
  return result.data;
}

function scheduleScan(element) {
  window.clearTimeout(scanTimer);
  scanTimer = window.setTimeout(() => {
    const content = readComposer(element).trim();
    if (content) scan(content);
  }, DEBOUNCE_MS);
}

async function enforceSubmit(event, composer) {
  if (guardedSubmit) return;
  const content = readComposer(composer).trim();
  if (!content) return;

  event.preventDefault();
  event.stopImmediatePropagation();
  const verdict = latestVerdict?.content === content ? latestVerdict.verdict : await scan(content);
  if (!verdict) return;
  if (!verdict.allowed || verdict.action === "redact") {
    sendMessage({
      type: MESSAGE_TYPES.INCIDENT,
      payload: {
        site: location.hostname,
        url: location.href,
        action: verdict.action === "redact" ? "redact" : "block",
        matched_rule: verdict.matched_rule,
        sensitivity_labels: verdict.sensitivity_labels,
        redacted_input: verdict.redacted_content,
        input_hash: verdict.input_hash,
        input_length: verdict.input_length,
      },
    }).catch(() => undefined);
    if (!verdict.allowed) return;
    if (!verdict.redacted_content) return;
    await writeComposer(composer, verdict.redacted_content);
    if (readComposer(composer).trim() !== verdict.redacted_content.trim()) {
      showBanner("Message blocked: the AI site did not accept the redacted prompt", true);
      sendMessage({
        type: MESSAGE_TYPES.INCIDENT,
        payload: {
          site: location.hostname,
          url: location.href,
          action: "block",
          matched_rule: verdict.matched_rule,
          sensitivity_labels: verdict.sensitivity_labels,
          input_hash: verdict.input_hash,
          input_length: verdict.input_length,
        },
      }).catch(() => undefined);
      return;
    }
  }

  guardedSubmit = true;
  if (event.type === "keydown") {
    composer.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", bubbles: true }));
  } else if (event.type === "submit" && composer.form) {
    composer.form.requestSubmit();
  } else if (event.target instanceof HTMLElement) {
    event.target.click();
  }
  window.setTimeout(() => { guardedSubmit = false; }, 0);
}

async function initialize() {
  const configResponse = await sendMessage({ type: MESSAGE_TYPES.CONFIG });
  if (!configResponse?.ok) {
    showBanner(`PySetu protection unavailable: ${configResponse?.error || "configuration failed"}`);
    return;
  }
  activeConfig = configResponse.data;
  if (!activeConfig.target_domains.length || !domainMatches(location.hostname, activeConfig.target_domains)) {
    showBanner(`PySetu protection is not configured for ${location.hostname}`);
    return;
  }

  const adapter = currentAdapter();
  if (!adapter) return;
  document.addEventListener("input", (event) => {
    const composer = event.target instanceof Element ? event.target.closest(adapter.composer) : null;
    if (composer) scheduleScan(composer);
  }, true);
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey) return;
    const composer = event.target instanceof Element ? event.target.closest(adapter.composer) : null;
    if (composer) enforceSubmit(event, composer);
  }, true);
  document.addEventListener("click", (event) => {
    const clicked = event.target instanceof Element ? event.target.closest("button") : null;
    const composer = findComposer(adapter.composer);
    const isSend = clicked && (clicked.matches(adapter.send) || clicked.type === "submit");
    if (composer && isSend) enforceSubmit(event, composer);
  }, true);
  document.addEventListener("submit", (event) => {
    const composer = findComposer(adapter.composer);
    if (composer) enforceSubmit(event, composer);
  }, true);
}

initialize();
