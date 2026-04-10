const sidebar = document.getElementById("sidebar");
const sessionList = document.getElementById("sessionList");
const messageList = document.getElementById("messageList");
const commandInput = document.getElementById("commandInput");

const sendCommandBtn = document.getElementById("sendCommandBtn");
const openSidebarBtn = document.getElementById("openSidebarBtn");
const closeSidebarBtn = document.getElementById("closeSidebarBtn");
const newSessionBtn = document.getElementById("newSessionBtn");
const rulesBtn = document.getElementById("rulesBtn");
const rulesModal = document.getElementById("rulesModal");
const rulesModalBackdrop = document.getElementById("rulesModalBackdrop");
const rulesModalClose = document.getElementById("rulesModalClose");
const rulesTextarea = document.getElementById("rulesTextarea");
const rulesSaveBtn = document.getElementById("rulesSaveBtn");

const siteBtn = document.getElementById("siteBtn");
const siteModal = document.getElementById("siteModal");
const siteModalBackdrop = document.getElementById("siteModalBackdrop");
const siteModalClose = document.getElementById("siteModalClose");
const siteSaveBtn = document.getElementById("siteSaveBtn");
const siteTitleInput = document.getElementById("siteTitleInput");
const siteActiveProjectInput = document.getElementById("siteActiveProjectInput");
const siteWebhookInput = document.getElementById("siteWebhookInput");
const siteN8nStatusInput = document.getElementById("siteN8nStatusInput");
const siteCloudRunHealthInput = document.getElementById("siteCloudRunHealthInput");
const siteUnityHealthInput = document.getElementById("siteUnityHealthInput");
const chatAssistantModeSelect = document.getElementById("chatAssistantModeSelect");
const cursorBridgeWebhookInput = document.getElementById("cursorBridgeWebhookInput");
const copyCursorPromptBtn = document.getElementById("copyCursorPromptBtn");

const statusTabs = document.getElementById("statusTabs");
const statusBodyWrap = document.getElementById("statusBodyWrap");
const cursorAgentWrap = document.getElementById("cursorAgentWrap");
const manualPanel = document.getElementById("manualPanel");
const pipelineCurrentCommand = document.getElementById("pipelineCurrentCommand");
const pipelineCurrentStep = document.getElementById("pipelineCurrentStep");
const pipelineNodeCommand = document.getElementById("pipelineNodeCommand");
const pipelineNodeCursor = document.getElementById("pipelineNodeCursor");
const pipelineNodeVm = document.getElementById("pipelineNodeVm");
const pipelineNodeGit = document.getElementById("pipelineNodeGit");
const pipelineCommandStatus = document.getElementById("pipelineCommandStatus");
const pipelineCursorStatus = document.getElementById("pipelineCursorStatus");
const pipelineVmStatus = document.getElementById("pipelineVmStatus");
const pipelineGitStatus = document.getElementById("pipelineGitStatus");
const pipelineCommandTs = document.getElementById("pipelineCommandTs");
const pipelineCursorTs = document.getElementById("pipelineCursorTs");
const pipelineVmTs = document.getElementById("pipelineVmTs");
const pipelineGitTs = document.getElementById("pipelineGitTs");
const statusMainTitle = document.getElementById("statusMainTitle");
const statusMainText = document.getElementById("statusMainText");
const statusMainLink = document.getElementById("statusMainLink");
const statusProgressWrap = document.getElementById("statusProgressWrap");
const statusProgressBody = document.getElementById("statusProgressBody");
const statusProgressMeta = document.getElementById("statusProgressMeta");
const currentChatName = document.getElementById("currentChatName");
const activeProjectName = document.getElementById("activeProjectName");

const stackInput = document.getElementById("stackInput");
const stackSaveBtn = document.getElementById("stackSaveBtn");
const dispatchNextBtn = document.getElementById("dispatchNextBtn");
const refreshQueueBtn = document.getElementById("refreshQueueBtn");
const queueList = document.getElementById("queueList");
const stackPanel = document.getElementById("stackPanel");
const toggleStackBtn = document.getElementById("toggleStackBtn");
const closeStackBtn = document.getElementById("closeStackBtn");

const sidebarTabSessions = document.getElementById("sidebarTabSessions");
const sidebarTabGuide = document.getElementById("sidebarTabGuide");
const sidebarSessionsWrap = document.getElementById("sidebarSessionsWrap");
const sidebarGuideWrap = document.getElementById("sidebarGuideWrap");

