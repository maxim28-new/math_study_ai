# 小欧 · 启发式数学老师 🧭

一个陪孩子**学会思考**的 AI 数学老师，而不是帮孩子对答案的机器。

它的理念只有一句话：**像欧几里得那样，只承认几条最朴素的"公理"，其余一切都靠自己推导；像苏格拉底那样，用提问代替灌输。**

小欧**永远不会直接给答案**。它会：

- 一次只问一个引导性的小问题，陪孩子一步步往前走；
- 孩子卡住时，只给"最小的一级台阶"，而不是替他爬上去；
- 孩子答错时，不说"错了"，而是用一个具体例子让他自己发现矛盾；
- 每遇到一个公式，都反问"它为什么成立？我们能不能自己推出来？"；
- 一道题做出来后，追问"还有没有别的方法？""你是怎么想到的？"；
- 把一切追溯回屏幕左侧那几条**公理**。

> 目标不是记住某道题的解法，而是养成一生受用的思考方式。

---

## 两种探究模式

小欧有两种可切换的模式（界面左上角/顶部切换）：

### 🧭 一起探索（小欧出题）
选一个**主题**，小欧就从这个主题的几条**公理**出发，给孩子出一道值得琢磨的探索题，陪他一步步**自己发现**一个规律或道理。点「✨ 出个新题」开始，一个探索告一段落还能「再来一题」层层递进。

这一模式下，**主题和公理是主角**——它们决定了小欧出什么题。出题会汲取经典数学著作的**精神**（不掉书袋，翻译成孩子能玩的具体探索）：

| 主题 | 灵感来源 | 可被孩子重新发现的"宝石" |
| --- | --- | --- |
| 算术与数 | 高斯少年巧算、欧几里得《几何原本》卷七 | 1+2+…+100 首尾配对；辗转相除求最大公因数；奇数累加得平方数 |
| 几何与图形 | 欧几里得《几何原本》 | 尺规作等边三角形、平分角；拼出三角形内角和 |
| 代数与等式 | 花拉子米《代数学》(al-Jabr) | 天平"还原与对消"，代数的字面起源 |
| 分数与比例 | 古埃及莱因德纸草书、欧几里得卷五 | 单位分数拼数游戏；"分饼"比例 |
| 逻辑·找规律·奥数 | 波利亚《怎样解题》、斐波那契《计算之书》、欧几里得反证法 | 兔子数列找规律；用小例子体会"反证" |
| 应用题与画图 | 《九章算术》 | 生活情境 + 线段图 |

### 📷 带题来问（孩子出题）
孩子把作业本或书上的题**拍照或打字**发来，小欧陪他一起想（依然不直接给答案）。适合搞定当天的作业和不会的题。

> 两种模式互不干扰，随时切换（切换会清空当前对话，因为教学设定不同）。

> **每次出的题是写死的吗？** 不是。各主题只提供几条"出题灵感"作为**种子**，具体题目的场景、数字、顺序都是模型**每次现场生成**的（并已指示它刻意变换花样），所以同一主题反复点「出个新题」会得到不同的题。想更换风格，改 `server/tutor.py` 里各主题的 `inspirations` 即可。

---

## 多种输入 / 输出方式

