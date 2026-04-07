const sidebar = document.getElementById("sidebar");
const sessionList = document.getElementById("sessionList");
const messageList = document.getElementById("messageList");
const chatTitle = document.getElementById("chatTitle");
const commandInput = document.getElementById("commandInput");

const refreshStatusBtn = document.getElementById("refreshStatusBtn");
const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
const sendCommandBtn = document.getElementById("sendCommandBtn");
const openSidebarBtn = document.getElementById("openSidebarBtn");
const closeSidebarBtn = document.getElementById("closeSidebarBtn");

const serviceStatusText = document.getElementById("serviceStatusText");
const n8nStatusText = document.getElementById("n8nStatusText");
const screenshotLink = document.getElementById("screenshotLink");
const debugSummaryText = document.getElementById("debugSummaryText");

let selectedSessionId = "";
let sessionsCache = [];
let messagesCache = [];

async function apiGet(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`request failed: ${res.status}`);
  return res.json();
}

async function loadHistory() {
  const [sessions, messages] = await Promise.all([
    apiGet("/api/chat/sessions"),
    apiGet("/api/chat/messages"),
  ]);
  sessionsCache = sessions;
  messagesCache = messages;
  if (!selectedSessionId && sessionsCache.length > 0) selectedSessionId = sessionsCache[0].id;
  renderSessions();
  renderMessages();
}

function renderSessions() {
  sessionList.innerHTML = "";
  sessionsCache.forEach((s) => {
    const li = document.createElement("li");
    li.className = "session-item" + (s.id === selectedSessionId ? " active" : "");
    li.innerHTML = `<strong>${s.title}</strong><br/><small>${s.updatedAt}</small>`;
    li.onclick = () => { selectedSessionId = s.id; renderSessions(); renderMessages(); };
    sessionList.appendChild(li);
  });
}

function renderMessages() {
  const visible = messagesCache.filter((m) => m.sessionId === selectedSessionId);
  chatTitle.textContent = sessionsCache.find((s) => s.id === selectedSessionId)?.title || "세션";
  messageList.innerHTML = "";
  visible.forEach((m) => {
    const div = document.createElement("div");
    div.className = "message " + (m.role === "user" ? "user" : "system");
    div.textContent = m.text;
    messageList.appendChild(div);
  });
  messageList.scrollTop = messageList.scrollHeight;
}

async function loadStatus() {
  const status = await apiGet("/api/status");
  serviceStatusText.textContent = `${status.cloudRun} / ${status.unityWorker}`;
  n8nStatusText.textContent = `${status.n8n.lastResult} at ${status.n8n.lastTime}`;
  screenshotLink.href = status.latestScreenshotUrl || "#";
  screenshotLink.textContent = status.latestScreenshotUrl ? "스크린샷 열기" : "스크린샷 없음";
  debugSummaryText.textContent = status.debugSummary;
}

async function saveCommand() {
  const text = commandInput.value.trim();
  if (!text || !selectedSessionId) return;
  await fetch("/api/chat/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessionId: selectedSessionId, role: "user", text }),
  });
  commandInput.value = "";
  await loadHistory();
}

refreshStatusBtn.onclick = () => loadStatus().catch((e) => alert(e.message));
refreshHistoryBtn.onclick = () => loadHistory().catch((e) => alert(e.message));
sendCommandBtn.onclick = () => saveCommand().catch((e) => alert(e.message));
openSidebarBtn.onclick = () => sidebar.classList.remove("hidden");
closeSidebarBtn.onclick = () => sidebar.classList.add("hidden");

loadHistory().catch(() => {});