let selectedSessionId = "";
let sessionsCache = [];
let messagesCache = [];
let activeStatusTab = "progress";
let progressPollTimer = null;

const TAB_TITLES = {
  queue: "명령 큐",
  progress: "진행 상황",
  manual: "메뉴얼",
  n8n: "n8n",
  service: "서비스",
  screenshot: "스크린샷",
  debug: "디버그",
  cursorAgent: "Cursor",
};

async function apiGet(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`request failed: ${res.status}`);
  return res.json();
}

function statusQuery(extra = {}) {
  const p = new URLSearchParams();
  Object.keys(extra).forEach((k) => {
    const v = extra[k];
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  });
  if (selectedSessionId) p.set("sessionId", selectedSessionId);
  const s = p.toString();
  return s ? `?${s}` : "";
}

function showTabPlaceholder() {
  statusMainLink.classList.remove("visible");
  statusMainLink.href = "#";
  statusMainTitle.textContent = TAB_TITLES[activeStatusTab] || "상태";
  if (activeStatusTab === "cursorAgent") {
    statusMainText.textContent = "";
    return;
  }
  if (activeStatusTab === "manual") {
    statusMainText.textContent = "";
    return;
  }
  const loadingTabs = ["queue", "progress", "n8n", "service", "screenshot", "debug"];
  statusMainText.textContent = loadingTabs.includes(activeStatusTab)
    ? "불러오는 중…"
    : "채팅 전송 시 이 탭이 갱신됩니다.";
}

function hideProgressPanel() {
  if (statusProgressWrap) statusProgressWrap.classList.add("hidden");
}

function renderProgressPanel(status) {
  if (!statusProgressWrap || !statusProgressBody || !statusProgressMeta) return;
  const pr = status.progress;
  if (!pr) {
    statusProgressWrap.classList.add("hidden");
    return;
  }
  statusProgressWrap.classList.remove("hidden");
  const parts = [];
  if (pr.hints && pr.hints.length) {
    parts.push("[안내]");
    pr.hints.forEach((h) => parts.push(`  • ${h}`));
    parts.push("");
  }
  const sections = [
    ["queue", "[큐]"],
    ["service", "[서비스]"],
    ["screenshot", "[스크린샷]"],
    ["debug", "[디버그]"],
  ];
  sections.forEach(([k, label]) => {
    const b = pr[k];
    if (!b) return;
    parts.push(`${label} ${b.summary}`);
    (b.lines || []).forEach((ln) => parts.push(`  ${ln}`));
    parts.push("");
  });
  statusProgressBody.textContent = parts.join("\n").trim();
  const sidLabel = pr.sessionId ? pr.sessionId : "(전체)";
  statusProgressMeta.textContent = `서버 시각 ${pr.serverTime || "-"} · 세션 ${sidLabel}`;
}

function startProgressPolling() {
  if (progressPollTimer) {
    clearInterval(progressPollTimer);
    progressPollTimer = null;
  }
  if (activeStatusTab !== "progress") return;
  progressPollTimer = setInterval(() => {
    refreshActiveStatusTab().catch(() => {});
  }, 4000);
}

async function loadHistory() {
  const [sessions, messages] = await Promise.all([
    apiGet("/api/chat/sessions"),
    apiGet("/api/chat/messages"),
  ]);
  sessionsCache = sessions;
  messagesCache = messages;
  if (!selectedSessionId && sessionsCache.length > 0) selectedSessionId = sessionsCache[0].id;
  if (sessionsCache.length > 0 && selectedSessionId && !sessionsCache.some((s) => s.id === selectedSessionId)) {
    selectedSessionId = sessionsCache[0].id;
  }
  renderSessions();
  renderMessages();
}

