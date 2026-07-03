const cfg = require("../config.js");

function getBaseUrl() {
  const app = getApp();
  if (app && app.globalData.baseUrl) return app.globalData.baseUrl;
  return cfg.useDev ? cfg.devBaseUrl : cfg.baseUrl;
}

function request(options) {
  return new Promise((resolve, reject) => {
    wx.request({
      ...options,
      url: getBaseUrl() + options.path,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data);
        else reject(new Error((res.data && res.data.detail) || `HTTP ${res.statusCode}`));
      },
      fail: reject,
    });
  });
}

function fetchConfig() {
  return request({ path: "/api/config", method: "GET" });
}

function healthCheck() {
  return request({ path: "/api/health", method: "GET" });
}

module.exports = { getBaseUrl, fetchConfig, healthCheck };
