const { fetchConfig } = require("../../utils/api.js");
const { streamChat } = require("../../utils/stream.js");
const { parseContent } = require("../../utils/markdown.js");
const { loadSession, saveSession, loadSettings } = require("../../utils/storage.js");

const LEVEL_NAMES = { lower: "一二年级", middle: "三四年级·进阶", upper: "五年级+" };

Page({
  data: {
    config: null,
    configured: false,
    messages: [],
    display: [],
    mode: "explore",
    topicKey: "arithmetic",
    level: "middle",
    childName: "",
    thinking: false,
    showReasoning: false,
    streaming: false,
    input: "",
    pendingImage: "",
    scrollTo: "",
    quickActions: [],
    topicName: "",
    showBanner: false,
  },

  onLoad() {
    const settings = loadSettings();
    const session = loadSession();
    const settingBool = (key, fallback) => (
      typeof settings[key] === "boolean" ? settings[key] : fallback
    );
    this.setData({
      mode: settings.mode || session?.mode || "explore",
      topicKey: settings.topicKey || session?.topicKey || "arithmetic",
      level: settings.level || session?.level || "middle",
      childName: settings.childName || session?.childName || "",
      thinking: settingBool("thinking", !!session?.thinking),
      showReasoning: settingBool("showReasoning", !!session?.showReasoning),
      messages: session?.messages || [],
    });
    this.refreshDisplay();
    this.bootstrap();
  },

  onShow() {
    const settings = loadSettings();
    if (settings._updated) {
      this.setData({
        mode: settings.mode || this.data.mode,
        topicKey: settings.topicKey || this.data.topicKey,
        level: settings.level || this.data.level,
        childName: settings.childName || "",
        thinking: !!settings.thinking,
        showReasoning: !!settings.showReasoning,
      });
      delete settings._updated;
    }
  },

  async bootstrap() {
    try {
      const config = await fetchConfig();
      const topic = (config.topics || []).find((t) => t.key === this.data.topicKey) || config.topics[0];
      this.setData({
        config,
        configured: config.configured,
        quickActions: config.quick_actions || [],
        topicName: topic ? topic.name : "",
        showBanner: !config.configured,
      });
      if (!this.data.messages.length) this.showWelcome();
      else this.refreshDisplay();
    } catch (e) {
      wx.showToast({ title: "连接服务器失败", icon: "none" });
      this.setData({ showBanner: true });
    }
  },

  showWelcome() {
    const { mode, childName, topicName } = this.data;
    const nm = childName ? `${childName}，` : "";
    let text;
    if (mode === "explore") {
      text = `${nm}你好呀，我是小欧。\n\n现在是「一起探索」模式（**${topicName}**）。点 **✨ 出个新题** 开始。`;
    } else {
      text = `${nm}你好呀，我是小欧。\n\n现在是「带题来问」模式。把题目拍照或打出来吧。`;
    }
    this.setData({
      display: [{ role: "tutor", segments: parseContent(text), reasoning: "" }],
    });
  },

  msgToDisplay(msg) {
    if (typeof msg.content === "string") {
      return { role: msg.role === "user" ? "child" : "tutor", segments: parseContent(msg.content), reasoning: "" };
    }
    const textPart = msg.content.find((p) => p.type === "text");
    const hasImg = msg.content.some((p) => p.type === "image_url");
    let text = textPart ? textPart.text : "";
    if (hasImg) text = (text ? text + "\n" : "") + "[题目照片]";
    return { role: "child", segments: parseContent(text), image: hasImg ? "photo" : "" };
  },

  refreshDisplay() {
    const display = this.data.messages.map((m) => this.msgToDisplay(m));
    this.setData({ display, scrollTo: "bottom" });
  },

  persist() {
    saveSession({
      mode: this.data.mode,
      topicKey: this.data.topicKey,
      level: this.data.level,
      childName: this.data.childName,
      thinking: this.data.thinking,
      showReasoning: this.data.showReasoning,
      messages: this.data.messages,
    });
  },

  onInput(e) {
    this.setData({ input: e.detail.value });
  },

  switchMode(e) {
    const mode = e.currentTarget.dataset.mode;
    if (mode === this.data.mode || this.data.streaming) return;
    wx.showModal({
      title: "切换模式",
      content: "切换模式会清空当前对话，确定吗？",
      success: (res) => {
        if (!res.confirm) return;
        this.setData({ mode, messages: [], pendingImage: "", input: "" });
        this.persist();
        this.showWelcome();
      },
    });
  },

  openSettings() {
    wx.navigateTo({ url: "/pages/settings/settings" });
  },

  choosePhoto() {
    if (this.data.mode === "explore") return;
    wx.chooseMedia({
      count: 1,
      mediaType: ["image"],
      sourceType: ["album", "camera"],
      success: (res) => {
        const path = res.tempFiles[0].tempFilePath;
        wx.getFileSystemManager().readFile({
          filePath: path,
          encoding: "base64",
          success: (r) => {
            const mime = path.toLowerCase().endsWith(".png") ? "image/png" : "image/jpeg";
            this.setData({ pendingImage: `data:${mime};base64,${r.data}` });
          },
        });
      },
    });
  },

  clearPhoto() {
    this.setData({ pendingImage: "" });
  },

  onQuick(e) {
    this.sendMessage(e.currentTarget.dataset.msg);
  },

  startExplore() {
    if (this.data.streaming || !this.data.configured) return;
    this.runStream(true);
  },

  onSend() {
    this.sendMessage(this.data.input);
  },

  sendMessage(text) {
    if (this.data.streaming) return;
    const typed = (text || this.data.input || "").trim();
    const image = this.data.pendingImage;
    if (!typed && !image) return;

    let content;
    if (image) {
      content = [
        { type: "text", text: typed || "这是我作业本上的题目，你先帮我看看。" },
        { type: "image_url", image_url: { url: image } },
      ];
    } else {
      content = typed;
    }

    const messages = this.data.messages.concat([{ role: "user", content }]);
    this.setData({ messages, input: "", pendingImage: "" });
    this.refreshDisplay();
    this.persist();
    this.runStream(false);
  },

  async runStream(kickoff) {
    this.setData({ streaming: true });
    const display = this.data.display.concat([{
      role: "tutor",
      segments: [{ type: "rich", html: "<p>…</p>" }],
      reasoning: "",
      streaming: true,
    }]);
    const tutorIdx = display.length - 1;
    this.setData({ display, scrollTo: "bottom" });

    let acc = "";
    let reasoningAcc = "";

    try {
      await streamChat(
        {
          messages: this.data.messages,
          topic: this.data.topicKey,
          level: this.data.level,
          child_name: this.data.childName,
          mode: this.data.mode,
          kickoff: !!kickoff,
          thinking: this.data.thinking,
          show_reasoning: this.data.showReasoning,
        },
        {
          onDelta: (d) => {
            acc += d;
            display[tutorIdx].segments = parseContent(acc);
            display[tutorIdx].streaming = true;
            this.setData({ display: [...display], scrollTo: "bottom" });
          },
          onReasoning: (d) => {
            if (!this.data.showReasoning) return;
            reasoningAcc += d;
            display[tutorIdx].reasoning = reasoningAcc;
            this.setData({ display: [...display], scrollTo: "bottom" });
          },
          onTranscript: (t) => {
            const msgs = this.data.messages.slice();
            const last = msgs[msgs.length - 1];
            if (last && Array.isArray(last.content)) {
              last.content = "（从照片读出的题目）\n" + t;
              this.setData({ messages: msgs });
              this.persist();
            }
            acc = `📷 读到的题目：\n${t}\n\n` + acc;
            display[tutorIdx].segments = parseContent(acc);
            this.setData({ display: [...display] });
          },
          onError: (err) => {
            acc += (acc ? "\n\n" : "") + err;
            display[tutorIdx].segments = parseContent(acc);
            this.setData({ display: [...display] });
          },
        }
      );
    } catch (e) {
      acc += (acc ? "\n\n" : "") + "连接失败，请检查服务器地址和网络。";
      display[tutorIdx].segments = parseContent(acc);
      this.setData({ display: [...display] });
    }

    display[tutorIdx].streaming = false;
    if (acc.trim()) {
      const messages = this.data.messages.concat([{ role: "assistant", content: acc }]);
      this.setData({ messages, display: [...display], streaming: false });
      this.persist();
    } else {
      display.pop();
      this.setData({ display, streaming: false });
    }
  },

  clearChat() {
    wx.showModal({
      title: "清空对话",
      content: "确定清空当前对话吗？",
      success: (res) => {
        if (!res.confirm) return;
        this.setData({ messages: [], pendingImage: "" });
        this.persist();
        this.showWelcome();
      },
    });
  },
});
