#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s7_plc_sim.py  ——  虚拟西门子 S7 主站(PLC 服务端模拟器)

用途:
    在没有真实 PLC 时, 用本机模拟一台 S7 PLC, 供 AutoWeldVisionZulu
    (s7connector/moka7 客户端) 连接, 测试 DB 块的读取与写入:
      - 视觉端(客户端)写: IN_通讯心跳(0) / OUT_结果(2, 3=OK/2=NG) / 读相机作业号回显(8) / IN_X(10起) / IN_Y(50起) / 完成后清 OUT_触发拍照(4)=0
      - PLC 端(本脚本)写: OUT_触发拍照(4, 上升沿触发流程) / 传相机作业号(6, 切换配方) / 报警DB11 报警位 / 取走结果后清 OUT_结果(2)=0
      - 握手规则"谁接收谁清0": 视觉接收触发->视觉清触发位; PLC接收结果->PLC清结果位

    本脚本内置:
      * S7 服务端(snap7 3.0 纯 Python 实现, 无需 snap7.dll), 默认监听 0.0.0.0:102
      * 过程 DB92/93/97/98 与报警 DB11, 大端 Int16 / Real32 编解码
      * 监视线程: 实时打印客户端(视觉软件)写入的心跳/结果/X/Y
      * 自动应答(auto-ack): 视觉写出 OK/NG 并清触发后, 模拟 PLC 自动清零结果位, 跑通完整握手
      * 交互命令: 手动发触发、切作业号、置报警位、查看 DB 原始数据

重要(IP 地址):
    视觉软件连接的目标 IP 取自其 PLC 配置(默认 192.168.1.110)。
    服务端监听 0.0.0.0 表示"本机所有网卡 IP", 因此只要 192.168.1.110 是本机地址即可连通:
      方案 A(推荐, 现场直连): 给本机网卡添加 192.168.1.110
          netsh interface ip add address "以太网" 192.168.1.110 255.255.255.0
      方案 B(同机自测): 把视觉软件 通讯→PLC通讯 的 IP 改成本机地址(如 127.0.0.1 或本机网卡IP)
    Windows 绑定 102 端口无需管理员权限。

依赖:
    pip install python-snap7     (已在 Python 3.13 64bit + snap7 3.0.0 验证)

用法:
    python scripts/s7_plc_sim.py                 # 监听 0.0.0.0:102, 注册默认 DB
    python scripts/s7_plc_sim.py --port 1102     # 换端口(视觉端也要改端口)
    python scripts/s7_plc_sim.py --dbs 97 --alarm-db 11
    python scripts/s7_plc_sim.py --demo          # 演示: 周期性自动发触发

