App({
  globalData: {
    baseUrl: "",
    config: null,
  },
  onLaunch() {
    const cfg = require("./config.js");
    this.globalData.baseUrl = cfg.useDev ? cfg.devBaseUrl : cfg.baseUrl;
  },
});
