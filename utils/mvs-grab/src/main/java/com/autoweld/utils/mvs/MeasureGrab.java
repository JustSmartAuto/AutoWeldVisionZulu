package com.autoweld.utils.mvs;

import MvCameraControlWrapper.CameraControlException;
import MvCameraControlWrapper.MvCameraControl;
import MvCameraControlWrapper.MvCameraControlDefines.Handle;
import MvCameraControlWrapper.MvCameraControlDefines.MVCC_FLOATVALUE;
import MvCameraControlWrapper.MvCameraControlDefines.MVCC_INTVALUE;
import MvCameraControlWrapper.MvCameraControlDefines.MV_CC_DEVICE_INFO;
import MvCameraControlWrapper.MvCameraControlDefines.MV_FRAME_OUT_INFO;
import MvCameraControlWrapper.MvCameraControlDefines.MV_GENTL_DEV_INFO;
import MvCameraControlWrapper.MvCameraControlDefines.MV_GENTL_IF_INFO;
import MvCameraControlWrapper.MvCameraControlDefines.MV_SAVE_IMAGE_TO_FILE_PARAM_EX;
import MvCameraControlWrapper.MvCameraControlDefines.MV_SAVE_IMG_TO_FILE_PARAM;
import MvCameraControlWrapper.MvCameraControlDefines.MV_SAVE_IAMGE_TYPE;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

import static MvCameraControlWrapper.MvCameraControlDefines.MV_GENTL_CAMERALINK_DEVICE;
import static MvCameraControlWrapper.MvCameraControlDefines.MV_GENTL_CXP_DEVICE;
import static MvCameraControlWrapper.MvCameraControlDefines.MV_GENTL_GIGE_DEVICE;
import static MvCameraControlWrapper.MvCameraControlDefines.MV_GENTL_XOF_DEVICE;
import static MvCameraControlWrapper.MvCameraControlDefines.MV_GIGE_DEVICE;
import static MvCameraControlWrapper.MvCameraControlDefines.MV_OK;
import static MvCameraControlWrapper.MvCameraControlDefines.MV_USB_DEVICE;

/**
 * 整件-尺寸测量工站 —— MVS SDK 取图测试工具(fatjar)。
 *
 * <p>用途: 不依赖主程序, 直接通过海康 MVS SDK(MvCameraControl) 连接测量相机
 * (型号 MV-CH650-90TC-M58S-NF, 9344×7000; 虚拟相机序列号 Vir75057900),
 * 以固定曝光 35000us 连续模式拍若干张, 存为带时间戳的 JPG, 用于验证 SDK 取图链路。
 *
 * <p>设备发现走两路: ①原生 GigE/USB 枚举(真机, 需网卡同网段);
 * ②GenTL 虚拟 Producer(MvProducerVIR.cti), 虚拟相机走该路径, 无需 IP 网络配置。
 *
 * <p>运行前提: 本机已安装 MVS(运行时目录 C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64
 * 需在 PATH 中, MVS 安装器默认已配置)。兼容新旧两版 MVS 运行时(自动适配
 * MV_CC_Initialize / MV_CC_SaveImageToFileEx 是否存在)。
 *
 * <p>用法:
 * <pre>
 *   java -jar mvs-grab.jar [-list] [-sn &lt;序列号&gt;] [-index &lt;n&gt;]
 *                          [-count &lt;张数&gt;] [-interval &lt;ms&gt;]
 *                          [-exposure &lt;us&gt;] [-quality &lt;50-99&gt;] [-out &lt;目录&gt;]
 *                          [-cti &lt;GenTL cti 路径&gt;]
 * </pre>
 * 不带选择参数时: 仅 1 台设备自动连接; 多台则列出设备并退出(用 -sn/-index 指定)。
 */
public final class MeasureGrab {