运行后输入 help 查看交互命令。
"""

import argparse
import logging
import socket
import struct
import sys
import threading
import time

# snap7 服务端在客户端断开瞬间会打印 "Expected COTP DT" 等无害的底层日志, 调高其级别静音
logging.getLogger("snap7").setLevel(logging.CRITICAL)

# ---------------------------------------------------------------- 依赖自检
try:
    import snap7
    try:
        from snap7.type import SrvArea        # snap7 3.x (纯 Python 服务端)
    except ImportError:
        from snap7.types import SrvArea       # snap7 1.x/2.x
except Exception as e:  # pragma: no cover
    print("[致命错误] 缺少 python-snap7 或其依赖: %s" % e)
    print("        请先安装:  pip install python-snap7")
    print("        (snap7 3.0 服务端为纯 Python 实现, 通常无需额外 snap7.dll)")
    sys.exit(1)

# Windows 控制台尽量用 UTF-8, 避免中文/方框乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------- DB 布局(与 Java DbLayout 一致, 大端)
OFF_HEARTBEAT = 0    # IN_通讯心跳 Int16  (视觉写, 周期翻转 0/1)
OFF_RESULT = 2       # OUT_结果    Int16  (视觉写: 3=OK 2=NG 0=重置)
OFF_TRIGGER = 4      # OUT_触发拍照 Int16 (PLC写: 上升沿触发, 值=triggerValue)
OFF_JOB_SET = 6      # 传相机作业号 Int16  (PLC写: 非0且变化则切配方)
OFF_JOB_ECHO = 8     # 读相机作业号 Int16  (视觉写: 回显当前配方号)
OFF_X_BASE = 10      # IN_X[0..9]  Real32 (视觉写, 步长4)
OFF_Y_BASE = 50      # IN_Y[0..9]  Real32 (视觉写, 步长4)
MAX_POINTS = 10

RESULT_TEXT = {0: "RESET", 2: "NG", 3: "OK"}

# 默认报警位(与视觉软件 StationConfig 默认报警定义一致), 位于报警 DB11
DEFAULT_ALARMS = [
    (89,  2, 5, "相机图像故障"),
    (108, 5, 0, "相机通讯超时"),
    (109, 5, 1, "相机拍照超时"),
    (113, 5, 5, "相机切换作业超时"),
]

DEFAULT_PROCESS_DBS = [92, 93, 97, 98]
DEFAULT_ALARM_DB = 11
DEFAULT_DB_SIZE = 256   # 实际过程 DB 仅用 90 字节, 这里给足余量


# ---------------------------------------------------------------- 编解码工具
def put_uint16(buf, off, val):
    buf[off:off + 2] = struct.pack(">H", int(val) & 0xFFFF)


def get_uint16(buf, off):
    return struct.unpack(">H", bytes(buf[off:off + 2]))[0]


def put_real(buf, off, val):
    buf[off:off + 4] = struct.pack(">f", float(val))


def get_real(buf, off):
    return struct.unpack(">f", bytes(buf[off:off + 4]))[0]


def set_bit(buf, byte_off, bit, on):
    if on:
        buf[byte_off] |= (1 << bit)
    else:
        buf[byte_off] &= ~(1 << bit) & 0xFF


def get_bit(buf, byte_off, bit):
    return (buf[byte_off] >> bit) & 0x01 == 1


def ts():
    return time.strftime("%H:%M:%S")


def log(msg):
    print("[%s] %s" % (ts(), msg))


def check_port_free(port):
    """用不带 SO_REUSEADDR 的普通套接字探测端口是否已被占用.
    snap7 服务端会置 SO_REUSEADDR, Windows 下即便端口已被监听也能"绑定成功",
    导致连接被既有服务抢占(常见于西门子 SIMATIC 的 s7oiehsx64 常驻 102 端口).
    这里提前给出可操作提示. 返回 True 表示端口空闲可用.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", port))
    except OSError as e:
        print("[端口检查] %d 端口已被占用/不可用: %s" % (port, e))
        print("           本机若装了西门子 SIMATIC/STEP7, 其 s7oiehsx64 等服务常占 102 端口。")
        print("           处理办法二选一:")
        print("             1) 停用该西门子服务后重试(任务管理器/服务中停止 SIMATIC 相关服务);")
        print("             2) 用其它端口, 例如:  python scripts/s7_plc_sim.py --port 1102")
        print("                并在视觉软件 通讯→PLC通讯 把端口同步改成 1102。")
        return False
    finally:
        s.close()
    return True


