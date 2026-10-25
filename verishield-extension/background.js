const ENDPOINT = "http://127.0.0.1:8001/verify";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "VERISHIELD_VERIFY") return false;
  if (!sender.tab || typeof message.html !== "string" || message.html.length > 30000) {
    sendResponse({ ok: false, error: "Invalid analysis request" });
    return false;
  }

  const controller = new AbortController();
  // Never leave a page bar waiting indefinitely when the local model stalls.
  const timeout = setTimeout(() => controller.abort(), 20000);
  fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ html: message.html }),
    signal: controller.signal
  })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Local API returned ${response.status}`);
      return response.json();
    })
    .then((result) => sendResponse({ ok: true, result }))
    .catch((error) => sendResponse({ ok: false, error: error.message }))
    .finally(() => clearTimeout(timeout));
  return true;
});