- **图形输出（数形结合）**：小欧在聊点阵、积木、平方数等题目时，**每一轮回复都会画图**——不只是出题第一句，答对反馈、追问「再加几块」、总结规律时都会换一张对应当前步骤的 SVG 图（含两个正方形对比 `square_compare` 等新类型）。孩子看不到底层 JSON。
- **LaTeX 公式**：正文里的 `$1 \times 1$`、`$\frac{1}{2}$` 等会用 [KaTeX](https://katex.org/) 渲染成标准数学公式（本地网页和手机体验页均支持）。
- **语音输入**：点麦克风按钮说话，自动转成文字（用浏览器自带的语音识别，Chrome/Edge/Safari 支持；不支持时按钮会置灰）。
- **画板输入**：点画板按钮，手写或画个图，"发送给小欧"——它会作为一张图走拍照读题的同一条通道。
- **拍照输入**：带题模式下拍作业本上的题。

## 思考模式（更快 or 更深）

左侧（或手机版设置里）可切换**思考模式**：
- **关闭**（默认）：回答更快，适合日常陪练。
- **开启**：模型先深度推理再回答，并**灰色展示思考过程**；适合难题/奥数。

自动适配不同服务商：DeepSeek 用 `thinking` 参数、通义千问/Qwen 用 `enable_thinking` 参数（程序自动选对）。

> ⚠️ 通义 `qwen-plus` 等 Qwen3 模型默认可能开着思考、响应很慢——把思考模式设为**关闭**即可明显变快。

---

## 手机上最快体验（无需搭服务器）

`docs/index.html` 是一个**单文件网页版**，整页都在你手机浏览器里运行，密钥由你自己填、只存在你手机本地、不经过任何中间服务器。

体验步骤：

1. 把本仓库的这个改动合并到 `main` 后，在 GitHub 仓库页打开 **Settings → Pages**，Source 选择 **Deploy from a branch**，分支选 `main`、目录选 **`/docs`**，保存。
2. 稍等一两分钟，GitHub 会给出一个网址（形如 `https://<你的用户名>.github.io/math_study_ai/`）。用**手机浏览器**打开它。
3. 点右上角**齿轮**填入密钥：
   - **文字模型（必填，负责教学）**：推荐 **DeepSeek**（中文好、便宜、允许手机网页直连）。接口 `https://api.deepseek.com/v1`，模型 `deepseek-v4-flash`（或 `deepseek-v4-pro`），密钥去 [platform.deepseek.com](https://platform.deepseek.com) 申请。
   - **视觉模型（选填，拍照读题用）**：推荐 **魔搭 ModelScope** 的 Qwen-VL（同样允许手机网页直连）。接口 `https://api-inference.modelscope.cn/v1`，模型 `Qwen/Qwen2.5-VL-7B-Instruct`，Token 去 [modelscope.cn](https://modelscope.cn) 注册后在"访问令牌"里拿。不填就先用文字功能。
4. 保存，就能在手机上和小欧对话、拍作业本了。

> **为什么挑这两家？** 浏览器有跨域（CORS）限制，不是每家模型都允许网页直接连。实测 **DeepSeek** 和 **魔搭 ModelScope** 允许网页直连；而通义百炼、Kimi、智谱**默认不允许**网页直连（它们只能用下面的"本地服务器版"）。

---

## 它长什么样

- 左边：**模式切换**（一起探索 / 带题来问）、孩子的名字、**主题**、**难度档位**、**思考模式**开关，以及本主题的几条**公理板**；探索模式下有「✨ 出个新题」按钮。
- 中间：和小欧的对话，逐字流式显示；小欧在需要时会插入**简单的图**（点阵 / 数轴 / 线段图）帮孩子看清楚。
- 输入方式：打字、**语音**（麦克风按钮）、**画板**（手写/画图）、以及带题模式下的**拍照**。
- 下面：几个快捷按钮——「我卡住了」「换种方法」「为什么是这样」「回顾思路」「先做简单版」——点一下就能把最能促进思考的问题发给小欧。
- 输入框左边有个**相机按钮**：可以直接**拍下作业本上的题目**（手机会调用摄像头）或从相册上传。小欧看到照片后**不会直接开始解题**，而是先陪孩子把题目读一遍、再从"这道题在问什么""可以先从哪里下手"这些问题反问回去。

内置五大主题，每个主题都配了一套"少数几条公理"：

| 主题 | 出发点（公理示例） |
| --- | --- |
| 算术与数 | 数是用来数东西的；合起来数就是加法…… |
| 几何与图形 | 两点之间能连一条线段；所有直角一样大…… |
| 代数与等式 | 等式是一架平衡的天平，两边同做一件事仍平衡…… |
| 分数与比例 | 分数就是把整体平均分再取几份…… |
| 逻辑与找规律 | 一件事非真即假；一个反例就能推翻"所有……" |

---

## 快速开始（Mac 本地 · 用虚拟环境，不污染系统 Python）

前提：Mac 上已装 **Python 3.10+**（终端里 `python3 --version` 能看到版本号即可）。

### 1. 进入项目，创建并激活 `.venv`

```bash
cd math_study_ai
python3 -m venv .venv
source .venv/bin/activate
```

激活成功后，命令行前面会出现 `(.venv)`，之后所有 `pip` / `python` 都只在这个环境里生效。

> 以后每次新开终端要跑小欧，先 `cd` 到项目目录，再执行 `source .venv/bin/activate` 即可。  
> 用完可以 `deactivate` 退出虚拟环境。

### 2. 在虚拟环境里安装依赖

```bash
pip install -r requirements.txt
```

是的，就是这一条——但**一定要在 `.venv` 激活之后**再跑，这样包装进 `.venv` 里，不会弄乱本机全局 Python。

### 3. 填写模型密钥

```bash
cp .env.example .env
```

用任意编辑器打开 `.env`，至少填好 `LLM_API_KEY`；想用拍照 OCR 再填 `LLM_VISION_*` 三项（见下文）。

### 4. 启动

```bash
python run.py
```

浏览器打开 `http://127.0.0.1:8000`。Mac 上如果提示 `python: command not found`，把上面命令换成 `python3 run.py`（虚拟环境里一般 `python` 和 `python3` 都行）。

---

## 快速开始（不用虚拟环境 · 不推荐）

如果你明确想装到全局环境（可能和别的项目冲突），也可以：

```bash
pip install -r requirements.txt
cp .env.example .env
python3 run.py
```

---

## 填写模型密钥（`.env` 说明）

小欧兼容所有"OpenAI 格式"的大模型接口，你可以任选一家（下面几家都支持中文、注册即用）：

| 服务商 | 接口地址 `LLM_BASE_URL` | 模型名 `LLM_MODEL` |
| --- | --- | --- |
| DeepSeek（推荐，便宜） | `https://api.deepseek.com/v1` | `deepseek-v4-flash`（日常） / `deepseek-v4-pro`（更强） |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` 或 `gpt-4o` |
| 月之暗面 Kimi | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| 本地 Ollama（免费离线） | `http://localhost:11434/v1` | 如 `qwen2.5` |

`.env` 里只需要把这三项对应填好：`LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`。

> **DeepSeek 模型名更新（2026）**：官方 V4 模型为 `deepseek-v4-flash` 和 `deepseek-v4-pro`；旧名 `deepseek-chat` / `deepseek-reasoner` 将于 **2026-07-24** 退役。接口地址 `https://api.deepseek.com/v1` 不变，只改模型名即可。

**DeepSeek V4 Thinking 模式（可配置）**：

| 变量 | 值 | 说明 |
| --- | --- | --- |
| `LLM_THINKING` | `disabled`（默认） | 关闭 thinking，短问短答、快、省，适合日常陪练 |
| | `enabled` | 开启 thinking，先深度推理再回复，适合奥数/难题 |
| `LLM_REASONING_EFFORT` | `high` / `max` | thinking 开启时的推理深度（默认 `high`） |
| `LLM_SHOW_REASONING` | `false`（默认） | thinking 开启时**不展示**思考过程，界面只看到最终回复 |
| | `true` | thinking 开启时**灰色展示**思考过程（给孩子看时建议保持 false） |

```bash
# 日常陪练（默认）
LLM_THINKING=disabled

# 难题模式：开启 thinking，但不给孩子看思考过程
LLM_THINKING=enabled
LLM_REASONING_EFFORT=high
LLM_SHOW_REASONING=false

# 家长调试：开启 thinking 且灰色展示思考过程
LLM_SHOW_REASONING=true
```

## 两种处理模式（`LLM_PIPELINE`）

小欧支持两种架构，在 `.env` 里用 **`LLM_PIPELINE`** 切换：

| | `split`（默认） | `unified`（多模态一体） |
|---|---|---|
| 原理 | 视觉模型 **OCR 读题** → 文字模型 **教学** | **一个多模态模型**直接看图+对话 |
| 适合 | 文字用 DeepSeek（强推理、便宜），OCR 用通义 | 配置简单，图形题信息更完整 |
| 拍照 | 需填 `LLM_VISION_*` | 只需填 `LLM_*`，不用 `LLM_VISION_*` |
| 教学风格 | 始终由你选的文字模型负责，最稳 | 同一个模型，风格统一 |

### 模式 A：`split` — OCR + 文字（默认）

复制默认模板：

```bash
cp .env.example .env
```

**想用"拍作业本"功能？** 视觉模型只当"眼睛"（OCR），教学仍由文字模型完成。在 `.env` 里单独填 **`LLM_VISION_BASE_URL` / `LLM_VISION_API_KEY` / `LLM_VISION_MODEL`**。

> **推荐 Mac 本地组合：** 文字用 DeepSeek，OCR 用通义——两家接口、密钥完全分开填，互不影响：

```bash
# 文字教学
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=你的DeepSeek密钥
LLM_MODEL=deepseek-v4-flash

# 拍照 OCR（只读题，不解题）
LLM_VISION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_VISION_API_KEY=你的通义密钥
LLM_VISION_MODEL=qwen-vl-plus
```

本地服务器不受浏览器跨域限制，OCR 还可以换 Kimi、智谱 `glm-4v`、OpenAI `gpt-4o` 等任意支持视觉的模型：

| 服务商 | OCR 接口 `LLM_VISION_BASE_URL` | 模型 `LLM_VISION_MODEL` |
| --- | --- | --- |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-vl-plus` / `qwen-vl-max` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` / `gpt-4o-mini` |
| 月之暗面 Kimi | `https://api.moonshot.cn/v1` | `moonshot-v1-8k-vision-preview` |
| 智谱 | `https://open.bigmodel.cn/api/paas/v4` | `glm-4v` |
| 魔搭 ModelScope | `https://api-inference.modelscope.cn/v1` | `Qwen/Qwen2.5-VL-7B-Instruct` |

读到的题目会显示在对话里（"小欧读到的题目：…"），读错了直接打字纠正即可。

### 模式 B：`unified` — 一个多模态模型包办（如 qwen3.7-plus）

复制多模态模板，填一个密钥即可：

```bash
cp .env.unified.example .env
```

示例配置（通义千问 **qwen3.7-plus**，支持文字+图片，OpenAI 兼容接口）：

```bash
LLM_PIPELINE=unified
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=你的通义密钥
LLM_MODEL=qwen3.7-plus

# 以下留空，不需要
LLM_VISION_BASE_URL=
LLM_VISION_API_KEY=
LLM_VISION_MODEL=
```

> **qwen3.7-plus 的优势**：既能对话又能直接看图，图形题、线段图不会像 OCR 那样丢信息。密钥在 [阿里云百炼/千问控制台](https://dashscope.aliyuncs.com/) 申请。模型名以控制台为准。

其他可用的多模态模型：`gpt-4o`、`qwen-vl-max` 等，同样设 `LLM_PIPELINE=unified` 即可。

> 还没填密钥也能先打开看看界面，只是暂时不能对话。

---

## 家长使用小贴士

- **先选对主题和难度档位**：档位决定小欧用多具体的语言、要不要用字母和符号。
- **鼓励孩子"想出声"**：小欧最喜欢孩子把思考过程说出来，哪怕说错。
- **善用「换种方法」**：一题多解是这个工具最想培养的习惯。
- **别急着要答案**：如果孩子想让小欧直接说答案，小欧会（礼貌地）拒绝，并再递一级台阶——这正是设计目的。
- **拍作业本**：遇到不会的题，直接点相机拍下来发给小欧。它会先帮孩子把题目读清楚（照片模糊时会请孩子确认），再用反问带她想，而不是报答案。一张图里有好几道题时，小欧会先问想研究哪一道。
- 对话会自动保存在本地浏览器里；点「开启新的探究」可以清空重来。

---

## 微信小程序版

`miniprogram/` 目录是微信小程序客户端，功能与网页版对齐：一起探索 / 带题来问、流式对话、拍照读题、xiaoou-draw 图形、快捷按钮、思考模式。

**架构：** 小程序 **不** 直连 DeepSeek/通义（密钥会暴露、域名也无法过审），而是连接 **你自己部署的后端**（本项目的 FastAPI），密钥仍放在服务器 `.env`。

### 1. 部署后端到 HTTPS

把本项目部署到有 **HTTPS** 的服务器（云主机 + Nginx + 证书），确保：

```bash
python3 run.py   # 或用 gunicorn/uvicorn 守护进程
```

外网可访问 `https://你的域名/api/health` 返回 `{"ok":true,"configured":true}`。

服务器需监听 `0.0.0.0`（在 `.env` 里设 `HOST=0.0.0.0`）。

### 2. 配置小程序

1. 用 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html) 打开 **`miniprogram/`** 目录。
2. 编辑 `miniprogram/config.js`：
   - 生产：`baseUrl: "https://你的域名"`，`useDev: false`
   - 本地调试：`useDev: true`，开发者工具勾选 **不校验合法域名**
3. 在微信公众平台 → **开发管理 → 开发设置 → 服务器域名**，把 `https://你的域名` 加入 **request 合法域名**。
4. 把 `project.config.json` 里的 `appid` 改成你的小程序 AppID。

### 3. 设置页

小程序 **设置** 里可填：服务器地址、孩子昵称、主题、难度、默认模式、思考开关。API 密钥仍在服务器 `.env`，不要写进小程序。

### 4. 与网页版的差异

| 功能 | 网页 | 小程序 |
|------|------|--------|
| LaTeX 公式 | KaTeX 渲染 | 常见符号转 Unicode（× ÷ 分数） |
| 图形 | SVG | Canvas 2D（同款 xiaoou-draw） |
| 语音输入 | Web Speech API | 暂未接入（可后续加微信录音 + 后端 STT） |
| 画板手写 | 有 | 暂未接入（可拍照代替） |

---

## 项目结构

```
math_study_ai/
├── run.py               # 启动入口：python run.py
├── requirements.txt     # Python 依赖
├── .env.example         # 配置模板（复制成 .env 使用）
├── miniprogram/         # 微信小程序（连你的 HTTPS 后端）
│   ├── app.js / app.json
│   ├── config.js        # 后端域名
│   ├── pages/           # 对话页 + 设置页
│   ├── components/diagram/
│   └── utils/           # 流式 SSE、Markdown、图形
├── server/
│   ├── app.py           # FastAPI 后端：网页 + 配置接口 + 流式对话
│   ├── tutor.py         # 教学引擎：把启发式教学法写成给模型的指令（灵魂所在）
│   └── config.py        # 读取 .env 配置
└── web/
    ├── index.html       # 界面结构
    ├── styles.css        # 样式
    └── app.js           # 前端逻辑（流式对话、公理板、快捷按钮）
```

想调整小欧的"性格"和教学方式？直接改 `server/tutor.py` 里的 `CORE_PHILOSOPHY` 和各主题的公理即可，改完重启生效。

---

## 隐私

- 密钥只保存在你本机的 `.env` 文件里（已通过 `.gitignore` 排除，不会被提交）。
- 网页版对话记录存在浏览器本地；小程序对话存在微信本地存储。
- 服务默认只监听本机（`127.0.0.1`）；对外部署（网页/小程序）时请自行加固 HTTPS 与访问控制。
