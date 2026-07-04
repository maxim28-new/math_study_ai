const { fetchConfig, getBaseUrl, healthCheck } = require("../../utils/api.js");
const { loadSettings, saveSettings } = require("../../utils/storage.js");
const cfg = require("../../config.js");

const LEVEL_NAMES = {
  lower: "一二年级（约 6-8 岁）",
  middle: "三四年级·进阶（约 8-10 岁）",
  upper: "五年级+（约 11 岁以上）",
};

Page({
  data: {
    baseUrl: "",
    useDev: true,
    childName: "",
    topicKey: "arithmetic",
    level: "middle",
    mode: "explore",
    thinking: false,
    showReasoning: false,
    topics: [],
    levels: [],
    topicIndex: 0,
    levelIndex: 1,
    configured: false,
    model: "",
    connOk: false,
  },

  onLoad() {
    const s = loadSettings();
    this.setData({
      baseUrl: cfg.useDev ? cfg.devBaseUrl : cfg.baseUrl,
      useDev: !!cfg.useDev,
      childName: s.childName || "",
      topicKey: s.topicKey || "arithmetic",
      level: s.level || "middle",
      mode: s.mode || "explore",
      thinking: !!s.thinking,
      showReasoning: !!s.showReasoning,
    });
    this.loadRemote();
  },

  async loadRemote() {
    try {
      const config = await fetchConfig();
      const topics = config.topics || [];
      const levelKeys = Object.keys(config.levels || LEVEL_NAMES);
      const topicIndex = Math.max(0, topics.findIndex((t) => t.key === this.data.topicKey));
      const levelIndex = Math.max(0, levelKeys.indexOf(this.data.level));
      this.setData({
        topics,
        levels: levelKeys.map((k) => ({ key: k, name: LEVEL_NAMES[k] || k })),
        topicIndex,
        levelIndex,
        configured: config.configured,
        model: config.model || "",
        connOk: true,
      });
    } catch (e) {
      this.setData({ connOk: false });
    }
  },

  onBaseUrl(e) { this.setData({ baseUrl: e.detail.value.trim() }); },
  onUseDev(e) { this.setData({ useDev: !!e.detail.value }); },
  onName(e) { this.setData({ childName: e.detail.value }); },
  onThinking(e) {
    const thinking = !!e.detail.value;
    this.setData({ thinking, showReasoning: thinking ? this.data.showReasoning : false });
  },
  onShowReasoning(e) { this.setData({ showReasoning: !!e.detail.value }); },

  onTopic(e) {
    const i = parseInt(e.detail.value, 10);
    const t = this.data.topics[i];
    if (t) this.setData({ topicIndex: i, topicKey: t.key });
  },

  onLevel(e) {
    const i = parseInt(e.detail.value, 10);
    const lv = this.data.levels[i];
    if (lv) this.setData({ levelIndex: i, level: lv.key });
  },

  setMode(e) {
    this.setData({ mode: e.currentTarget.dataset.mode });
  },

  async testConn() {
    const app = getApp();
    app.globalData.baseUrl = this.data.useDev ? cfg.devBaseUrl : this.data.baseUrl;
    if (!this.data.useDev) cfg.baseUrl = this.data.baseUrl;
    cfg.useDev = this.data.useDev;
    wx.showLoading({ title: "测试中" });
    try {
      await healthCheck();
      wx.hideLoading();
      wx.showToast({ title: "连接成功" });
      this.loadRemote();
    } catch (e) {
      wx.hideLoading();
      wx.showModal({ title: "连接失败", content: String(e.message || e), showCancel: false });
    }
  },

  save() {
    const app = getApp();
    if (this.data.useDev) {
      cfg.useDev = true;
      app.globalData.baseUrl = cfg.devBaseUrl;
    } else {
      cfg.useDev = false;
      cfg.baseUrl = this.data.baseUrl.replace(/\/$/, "");
      app.globalData.baseUrl = cfg.baseUrl;
    }
    saveSettings({
      childName: this.data.childName,
      topicKey: this.data.topicKey,
      level: this.data.level,
      mode: this.data.mode,
      thinking: this.data.thinking,
      showReasoning: this.data.showReasoning,
      _updated: true,
    });
    wx.showToast({ title: "已保存" });
    setTimeout(() => wx.navigateBack(), 500);
  },
});