    /** 测量工站默认曝光时间(us), 35ms */
    private static final float DEFAULT_EXPOSURE_US = 35000f;
    /** 取图超时(ms), 9344×7000 大图 + JPEG 编码给足余量 */
    private static final int GRAB_TIMEOUT_MS = 15000;
    private static final SimpleDateFormat TS_FMT =
            new SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.ROOT);

    /** 统一表示一路设备(原生 GigE/USB 或 GenTL 虚拟) */
    private static final class DeviceRef {
        final MV_CC_DEVICE_INFO nativeInfo; // 原生 GigE/USB 设备(非 GenTL 时非 null)
        final MV_GENTL_DEV_INFO gentlInfo;  // GenTL 设备(非 null 表示走 CreateHandleByGenTL)
        final String transport;             // GigE / USB3 / GenTL:Virtual GigE ...
        final String model;
        final String name;
        final String sn;
        final String ip;

        DeviceRef(MV_CC_DEVICE_INFO d) {
            this.nativeInfo = d;
            this.gentlInfo = null;
            boolean usb = d.transportLayerType == MV_USB_DEVICE;
            this.transport = typeName(d.transportLayerType);
            this.model = usb ? (d.usb3VInfo != null ? d.usb3VInfo.userDefinedName : "?")
                            : (d.gigEInfo != null ? d.gigEInfo.modelName : "?");
            this.name = usb ? (d.usb3VInfo != null ? d.usb3VInfo.userDefinedName : "?")
                           : (d.gigEInfo != null ? d.gigEInfo.userDefinedName : "?");
            this.sn = usb ? (d.usb3VInfo != null ? d.usb3VInfo.serialNumber : "?")
                         : (d.gigEInfo != null ? d.gigEInfo.serialNumber : "?");
            this.ip = (!usb && d.gigEInfo != null) ? d.gigEInfo.currentIp : "-";
        }

        DeviceRef(MV_GENTL_DEV_INFO d, String transport) {
            this.nativeInfo = null;
            this.gentlInfo = d;
            this.transport = transport;
            this.model = d.modelName;
            this.name = d.userDefinedName;
            this.sn = d.serialNumber;
            this.ip = "-";
        }
    }

    private MeasureGrab() {
    }

    // ---------------- 参数 ----------------
    private boolean listOnly = false;
    private String sn = null;
    private int index = -1;
    private int count = 1;
    private long intervalMs = 1000;
    private float exposureUs = DEFAULT_EXPOSURE_US;
    private int jpgQuality = 95;
    private File outDir = new File("captures");
    private String ctiPath = null;

    public static void main(String[] args) {
        MeasureGrab app = new MeasureGrab();
        if (!app.parseArgs(args)) {
            printUsage();
            System.exit(2);
            return;
        }
        System.exit(app.run());
    }

    private static void printUsage() {
        System.out.println("整件-尺寸测量 MVS SDK 取图测试工具");
        System.out.println("用法: java -jar mvs-grab.jar [选项]");
        System.out.println("  -list               仅枚举设备列表后退出");
        System.out.println("  -sn <序列号>        按序列号选择相机(如 Vir75057900 / DB1021745)");
        System.out.println("  -index <n>          按枚举序号选择相机");
        System.out.println("  -count <张数>       拍照张数, 默认 1");
        System.out.println("  -interval <ms>      多张拍照间隔, 默认 1000ms");
        System.out.println("  -exposure <us>      曝光时间(微秒), 默认 35000");
        System.out.println("  -quality <50-99>    JPEG 质量, 默认 95");
        System.out.println("  -out <目录>         图片输出目录, 默认 ./captures");
        System.out.println("  -cti <路径>         指定 GenTL Producer(默认自动查找 MvProducerVIR.cti)");
    }

    private boolean parseArgs(String[] args) {
        try {
            for (int i = 0; i < args.length; i++) {
                switch (args[i]) {
                    case "-list":
                        listOnly = true;
                        break;
                    case "-sn":
                        sn = args[++i];
                        break;
                    case "-index":
                        index = Integer.parseInt(args[++i]);
                        break;
                    case "-count":
                        count = Integer.parseInt(args[++i]);
                        break;
                    case "-interval":
                        intervalMs = Long.parseLong(args[++i]);
                        break;
                    case "-exposure":
                        exposureUs = Float.parseFloat(args[++i]);
                        break;
                    case "-quality":
                        jpgQuality = Integer.parseInt(args[++i]);
                        break;
                    case "-out":
                        outDir = new File(args[++i]);
                        break;
                    case "-cti":
                        ctiPath = args[++i];
                        break;
                    case "-h":
                    case "--help":
                    case "-help":
                        printUsage();
                        System.exit(0);
                        return false;
                    default:
                        System.err.println("未知参数: " + args[i]);
                        return false;
                }
            }
        } catch (ArrayIndexOutOfBoundsException | NumberFormatException e) {
            System.err.println("参数解析失败: " + e.getMessage());
            return false;
        }
        if (count < 1 || jpgQuality < 50 || jpgQuality > 99 || exposureUs <= 0) {
            System.err.println("参数取值非法(count>=1, quality 50-99, exposure>0)");
            return false;
        }
        return true;
    }

    private int run() {
        System.out.println("MVS SDK 版本: " + MvCameraControl.MV_CC_GetSDKVersion());

        // 新版 SDK(运行时) 需显式 Initialize; 旧版运行时无此导出(加载即初始化),
        // UnsatisfiedLinkError 时按旧版处理。
        boolean hasInit = true;
        int nRet;
        try {
            nRet = MvCameraControl.MV_CC_Initialize();
            if (nRet != MV_OK) {
                System.err.printf(Locale.ROOT, "SDK 初始化失败: 0x%x%n", nRet);
                return 1;
            }
        } catch (UnsatisfiedLinkError e) {
            hasInit = false;
            System.out.println("检测到旧版 MVS 运行时(无 MV_CC_Initialize), 跳过显式初始化。");
        }

        Handle hCamera = null;
        try {
            List<DeviceRef> devices = discoverAll();
            if (devices.isEmpty()) {
                System.err.println("未发现任何相机设备(虚拟相机请确认 MVS 虚拟设备已添加)。");
                return 2;
            }
            printDeviceList(devices);
            if (listOnly) {
                return 0;
            }

            int sel = selectDevice(devices);
            if (sel < 0) {
                System.err.println("未选择相机: 多台设备时请用 -sn <序列号> 或 -index <序号> 指定。");
                return 2;
            }
            DeviceRef dev = devices.get(sel);
            System.out.printf(Locale.ROOT, "选中相机[%d]: %s / %s (SN=%s, 通道=%s)%n",
                    sel, dev.model, dev.name, dev.sn, dev.transport);

            try {
                hCamera = (dev.gentlInfo != null)
                        ? MvCameraControl.MV_CC_CreateHandleByGenTL(dev.gentlInfo)
                        : MvCameraControl.MV_CC_CreateHandle(dev.nativeInfo);
            } catch (CameraControlException e) {
                System.err.println("CreateHandle 失败: " + e);
                return 1;
            }

            nRet = MvCameraControl.MV_CC_OpenDevice(hCamera);
            if (nRet != MV_OK) {
                System.err.printf(Locale.ROOT, "打开设备失败: 0x%x%n", nRet);
                if (dev.gentlInfo == null) {
                    System.err.println("提示: GigE/USB 真机打开失败多为网段不通, 请检查网卡 IP 与相机同网段;");
                    System.err.println("      虚拟相机应走 GenTL 通道(设备列表中通道以 GenTL: 开头)。");
                }
                return 1;
            }
            System.out.println("打开设备成功。");

            configureCamera(hCamera);

            // PayloadSize → 取图缓冲区
            MVCC_INTVALUE payload = new MVCC_INTVALUE();
            nRet = MvCameraControl.MV_CC_GetIntValue(hCamera, "PayloadSize", payload);
            if (nRet != MV_OK || payload.curValue <= 0) {
                System.err.printf(Locale.ROOT, "获取 PayloadSize 失败: 0x%x%n", nRet);
                return 1;
            }
            byte[] buf = new byte[(int) payload.curValue];

            nRet = MvCameraControl.MV_CC_StartGrabbing(hCamera);
            if (nRet != MV_OK) {
                System.err.printf(Locale.ROOT, "StartGrabbing 失败: 0x%x%n", nRet);
                return 1;
            }
            System.out.println("开始取图(连续模式, 曝光 " + exposureUs + "us)...");

            if (!outDir.exists() && !outDir.mkdirs()) {
                System.err.println("输出目录创建失败: " + outDir.getAbsolutePath());
                return 1;
            }

            int ok = 0;
            for (int i = 0; i < count; i++) {
                if (i > 0 && intervalMs > 0) {
                    Thread.sleep(intervalMs);
                }
                MV_FRAME_OUT_INFO frame = new MV_FRAME_OUT_INFO();
                nRet = MvCameraControl.MV_CC_GetOneFrameTimeout(hCamera, buf, frame, GRAB_TIMEOUT_MS);
                if (nRet != MV_OK) {
                    System.err.printf(Locale.ROOT, "第 %d 张取图失败: 0x%x%n", i + 1, nRet);
                    continue;
                }
                String path = saveJpeg(hCamera, buf, frame, dev.sn);
                if (path != null) {
                    ok++;
                    System.out.printf(Locale.ROOT,
                            "已保存[%d/%d]: %s  (%dx%d, frameNum=%d, pixelType=%s)%n",
                            i + 1, count, path, effW(frame), effH(frame),
                            frame.frameNum, frame.pixelType);
                }
            }
            System.out.printf(Locale.ROOT, "完成: 成功 %d/%d 张, 输出目录 %s%n",
                    ok, count, outDir.getAbsolutePath());

            MvCameraControl.MV_CC_StopGrabbing(hCamera);
            return ok > 0 ? 0 : 1;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return 1;
        } finally {
            if (hCamera != null) {
                MvCameraControl.MV_CC_CloseDevice(hCamera);
                MvCameraControl.MV_CC_DestroyHandle(hCamera);
            }
            if (hasInit) {
                try {
                    MvCameraControl.MV_CC_Finalize();
                } catch (UnsatisfiedLinkError ignored) {
                    // 旧版运行时无 Finalize
                }
            }
        }
    }

    /** 两路发现设备: 原生 GigE/USB + GenTL 虚拟 Producer。 */
    private List<DeviceRef> discoverAll() {
        List<DeviceRef> refs = new ArrayList<>();

        // ① 原生 GigE/USB/GenTL-CameraLink/CXP/XoF
        try {
            int layerType = MV_GIGE_DEVICE | MV_USB_DEVICE | MV_GENTL_GIGE_DEVICE
                    | MV_GENTL_CAMERALINK_DEVICE | MV_GENTL_CXP_DEVICE | MV_GENTL_XOF_DEVICE;
            ArrayList<MV_CC_DEVICE_INFO> list = MvCameraControl.MV_CC_EnumDevices(layerType);
            for (MV_CC_DEVICE_INFO d : list) {
                if (d != null) {
                    refs.add(new DeviceRef(d));
                }
            }
        } catch (Throwable t) {
            System.out.println("提示: 原生枚举设备异常(忽略): " + t);
        }

        // ② GenTL 虚拟相机(MvProducerVIR.cti), 虚拟 GigE/USB3 相机不需要 IP 网络
        String cti = resolveCtiPath();
        if (cti != null) {
            try {
                ArrayList<MV_GENTL_IF_INFO> ifs = MvCameraControl.MV_CC_EnumInterfacesByGenTL(cti);
                if (ifs != null) {
                    for (MV_GENTL_IF_INFO inf : ifs) {
                        ArrayList<MV_GENTL_DEV_INFO> devs =
                                MvCameraControl.MV_CC_EnumDevicesByGenTL(inf);
                        if (devs == null) {
                            continue;
                        }
                        for (MV_GENTL_DEV_INFO d : devs) {
                            refs.add(new DeviceRef(d, "GenTL:" + inf.displayName));
                        }
                    }
                }
            } catch (UnsatisfiedLinkError | CameraControlException e) {
                System.out.println("提示: GenTL 虚拟设备枚举不可用(忽略): " + e);
            } catch (Throwable t) {
                System.out.println("提示: GenTL 枚举异常(忽略): " + t);
            }
        } else {
            System.out.println("提示: 未找到 MvProducerVIR.cti, 跳过虚拟相机 GenTL 枚举。");
        }

        // 去重: 虚拟相机同时出现在原生 GigE 与 GenTL(VIR) 两路,
        // 原生通道受网卡网段限制常打不开, 同序列号时保留 GenTL 通道。
        List<String> gentlSns = new ArrayList<>();
        for (DeviceRef r : refs) {
            if (r.gentlInfo != null && r.sn != null) {
                gentlSns.add(r.sn);
            }
        }
        List<DeviceRef> dedup = new ArrayList<>();
        for (DeviceRef r : refs) {
            if (r.gentlInfo == null && r.sn != null && gentlSns.contains(r.sn)) {
                continue;
            }
            dedup.add(r);
        }
        return dedup;
    }

    /** 定位虚拟相机 GenTL Producer: -cti 参数优先, 其次 MVS 标准安装路径。 */
    private String resolveCtiPath() {
        if (ctiPath != null) {
            return new File(ctiPath).exists() ? ctiPath : null;
        }
        List<String> candidates = new ArrayList<>();
        String commonX86 = System.getenv("CommonProgramFiles(x86)");
        String common = System.getenv("CommonProgramFiles");
        if (commonX86 != null) {
            candidates.add(commonX86 + "\\MVS\\Runtime\\Win64_x64\\MvProducerVIR.cti");
        }
        if (common != null) {
            candidates.add(common + "\\MVS\\Runtime\\Win64_x64\\MvProducerVIR.cti");
            candidates.add(common + "\\MVS\\Runtime\\Win32_i86\\MvProducerVIR.cti");
        }
        // 兜底: D 盘工程内常见的便携运行时
        candidates.add("D:\\JustStupid\\autoweld定位与测量_2608202130\\mvs_runtime\\MvProducerVIR.cti");
        candidates.add("D:\\JustStupid\\autoweld定位与测量_2608202130\\dist\\runtime\\MvProducerVIR.cti");
        for (String c : candidates) {
            if (new File(c).exists()) {
                return c;
            }
        }
        return null;
    }

    /** 曝光/触发等参数配置; 非关键项失败仅告警不中止。 */
    private void configureCamera(Handle hCamera) {
        int nRet;

        // GigE 大包传输(虚拟相机/不支持时忽略)
        nRet = MvCameraControl.MV_CC_SetIntValue(hCamera, "GevSCPSPacketSize", 8192);
        if (nRet != MV_OK) {
            System.out.printf(Locale.ROOT, "提示: 设置 GevSCPSPacketSize=8192 返回 0x%x(忽略)%n", nRet);
        }

        // 连续模式(关触发)
        nRet = MvCameraControl.MV_CC_SetEnumValueByString(hCamera, "TriggerMode", "Off");
        if (nRet != MV_OK) {
            System.err.printf(Locale.ROOT, "警告: 关闭触发模式失败: 0x%x%n", nRet);
        }

        // 关自动曝光 → 固定曝光 35000us
        nRet = MvCameraControl.MV_CC_SetEnumValueByString(hCamera, "ExposureAuto", "Off");
        if (nRet != MV_OK) {
            System.err.printf(Locale.ROOT, "警告: 关闭自动曝光返回 0x%x(继续尝试写曝光值)%n", nRet);
        }
        nRet = MvCameraControl.MV_CC_SetFloatValue(hCamera, "ExposureTime", exposureUs);
        if (nRet != MV_OK) {
            System.err.printf(Locale.ROOT, "警告: 设置 ExposureTime=" + exposureUs + "us 失败: 0x%x%n", nRet);
        }

        // 回读确认实际曝光
        MVCC_FLOATVALUE exp = new MVCC_FLOATVALUE();
        nRet = MvCameraControl.MV_CC_GetFloatValue(hCamera, "ExposureTime", exp);
        if (nRet == MV_OK) {
            System.out.printf(Locale.ROOT, "实际曝光时间: %.1fus (范围 %.1f ~ %.1f)%n",
                    exp.curValue, exp.min, exp.max);
        }
    }

    /** 有效帧宽: 新版字段 ExtendWidth 优先, 旧运行时 GenTL 仅填 width(short)。 */
    private static int effW(MV_FRAME_OUT_INFO f) {
        if (f.ExtendWidth > 0) {
            return f.ExtendWidth;
        }
        return f.width > 0 ? f.width : 0;
    }

    private static int effH(MV_FRAME_OUT_INFO f) {
        if (f.ExtendHeight > 0) {
            return f.ExtendHeight;
        }
        return f.height > 0 ? f.height : 0;
    }

    private String saveJpeg(Handle hCamera, byte[] data, MV_FRAME_OUT_INFO frame, String devSn) {
        int w = effW(frame);
        int h = effH(frame);
        int dataLen = frame.frameLen > 0 ? frame.frameLen : data.length;
        String name = String.format(Locale.ROOT, "measure_%s_%s_%dx%d_fn%d.jpg",
                safeName(devSn), TS_FMT.format(new Date()), w, h, frame.frameNum);
        File file = new File(outDir, name);
        String path = file.getAbsolutePath();

        // 优先新版 MV_CC_SaveImageToFileEx(int 宽高); 旧版运行时无此导出时
        // 回退到 MV_CC_SaveImageToFile(short 宽高)。
        int nRet;
        try {
            MV_SAVE_IMAGE_TO_FILE_PARAM_EX p = new MV_SAVE_IMAGE_TO_FILE_PARAM_EX();
            p.imageType = MV_SAVE_IAMGE_TYPE.MV_Image_Jpeg;
            p.pixelType = frame.pixelType;
            p.width = w;
            p.height = h;
            p.dataLen = dataLen;
            p.data = data;
            p.methodValue = 1;
            p.jpgQuality = jpgQuality;
            p.imagePath = path;
            nRet = MvCameraControl.MV_CC_SaveImageToFileEx(hCamera, p);
        } catch (UnsatisfiedLinkError e) {
            MV_SAVE_IMG_TO_FILE_PARAM p = new MV_SAVE_IMG_TO_FILE_PARAM();
            p.imageType = MV_SAVE_IAMGE_TYPE.MV_Image_Jpeg;
            p.pixelType = frame.pixelType;
            p.width = (short) w;
            p.height = (short) h;
            p.dataLen = dataLen;
            p.data = data;
            p.methodValue = 1;
            p.jpgQuality = jpgQuality;
            p.imagePath = path;
            nRet = MvCameraControl.MV_CC_SaveImageToFile(hCamera, p);
        }

        if (nRet != MV_OK) {
            System.err.printf(Locale.ROOT, "保存 JPG 失败: 0x%x -> %s%n", nRet, path);
            return null;
        }
        return path;
    }

    private int selectDevice(List<DeviceRef> devices) {
        if (sn != null) {
            for (int i = 0; i < devices.size(); i++) {
                if (sn.equalsIgnoreCase(devices.get(i).sn)) {
                    return i;
                }
            }
            System.err.println("未找到序列号为 " + sn + " 的相机。");
            return -1;
        }
        if (index >= 0) {
            if (index >= devices.size()) {
                System.err.println("序号越界: " + index + ", 共 " + devices.size() + " 台。");
                return -1;
            }
            return index;
        }
        if (devices.size() == 1) {
            return 0;
        }
        return -1;
    }

    private void printDeviceList(List<DeviceRef> devices) {
        System.out.println("发现 " + devices.size() + " 台设备:");
        for (int i = 0; i < devices.size(); i++) {
            DeviceRef d = devices.get(i);
            System.out.printf(Locale.ROOT, "  [%d] 通道=%s 型号=%s 名称=%s SN=%s IP=%s%n",
                    i, d.transport, d.model, d.name, d.sn, d.ip);
        }
    }

    private static String typeName(int t) {
        switch (t) {
            case MV_GIGE_DEVICE: return "GigE";
            case MV_USB_DEVICE: return "USB3";
            case MV_GENTL_GIGE_DEVICE: return "GenTL-GigE";
            case MV_GENTL_CAMERALINK_DEVICE: return "CameraLink";
            case MV_GENTL_CXP_DEVICE: return "CXP";
            case MV_GENTL_XOF_DEVICE: return "XoF";
            default: return "Unknown(" + t + ")";
        }
    }

    /** 文件名安全化: 去掉路径非法字符 */
    private static String safeName(String s) {
        if (s == null || s.isEmpty()) {
            return "cam";
        }
        return s.replaceAll("[\\\\/:*?\"<>|\\s]", "_");
    }
}
