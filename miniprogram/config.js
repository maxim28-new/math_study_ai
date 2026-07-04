/** 后端 API 地址。部署后改成你的 HTTPS 域名，并在微信小程序后台配置 request 合法域名。 */
module.exports = {
  // 生产环境：你的公网 HTTPS 地址（不要末尾斜杠）
  baseUrl: "https://your-domain.com",
  // 开发者工具本地调试：勾选「不校验合法域名」后可用
  devBaseUrl: "http://127.0.0.1:8000",
  // true = 使用 devBaseUrl（仅开发）
  useDev: true,
};
