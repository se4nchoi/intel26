/**
 * app.js — Classroom Chat 클라이언트
 * 사이드바 + 대화탭 구조
 */
'use strict';

// ────────────────────────────────────────
//  상수
// ────────────────────────────────────────
const STORAGE_KEY     = 'classroom_chat_nickname';
const MAX_NICK_LEN    = 30;
const MAX_MSG_LEN     = 500;
const RECONNECT_DELAY = 3000;
const GLOBAL_ID       = 'global';

// ────────────────────────────────────────
//  DOM
// ────────────────────────────────────────
const nicknameModal   = document.getElementById('nickname-modal');
const nicknameInput   = document.getElementById('nickname-input');
const nicknameSubmit  = document.getElementById('nickname-submit');
const nicknameError   = document.getElementById('nickname-error');

const chatApp         = document.getElementById('chat-app');
const sidebarToggle   = document.getElementById('sidebar-toggle');
const sidebar         = document.getElementById('sidebar');
const sidebarBackdrop = document.getElementById('sidebar-backdrop');
const convListEl      = document.getElementById('conv-list');
const onlineListEl    = document.getElementById('online-list');
const onlineCountEl   = document.getElementById('online-count');
const messageListEl   = document.getElementById('message-list');
const msgInput        = document.getElementById('msg-input');
const sendBtn         = document.getElementById('send-btn');
const chatAreaTitle   = document.getElementById('chat-area-title');
const connStatus      = document.getElementById('conn-status');
const myNickBadge     = document.getElementById('my-nick-badge');

// ────────────────────────────────────────
//  대화 상태 관리
//  conversations: Map<id, { id, name, type, messages[], unread }>
//  type: 'global' | 'dm'
// ────────────────────────────────────────
const conversations = new Map();
let activeConvId    = GLOBAL_ID;
let myNickname      = '';
let ws              = null;
let reconnectTimer  = null;
let nicknameRejected = false;
let _lastNickErr    = '';

/** 전체 채팅방은 항상 존재 */
function initConversations() {
  conversations.clear();
  conversations.set(GLOBAL_ID, {
    id:       GLOBAL_ID,
    name:     '전체 채팅',
    type:     'global',
    messages: [],
    unread:   0,
  });
}

function displayNickname(nick, ipSuffix = '') {
  return ipSuffix ? `${nick} (${ipSuffix})` : nick;
}

/** DM 대화를 가져오거나 새로 생성 */
function getOrCreateDm(nick, ipSuffix = '') {
  if (!conversations.has(nick)) {
    conversations.set(nick, {
      id:       nick,
      name:     nick,
      ipSuffix,
      type:     'dm',
      messages: [],
      unread:   0,
    });
  } else if (ipSuffix) {
    conversations.get(nick).ipSuffix = ipSuffix;
  }
  return conversations.get(nick);
}

// ────────────────────────────────────────
//  닉네임 처리
// ────────────────────────────────────────
async function fetchSuggested() {
  try {
    const r = await fetch('/api/client-info');
    return (await r.json()).suggested_nickname || '';
  } catch { return ''; }
}

async function showNicknameModal(errMsg = '') {
  const stored    = (localStorage.getItem(STORAGE_KEY) || '').trim();
  const suggested = stored || await fetchSuggested();
  nicknameInput.value = suggested;
  nicknameError.textContent = errMsg;
  nicknameModal.classList.remove('hidden');
  setTimeout(() => nicknameInput.focus(), 50);
}

function hideNicknameModal() {
  nicknameModal.classList.add('hidden');
}

function enterChat(nick) {
  myNickname = nick;
  localStorage.setItem(STORAGE_KEY, nick);
  myNickBadge.textContent = nick;
  hideNicknameModal();
  initConversations();
  chatApp.classList.remove('hidden');
  switchConv(GLOBAL_ID);
  initWebSocket();
}

