# Motor CAN Tool 

电机 MCU CAN 总线上位机，参考 ZCANPro 风格。

## 功能
- 上传并解析 DBC 文件，展示所有报文和信号
- 左侧报文树，支持搜索和展开信号列表
- 信号赋值编辑器（支持数值输入 + 枚举选择 + 范围校验）
- 单次发送 / 周期发送 CAN 报文
- SSE 实时监控收发帧（含信号解析、方向标色、闪烁动画）
- 底部状态栏显示 RX/TX/ERR 计数和当前周期任务

## 快速启动

### 后端

```bash
cd backend

# 安装 uv（如未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖并启动
uv sync
uv run main.py
# 或：uv run uvicorn main:app --reload --port 8001
```

### 前端

```bash
cd frontend

# 安装 pnpm（如未安装）
npm install -g pnpm

pnpm install
pnpm dev
```

浏览器打开 http://localhost:5173

## CAN 接口说明

| interface | channel 示例 | 说明 |
|-----------|-------------|------|
| virtual | vcan0 | 纯软件虚拟总线（测试用） |
| pcan | PCAN_USBBUS1 | PEAK USB 适配器 |
| socketcan | can0 | Linux SocketCAN |
| kvaser | 0 | Kvaser 适配器 |
| zlgcan | 面板中选 CAN1 / CAN2 | 周立功 USBCAN-I / USBCAN-II（见下） |
| chuangxin | 面板中选 CAN1 / CAN2 | 创芯科技 CANalyst-II / USBCAN-2A / 2C（见下） |

### 周立功 USBCAN-I / II

通过 [zlgcan](https://github.com/jesses2025smith/zlgcan-driver) 插件接入（`uv sync` 会自动安装，仅支持 64 位 Python）。
还需要 `backend/library` 驱动库目录（可在连接面板里改路径）：

```
backend/library/
├── bitrate.cfg.yaml          # 波特率 → timing0/timing1，来自 rust-can 仓库 zlg-lib 分支
└── windows/x86_64/
    ├── zlgcan.dll            # 周立功官方 64 位二次开发库
    └── kerneldlls/           # 含 USBCAN.dll 等
```

- 仓库里只包含 `bitrate.cfg.yaml`（来自 [rust-can](https://github.com/jesses2025smith/rust-can/tree/zlg-lib/library)）。`windows/x86_64/` 下的 DLL 是周立功的专有文件，**不随仓库分发**：请从[周立功官网](https://manual.zlg.cn/web/#/152/5332)下载 64 位二次开发库（`zlgcan_x64` 目录），把 `zlgcan.dll` 和 `kerneldlls/` 复制到 `backend/library/windows/x86_64/`。
- `zlgcan.dll` 必须是 **64 位**的；ZCANPro 安装目录里的是 32 位，不能用。
- 连接前先关闭 ZCANPro，同一张卡同时只能被一个程序打开。

### 创芯 CANalyst-II / USBCAN-2A / 2C

通过 ctypes 直接调用创芯自带的 `ControlCAN.dll`（[app/drivers/chuangxin.py](backend/app/drivers/chuangxin.py)），**沿用原厂驱动**，创芯自带的上位机软件不受影响。

- 把创芯驱动包里的 **64 位** `ControlCAN.dll` 放到 `backend/library/chuangxin/`（或在连接面板里填它所在的目录）。DLL 是创芯的专有文件，不随仓库分发。
- 必须是 64 位的；创芯 Demo / 旧上位机目录里常见的是 32 位版本，不能用，连接时会提示。
- 支持波特率 5k – 1M（125k / 250k / 500k / 1M 等），使用与周立功相同的 Timing0/Timing1 标准值。
- 终端电阻在卡上用拨码开关设置。连接前先关闭创芯自带的上位机软件。

## 项目结构

```
motor-can-tool/
├── backend/
│   ├── main.py                  # FastAPI 入口
│   ├── app/
│   │   ├── config.py            # 配置
│   │   ├── routers/
│   │   │   ├── dbc.py           # DBC 上传解析
│   │   │   ├── can.py           # CAN 连接/发送
│   │   │   └── sse.py           # SSE 推流
│   │   ├── drivers/
│   │   │   └── chuangxin.py     # 创芯 ControlCAN.dll (ctypes)
│   │   ├── services/
│   │   │   ├── dbc_service.py   # cantools 封装
│   │   │   └── can_service.py   # python-can + SSE Queue
│   │   └── schemas/             # Pydantic schemas
│   └── pyproject.toml
└── frontend/
    └── src/
        ├── api/                 # Alova 请求
        ├── stores/              # Pinia 状态
        ├── components/          # 功能组件
        └── pages/HomePage.vue   # 主布局
```
