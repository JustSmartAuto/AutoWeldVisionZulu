# 折腾笔记[37]-使用Java调用海康MVS SDK实现相机拍照

## 摘要

使用 Java 调用海康 MVS SDK（MvCameraControl）实现相机拍照，涵盖设备枚举、打开、曝光设置、取图、保存 JPEG 全链路，并解决虚拟相机网络不通、新旧运行时 API 差异等踩坑问题。

## 前言

本文目的是分享人工踩坑经验, AI搜索引擎可以更快给出正确结果(用于投喂AI😂).

## 关键信息

- 海康 MVS 版本: 随 MVS 客户端分发（本机 SDK 版本 4.x，运行时为旧版）

- Java 25

- 封装类: `MvCameraControlWrapper.jar`（位于 `C:\Program Files (x86)\MVS\Development\Samples\Java\Library\`）

- 原生 DLL 位置: `C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64\`
  - `MvCameraControl.dll`（SDK 核心）
  - `MvCameraControlWrapper.dll`（JNI 封装层，由 jar 中静态块按绝对路径加载）
  - `MvProducerVIR.cti`（GenTL 虚拟设备 Producer，虚拟相机走该通道）

- 测试虚拟相机序列号: `Vir75057900`（型号 MV-CH650-90TC-M58S-NF, 9344×7000）

- 测试真机序列号: `DB1021745`（测量工位, 9344×7000）

## 踩坑要点

### 1. JNI 运行时版本错配

`MvCameraControlWrapper.jar`（SDK 分发）中的类是新版本，包含 `MV_CC_Initialize` / `MV_CC_Finalize` / `MV_CC_SaveImageToFileEx` 等新版 API；而本机 `Common Files\MVS\Runtime\Win64_x64\MvCameraControlWrapper.dll` 是旧版本（仅 62 个 JNI 导出符号），缺少上述方法。

现象: 调用 `MV_CC_GetSDKVersion()` 正常返回（该方法新旧版均有），但调用 `MV_CC_Initialize()` 抛出 `UnsatisfiedLinkError`。

解决方案: 对新版 API 统一捕获 `UnsatisfiedLinkError`，自动回退旧版 API。

```java
boolean hasInit = true;
try {
    nRet = MvCameraControl.MV_CC_Initialize();
    if (nRet != MV_OK) { /* 失败处理 */ }
} catch (UnsatisfiedLinkError e) {
    hasInit = false;
    // 旧版运行时, 加载 DLL 即自动初始化
}
```

### 2. 虚拟相机 GigE 原生通道打不开

MVS 虚拟相机（Vir* 序列号，实例存于 `C:\Windows\Temp\VirtualCamera`）通过原生 GigE 枚举能发现，但 `MV_CC_OpenDevice` 报错 `0x80000206`（MV_E_NETER，网络错误）。

原因: 虚拟相机 IP 在 `10.64.x.x` 网段，而主机网卡无同网段 IP，GVCP 广播能发现设备但单播打不开。

错误尝试: 给网卡添加辅助 IP `10.64.52.24/16`，仍无法 ping 通虚拟相机 IP（虚拟设备模拟器绑定在特定虚拟网卡上，与物理网卡不互通）。

正确方案: 通过 **GenTL 虚拟 Producer**（`MvProducerVIR.cti`）直连虚拟相机，完全绕开 IP 网络。

```java
// GenTL 路径: 无需任何 IP 配置即可打开虚拟相机
String cti = "C:\\Program Files (x86)\\Common Files\\MVS\\Runtime\\Win64_x64\\MvProducerVIR.cti";
ArrayList<MV_GENTL_IF_INFO> ifs = MvCameraControl.MV_CC_EnumInterfacesByGenTL(cti);
for (MV_GENTL_IF_INFO inf : ifs) {
    ArrayList<MV_GENTL_DEV_INFO> devs = MvCameraControl.MV_CC_EnumDevicesByGenTL(inf);
    // 选中后创建 Handle
    hCamera = MvCameraControl.MV_CC_CreateHandleByGenTL(dev);
}
```

### 3. 旧运行时帧信息字段差异

GenTL 通道下 `MV_FRAME_OUT_INFO` 的 `ExtendWidth` / `ExtendHeight`（新版 int 字段）为 0，旧版运行时仅填充 `width` / `height`（short 字段）。

```java
// 兼容写法
int w = frame.ExtendWidth > 0 ? frame.ExtendWidth : frame.width;
int h = frame.ExtendHeight > 0 ? frame.ExtendHeight : frame.height;
```

### 4. SaveImage API 新旧差异

| API | 宽高字段类型 | 适用版本 |
| --- | --- | --- |
| `MV_CC_SaveImageToFileEx` + `MV_SAVE_IMAGE_TO_FILE_PARAM_EX` | `int` | 新版 |
| `MV_CC_SaveImageToFile` + `MV_SAVE_IMG_TO_FILE_PARAM` | `short` | 旧版 |

9344×7000 在 short 范围内（max 32767），旧 API 可用；更大分辨率需新版 API。

## 实现

### 文件

```text
AutoWeldVisionZulu/
├── libs/
│   └── MvCameraControlWrapper.jar          # 海康 MVS SDK Java 封装(随 MVS 客户端分发)
├── src/main/java/com/autoweld/camera/
│   └── MvsGrabber.java                      # MVS SDK 取图器(双路发现+新旧兼容)
└── utils/mvs-grab/                           # 独立 fatjar 测试工具
    ├── build.gradle
    ├── libs/MvCameraControlWrapper.jar
    └── src/main/java/com/autoweld/utils/mvs/MeasureGrab.java