nicknameSubmit.addEventListener('click', submitNickname);
nicknameInput.addEventListener('keydown', e => { if (e.key === 'Enter') submitNickname(); });

function submitNickname() {
  const nick = nicknameInput.value.trim();
  if (!nick) { nicknameError.textContent = '닉네임을 입력해 주세요.'; return; }
  if (nick.length > MAX_NICK_LEN) { nicknameError.textContent = `닉네임은 ${MAX_NICK_LEN}자 이하여야 합니다.`; return; }
  nicknameError.textContent = '';
  enterChat(nick);
}

// ────────────────────────────────────────
//  사이드바 토글 (모바일)
// ────────────────────────────────────────
sidebarToggle.addEventListener('click', () => {
  sidebar.classList.toggle('open');
  sidebarBackdrop.classList.toggle('hidden', !sidebar.classList.contains('open'));
});

sidebarBackdrop.addEventListener('click', closeSidebar);

function closeSidebar() {
  sidebar.classList.remove('open');
  sidebarBackdrop.classList.add('hidden');
}

// ────────────────────────────────────────
//  대화 전환
// ────────────────────────────────────────
function switchConv(id) {
  if (!conversations.has(id)) return;
  activeConvId = id;
  const conv = conversations.get(id);
  conv.unread = 0;

  // 타이틀 업데이트
  const convDisplayName = displayNickname(conv.name, conv.ipSuffix);
  chatAreaTitle.textContent = conv.type === 'global' ? '🌐 전체 채팅' : `💬 ${convDisplayName}`;

  // 입력 placeholder 변경
  msgInput.placeholder = conv.type === 'global'
    ? '메시지를 입력하세요 (Enter로 전송)'
    : `${convDisplayName}에게 DM... (Enter로 전송)`;

  // 메시지 렌더링
  renderMessages();
  renderConvList();
  closeSidebar();
}

// ────────────────────────────────────────
//  사이드바 렌더링
// ────────────────────────────────────────
function renderConvList() {
  convListEl.innerHTML = '';
  for (const conv of conversations.values()) {
    const li = document.createElement('li');
    li.className = 'conv-item' + (conv.id === activeConvId ? ' active' : '');
    li.dataset.id = conv.id;

    const icon = document.createElement('span');
    icon.className = 'conv-icon';
    icon.textContent = conv.type === 'global' ? '🌐' : '👤';

    const name = document.createElement('span');
    name.className = 'conv-name';
    name.textContent = conv.name;

    li.appendChild(icon);
    li.appendChild(name);

    if (conv.unread > 0) {
      const badge = document.createElement('span');
      badge.className = 'conv-unread' + (conv.type === 'dm' ? ' dm-unread' : '');
      badge.textContent = conv.unread > 99 ? '99+' : conv.unread;
      li.appendChild(badge);
    }

    li.addEventListener('click', () => switchConv(conv.id));
    convListEl.appendChild(li);
  }
}

function renderOnlineList(users) {
  onlineCountEl.textContent = users.length;
  onlineListEl.innerHTML = '';

  users.forEach(user => {
    const nick = user.nickname;
    const ipSuffix = user.ip_suffix || '';
    const li = document.createElement('li');
    li.className = 'online-item';

    const dot = document.createElement('span');
    dot.className = 'online-dot';

    const nickEl = document.createElement('span');
    nickEl.className = 'online-nick' + (nick === myNickname ? ' is-me' : '');
    nickEl.textContent = displayNickname(nick, ipSuffix) + (nick === myNickname ? ' (나)' : '');

    li.appendChild(dot);
    li.appendChild(nickEl);

    if (nick !== myNickname) {
      const dmBtn = document.createElement('button');
      dmBtn.className = 'online-dm-btn';
      dmBtn.textContent = 'DM';
      dmBtn.addEventListener('click', e => {
        e.stopPropagation();
        getOrCreateDm(nick, ipSuffix);
        renderConvList();
        switchConv(nick);
      });
      li.appendChild(dmBtn);

      li.addEventListener('click', () => {
        getOrCreateDm(nick, ipSuffix);
        renderConvList();
        switchConv(nick);
      });
    }

    onlineListEl.appendChild(li);
  });
}

