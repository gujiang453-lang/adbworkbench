#!/usr/bin/env python3
"""
ADB Workbench - Android 运行时分析工作台 (最小可运行 Demo)

用法:
    python adbworkbench.py devices
    python adbworkbench.py scripts
    python adbworkbench.py run enum_modules --target com.android.settings --duration 5
    python adbworkbench.py run method_tracer --target com.android.settings --duration 10
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import frida
except ImportError:
    print("[!] 请先安装依赖: pip install -r requirements.txt")
    sys.exit(1)


BASE_DIR = Path(__file__).parent
SCRIPTS_DIR = BASE_DIR / "scripts"
OUTPUT_DIR = BASE_DIR / "output"


# ============ 设备管理 ============
def list_usb_devices():
    return [d for d in frida.enumerate_devices() if d.type == "usb"]


def get_device(index=0):
    devices = list_usb_devices()
    if not devices:
        print("[!] 未检测到 USB 设备")
        print("[i] 检查清单:")
        print("    1. 设备已通过 USB 连接")
        print("    2. 已开启 USB 调试")
        print("    3. 设备端 frida-server 正在运行 (adb shell su -c ./frida-server &)")
        return None
    if index >= len(devices):
        print(f"[!] 设备索引 {index} 超出范围 (共 {len(devices)} 个)")
        return None
    return devices[index]


def cmd_devices(args):
    devices = list_usb_devices()
    if not devices:
        print("[!] 未检测到 USB 设备")
        return 1
    print(f"[+] 找到 {len(devices)} 个设备:")
    for i, d in enumerate(devices):
        print(f"    [{i}] {d.name}  (id={d.id})")
    return 0


# ============ 脚本管理 ============
def cmd_scripts(args):
    if not SCRIPTS_DIR.exists():
        print(f"[!] 脚本目录不存在: {SCRIPTS_DIR}")
        return 1
    scripts = sorted(SCRIPTS_DIR.glob("*.js"))
    if not scripts:
        print("[!] 没有找到任何脚本")
        return 1
    print(f"[+] 找到 {len(scripts)} 个脚本:")
    for s in scripts:
        print(f"    - {s.stem}")
    return 0


def load_script(name):
    path = SCRIPTS_DIR / f"{name}.js"
    if not path.exists():
        path = SCRIPTS_DIR / name
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


# ============ 结果收集器 ============
class Collector:
    """收集 Frida 脚本通过 send() 发送的结构化消息"""

    def __init__(self, verbose=True):
        self.messages = []
        self.errors = []
        self.status = []
        self.verbose = verbose

    def on_message(self, message, data):
        if message["type"] == "send":
            payload = message.get("payload", {})
            msg_type = payload.get("type", "unknown")
            inner = payload.get("payload", {})

            if msg_type == "status":
                self.status.append(inner)
                if self.verbose:
                    print(f"    [status] {inner}")
            elif msg_type == "error":
                self.errors.append(inner)
                if self.verbose:
                    print(f"    [error]  {inner}")
            else:
                self.messages.append(payload)
                if self.verbose:
                    preview = json.dumps(inner, ensure_ascii=False)
                    if len(preview) > 110:
                        preview = preview[:110] + "..."
                    print(f"    [{msg_type}] {preview}")

        elif message["type"] == "error":
            err = {
                "description": message.get("description"),
                "stack": message.get("stack"),
            }
            self.errors.append(err)
            if self.verbose:
                print(f"    [frida-error] {err['description']}")

    def to_dict(self):
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "messages": len(self.messages),
                "errors": len(self.errors),
                "status_events": len(self.status),
            },
            "status": self.status,
            "errors": self.errors,
            "messages": self.messages,
        }


# ============ 核心：run 命令 ============
def cmd_run(args):
    print(f"[*] ADB Workbench | 脚本={args.script} | 目标={args.target}")

    # 1. 加载脚本
    source = load_script(args.script)
    if source is None:
        print(f"[!] 脚本不存在: {args.script}")
        print(f"[i] 可用脚本请运行: python adbworkbench.py scripts")
        return 1
    print(f"[+] 已加载脚本 ({len(source)} 字节)")

    # 2. 获取设备
    device = get_device(args.device_index)
    if device is None:
        return 1
    print(f"[+] 使用设备: {device.name}")

    # 3. 附加到目标进程
    print(f"[*] 附加到进程: {args.target}")
    try:
        session = device.attach(args.target)
    except frida.ProcessNotFoundError:
        print(f"[!] 进程未找到: {args.target}")
        print("[i] 提示: 请先启动目标应用, 或使用包名而非 PID")
        return 1
    except Exception as e:
        print(f"[!] 附加失败: {e}")
        return 1

    # 4. 注入脚本
    collector = Collector(verbose=True)
    script = session.create_script(source)
    script.on("message", collector.on_message)
    script.load()
    print(f"[+] 脚本已注入, 收集数据中 (时长 {args.duration}s)...")
    print("-" * 60)

    # 5. 等待收集
    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print("\n[*] 用户中断, 提前结束收集")

    # 6. 清理
    try:
        script.unload()
        session.detach()
    except Exception:
        pass

    # 7. 输出报告
    result = collector.to_dict()
    result["meta"] = {
        "script": args.script,
        "target": args.target,
        "device": device.name,
        "duration_seconds": args.duration,
    }

    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"{args.script}_{timestamp}.json"
    output_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("-" * 60)
    print("[+] 完成!")
    print(f"    消息数: {result['summary']['messages']}")
    print(f"    错误数: {result['summary']['errors']}")
    print(f"    报告:   {output_file}")
    return 0


# ============ CLI 入口 ============
def main():
    parser = argparse.ArgumentParser(
        prog="adbworkbench",
        description="ADB Workbench - Android 运行时分析工作台",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("devices", help="列出已连接的 USB 设备")
    sub.add_parser("scripts", help="列出可用的 Frida 脚本")

    p_run = sub.add_parser("run", help="注入并运行脚本")
    p_run.add_argument("script", help="脚本名称 (不含 .js)")
    p_run.add_argument("--target", required=True, help="目标进程名或包名")
    p_run.add_argument("--duration", type=int, default=10, help="收集时长(秒), 默认 10")
    p_run.add_argument("--device-index", type=int, default=0, help="设备索引, 默认 0")

    args = parser.parse_args()

    if args.command == "devices":
        return cmd_devices(args)
    if args.command == "scripts":
        return cmd_scripts(args)
    if args.command == "run":
        return cmd_run(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
