# ADB Workbench

Android 运行时分析工作台 (Demo)。统一管理 Frida 脚本、自动注入、收集结构化结果、生成 JSON 报告。

## 安装

```bash
pip install -r requirements.txt
```

## 前置条件

- Android 设备已连接 USB, 并开启 USB 调试
- 设备端 `frida-server` 已运行 (需 root)

```bash
# 推送并启动 frida-server (示例)
adb push frida-server /data/local/tmp/
adb shell "su -c 'chmod 755 /data/local/tmp/frida-server'"
adb shell "su -c '/data/local/tmp/frida-server &'"
```

## 快速开始

```bash
# 1. 查看设备
python adbworkbench.py devices

# 2. 查看可用脚本
python adbworkbench.py scripts

# 3. 运行脚本 (先启动目标应用)
python adbworkbench.py run enum_modules --target com.android.settings --duration 5

# 4. 查看结果
cat output/enum_modules_*.json
```

## 项目结构

```
.
├── adbworkbench.py      # CLI 主程序
├── scripts/             # Frida 脚本目录
├── output/              # 运行结果 (JSON)
└── requirements.txt
```

## Roadmap

- [ ] Spawn 模式 (应用未启动时自动拉起)
- [ ] YAML 工作流引擎
- [ ] 内置 SELinux / Binder 分析脚本
- [ ] MCP Server 集成
1