```

### 关键依赖

```groovy
// build.gradle
dependencies {
    implementation files('libs/MvCameraControlWrapper.jar')
}
```

### 官方示例

MVS 安装目录下自带 Java 示例: `C:\Program Files (x86)\MVS\Development\Samples\Java\`

```powershell
# 查看示例目录
Get-ChildItem "C:\Program Files (x86)\MVS\Development\Samples\Java"
# GetImage     —— 基本取图
# ImageSave    —— 取图+保存文件
# InterfaceDemo —— GenTL 接口枚举

# 查看 wrapper jar 中的类
$jar = "C:\Program Files (x86)\MVS\Development\Samples\Java\Library\MvCameraControlWrapper.jar"
javap -classpath $jar MvCameraControlWrapper.MvCameraControl
```

### 封装代码

**MvsGrabber.java** — 封装 MVS SDK 取图，双路设备发现，新旧运行时兼容:

```java
package com.autoweld.camera;

import com.autoweld.core.Log;

import MvCameraControlWrapper.CameraControlException;
import MvCameraControlWrapper.MvCameraControl;
import MvCameraControlWrapper.MvCameraControlDefines.Handle;
import MvCameraControlWrapper.MvCameraControlDefines.MVCC_INTVALUE;
import MvCameraControlWrapper.MvCameraControlDefines.MV_CC_DEVICE_INFO;
import MvCameraControlWrapper.MvCameraControlDefines.MV_FRAME_OUT_INFO;
import MvCameraControlWrapper.MvCameraControlDefines.MV_GENTL_DEV_INFO;
import MvCameraControlWrapper.MvCameraControlDefines.MV_GENTL_IF_INFO;
import MvCameraControlWrapper.MvCameraControlDefines.MV_SAVE_IMAGE_TO_FILE_PARAM_EX;
import MvCameraControlWrapper.MvCameraControlDefines.MV_SAVE_IMG_TO_FILE_PARAM;
import MvCameraControlWrapper.MvCameraControlDefines.MV_SAVE_IAMGE_TYPE;

import java.io.File;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import static MvCameraControlWrapper.MvCameraControlDefines.MV_GIGE_DEVICE;
import static MvCameraControlWrapper.MvCameraControlDefines.MV_OK;
import static MvCameraControlWrapper.MvCameraControlDefines.MV_USB_DEVICE;
// ... 其他 import 省略

