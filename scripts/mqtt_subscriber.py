#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mqtt_subscriber.py  ——  AutoWeldVisionZulu 测量工站 MQTT 订阅端测试脚本

用途:
    订阅视觉软件发布的测量数据, 验证 MQTT 通讯链路与 XML 报文格式.
    与 MqttDataRecorder 消费相同的三个主题:
      /autoweld/measure/data/raw   —— DataMessage (测量数据)
      /autoweld/measure/image/raw  —— ImageMessage (JPEG base64)
      /autoweld/measure/logs/raw   —— LogMessage (检测日志)

依赖:
    pip install paho-mqtt

用法:
    python scripts/mqtt_subscriber.py
    python scripts/mqtt_subscriber.py --broker tcp://127.0.0.1:8907
    python scripts/mqtt_subscriber.py --prefix autoweld --save-images images/recv
    python scripts/mqtt_subscriber.py --save-images images/recv --log-recv recv.log

说明:
    - 默认 broker = tcp://127.0.0.1:8907 (与软件默认一致)
    - 主题前缀默认 autoweld (与软件 StationConfig.mqtt.topicPrefix 一致)
    - --save-images: 把收到的 ImageMessage 解码为 jpg 落盘, 文件名 配方号_面号_时间戳.jpg
    - --log-recv: 把所有收到的报文原文追加到文件
    - Ctrl+C 退出
"""

import argparse
import base64
import os
import sys
import time
import xml.etree.ElementTree as ET

# 重定向到文件时也按行刷新, 便于实时观察
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("[致命错误] 缺少 paho-mqtt:  pip install paho-mqtt")
    sys.exit(1)


def parse_args():
    ap = argparse.ArgumentParser(description="AutoWeldVisionZulu MQTT 订阅端测试")
    ap.add_argument("--broker", default="tcp://127.0.0.1:8907",
                    help="MQTT Broker 地址, 默认 tcp://127.0.0.1:8907")
    ap.add_argument("--prefix", default="autoweld",
                    help="主题前缀(对应 StationConfig.mqtt.topicPrefix), 默认 autoweld")
    ap.add_argument("--save-images", metavar="DIR", default=None,
                    help="把收到的图像保存为 jpg 到该目录")
    ap.add_argument("--log-recv", metavar="FILE", default=None,
                    help="把所有报文原文追加到该文件")
    return ap.parse_args()


def parse_broker(broker):
    """tcp://host:port -> (host, port)."""
    s = broker.replace("tcp://", "").replace("ssl://", "")
    host, _, port = s.partition(":")
    return host, int(port) if port else 1883


def xml_tag_map(payload):
    """解析 XML 报文为 {tag: text}."""
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        # 兼容旧版无根元素: 包一层 <root>
        root = ET.fromstring("<root>" + payload + "</root>")
    return root.tag, {c.tag: (c.text or "").strip() for c in list(root)}


def fmt_value(v, width=10):
    return str(v).ljust(width)


def main():
    args = parse_args()
    host, port = parse_broker(args.broker)
    prefix = args.prefix.strip("/")
    topics = {
        "/%s/measure/data/raw" % prefix: "data",
        "/%s/measure/image/raw" % prefix: "image",
        "/%s/measure/logs/raw" % prefix: "logs",
    }
    if args.save_images:
        os.makedirs(args.save_images, exist_ok=True)
    logf = open(args.log_recv, "a", encoding="utf-8") if args.log_recv else None

    counts = {k: 0 for k in topics.values()}

    def on_connect(client, userdata, flags, rc, props=None):
        if rc == 0:
            print("[就绪] 已连接 %s, 订阅:" % args.broker)
            for t in topics:
                client.subscribe(t, 1)
                print("        %s" % t)
            print("  等待报文 (Ctrl+C 退出)...\n")
        else:
            print("[错误] 连接失败 rc=%s" % rc)

    def on_message(client, userdata, msg):
        topic = msg.topic
        kind = topics.get(topic)
        payload = msg.payload.decode("utf-8", "replace")
        counts[kind] += 1
        if logf:
            logf.write("===== %s @ %s =====\n" % (topic, time.strftime("%H:%M:%S")))
            logf.write(payload + "\n")
            logf.flush()
        try:
            root, tags = xml_tag_map(payload)
        except Exception as e:
            print("[%s] #%d 收到 %d 字节, 但 XML 解析失败: %s"
                  % (time.strftime("%H:%M:%S"), counts[kind], len(payload), e))
            return

        if kind == "data":
            h = tags.get("ProductHeight", "?")
            w = tags.get("ProductWidth", "?")
            sym = tags.get("Symmetry", "?")
            print("[%s] [data #%d] root=%s 配方=%s 面=%s H=%s W=%s Sym=%s"
                  % (time.strftime("%H:%M:%S"), counts[kind], root,
                     fmt_value(tags.get("ProductNumber")),
                     fmt_value(tags.get("SurfaceNumber")),
                     fmt_value(h), fmt_value(w), sym))
        elif kind == "image":
            b64 = tags.get("ImageData", "")
            blob = base64.b64decode(b64) if b64 else b""
            is_jpg = blob[:2] == b"\xff\xd8"
            saved = ""
            if args.save_images and is_jpg:
                fn = "%s_%s_%s.jpg" % (tags.get("ProductNumber", "0"),
                                       tags.get("SurfaceNumber", "0"),
                                       int(time.time() * 1000))
                path = os.path.join(args.save_images, fn)
                with open(path, "wb") as f:
                    f.write(blob)
                saved = " -> " + path
            print("[%s] [image #%d] root=%s 配方=%s 面=%s ImageData=%d字节 jpg=%s%s"
                  % (time.strftime("%H:%M:%S"), counts[kind], root,
                     fmt_value(tags.get("ProductNumber")),
                     fmt_value(tags.get("SurfaceNumber")),
                     len(blob), is_jpg, saved))
        elif kind == "logs":
            print("[%s] [logs #%d] root=%s 配方=%s 面=%s Message=%s"
                  % (time.strftime("%H:%M:%S"), counts[kind], root,
                     fmt_value(tags.get("ProductNumber")),
                     fmt_value(tags.get("SurfaceNumber")),
                     tags.get("Message")))

    client = mqtt.Client(client_id="awv-sub-" + str(int(time.time())))
    # paho 2.x callback API 兼容
    if hasattr(client, "on_connect"):
        client.on_connect = on_connect
    else:
        client.on_connect = lambda c, u, f, r: on_connect(c, u, f, r)
    client.on_message = on_message

    print("[启动] 连接 %s ..." % args.broker)
    try:
        client.connect(host, port, 60)
    except Exception as e:
        print("[致命错误] 无法连接 %s: %s" % (args.broker, e))
        sys.exit(1)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[退出] 统计:", ", ".join("%s=%d" % (k, v) for k, v in counts.items()))
    finally:
        client.disconnect()
        if logf:
            logf.close()


if __name__ == "__main__":
    main()
