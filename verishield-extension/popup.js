const activeInput = document.getElementById("active");
const rescanButton = document.getElementById("rescan");
const status = document.getElementById("status");

async function currentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function updateSummary() {
  const tab = await currentTab();
  if (!tab?.id) throw new Error("No active tab");
  const summary = await chrome.tabs.sendMessage(tab.id, { type: "VERIBAR_SUMMARY" });
  document.getElementById("scanned").textContent = String(summary.scanned);
  document.getElementById("average").textContent = summary.averageScore == null ? "—" : `${summary.averageScore}%`;
  document.getElementById("patterns").textContent = String(summary.patternScanned);
  status.textContent = summary.active ? "Scanning is active on this page." : "Scanning is off.";
}

activeInput.addEventListener("change", async () => {
  await chrome.storage.local.set({ veribarActive: activeInput.checked });
  try { await updateSummary(); } catch (_error) { status.textContent = "Reload this page to start scanning."; }
});

rescanButton.addEventListener("click", async () => {
  rescanButton.disabled = true;
  try {
    const tab = await currentTab();
    await chrome.tabs.sendMessage(tab.id, { type: "VERIBAR_RESCAN" });
    await updateSummary();
  } catch (_error) {
    status.textContent = "This page cannot be scanned. Try an ordinary web page.";
  } finally {
    rescanButton.disabled = false;
  }
});

chrome.storage.local.get({ veribarActive: true }).then(async ({ veribarActive }) => {
  activeInput.checked = veribarActive;
  try {
    await updateSummary();
    // Analysis completes asynchronously, including after a manual rescan.
    setInterval(() => { updateSummary().catch(() => {}); }, 1000);
  } catch (_error) {
    status.textContent = "Open or reload an ordinary web page to use VeriBar.";
    rescanButton.disabled = true;
  }
});
