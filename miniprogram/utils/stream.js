const { getBaseUrl } = require("./api.js");

function decodeChunk(data) {
  if (typeof data === "string") return data;
  try {
    return new TextDecoder("utf-8").decode(new Uint8Array(data));
  } catch (e) {
    let s = "";
    const u8 = new Uint8Array(data);
    for (let i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]);
    return decodeURIComponent(escape(s));
  }
}

function parseSseBlock(block, handlers) {
  const line = block.trim();
  if (!line.startsWith("data:")) return;
  let payload;
  try {
    payload = JSON.parse(line.slice(5).trim());
  } catch (e) {
    return;
  }
  if (payload.delta && handlers.onDelta) handlers.onDelta(payload.delta);
  if (payload.reasoning_delta && handlers.onReasoning) handlers.onReasoning(payload.reasoning_delta);
  if (payload.transcript && handlers.onTranscript) handlers.onTranscript(payload.transcript);
  if (payload.error && handlers.onError) handlers.onError(payload.error);
  if (payload.done && handlers.onDone) handlers.onDone();
}

/**
 * 流式 POST /api/chat（enableChunked）
 * @returns {Promise<{abort: Function}>}
 */
function streamChat(body, handlers) {
  return new Promise((resolve, reject) => {
    let buf = "";
    let finished = false;

    const task = wx.request({
      url: getBaseUrl() + "/api/chat",
      method: "POST",
      enableChunked: true,
      responseType: "text",
      header: { "Content-Type": "application/json" },
      data: body,
      success: () => {
        if (buf.trim()) parseSseBlock(buf, handlers);
        if (!finished) {
          finished = true;
          if (handlers.onDone) handlers.onDone();
        }
      },
      fail: (err) => {
        if (!finished) reject(err);
      },
    });

    if (task && task.onChunkReceived) {
      task.onChunkReceived((res) => {
        buf += decodeChunk(res.data);
        const parts = buf.split("\n\n");
        buf = parts.pop();
        parts.forEach((p) => parseSseBlock(p, handlers));
      });
    } else {
      // 基础库过旧时降级：非流式整包返回（需后端支持；此处提示升级）
      reject(new Error("当前微信版本不支持流式响应，请升级微信或使用较新基础库"));
    }

    resolve({
      abort: () => {
        if (task && task.abort) task.abort();
      },
    });
  });
}

module.exports = { streamChat };