# ---------------------------------------------------------------- 模拟器主体
class S7PlcSim:
    def __init__(self, port, process_dbs, alarm_db, db_size, auto_ack, demo):
        self.port = port
        self.process_dbs = list(process_dbs)
        self.alarm_db = alarm_db
        self.db_size = db_size
        self.auto_ack = auto_ack
        self.demo = demo

        self.server = snap7.server.Server(log=False)
        # db号 -> bytearray(同一引用注册给服务端, 客户端读写即作用于此)
        self.areas = {}
        self.area_lock = threading.Lock()
        self._snapshot = {}        # 上次监视快照, 用于变化检测
        self._last_result = {}     # db -> 上次结果值, auto-ack 用
        self.stop_flag = threading.Event()

    # ------------------------------------------------ 注册内存区
    def setup_areas(self):
        for db in self.process_dbs:
            buf = bytearray(self.db_size)
            self.areas[db] = buf
            self.server.register_area(SrvArea.DB, db, buf)
            self._snapshot[db] = bytes(buf)
            self._last_result[db] = 0
        # 报警 DB
        abuf = bytearray(self.db_size)
        self.areas[self.alarm_db] = abuf
        self.server.register_area(SrvArea.DB, self.alarm_db, abuf)
        self._snapshot[self.alarm_db] = bytes(abuf)
        log("已注册过程 DB %s (各 %d 字节), 报警 DB%d (%d 字节)"
            % (self.process_dbs, self.db_size, self.alarm_db, self.db_size))

    def start(self):
        self.setup_areas()
        self.server.start(tcp_port=self.port)
        log("S7 虚拟主站已启动, 监听 0.0.0.0:%d (本机所有网卡)" % self.port)
        log("等待视觉软件连接 ... (rack/slot 用视觉端配置, 默认 rack=0 slot=1)")
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        threading.Thread(target=self._event_loop, daemon=True).start()
        if self.demo:
            threading.Thread(target=self._demo_loop, daemon=True).start()
            log("演示模式开启: 每 8 秒对每个过程 DB 发一次触发")

    def stop(self):
        self.stop_flag.set()
        try:
            self.server.stop()
        except Exception:
            pass

    # ------------------------------------------------ 事件(客户端上下线)打印
    def _event_loop(self):
        while not self.stop_flag.is_set():
            try:
                ev = self.server.pick_event()
            except Exception:
                ev = False
            if ev:
                try:
                    code = getattr(ev, "EvtCode", 0)
                    # 常见: 0x00010000 服务启动; 客户端连接/断开等
                    log("S7事件: EvtCode=0x%08X" % (code & 0xFFFFFFFF))
                except Exception:
                    pass
            time.sleep(0.2)

    # ------------------------------------------------ 监视客户端(视觉)写入
    def _monitor_loop(self):
        while not self.stop_flag.is_set():
            with self.area_lock:
                for db, buf in self.areas.items():
                    self._inspect(db, buf)
            time.sleep(0.15)

    def _inspect(self, db, buf):
        snap = self._snapshot.get(db)
        if snap is None:
            self._snapshot[db] = bytes(buf)
            return
        cur = bytes(buf)
        if cur == snap:
            return
        self._snapshot[db] = cur

        if db == self.alarm_db:
            # 报警 DB 由本脚本置位, 客户端只读; 变化一般来自命令, 不必打印
            return

        # 过程 DB: 解析视觉端写入的字段
        hb = get_uint16(buf, OFF_HEARTBEAT)
        result = get_uint16(buf, OFF_RESULT)
        echo = get_uint16(buf, OFF_JOB_ECHO)

        if cur[OFF_HEARTBEAT:OFF_HEARTBEAT + 2] != snap[OFF_HEARTBEAT:OFF_HEARTBEAT + 2]:
            log("DB%d  <== 心跳翻转 = %d" % (db, hb))
        if cur[OFF_JOB_ECHO:OFF_JOB_ECHO + 2] != snap[OFF_JOB_ECHO:OFF_JOB_ECHO + 2]:
            log("DB%d  <== 读相机作业号回显 = %d" % (db, echo))
        if cur[OFF_RESULT:OFF_RESULT + 2] != snap[OFF_RESULT:OFF_RESULT + 2]:
            log("DB%d  <== OUT_结果 = %d (%s)"
                % (db, result, RESULT_TEXT.get(result, "?")))
            self._last_result[db] = result
            if self.auto_ack and result in (2, 3):
                # 视觉已出结果, 且视觉会在结果就绪后自行清零触发位(谁接收拍照触发谁清0) ->
                # 模拟PLC等触发位回0后清零结果位(PLC接收结果, 由PLC清结果位)
                threading.Thread(target=self._auto_clear_result,
                                 args=(db,), daemon=True).start()

        # X/Y Real 变化(非0才打印, 避免刷屏)
        xs = [get_real(buf, OFF_X_BASE + i * 4) for i in range(MAX_POINTS)]
        ys = [get_real(buf, OFF_Y_BASE + i * 4) for i in range(MAX_POINTS)]
        xn = [v for v in xs if abs(v) > 1e-6]
        yn = [v for v in ys if abs(v) > 1e-6]
        if xn or yn:
            # 仅在 X/Y 区有变化时打印
            if cur[OFF_X_BASE:OFF_Y_BASE] != snap[OFF_X_BASE:OFF_Y_BASE] \
                    or cur[OFF_Y_BASE:OFF_Y_BASE + 40] != snap[OFF_Y_BASE:OFF_Y_BASE + 40]:
                log("DB%d  <== 数据回写: X=%s | Y=%s"
                    % (db, self._fmt_reals(xs), self._fmt_reals(ys)))

    @staticmethod
    def _fmt_reals(vals):
        parts = []
        for i, v in enumerate(vals):
            if abs(v) > 1e-6:
                parts.append("%d:%.3f" % (i + 1, v))
        return "[" + " ".join(parts) + "]" if parts else "[]"

    def _auto_clear_result(self, db):
        # 等视觉把触发位清0(表示结果已就绪), 再由PLC清结果位, 完成"谁接收谁清0"握手
        for _ in range(50):               # 最多约 5s
            time.sleep(0.1)
            with self.area_lock:
                b = self.areas.get(db)
                trig = get_uint16(b, OFF_TRIGGER) if b is not None else 0
            if trig == 0:
                break
        with self.area_lock:
            buf = self.areas.get(db)
            if buf is not None and get_uint16(buf, OFF_RESULT) != 0:
                put_uint16(buf, OFF_RESULT, 0)
        log("DB%d  ==> [auto] 视觉已清触发, 模拟PLC清零结果 (完成本次握手)" % db)

    # ------------------------------------------------ 演示: 周期触发
    def _demo_loop(self):
        # 等服务端稳定
        time.sleep(2.0)
        while not self.stop_flag.is_set():
            for db in self.process_dbs:
                if self.stop_flag.is_set():
                    break
                self.send_trigger(db, 1)
                time.sleep(8.0)

    # ------------------------------------------------ PLC 侧动作(命令调用)
    def send_trigger(self, db, value):
        with self.area_lock:
            buf = self.areas.get(db)
            if buf is None:
                log("DB%d 未注册" % db)
                return
            put_uint16(buf, OFF_TRIGGER, 0)   # 先保证低电平
        time.sleep(0.05)
        with self.area_lock:
            put_uint16(buf, OFF_TRIGGER, value)  # 上升沿
        log("DB%d  ==> OUT_触发拍照上升沿 = %d (等待视觉处理)" % (db, value))

    def clear_trigger(self, db):
        with self.area_lock:
            buf = self.areas.get(db)
            if buf is None:
                return
            put_uint16(buf, OFF_TRIGGER, 0)
        log("DB%d  ==> 手动清零触发" % db)

    def run_measure_seq(self, db, job_no=1, faces=4, gap=0.25):
        """测量工站空跑联调序列: 切配方 -> 面1触发 ->(视觉回OK/清触发)-> 面2 ... 面N.
        每个面触发后等待视觉空跑握手完成(视觉会自行把拍照位清0), 再发下一个面。"""
        def worker():
            if db not in self.process_dbs:
                log("DB%d 不在过程DB列表 %s" % (db, self.process_dbs))
                return
            log("=== 测量空跑序列开始: DB%d 配方%d ===" % (db, job_no))
            self.send_job(db, job_no)
            time.sleep(0.6)   # 等切配方 + 作业号回显
            for n in range(1, faces + 1):
                self.send_trigger(db, n)
                time.sleep(gap + 0.25)   # 等视觉空跑处理(回作业号/清拍照位/写点/回OK)
            log("=== 测量空跑序列结束: 已依次触发 面1..面%d ===" % faces)
        threading.Thread(target=worker, daemon=True).start()

    def send_job(self, db, job_no):
        with self.area_lock:
            buf = self.areas.get(db)
            if buf is None:
                return
            put_uint16(buf, OFF_JOB_SET, job_no)
        log("DB%d  ==> 传相机作业号 = %d (视觉应切配方并回显)" % (db, job_no))

    def set_alarm_by_pos(self, byte_off, bit, on):
        with self.area_lock:
            buf = self.areas.get(self.alarm_db)
            if buf is None:
                return
            set_bit(buf, byte_off, bit, on)
        log("DB%d ==> 报警位 字节%d 位%d = %d"
            % (self.alarm_db, byte_off, bit, 1 if on else 0))

    def set_alarm_by_id(self, alarm_id, on):
        for aid, bo, bi, name in DEFAULT_ALARMS:
            if aid == alarm_id:
                self.set_alarm_by_pos(bo, bi, on)
                log("报警[%d]%s -> %s" % (aid, name, "置位" if on else "复位"))
                return
        log("未知报警ID %d, 预置: %s" % (alarm_id,
            ", ".join(str(a[0]) for a in DEFAULT_ALARMS)))

    def dump_db(self, db, off=0, length=None):
        with self.area_lock:
            buf = self.areas.get(db)
        if buf is None:
            log("DB%d 未注册" % db)
            return
        end = len(buf) if length is None else min(len(buf), off + length)
        log("DB%d 原始数据 (偏移 %d..%d):" % (db, off, end - 1))
        for i in range(off, end, 16):
            chunk = buf[i:i + 16]
            hexs = " ".join("%02X" % b for b in chunk)
            print("      %4d: %-47s" % (i, hexs))
        # 附带解析关键字段
        if db != self.alarm_db and end >= OFF_JOB_ECHO + 2:
            log("    心跳=%d 结果=%d(%s) 触发=%d 作业号=%d 回显=%d"
                % (get_uint16(buf, OFF_HEARTBEAT),
                   get_uint16(buf, OFF_RESULT),
                   RESULT_TEXT.get(get_uint16(buf, OFF_RESULT), "?"),
                   get_uint16(buf, OFF_TRIGGER),
                   get_uint16(buf, OFF_JOB_SET),
                   get_uint16(buf, OFF_JOB_ECHO)))


