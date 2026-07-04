const SESSION_KEY = "xiaoou.session.v1";
const SETTINGS_KEY = "xiaoou.settings.v1";

function sanitizeMessages(messages) {
  return (messages || []).map((m) => {
    if (!Array.isArray(m.content)) return m;
    const textPart = m.content.find((p) => p.type === "text");
    const text = textPart ? textPart.text : "";
    return { role: m.role, content: (text ? text + "\n" : "") + "[一张题目照片]" };
  });
}

function loadSession() {
  try {
    return wx.getStorageSync(SESSION_KEY) || null;
  } catch (e) {
    return null;
  }
}

function saveSession(data) {
  try {
    wx.setStorageSync(SESSION_KEY, {
      ...data,
      messages: sanitizeMessages(data.messages),
    });
  } catch (e) {}
}

function loadSettings() {
  try {
    return wx.getStorageSync(SETTINGS_KEY) || {};
  } catch (e) {
    return {};
  }
}

function saveSettings(settings) {
  try {
    wx.setStorageSync(SETTINGS_KEY, settings);
  } catch (e) {}
}

module.exports = { loadSession, saveSession, loadSettings, saveSettings };