/**
 * MVS SDK 相机取图器.
 *
 * <p>设备发现走两路: ①原生 GigE/USB 枚举(真机); ②GenTL 虚拟 Producer(MvProducerVIR.cti),
 * 虚拟相机走该路径无需 IP 网络配置. 同序列号去重时优先 GenTL 通道.
 *
 * <p>兼容新旧两版 MVS 运行时: 对 MV_CC_Initialize / MV_CC_SaveImageToFileEx 等新版 API
 * 捕获 UnsatisfiedLinkError 自动回退旧版.
 *
 * <p>每个相机序列号对应一个 MvsGrabber 实例(缓存), Handle 保持打开, 多次拍照复用.
 */
public class MvsGrabber implements AutoCloseable {

    public static final class GrabResult {
        public final byte[] jpgBytes;
        public final int width;
        public final int height;
        // 构造省略
    }

    private static final float DEFAULT_EXPOSURE = 35000f;
    private static final int GRAB_TIMEOUT_MS = 15000;

    /** 序列号 → 实例缓存 */
    private static final Map<String, MvsGrabber> CACHE = new ConcurrentHashMap<>();

    public static MvsGrabber getOrCreate(String cameraSn) {
        return CACHE.computeIfAbsent(cameraSn, MvsGrabber::new);
    }

    public static void closeAll() {
        for (MvsGrabber g : CACHE.values()) {
            try { g.close(); } catch (Throwable ignore) {}
        }
        CACHE.clear();
    }

    // ---------------- 拍照 ----------------

    public GrabResult grabJpg(File savePath, int quality) throws Exception {
        init();
        MV_FRAME_OUT_INFO frame = new MV_FRAME_OUT_INFO();
        int nRet = MvCameraControl.MV_CC_GetOneFrameTimeout(
                hCamera, grabBuf, frame, GRAB_TIMEOUT_MS);
        if (nRet != MV_OK) {
            throw new RuntimeException(String.format(
                    Locale.ROOT, "取图失败: 0x%x", nRet));
        }
        // 兼容新旧运行时字段
        int w = frame.ExtendWidth > 0 ? frame.ExtendWidth : frame.width;
        int h = frame.ExtendHeight > 0 ? frame.ExtendHeight : frame.height;
        int dataLen = frame.frameLen > 0 ? frame.frameLen : grabBuf.length;

        if (savePath != null) {
            saveJpeg(savePath, quality, frame, w, h, dataLen);
        }
        // ... 返回 GrabResult
    }

    // ---------------- 惰性初始化 ----------------

    private synchronized void init() throws Exception {
        if (initialized) return;

        // 新版 SDK 显式 Initialize; 旧版无此导出, 捕获后跳过
        try {
            int nRet = MvCameraControl.MV_CC_Initialize();
            if (nRet != MV_OK) throw new RuntimeException("SDK初始化失败");
            hasInitialize = true;
        } catch (UnsatisfiedLinkError e) {
            // 旧版运行时, 加载即初始化
        }

        // 双路枚举设备
        DeviceEntry entry = findDevice();

        // 创建 Handle (GenTL 或原生)
        hCamera = (entry.gentlDev != null)
                ? MvCameraControl.MV_CC_CreateHandleByGenTL(entry.gentlDev)
                : MvCameraControl.MV_CC_CreateHandle(entry.nativeDev);

        MvCameraControl.MV_CC_OpenDevice(hCamera);

        // 关触发 → 连续模式
        MvCameraControl.MV_CC_SetEnumValueByString(hCamera, "TriggerMode", "Off");
        // 关自动曝光 → 固定曝光
        MvCameraControl.MV_CC_SetEnumValueByString(hCamera, "ExposureAuto", "Off");
        MvCameraControl.MV_CC_SetFloatValue(hCamera, "ExposureTime", DEFAULT_EXPOSURE);

        // 分配取图缓冲区
        MVCC_INTVALUE payload = new MVCC_INTVALUE();
        MvCameraControl.MV_CC_GetIntValue(hCamera, "PayloadSize", payload);
        grabBuf = new byte[(int) payload.curValue];

        MvCameraControl.MV_CC_StartGrabbing(hCamera);
        initialized = true;
    }