# ---------------------------------------------------------------- 交互命令
HELP_TEXT = """
可用命令:
  trig <db> [值]      发触发上升沿(默认值=1, 对应流程 triggerValue)  例: trig 97 1
  seq <db> [作业号]   测量空跑联调: 切配方后依次触发 面1..面4       例: seq 97 1
  clear <db>          清零触发(手动模拟下降沿)
  job <db> <作业号>   下发传相机作业号(切换配方)                    例: job 97 163
  alarmid <id> <0|1>  按预置ID置位/复位报警(DB11)                  例: alarmid 89 1
  alarm <字节> <位> <0|1>  直接置位/复位报警位                     例: alarm 5 0 1
  db <db> [偏移] [长度]     查看DB原始数据(hex)                     例: db 97 0 90
  auto <on|off>       自动应答开关(视觉出结果后自动清零触发, 默认on)
  demo <on|off>       演示模式(周期自动发触发)
  list                列出已注册DB与预置报警
  help                显示本帮助
  quit / exit         退出
""".strip()


def repl(sim):
    print(HELP_TEXT)
    while True:
        try:
            line = input("\nPLC-SIM> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        try:
            if cmd in ("quit", "exit"):
                break
            elif cmd == "help":
                print(HELP_TEXT)
            elif cmd == "list":
                log("过程DB: %s  报警DB: %d  自动应答: %s  演示: %s"
                    % (sim.process_dbs, sim.alarm_db,
                       "on" if sim.auto_ack else "off",
                       "on" if sim.demo else "off"))
                for aid, bo, bi, name in DEFAULT_ALARMS:
                    print("      报警ID %-4d 字节%2d 位%d  %s" % (aid, bo, bi, name))
            elif cmd == "trig" or cmd == "trigger":
                db = int(parts[1]); val = int(parts[2]) if len(parts) > 2 else 1
                sim.send_trigger(db, val)
            elif cmd == "seq":
                db = int(parts[1]); job = int(parts[2]) if len(parts) > 2 else 1
                sim.run_measure_seq(db, job)
            elif cmd == "clear":
                sim.clear_trigger(int(parts[1]))
            elif cmd == "job":
                sim.send_job(int(parts[1]), int(parts[2]))
            elif cmd == "alarmid":
                sim.set_alarm_by_id(int(parts[1]), parts[2] == "1")
            elif cmd == "alarm":
                sim.set_alarm_by_pos(int(parts[1]), int(parts[2]), parts[3] == "1")
            elif cmd == "db":
                db = int(parts[1])
                off = int(parts[2]) if len(parts) > 2 else 0
                ln = int(parts[3]) if len(parts) > 3 else None
                sim.dump_db(db, off, ln)
            elif cmd == "auto":
                sim.auto_ack = (len(parts) < 2 or parts[1].lower() != "off")
                log("自动应答: %s" % ("on" if sim.auto_ack else "off"))
            elif cmd == "demo":
                on = len(parts) < 2 or parts[1].lower() != "off"
                if on and not sim.demo:
                    sim.demo = True
                    threading.Thread(target=sim._demo_loop, daemon=True).start()
                else:
                    sim.demo = on
                log("演示模式: %s" % ("on" if on else "off"))
            else:
                print("未知命令: %s (输入 help)" % cmd)
        except IndexError:
            print("参数不足, 用法见 help")
        except ValueError:
            print("参数应为数字, 用法见 help")
        except Exception as e:
            print("命令执行失败: %s" % e)


def main():
    ap = argparse.ArgumentParser(
        description="虚拟西门子 S7 主站(PLC 服务端), 供 AutoWeldVisionZulu 测试 DB 读写")
    ap.add_argument("--port", type=int, default=102, help="监听端口(默认102, 需与视觉端PLC端口一致)")
    ap.add_argument("--dbs", type=int, nargs="+", default=DEFAULT_PROCESS_DBS,
                    help="过程DB号列表(默认 92 93 97 98)")
    ap.add_argument("--alarm-db", type=int, default=DEFAULT_ALARM_DB, help="报警DB号(默认11)")
    ap.add_argument("--db-size", type=int, default=DEFAULT_DB_SIZE, help="每个DB分配字节数(默认256)")
    ap.add_argument("--no-auto-ack", action="store_true",
                    help="关闭自动应答(默认视觉出OK/NG后自动清零触发跑通握手)")
    ap.add_argument("--demo", action="store_true", help="演示模式: 周期自动发触发")
    ap.add_argument("--force", action="store_true",
                    help="跳过端口占用检查(不建议: 端口被西门子服务占用时连接会被抢占)")
    args = ap.parse_args()

    if not args.force and not check_port_free(args.port):
        sys.exit(2)

    sim = S7PlcSim(args.port, args.dbs, args.alarm_db, args.db_size,
                   auto_ack=not args.no_auto_ack, demo=args.demo)
    try:
        sim.start()
    except Exception as e:
        log("[启动失败] %s" % e)
        log("若为端口占用/权限问题: 可换 --port 1102 并在视觉端同步修改端口;")
        log("Windows 绑定102一般无需管理员, Linux/macOS 需 root 或改用高端口。")
        sys.exit(1)

    try:
        repl(sim)
    finally:
        log("正在停止 S7 虚拟主站 ...")
        sim.stop()


if __name__ == "__main__":
    main()