// ────────────────────────────────────────
//  메시지 렌더링
// ────────────────────────────────────────
function formatTime(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return isToday ? `${hh}:${mm}` : `${d.getMonth()+1}/${d.getDate()} ${hh}:${mm}`;
  } catch { return ''; }
}

function renderMessages() {
  messageListEl.innerHTML = '';
  const conv = conversations.get(activeConvId);
  if (!conv) return;

  conv.messages.forEach(msg => {
    appendMsgNode(msg);
  });
  scrollBottom();
}

/** 메시지 저장 + 표시 (활성 대화일 때만 DOM 추가) */
function addMessage(convId, msg) {
  const conv = conversations.get(convId);
  if (!conv) return;
  conv.messages.push(msg);

  if (convId === activeConvId) {
    appendMsgNode(msg);
    scrollBottom();
  } else {
    conv.unread++;
    renderConvList();
  }
}

function appendMsgNode(msg) {
  if (msg.msgType === 'system') {
    const row = document.createElement('div');
    row.className = 'msg-row system';
    const b = document.createElement('div');
    b.className = 'msg-bubble';
    b.textContent = msg.content;
    row.appendChild(b);
    messageListEl.appendChild(row);
    return;
  }

  if (msg.msgType === 'chat') {
    const isOwn = msg.nickname === myNickname;
    const row = document.createElement('div');
    row.className = `msg-row ${isOwn ? 'own' : 'other'}`;

    const meta = document.createElement('div');
    meta.className = 'msg-meta';
    const nickEl = document.createElement('span');
    nickEl.className = 'nick';
    nickEl.textContent = displayNickname(msg.nickname, msg.ip_suffix);
    const timeEl = document.createElement('span');
    timeEl.textContent = formatTime(msg.created_at);
    meta.appendChild(nickEl);
    meta.appendChild(timeEl);

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.textContent = msg.content;

    row.appendChild(meta);
    row.appendChild(bubble);
    messageListEl.appendChild(row);
    return;
  }

  if (msg.msgType === 'dm') {
    const isSent = msg.from_nick === myNickname;
    const row = document.createElement('div');
    row.className = `msg-row ${isSent ? 'dm-own' : 'dm-recv'}`;

    const label = document.createElement('div');
    label.className = 'dm-label';
    label.textContent = isSent
      ? `→ ${displayNickname(msg.to_nick, msg.to_ip_suffix)}`
      : `← ${displayNickname(msg.from_nick, msg.from_ip_suffix)}`;

    const meta = document.createElement('div');
    meta.className = 'msg-meta';
    const timeEl = document.createElement('span');
    timeEl.textContent = formatTime(msg.created_at);
    meta.appendChild(timeEl);

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.textContent = msg.content;

    row.appendChild(label);
    row.appendChild(meta);
    row.appendChild(bubble);
    messageListEl.appendChild(row);
  }
}

function addSystemMsg(convId, text) {
  addMessage(convId, { msgType: 'system', content: text });
}

function scrollBottom() {
  messageListEl.scrollTop = messageListEl.scrollHeight;
}

// ────────────────────────────────────────
//  전송
// ────────────────────────────────────────
function sendMessage() {
  const content = msgInput.value.trim();
  if (!content) return;
  if (content.length > MAX_MSG_LEN) {
    addSystemMsg(activeConvId, `⚠️ 메시지는 ${MAX_MSG_LEN}자 이하여야 합니다.`);
    return;
  }
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    addSystemMsg(activeConvId, '⚠️ 서버에 연결되지 않았습니다.');
    return;
  }

  if (activeConvId === GLOBAL_ID) {
    ws.send(JSON.stringify({ type: 'chat', content }));
  } else {
    ws.send(JSON.stringify({ type: 'dm', to: activeConvId, content }));
  }

  msgInput.value = '';
  msgInput.focus();
}