    // ---------------- 双路设备发现 ----------------

    private DeviceEntry findDevice() {
        List<DeviceEntry> all = new ArrayList<>();

        // ① 原生 GigE/USB 枚举(真机)
        try {
            int layer = MV_GIGE_DEVICE | MV_USB_DEVICE; // | 其他 GenTL 类型
            ArrayList<MV_CC_DEVICE_INFO> list =
                    MvCameraControl.MV_CC_EnumDevices(layer);
            if (list != null) {
                for (MV_CC_DEVICE_INFO d : list) {
                    if (d != null) all.add(new DeviceEntry(d, null));
                }
            }
        } catch (Throwable ignore) {}

        // ② GenTL 虚拟 Producer(虚拟相机, 无需 IP 网络)
        String cti = resolveCtiPath();
        if (cti != null) {
            try {
                ArrayList<MV_GENTL_IF_INFO> ifs =
                        MvCameraControl.MV_CC_EnumInterfacesByGenTL(cti);
                if (ifs != null) {
                    for (MV_GENTL_IF_INFO inf : ifs) {
                        ArrayList<MV_GENTL_DEV_INFO> devs =
                                MvCameraControl.MV_CC_EnumDevicesByGenTL(inf);
                        if (devs == null) continue;
                        for (MV_GENTL_DEV_INFO d : devs) {
                            all.add(new DeviceEntry(null, d));
                        }
                    }
                }
            } catch (Throwable ignore) {}
        }

        // 去重: 同序列号优先 GenTL 通道(原生 GigE 虚拟相机打不开)
        // ... 返回匹配 cameraSn 的设备
    }

    /** 定位 GenTL Producer: MVS 标准安装路径 */
    private String resolveCtiPath() {
        String c86 = System.getenv("CommonProgramFiles(x86)");
        String c = System.getenv("CommonProgramFiles");
        if (c86 != null) {
            String p = c86 + "\\MVS\\Runtime\\Win64_x64\\MvProducerVIR.cti";
            if (new File(p).exists()) return p;
        }
        if (c != null) {
            String p = c + "\\MVS\\Runtime\\Win64_x64\\MvProducerVIR.cti";
            if (new File(p).exists()) return p;
        }
        return null;
    }

    // ---------------- 保存 JPEG(新旧 API 兼容) ----------------

    @SuppressWarnings("deprecation")
    private void saveJpeg(File file, int quality,
            MV_FRAME_OUT_INFO frame, int w, int h, int dataLen) {
        int nRet;
        try {
            // 新版: MV_CC_SaveImageToFileEx (int 宽高)
            MV_SAVE_IMAGE_TO_FILE_PARAM_EX p = new MV_SAVE_IMAGE_TO_FILE_PARAM_EX();
            p.imageType = MV_SAVE_IAMGE_TYPE.MV_Image_Jpeg;
            p.pixelType = frame.pixelType;
            p.width = w;
            p.height = h;
            p.dataLen = dataLen;
            p.data = grabBuf;
            p.methodValue = 1;
            p.jpgQuality = quality;
            p.imagePath = file.getAbsolutePath();
            nRet = MvCameraControl.MV_CC_SaveImageToFileEx(hCamera, p);
        } catch (UnsatisfiedLinkError e) {
            // 旧版: MV_CC_SaveImageToFile (short 宽高)
            MV_SAVE_IMG_TO_FILE_PARAM p = new MV_SAVE_IMG_TO_FILE_PARAM();
            p.imageType = MV_SAVE_IAMGE_TYPE.MV_Image_Jpeg;
            p.pixelType = frame.pixelType;
            p.width = (short) w;
            p.height = (short) h;
            p.dataLen = dataLen;
            p.data = grabBuf;
            p.methodValue = 1;
            p.jpgQuality = quality;
            p.imagePath = file.getAbsolutePath();
            nRet = MvCameraControl.MV_CC_SaveImageToFile(hCamera, p);
        }
        if (nRet != MV_OK) {
            throw new RuntimeException(String.format(
                    Locale.ROOT, "保存JPG失败: 0x%x -> %s", nRet, file));
        }
    }

