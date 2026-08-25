# 小欧数学世界 V2

独立于 V1 的体素数学箱庭。默认入口仍是 `/`；这里只服务 `/v2/`。

当前切片是 **Slice 0 交互探针**：固定斜俯视、三堆材料、整组拖拽、拆分把手、桥槽吸附。还没有正式领域 schema、小欧或 AI。

```bash
cd v2
npm install
npm test
npm run dev    # http://127.0.0.1:5173/v2/
npm run build  # 产物供 FastAPI 挂到 /v2/
```

`domain` 包尚未开始。探针状态在 `apps/web/src/prototype/`，不得被后续正式规则引擎直接沿用。