function renderSessions() {
  sessionList.innerHTML = "";
  sessionsCache.forEach((s) => {
    const li = document.createElement("li");
    li.className = "session-item" + (s.id === selectedSessionId ? " active" : "");

    const body = document.createElement("div");
    body.className = "session-item-body";
    body.innerHTML = `<strong>${escapeHtml(s.title)}</strong><br/><small>${escapeHtml(s.updatedAt || "")}</small>`;
    body.onclick = () => {
      selectedSessionId = s.id;
      renderSessions();
      renderMessages();
      refreshActiveStatusTab().catch(() => {});
    };

    const del = document.createElement("button");
    del.type = "button";
    del.className = "session-delete";
    del.textContent = "삭제";
    del.onclick = (e) => {
      e.stopPropagation();
      deleteSession(s.id);
    };

    li.appendChild(body);
    li.appendChild(del);
    sessionList.appendChild(li);
  });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function deleteSession(sessionId) {
  if (!confirm("이 기록을 삭제할까요?")) return;
  const res = await fetch(`/api/chat/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("삭제 실패");
  if (selectedSessionId === sessionId) selectedSessionId = "";
  await loadHistory();
  showTabPlaceholder();
  refreshActiveStatusTab().catch(() => {});
}

async function createNewSession() {
  const res = await fetch("/api/chat/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: "새 채팅" }),
  });
  if (!res.ok) throw new Error("새 글 생성 실패");
  const data = await res.json();
  selectedSessionId = data.session.id;
  await loadHistory();
  sidebar.classList.remove("hidden");
  refreshActiveStatusTab().catch(() => {});
}

function renderMessages() {
  const visible = messagesCache.filter((m) => m.sessionId === selectedSessionId);
  const title = sessionsCache.find((s) => s.id === selectedSessionId)?.title || "세션";
  currentChatName.textContent = `현재 채팅: ${title}`;
  messageList.innerHTML = "";
  visible.forEach((m) => {
    const div = document.createElement("div");
    div.className =
      "message " +
      (m.role === "user" ? "user" : m.role === "assistant" ? "assistant" : "system");
    div.textContent = m.text;
    messageList.appendChild(div);
  });
  messageList.scrollTop = messageList.scrollHeight;
}

async function loadStatusN8n() {
  return apiGet(`/api/status${statusQuery({ include_n8n: "true" })}`);
}

async function loadStatusServices() {
  return apiGet(`/api/status${statusQuery({ include_services: "true" })}`);
}

async function loadStatusScreenshot() {
  return apiGet(`/api/status${statusQuery({})}`);
}

async function loadStatusDebug() {
  return apiGet(`/api/status${statusQuery({})}`);
}

async function loadStatusQueue() {
  return apiGet(`/api/status${statusQuery({})}`);
}

async function loadStatusFull() {
  return apiGet(`/api/status${statusQuery({ include_services: "true", include_n8n: "true" })}`);
}

async function loadPipelineSnapshot() {
  return apiGet("/api/pipeline-state");
}

function setNodeVisual(groupEl, state) {
  if (!groupEl) return;
  const rect = groupEl.querySelector("rect");
  if (!rect) return;
  rect.classList.remove("pipeline-node-pending", "pipeline-node-running", "pipeline-node-success", "pipeline-node-failed");
  if (state === "running") rect.classList.add("pipeline-node-running");
  else if (state === "success") rect.classList.add("pipeline-node-success");
  else if (state === "failed") rect.classList.add("pipeline-node-failed");
  else rect.classList.add("pipeline-node-pending");
}

function setStatusText(el, status, ts) {
  if (!el) return;
  el.textContent = `상태: ${status || "-"}`;
  if (ts) {
    const tsEl =
      el === pipelineCommandStatus ? pipelineCommandTs :
      el === pipelineCursorStatus ? pipelineCursorTs :
      el === pipelineVmStatus ? pipelineVmTs :
      el === pipelineGitStatus ? pipelineGitTs : null;
    if (tsEl) tsEl.textContent = ts;
  }
}

async function refreshPipelineSnapshot() {
  try {
    const res = await loadPipelineSnapshot();
    const snap = res.pipeline || {};
    const nodeMap = {};
    (snap.nodes || []).forEach((n) => {
      nodeMap[n.id] = n;
    });

    if (pipelineCurrentCommand) {
      pipelineCurrentCommand.textContent = `현재 명령: ${snap.currentCommand || "-"}`;
    }
    if (pipelineCurrentStep) {
      pipelineCurrentStep.textContent = `현재 단계: ${snap.currentStage || "-"} (${snap.belongsTo || "일반"})`;
    }

    setNodeVisual(pipelineNodeCommand, nodeMap.command?.state);
    setNodeVisual(pipelineNodeCursor, nodeMap.cursor?.state);
    setNodeVisual(pipelineNodeVm, nodeMap.vm?.state);
    setNodeVisual(pipelineNodeGit, nodeMap.git?.state);

    setStatusText(pipelineCommandStatus, nodeMap.command?.state || "pending", snap.updatedAt || "-");
    setStatusText(pipelineCursorStatus, nodeMap.cursor?.state || "idle", snap.updatedAt || "-");
    setStatusText(pipelineVmStatus, nodeMap.vm?.state || "unknown", snap.updatedAt || "-");
    setStatusText(pipelineGitStatus, nodeMap.git?.state || "unknown", snap.updatedAt || "-");
  } catch (_e) {
    if (pipelineCurrentCommand) pipelineCurrentCommand.textContent = "현재 명령: -";
    if (pipelineCurrentStep) pipelineCurrentStep.textContent = "현재 단계: -";
  }
}

async function loadActiveProject() {
  try {
    const status = await apiGet(`/api/status${statusQuery({})}`);
    activeProjectName.textContent = `활성 프로젝트: ${status.activeProject || "-"}`;
  } catch (_e) {
    activeProjectName.textContent = "활성 프로젝트: -";
  }
}

function renderStatusTab(tab, status) {
  if (tab === "cursorAgent") {
    if (statusBodyWrap) statusBodyWrap.classList.add("hidden");
    if (cursorAgentWrap) cursorAgentWrap.classList.remove("hidden");
    if (manualPanel) manualPanel.classList.add("hidden");
    hideProgressPanel();
    statusMainLink.classList.remove("visible");
    statusMainLink.href = "#";
    return;
  }
  if (tab === "manual") {
    if (statusBodyWrap) statusBodyWrap.classList.add("hidden");
    if (cursorAgentWrap) cursorAgentWrap.classList.add("hidden");
    if (manualPanel) manualPanel.classList.remove("hidden");
    hideProgressPanel();
    statusMainLink.classList.remove("visible");
    statusMainLink.href = "#";
    return;
  }
  if (statusBodyWrap) statusBodyWrap.classList.remove("hidden");
  if (cursorAgentWrap) cursorAgentWrap.classList.add("hidden");
  if (manualPanel) manualPanel.classList.add("hidden");

  statusMainLink.classList.remove("visible");
  statusMainLink.href = "#";
  statusMainLink.textContent = "열기";
  activeProjectName.textContent = `활성 프로젝트: ${status.activeProject || "-"}`;

  if (tab === "progress") {
    statusMainTitle.textContent = TAB_TITLES.progress;
    statusMainText.textContent = "큐·서비스·스크린샷·디버그 요약·안내 (아래 스크롤)";
    renderProgressPanel(status);
    return;
  }

  hideProgressPanel();

  if (tab === "n8n") {
    statusMainTitle.textContent = "n8n 최근 실행";
    statusMainText.textContent = `${status.n8n?.lastResult || "unknown"} · ${status.n8n?.lastTime || "-"}`;
    return;
  }
  if (tab === "service") {
    statusMainTitle.textContent = "서비스 상태";
    statusMainText.textContent = `${status.cloudRun || "Cloud Run: unknown"} / ${status.unityWorker || "Unity Worker: unknown"}`;
  } else if (tab === "screenshot") {
    statusMainTitle.textContent = "최신 스크린샷";
    if (status.latestScreenshotUrl) {
      statusMainText.textContent = "스크린샷 링크가 있습니다.";
      statusMainLink.href = status.latestScreenshotUrl;
      statusMainLink.textContent = "스크린샷 열기";
      statusMainLink.classList.add("visible");
    } else {
      statusMainText.textContent = "스크린샷 없음";
    }
  } else if (tab === "debug") {
    statusMainTitle.textContent = "디버그 요약";
    statusMainText.textContent = status.debugSummary || "요약 없음";
  } else if (tab === "queue") {
    statusMainTitle.textContent = "명령 큐 상태";
    statusMainText.textContent = `대기 ${status.queue?.queued || 0} / 전송 ${status.queue?.sent || 0} / 전체 ${status.queue?.total || 0}`;
  }
}

async function refreshActiveStatusTab() {
  if (activeStatusTab === "cursorAgent") {
    renderStatusTab("cursorAgent", {});
    return;
  }
  if (activeStatusTab === "manual") {
    renderStatusTab("manual", {});
    return;
  }
  let status;
  if (activeStatusTab === "n8n") {
    status = await loadStatusN8n();
  } else if (activeStatusTab === "service") {
    status = await loadStatusServices();
  } else if (activeStatusTab === "screenshot") {
    status = await loadStatusScreenshot();
  } else if (activeStatusTab === "debug") {
    status = await loadStatusDebug();
  } else if (activeStatusTab === "progress") {
    status = await loadStatusFull();
  } else {
    status = await loadStatusQueue();
  }
  renderStatusTab(activeStatusTab, status);
}

function setActiveStatusTab(tab) {
  activeStatusTab = tab;
  [...statusTabs.querySelectorAll(".status-tab")].forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  if (progressPollTimer) {
    clearInterval(progressPollTimer);
    progressPollTimer = null;
  }
  showTabPlaceholder();
  refreshActiveStatusTab()
    .catch(() => {
      statusMainTitle.textContent = TAB_TITLES[activeStatusTab] || "상태";
      statusMainText.textContent = "상태를 불러오지 못했습니다. 잠시 후 채팅을 보내면 다시 갱신됩니다.";
    })
    .finally(() => {
      startProgressPolling();
    });
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
  await refreshActiveStatusTab();
}

function lastUserTextInSession() {
  const forSession = messagesCache.filter((m) => m.sessionId === selectedSessionId);
  for (let i = forSession.length - 1; i >= 0; i--) {
    if (forSession[i].role === "user") return forSession[i].text || "";
  }
  return "";
}

async function copyTextWithFallback(text) {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch (_e) {
      // clipboard API 거부·권한 없음 → execCommand 시도
    }
  }
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  ta.style.top = "0";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  ta.setSelectionRange(0, text.length);
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } finally {
    document.body.removeChild(ta);
  }
  if (!ok) throw new Error("copy failed");
}

async function copyCursorPromptToClipboard() {
  const raw = commandInput.value.trim() || lastUserTextInSession();
  if (!raw) {
    alert("입력창에 요청을 쓰거나, 먼저 명령을 저장한 뒤 다시 시도하세요.");
    return;
  }
  const res = await fetch(`/api/cursor-prompt?text=${encodeURIComponent(raw)}`);
  if (!res.ok) {
    alert("복사 실패");
    return;
  }
  const data = await res.json();
  try {
    await copyTextWithFallback(data.prompt || "");
    alert("Cursor 채팅에 붙여 넣을 프롬프트를 복사했습니다.");
  } catch (_e) {
    alert("클립보드에 복사하지 못했습니다. 브라우저 설정에서 이 사이트의 클립보드 접근을 허용한 뒤 다시 시도하세요.");
  }
}

async function loadQueue() {
  const items = await apiGet("/api/queue");
  queueList.innerHTML = "";
  items.slice().reverse().forEach((q) => {
    const li = document.createElement("li");
    li.textContent = `[${q.status}] ${q.command}`;
    queueList.appendChild(li);
  });
}

async function saveStack() {
  const rawText = stackInput.value.trim();
  if (!rawText || !selectedSessionId) return;
  const res = await fetch("/api/queue/stack", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessionId: selectedSessionId, rawText }),
  });
  if (!res.ok) throw new Error("스택 저장 실패");
  stackInput.value = "";
  await Promise.all([loadQueue(), loadHistory(), refreshActiveStatusTab()]);
}

async function dispatchNext() {
  const res = await fetch("/api/queue/dispatch-next", { method: "POST" });
  if (!res.ok) throw new Error("다음 명령 전송 실패");
  await Promise.all([loadQueue(), loadHistory(), refreshActiveStatusTab()]);
}

function openRulesModal() {
  rulesModal.classList.remove("hidden");
  rulesModal.setAttribute("aria-hidden", "false");
  apiGet("/api/rules")
    .then((data) => {
      rulesTextarea.value = data.content || "";
    })
    .catch(() => {
      rulesTextarea.value = "";
    });
}

function closeRulesModal() {
  rulesModal.classList.add("hidden");
  rulesModal.setAttribute("aria-hidden", "true");
}

async function saveRules() {
  const res = await fetch("/api/rules", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: rulesTextarea.value }),
  });
  if (!res.ok) throw new Error("규칙 저장 실패");
  closeRulesModal();
}

function applySiteTitleFromConfig(cfg) {
  const t = ((cfg && cfg.siteTitle) || "").trim() || "원격 개발 대시보드";
  document.title = t;
}

function openSiteModal() {
  siteModal.classList.remove("hidden");
  siteModal.setAttribute("aria-hidden", "false");
  apiGet("/api/site-config")
    .then((c) => {
      siteTitleInput.value = c.siteTitle || "";
      siteActiveProjectInput.value = c.activeProjectName || "";
      siteWebhookInput.value = c.n8nCommandWebhookUrl || "";
      siteN8nStatusInput.value = c.n8nStatusUrl || "";
      siteCloudRunHealthInput.value = c.cloudRunHealthUrl || "";
      siteUnityHealthInput.value = c.unityWorkerHealthUrl || "";
      chatAssistantModeSelect.value = c.chatAssistantMode === "cursor_bridge" ? "cursor_bridge" : "gemini";
      cursorBridgeWebhookInput.value = c.cursorBridgeWebhookUrl || "";
    })
    .catch(() => {});
}

function closeSiteModal() {
  siteModal.classList.add("hidden");
  siteModal.setAttribute("aria-hidden", "true");
}

async function saveSiteConfig() {
  const body = {
    siteTitle: siteTitleInput.value.trim(),
    activeProjectName: siteActiveProjectInput.value.trim(),
    n8nCommandWebhookUrl: siteWebhookInput.value.trim(),
    n8nStatusUrl: siteN8nStatusInput.value.trim(),
    cloudRunHealthUrl: siteCloudRunHealthInput.value.trim(),
    unityWorkerHealthUrl: siteUnityHealthInput.value.trim(),
    chatAssistantMode: chatAssistantModeSelect.value,
    cursorBridgeWebhookUrl: cursorBridgeWebhookInput.value.trim(),
  };
  const res = await fetch("/api/site-config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("사이트 설정 저장 실패");
  applySiteTitleFromConfig(body);
  closeSiteModal();
  await loadActiveProject();
  await refreshActiveStatusTab();
}

sendCommandBtn.onclick = () => saveCommand().catch((e) => alert(e.message));
copyCursorPromptBtn.onclick = () => copyCursorPromptToClipboard().catch((e) => alert(e.message));
stackSaveBtn.onclick = () => saveStack().catch((e) => alert(e.message));
dispatchNextBtn.onclick = () => dispatchNext().catch((e) => alert(e.message));
refreshQueueBtn.onclick = () => loadQueue().catch((e) => alert(e.message));
openSidebarBtn.onclick = () => sidebar.classList.remove("hidden");
closeSidebarBtn.onclick = () => sidebar.classList.add("hidden");
newSessionBtn.onclick = () => createNewSession().catch((e) => alert(e.message));
rulesBtn.onclick = () => openRulesModal();
rulesModalClose.onclick = () => closeRulesModal();
rulesModalBackdrop.onclick = () => closeRulesModal();
rulesSaveBtn.onclick = () => saveRules().catch((e) => alert(e.message));
siteBtn.onclick = () => openSiteModal();
siteModalClose.onclick = () => closeSiteModal();
siteModalBackdrop.onclick = () => closeSiteModal();
siteSaveBtn.onclick = () => saveSiteConfig().catch((e) => alert(e.message));
toggleStackBtn.onclick = () => stackPanel.classList.remove("hidden-stack");
closeStackBtn.onclick = () => stackPanel.classList.add("hidden-stack");

function setSidebarPanel(mode) {
  const showGuide = mode === "guide";
  sidebarSessionsWrap.classList.toggle("hidden", showGuide);
  sidebarGuideWrap.classList.toggle("hidden", !showGuide);
  sidebarTabSessions.classList.toggle("active", !showGuide);
  sidebarTabGuide.classList.toggle("active", showGuide);
  sidebarTabSessions.setAttribute("aria-selected", showGuide ? "false" : "true");
  sidebarTabGuide.setAttribute("aria-selected", showGuide ? "true" : "false");
}

sidebarTabSessions.onclick = () => setSidebarPanel("sessions");
sidebarTabGuide.onclick = () => setSidebarPanel("guide");

statusTabs.onclick = (e) => {
  const btn = e.target.closest(".status-tab");
  if (!btn) return;
  setActiveStatusTab(btn.dataset.tab);
};

(async () => {
  await apiGet("/api/site-config")
    .then((c) => applySiteTitleFromConfig(c))
    .catch(() => {});
  await loadHistory().catch(() => {});
  await loadQueue().catch(() => {});
  await loadActiveProject().catch(() => {});
  await refreshPipelineSnapshot().catch(() => {});
  setInterval(() => {
    refreshPipelineSnapshot().catch(() => {});
  }, 4000);
  setActiveStatusTab("progress");
})();