    @Override
    public void close() {
        if (hCamera != null) {
            try { MvCameraControl.MV_CC_StopGrabbing(hCamera); } catch (Throwable ignore) {}
            try { MvCameraControl.MV_CC_CloseDevice(hCamera); } catch (Throwable ignore) {}
            try { MvCameraControl.MV_CC_DestroyHandle(hCamera); } catch (Throwable ignore) {}
            hCamera = null;
        }
        if (hasInitialize) {
            try { MvCameraControl.MV_CC_Finalize(); } catch (UnsatisfiedLinkError ignore) {}
        }
    }
}
```

### 独立测试工具

**MeasureGrab.java** — 专用 fatjar 命令行工具，不依赖主程序:

```java
// 用法:
//   java -jar mvs-grab.jar -list                    // 枚举设备
//   java -jar mvs-grab.jar -sn Vir75057900 -count 2 // 拍 2 张
//   java -jar mvs-grab.jar -sn DB1021745 -exposure 35000 -out D:/imgs

public final class MeasureGrab {
    public static void main(String[] args) {
        MeasureGrab app = new MeasureGrab();
        if (!app.parseArgs(args)) {
            printUsage();
            System.exit(2);
        }
        System.exit(app.run());
    }

    // 核心流程: Initialize → 枚举(双路) → 选机 → CreateHandle → Open
    //   → SetExposure → GetPayloadSize → StartGrabbing
    //   → GetOneFrameTimeout → SaveImageToFileEx → 循环
    //   → StopGrabbing → Close → Destroy → Finalize
}
```

构建与运行:

```bash
# 构建 fatjar (仓库根目录)
gradlew -p utils/mvs-grab shadowJar
# 产物: utils/mvs-grab/build/libs/mvs-grab.jar

# 枚举设备
java -jar mvs-grab.jar -list

# 虚拟相机拍照(无需 IP 配置, 走 GenTL 通道)
java -jar mvs-grab.jar -sn Vir75057900 -count 2 -interval 1000

# 真机拍照
java -jar mvs-grab.jar -sn DB1021745 -exposure 35000 -quality 95 -out D:/captures
```

### 实测输出

```
MVS SDK 版本: 0x24000000
检测到旧版 MVS 运行时(无 MV_CC_Initialize), 跳过显式初始化。
发现 3 台设备:
  [0] 通道=GenTL:Virtual GigE Device 型号=MV-CH250-90TM-C-NF SN=Vir59302920 IP=-
  [1] 通道=GenTL:Virtual GigE Device 型号=MV-CH250-90TM-C-NF SN=Vir59303255 IP=-
  [2] 通道=GenTL:Virtual GigE Device 型号=MV-CH650-90TC-M58S-NF SN=Vir75057900 IP=-