sendBtn.addEventListener('click', sendMessage);
msgInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

// ────────────────────────────────────────
//  연결 상태
// ────────────────────────────────────────
function setConnected(flag) {
  if (flag) {
    connStatus.textContent = '연결됨';
    connStatus.className   = 'conn-status connected';
    msgInput.disabled      = false;
    sendBtn.disabled       = false;
  } else {
    connStatus.textContent = '연결 끊김';
    connStatus.className   = 'conn-status disconnected';
    msgInput.disabled      = true;
    sendBtn.disabled       = true;
  }
}

// ────────────────────────────────────────
//  WebSocket
// ────────────────────────────────────────
function getWsUrl() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${location.host}/ws?nickname=${encodeURIComponent(myNickname)}`;
}

function initWebSocket() {
  if (ws) { ws.onclose = null; ws.onerror = null; ws.close(); }
  nicknameRejected = false;
  _lastNickErr     = '';

  ws = new WebSocket(getWsUrl());

  ws.onopen = () => {
    setConnected(true);
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
  };

  ws.onmessage = (e) => {
    let data;
    try { data = JSON.parse(e.data); } catch { return; }

    switch (data.type) {

      case 'chat':
        addMessage(GLOBAL_ID, {
          msgType:    'chat',
          nickname:   data.nickname,
          ip_suffix:  data.ip_suffix || '',
          content:    data.content,
          created_at: data.created_at,
        });
        break;

      case 'dm': {
        // 어느 대화에 넣을지 결정 (나 기준: 상대방 닉네임이 convId)
        const partner = data.from_nick === myNickname ? data.to_nick : data.from_nick;
        const partnerIpSuffix = data.from_nick === myNickname
          ? (data.to_ip_suffix || '')
          : (data.from_ip_suffix || '');
        getOrCreateDm(partner, partnerIpSuffix);
        renderConvList();
        addMessage(partner, {
          msgType:    'dm',
          from_nick:       data.from_nick,
          to_nick:         data.to_nick,
          from_ip_suffix: data.from_ip_suffix || '',
          to_ip_suffix:   data.to_ip_suffix || '',
          content:         data.content,
          created_at: data.created_at,
        });
        // 자동으로 해당 DM 탭으로 전환 (수신 시 + 해당 탭이 비활성일 때)
        if (data.from_nick !== myNickname && activeConvId !== partner) {
          // 탭 전환 대신 unread만 표시 (강제 전환 시 UX 방해)
          // 원하면 주석 해제: switchConv(partner);
        }
        break;
      }

      case 'presence':
        // 접속자 수는 온라인 목록으로 표시하므로 생략 가능
        break;

      case 'users':
        renderOnlineList(data.list);
        break;

      case 'error_nickname':
        nicknameRejected = true;
        _lastNickErr     = data.message || '닉네임이 이미 사용 중입니다.';
        break;

      case 'error':
        addSystemMsg(activeConvId, `⚠️ ${data.message}`);
        break;
    }
  };

  ws.onclose = () => {
    setConnected(false);
    renderOnlineList([]);
    if (nicknameRejected) {
      chatApp.classList.add('hidden');
      myNickname = '';
      localStorage.removeItem(STORAGE_KEY);
      showNicknameModal(_lastNickErr);
      nicknameRejected = false;
    } else {
      scheduleReconnect();
    }
  };

  ws.onerror = () => setConnected(false);
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  addSystemMsg(activeConvId, '연결이 끊어졌습니다. 재연결을 시도합니다...');
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    if (myNickname) initWebSocket();
  }, RECONNECT_DELAY);
}

// ────────────────────────────────────────
//  초기화
// ────────────────────────────────────────
setConnected(false);
showNicknameModal();