选中相机[2]: MV-CH650-90TC-M58S-NF / Vir75057900 (SN=Vir75057900, 通道=GenTL:Virtual GigE Device)
打开设备成功。
提示: 设置 GevSCPSPacketSize=8192 返回 0x80000001(忽略)
实际曝光时间: 35000.0us (范围 18.0 ~ 9999872.0)
开始取图(连续模式, 曝光 35000.0us)...
已保存[1/2]: captures/measure_Vir75057900_20260907_144612_123_9344x7000_fn1.jpg
已保存[2/2]: captures/measure_Vir75057900_20260907_144613_456_9344x7000_fn2.jpg
完成: 成功 2/2 张, 输出目录 captures
```

## 设备发现双路对比

| | 原生 GigE/USB 枚举 | GenTL 虚拟 Producer |
| --- | --- | --- |
| API | `MV_CC_EnumDevices(layerType)` | `MV_CC_EnumInterfacesByGenTL(cti)` → `MV_CC_EnumDevicesByGenTL(ifInfo)` |
| 适用 | 真机（GigE/USB3） | 虚拟相机（Vir*） |
| 网络要求 | GigE 需同网段 IP | 无需 IP 配置 |
| CreateHandle | `MV_CC_CreateHandle(nativeDev)` | `MV_CC_CreateHandleByGenTL(gentlDev)` |
| OpenDevice | 真机正常 | 虚拟相机正常（原生 GigE 报 0x80000206） |

**去重策略**: 虚拟相机同时出现在两路枚举中，同序列号时保留 GenTL 通道（原生通道打不开）。

## 新旧运行时 API 对照

| 功能 | 新版 API | 旧版 API | 处理方式 |
| --- | --- | --- | --- |
| SDK 初始化 | `MV_CC_Initialize()` | 无（加载即初始化） | try-catch `UnsatisfiedLinkError` |
| SDK 释放 | `MV_CC_Finalize()` | 无 | try-catch `UnsatisfiedLinkError` |
| 保存 JPEG | `MV_CC_SaveImageToFileEx` + `MV_SAVE_IMAGE_TO_FILE_PARAM_EX` (int 宽高) | `MV_CC_SaveImageToFile` + `MV_SAVE_IMG_TO_FILE_PARAM` (short 宽高) | try-catch 回退 |
| 帧宽高 | `ExtendWidth` / `ExtendHeight` (int) | `width` / `height` (short) | 先取 Extend，为 0 回退 width |

**如何判断旧版运行时**: `javap` 查看 DLL 导出符号数，旧版约 62 个，新版更多。或直接调用 `MV_CC_Initialize()`，抛 `UnsatisfiedLinkError` 即旧版。

## 传感器分辨率验证

虚拟相机型号模板存于 `C:\ProgramData\MVS\VirtualCamera\`，每个型号目录下有 `*_regfile.dat`（ASCII 文本，每行 `<十六进制地址> <十进制值>`）。传感器分辨率在寄存器 `0x30310`（Width）和 `0x30314`（Height）。

```powershell
# 查看所有模板的传感器分辨率
Get-ChildItem "C:\ProgramData\MVS\VirtualCamera" -Directory | ForEach-Object {
    $dat = Get-ChildItem $_.FullName -Filter "*_regfile.dat" | Select-Object -First 1
    $w = 0; $h = 0
    foreach ($line in [System.IO.File]::ReadAllLines($dat.FullName)) {
        $t = $line.Trim() -split '\s+'
        if ($t[0] -eq '30310') { $w = [int]$t[1] }
        if ($t[0] -eq '30314') { $h = [int]$t[1] }
    }
    [PSCustomObject]@{ Model = $_.Name; W = $w; H = $h }
} | Sort-Object W -Descending | Format-Table -AutoSize
```

匹配项目需求的型号:

| 分辨率需求 | 型号 |
| --- | --- |
| 9344×7000（测量工站） | MV-CH650-90TC-M58S-NF |
| 5120×5120（定位/焊接工站） | MV-CH250-90TM-C-NF / MV-CH250-90VM |

## 总结

1. **Java 调用 MVS SDK 完全可行**: `MvCameraControlWrapper.jar` 封装了全部 JNI 调用，Java 侧无需 JNA/子进程桥接
2. **虚拟相机走 GenTL 通道**: 原生 GigE 枚举能发现但打不开，GenTL Producer（`MvProducerVIR.cti`）才是正确路径
3. **新旧运行时兼容**: 对 `UnsatisfiedLinkError` 做 try-catch 回退，一套代码兼容新旧 MVS
4. **fatjar 打包**: wrapper jar 中的 Java 类打进 fatjar，原生 DLL 由本机 MVS 运行时提供（PATH 已配置）
5. **实际项目集成**: 在 AutoWeldVisionZulu 的"存图模式"中集成 `MvsGrabber`，PLC 触发后拍照存图、强制 OK、走完整数据链路
