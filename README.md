# AutoWeldVisionZulu

自动焊接视觉定位与测量系统。基于 Java + OpenCV(JavaCV) 实现焊点定位与尺寸测量，对接西门子 S7 PLC 完成握手触发与结果回写，并提供 Swing 桌面端管理界面与内置 HMI 网页。

Automatic welding vision positioning and measurement system. Based on Java + OpenCV (JavaCV), it performs weld-spot locating and dimension measurement, connects to a Siemens S7 PLC for handshake triggering and result write-back, and provides a Swing desktop management UI plus a built-in HMI web page.

当前版本 / Current version：`26.9.7`

## 功能特性 / Features

- **焊点定位**（整件-支架焊接 / 电磁-磁保持 / 电磁-单稳态）：粗定位 + 左右角点精定位，输出 8 个焊点世界坐标 / **Weld-spot locating** (assembly-bracket welding / electromagnet-latching / electromagnet-mono-stable): coarse locating + left/right corner refinement, outputs 8 weld-spot world coordinates
- **尺寸测量**（整件-尺寸测量）：四角顶点定位 + 边缘卡尺，输出高度、宽度、对称度 / **Dimension measurement** (assembly-dimension measurement): four-corner vertex locating + edge calipers, outputs height, width, and symmetry
- **工位与相机一对多**：一个工位对应多个相机，启动时仅运行所选工位的相机 / **One-to-many station/camera**: one station maps to multiple cameras; only the cameras of the selected station run at startup
- **配方管理**：按工站/工位独立配方，支持配方号排序、名称搜索、工位过滤 / **Recipe management**: independent recipes per station/position, with recipe-number sorting, name search, and station filtering
- **PLC S7 通讯**：心跳翻转、触发上升沿、作业号切换配方、X/Y 结果回写 / **PLC S7 communication**: heartbeat toggling, trigger rising edge, recipe switching by job number, X/Y result write-back
- **多机台支持**：4 个机台共用同一软件实例，统一配置文件 / **Multi-machine support**: 4 machines share one software instance with a unified config file
- **配置自动记忆**：机台/工位/配方选择持久化到 `autoweld-vision.config.json`，开机自动恢复并启动 / **Auto config memory**: machine/station/recipe selection persisted to `autoweld-vision.config.json`, auto-restored and auto-started on boot
- **内置 HMI 网页**：每相机一个端口，浏览器实时查看图像与结果 / **Built-in HMI web page**: one port per camera; view images and results live in a browser
- **运行模式切换**（运行 → 模式选择器）：带料模式（正常生产）/ 空跑模式（屏蔽取图与视觉，仅验证 PLC 触发 → 结果保存链路）/ 存图模式（在空跑基础上用 MVS SDK 拍照存图，结果强制 OK，验证相机取图链路）/ 测试模式（测试管理器提供图片源，跑视觉+MQTT，忽略PLC）/ **Run mode switching** (Run → Mode Selector): material mode (normal production) / dry-run mode (capture and vision bypassed, only validating the PLC trigger → result-save chain) / capture mode (takes and saves images with the MVS SDK on top of dry-run, result forced OK, validating the camera capture chain) / test mode (image source from Test Manager, runs vision + MQTT, ignores PLC)
- **点检管理器**（运行 → 点检管理器）：一键 OK 点检（参考图应判 OK）/ NG 点检（黑屏图应判 NG），自动跑视觉管线并回显渲染图 / **Check Manager** (Run → Check Manager): one-click OK check (reference image should be judged OK) / NG check (black image should be judged NG), automatically runs the vision pipeline and shows the rendered image
- **视觉流程脚本编辑器**（机器视觉 → 视觉流程脚本编辑器）：按配方+流程编写 JavaScript 视觉脚本（QuickJS），内置找线/找圆/模板匹配等工具与示例模板，支持测试图运行预览、ROI 代码生成、脚本存入配方；流程下拉框按工站类型区分（测量：面1～面4，定位：正面/背面）/ **Vision flow script editor** (Machine Vision → Vision Flow Script Editor): write JavaScript vision scripts (QuickJS) per recipe + flow, with built-in tools (line/circle/template matching) and sample templates, supporting test-image run preview, ROI code generation, and saving scripts into recipes; the flow dropdown differs by station type (measure: surface 1–4, locate: front/back)
- **界面图标化**：Swing 界面集成 Ikonli（FontAwesome 5）矢量图标，菜单、按钮、说明文本统一美化 / **Iconified UI**: Swing UI integrates Ikonli (FontAwesome 5) vector icons; menus, buttons, and descriptive text are uniformly beautified
- **自检模式**：`--selftest` 用参考图跑定位+测量管线并输出渲染图 / **Self-test mode**: `--selftest` runs the locate + measure pipelines with reference images and outputs rendered images

## 机台 / 工站 / 相机 / PLC的ip / Machines / Stations / Cameras / PLC IPs

| 机台 Machine | 工位 Station | 相机 Camera | 序列号 Serial No. | DB号 DB No. | 配方数 Recipes | PLC的ip PLC IP |
| --- | --- | --- | --- | --- | --- | --- |
| 整件-尺寸测量 Assembly-Dimension Measurement | 测量 Measure | 测量 Measure | DB1021745 | 97 | 17 | 192.168.1.110 |
| 整件-支架焊接 Assembly-Bracket Welding | 左 Left | 左左 Left-Left | DA9339941 | 92 | 5 |  192.168.1.70 |
|  |  | 左右 Left-Right | DA8432642 | 97 | 5 |  192.168.1.70 |
|  | 右 Right | 右左 Right-Left | DA9340129 | 98 | 8 |  192.168.1.70 |
|  |  | 右右 Right-Right | DA9339926 | 93 | 8 |  192.168.1.70 |
| 电磁-磁保持 Electromagnet-Latching | 左 Left | 左 Left | DA9339921 | 92 | 4 |  192.168.1.10 |
|  | 右 Right | 右 Right | DA9340145 | 93 | 4 |  192.168.1.10 |
| 电磁-单稳态 Electromagnet-Mono-stable | 左 Left | 左 Left | DA9339917 | 92 | 5 |  192.168.1.10 |
|  | 右 Right | 右 Right | DA9340113 | 93 | 5 |  192.168.1.10 |

- 定位/焊接类相机分辨率：5120×5120；测量类相机分辨率：9344×7000 / Locating/welding camera resolution: 5120×5120; measurement camera resolution: 9344×7000
- 工站 ID：1=单稳态，2=磁保持，3=支架焊接，4=尺寸测量 / Station ID: 1=mono-stable, 2=latching, 3=bracket welding, 4=dimension measurement

## 技术栈 / Tech Stack

| 类别 Category | 技术 Technology |
| --- | --- |
| 语言 Language | Java 25 |
| 构建 Build | Gradle 9 + Shadow Plugin (fatjar) |
| 视觉 Vision | OpenCV 4.10 (JavaCV 1.5.11) |
| PLC | s7connector 2.1 (Siemens S7) |
| 界面 UI | Swing + FlatLaf + Ikonli |
| JSON | Gson 2.11 |
| MQTT | Eclipse Paho 1.2.5 |
| 相机 SDK Camera SDK | 海康 MVS (MvCameraControlWrapper.jar) / Hikrobot MVS (MvCameraControlWrapper.jar) |
| 脚本 Scripting | QuickJS (cn.net.zhijian.quickjs 0.2.2) |
| 代码编辑 Code editing | RSyntaxTextArea 3.5.4 |

## 环境要求 / Requirements

- JDK 25
- Windows x86_64（OpenCV / VisionMaster 原生依赖）/ Windows x86_64 (OpenCV / VisionMaster native dependencies)
- VisionMaster 平台（使用 `vm` 相机类型或存图模式时需安装 MVS 客户端，提供 `MvCameraControlWrapper.dll` 运行时与 SDK 取图）/ VisionMaster platform (when using `vm` camera type or capture mode, the MVS client must be installed, providing the `MvCameraControlWrapper.dll` runtime and SDK capture)
- 西门子 PLC（S7-1200/1500，DB 块按约定布局）/ Siemens PLC (S7-1200/1500, DB blocks laid out as agreed)

## 构建与运行 / Build & Run

```bash
# 构建 fatjar / Build fatjar
gradlew shadowJar
# 产物: build/libs/autoweld-vision-1.0.0.jar
```

```bash
# GUI 模式（默认）/ GUI mode (default)
java -jar autoweld-vision-1.0.0.jar

# 后台运行指定工站 / Run a specified station in headless mode
java -jar autoweld-vision-1.0.0.jar --station 3 --headless

# 自检（用参考图跑定位+测量，输出到 selftest-output/）/ Self-test (run locate+measure with reference images, output to selftest-output/)
java -jar autoweld-vision-1.0.0.jar --selftest
```

## 虚拟 PLC（无实物调试）/ Virtual PLC (Debugging Without Hardware)

无真实 PLC 时，可用 Python 模拟一台 S7 主站（服务端），供本软件连接测试 DB 读写：

When there is no real PLC, you can use Python to simulate an S7 master (server) for this software to connect to and test DB read/write:

```bash
pip install python-snap7
python scripts/s7_plc_sim.py                # 监听 0.0.0.0:102，注册 DB92/93/97/98 + 报警 DB11
python scripts/s7_plc_sim.py --demo         # 演示：周期性自动发触发
```

- 脚本为纯 Python S7 服务端（snap7 3.0），**无需 snap7.dll**；默认过程 DB92/93/97/98、报警 DB11，大端 Int16/Real32 编解码与 [DbLayout](src/main/java/com/autoweld/plc/DbLayout.java) 一致。/ The script is a pure-Python S7 server (snap7 3.0), **no snap7.dll required**; default process DBs 92/93/97/98 and alarm DB11, with big-endian Int16/Real32 encoding consistent with [DbLayout](src/main/java/com/autoweld/plc/DbLayout.java).
- 实时监视并打印视觉端写入：心跳(0)、OUT_结果(2, 3=OK/2=NG)、作业号回显(8)、IN_X(10起)/IN_Y(50起)；`auto` 默认开启——视觉写出结果并自清触发位后，模拟 PLC 自动清零结果位，跑通"谁接收谁清0"的完整握手。/ Monitors and prints vision-side writes in real time: heartbeat (0), OUT_Result (2, 3=OK/2=NG), job-number echo (8), IN_X (from 10)/IN_Y (from 50); `auto` is on by default — after the vision side writes the result and clears the trigger bit itself, the simulated PLC auto-clears the result bit, completing the full "whoever receives clears to 0" handshake.
- 交互命令（`help` 查看全部）：`trig <db> [值]` 发触发上升沿、`job <db> <作业号>` 切配方、`alarmid <id> 0/1` 置报警位、`db <db>` hex 查看、`quit` 退出。/ Interactive commands (`help` for all): `trig <db> [value]` sends a trigger rising edge, `job <db> <jobNo>` switches recipe, `alarmid <id> 0/1` sets alarm bits, `db <db>` shows hex dump, `quit` exits.

**IP 地址 / IP address**：服务端监听 `0.0.0.0`（本机所有网卡），视觉端默认连 `192.168.1.110:102`，需让该 IP 属于本机：/ The server listens on `0.0.0.0` (all NICs of this machine); the vision side connects to `192.168.1.110:102` by default, so this IP must belong to the local machine:
- 现场直连：给网卡添加该地址 `netsh interface ip add address "以太网" 192.168.1.110 255.255.255.0`；/ On-site direct connection: add that address to the NIC via `netsh interface ip add address "以太网" 192.168.1.110 255.255.255.0`;
- 同机自测：在 通讯→PLC通讯 把 IP 改为 `127.0.0.1`。/ Same-machine self-test: change the IP to `127.0.0.1` in Communication → PLC Communication.

**端口冲突 / Port conflict**：本机若装有西门子 SIMATIC/STEP7，其 `s7oiehsx64` 等服务常已占用 102 端口（脚本启动时会自动探测并提示）。此时可停用该西门子服务，或改用高端口 `python scripts/s7_plc_sim.py --port 1102` 并在 通讯→PLC通讯 把端口同步改为 1102。Windows 绑定 102 端口本身无需管理员。/ If Siemens SIMATIC/STEP7 is installed on this machine, its `s7oiehsx64` and similar services often already occupy port 102 (the script auto-detects and warns on startup). You can stop that Siemens service, or use a high port `python scripts/s7_plc_sim.py --port 1102` and sync the port to 1102 in Communication → PLC Communication. Binding port 102 on Windows requires no administrator rights.

## 虚拟相机（无实物调试）/ Virtual Camera (Debugging Without Hardware)

无真实相机时，可使用 VisionMaster（MVS）自带的虚拟设备工具生成虚拟相机，供本软件以 `vm` 相机类型连接测试取图与视觉流程。以下步骤基于 [海康机器人 MVS 用户手册·添加虚拟设备](file:///C:/Program Files (x86)/MVS/Applications/doc/User_Manual_Chinese/GUID-2148F185-ADF7-4A98-A469-66AE5F133AEF.html)。

When there is no real camera, you can use the virtual device tool bundled with VisionMaster (MVS) to create virtual cameras, and connect with the `vm` camera type to test capture and vision flows. The steps below are based on the [Hikrobot MVS User Manual · Adding Virtual Devices](file:///C:/Program Files (x86)/MVS/Applications/doc/User_Manual_Chinese/GUID-2148F185-ADF7-4A98-A469-66AE5F133AEF.html).

### 添加虚拟相机 / Adding a Virtual Camera

1. 打开 MVS 客户端，通过 **工具 → 虚拟设备** 进入虚拟设备工具。/ Open the MVS client and go to the virtual device tool via **Tools → Virtual Device**.
2. 选择 **虚拟相机** 页面，下拉选择需要的相机 **类型** 和 **型号**。/ Open the **Virtual Camera** page and select the camera **Type** and **Model** from the dropdowns.
3. 单击 **添加虚拟相机**（最多支持 256 个），添加完成后相机显示在已添加列表中。/ Click **Add Virtual Camera** (up to 256 supported); after adding, the camera appears in the added list.
4. 添加完成的虚拟相机自动出现在设备列表的对应接口下：/ Added virtual cameras automatically appear under the corresponding interface in the device list:
   - **U3V 虚拟相机**：在 USB 接口下直接显示并连接。/ **U3V virtual camera**: shown and connectable directly under the USB interface.
   - **网口虚拟相机**：在 GigE 接口下显示并连接；添加网口虚拟采集卡并绑定后也可在 PCIe 接口下显示。/ **GigE virtual camera**: shown and connectable under the GigE interface; also shown under PCIe after adding and binding a GigE virtual frame grabber.
   - **CameraLink/CoaXPress/XoFLink 虚拟相机**：必须先添加对应接口的虚拟采集卡并绑定，才在 PCIe 接口下显示。/ **CameraLink/CoaXPress/XoFLink virtual camera**: must add and bind a virtual frame grabber of the corresponding interface first before it appears under PCIe.
5. 若设备列表未显示，单击对应接口右侧的刷新按钮手动刷新。/ If the device list does not show it, click the refresh button on the right of the corresponding interface to refresh manually.

### 导入图片 / Importing Images

1. 根据虚拟相机名称（形如 `Vir********`），在 `C:\Windows\Temp\VirtualCamera\Cameras\` 路径下找到对应型号的文件夹。/ According to the virtual camera name (like `Vir********`), find the folder of the corresponding model under `C:\Windows\Temp\VirtualCamera\Cameras\`.
2. 根据像素格式需求，将测试图片放入 `Mono`（单色）或 `RGB24`（彩色）文件夹。/ Depending on the pixel format requirement, put test images into the `Mono` (monochrome) or `RGB24` (color) folder.
3. **图片分辨率必须与相机分辨率一致**，否则预览时不显示。/ **The image resolution must match the camera resolution**, otherwise it will not display in preview.

### 设置参数并采集 / Setting Parameters and Acquiring

1. 双击连接虚拟相机。/ Double-click to connect the virtual camera.
2. 通过 **Feature Tree → Image Format Control → Pixel Format** 设置与图片对应的像素格式。/ Set the pixel format matching the image via **Feature Tree → Image Format Control → Pixel Format**.
   - 虚拟相机仅支持设置 **宽度、高度、像素格式**；触发源仅支持 **软触发** 或 **采集卡触发**，其余参数设置后会报错。/ A virtual camera only supports setting **Width, Height, Pixel Format**; the trigger source only supports **Software Trigger** or **Frame Grabber Trigger**; setting other parameters will raise errors.
   - 像素格式与图片路径不一致时图片不显示，需统一设置。/ If the pixel format does not match the image path, the image will not display; keep them consistent.
3. 点击开始采集按钮，对导入的图片进行循环播放。/ Click the Start Acquisition button to loop-play the imported images.

### 添加虚拟采集卡（CameraLink/CoaXPress/XoFLink 虚拟相机需要）/ Adding a Virtual Frame Grabber (Required for CameraLink/CoaXPress/XoFLink Virtual Cameras)

1. 通过 **工具 → 虚拟设备 → 虚拟采集卡** 进入添加页面。/ Go to the add page via **Tools → Virtual Device → Virtual Frame Grabber**.
2. 选择采集卡 **类型** 和 **型号**（型号最后一位数字表示接口数量，即可绑定的虚拟相机数）。/ Select the grabber **Type** and **Model** (the last digit of the model indicates the number of interfaces, i.e. bindable virtual cameras).
3. 单击 **添加虚拟采集卡**（最多 64 个）。/ Click **Add Virtual Frame Grabber** (up to 64 supported).
4. 在已添加列表中通过 **绑定相机** 下拉选择该采集卡下需要枚举的虚拟相机。/ In the added list, select the virtual cameras to be enumerated under this grabber via the **Bind Camera** dropdown.
5. 虚拟采集卡仅支持设置：出图方式（Frame Scan / Line Scan）、触发设置（Stream 触发 / Link Trigger 触发 / 定时器控制，触发源仅软触发或快速软触发）。/ A virtual frame grabber only supports setting: output mode (Frame Scan / Line Scan) and trigger settings (Stream trigger / Link Trigger / timer control; trigger source only software or quick software trigger).
6. 添加完成后在设备列表 PCIe 接口下显示，双击连接后可看到已绑定的虚拟相机。/ After adding, it appears under the PCIe interface in the device list; double-click to connect and see the bound virtual cameras.

### 在本软件中使用虚拟相机 / Using Virtual Cameras in This Software

- 在 **设备 → 相机管理** 中将相机类型设为 `vm`，序列号填写虚拟相机的序列号（Vir 开头）。/ In **Device → Camera Management**, set the camera type to `vm` and enter the virtual camera's serial number (starting with Vir).
- 相机序列号为空时 VisionMaster SDK 取图会降级为文件夹取图，可直接用本地图片测试视觉流程。/ When the camera serial number is empty, VisionMaster SDK capture degrades to folder capture, so you can test vision flows directly with local images.
- 虚拟相机配合空跑模式可完整验证 PLC 触发 → 取图 → 视觉 → MQTT 发布 → 结果回写全链路。/ Virtual cameras combined with dry-run mode fully validate the whole chain: PLC trigger → capture → vision → MQTT publish → result write-back.

## 配置文件 / Configuration Files

### 统一配置：`autoweld-vision.config.json` / Unified Config: `autoweld-vision.config.json`

位于 **jar 同目录**，首次运行自动生成（全新部署只拷一个 jar 即可）。结构：/ Located in the **same directory as the jar**, auto-generated on first run (a fresh deployment only needs the jar copied). Structure:

```json
{
  "selection": { "machine": "整件-支架焊接", "station": "左" },
  "software":  { "defaultScreenIndex": -1, "imageRetentionDays": 0, "runMode": "material" },
  "stations":  [ ... 4 个工站配置 ... ]
}
```

`software.runMode` 运行模式：`material`=带料（正常生产，默认）；`dryRun`=空跑（跳过取图与视觉，模拟 OK 走通 PLC 触发 → 结果保存/回写链路）；`capture`=存图（在空跑基础上用 MVS SDK 拍照存图，结果强制 OK，验证取图链路）；`test`=测试（测试管理器提供图片源，跑视觉+MQTT，忽略 PLC）。模式可由界面"运行 → 模式选择器"切换并即时生效，开机自动恢复。/ `software.runMode` run mode: `material`=material (normal production, default); `dryRun`=dry-run (skip capture and vision, simulate OK through the PLC trigger → result save/write-back chain); `capture`=capture (take and save images with the MVS SDK on top of dry-run, result forced OK, validating the capture chain); `test`=test (image source from Test Manager, runs vision + MQTT, ignores PLC). The mode can be switched in the UI under "Run → Mode Selector" and takes effect immediately; it is auto-restored on boot.

每个工站配置包含：PLC / MQTT 连接参数、flows（相机列表）、配方映射、所选配方号、配方名称、相机备注等。/ Each station config contains: PLC / MQTT connection parameters, flows (camera list), recipe mapping, selected recipe number, recipe name, camera remarks, etc.

**相机取图来源（flows[].cameraType）**：由 `CameraFactory` 按每个流程选择——/ **Camera capture source (flows[].cameraType)**: selected per flow by `CameraFactory` —

| cameraType | 取图方式 Capture Method | 适用 Applicability |
| --- | --- | --- |
| 留空 / `auto`（默认）/ empty / `auto` (default) | 配置了相机序列号即用 **MVS 实时拍照**（`MvsCamera`），否则文件夹取图 / If a camera serial number is configured, use **MVS live capture** (`MvsCamera`); otherwise folder capture | 生产默认 / Production default |
| `mvs` | 海康 MVS SDK 实时拍照（序列号取图，同步 `MV_CC_GetOneFrameTimeout`）/ Hikrobot MVS SDK live capture (by serial number, synchronous `MV_CC_GetOneFrameTimeout`) | 带料生产、强制 MVS / Material production, force MVS |
| `vm` | VisionMaster 平台 SDK（.sol 方案），SDK 不可用/缺方案时降级文件夹 / VisionMaster platform SDK (.sol solution); degrades to folder when SDK unavailable/solution missing | VM 方案、虚拟相机 / VM solutions, virtual cameras |
| `folder` | 循环读 `cameraDir` 静态图（`FolderCamera`）/ Cyclically reads static images from `cameraDir` (`FolderCamera`) | 离线回放/无相机调试 / Offline replay / camera-less debugging |

带料模式与存图模式共用同一套已验证的 MvsGrabber 取图链路（同序列号复用长开 Handle，软件停止时 `MvsGrabber.closeAll()` 统一释放）；曝光由配方"曝光1"字段透传（微秒）。/ Material mode and capture mode share the same validated MvsGrabber capture chain (the long-open Handle is reused per serial number; `MvsGrabber.closeAll()` releases everything when the software stops); exposure is passed through from the recipe's "曝光1" field (in microseconds).

**自动迁移**：旧版 `config/stationN.json` + `config/software.json` 首次启动会自动迁入统一文件，旧文件保留但不再读取。/ **Auto migration**: the legacy `config/stationN.json` + `config/software.json` are automatically migrated into the unified file on first startup; old files are kept but no longer read.

### 配方文件：`recipes/station{N}/{配方号}.json` / Recipe Files: `recipes/station{N}/{recipeNo}.json`

每个配方一个文件，包含曝光、拍照距离、ROI、像素精度、模板图、算法参数（粗定位/精定位/卡尺范围/公差）等，以及可选的 `customVars` 自定义变量（名称/值/类型）。/ One file per recipe, containing exposure, capture distance, ROI, pixel precision, template image, algorithm parameters (coarse/fine locating, caliper range, tolerance), and optional `customVars` custom variables (name/value/type).

`visionScripts` 字段保存视觉流程脚本编辑器编写的 JS 脚本，以流程 ID 为键（字符串）：测量工位键为 `"1"`～`"4"`（对应面1～面4）；定位工位键为 `"1"`（正面）、`"2"`（背面）。键缺失或脚本为空时该流程使用内置硬编码管线。/ The `visionScripts` field stores JS scripts written in the vision flow script editor, keyed by flow ID (string): measurement station keys are `"1"`–`"4"` (corresponding to surfaces 1–4); locating station keys are `"1"` (front) and `"2"` (back). When a key is missing or the script is empty, the flow uses the built-in hard-coded pipeline.

**测量失败默认值**：测量工位的配方含 `defHeightN`/`defWidthN`/`defSymN`（N=1～4，对应变量管理器中的「默认面N高度/宽度/对称度」，均为 float、默认 **1.0**，仅测量工位显示）。当视觉判定失败（NG）或拍照/算法异常时，PLC 与 MQTT 不再发送随机数，而是回发该面配置的默认高度/宽度/对称度，关键点像素坐标置 0；脚本也可用 `GetFloatVar("默认面2高度")` 读取。/ **Default values on measurement failure**: measurement-station recipes contain `defHeightN`/`defWidthN`/`defSymN` (N=1–4, corresponding to the Variable Manager entries "默认面N高度/宽度/对称度", all float, default **1.0**, shown only for the measurement station). When vision judges NG or capture/algorithm errors occur, the PLC and MQTT no longer send random numbers but send back the configured default height/width/symmetry of that surface, with key-point pixel coordinates set to 0; scripts can also read them via `GetFloatVar("默认面2高度")`.

**是否视觉端判断**（`visionJudgesOk`，bool，默认 **false**，仅测量工位）：为 `false` 时视觉端**不做 OK/NG 判定，结果一律强制 OK**，测量数据照常回发，由上位机依据数据自行判定；为 `true` 时才由视觉端按公差判定 OK/NG。脚本可用 `GetBoolVar("是否视觉端判断")` 读取。/ **Whether vision judges** (`visionJudgesOk`, bool, default **false**, measurement station only): when `false`, the vision side **does not judge OK/NG and forces all results to OK**, measurement data is still sent back, and the host PC judges by itself based on the data; only when `true` does the vision side judge OK/NG by tolerance. Scripts can read it via `GetBoolVar("是否视觉端判断")`.

## PLC 通讯点位（DB 布局）/ PLC Communication Points (DB Layout)

所有工站的 DB 块共用基础布局（Int=2 字节大端，Real=4 字节大端 float）：/ All stations' DB blocks share the base layout (Int = 2-byte big-endian, Real = 4-byte big-endian float):

| 偏移 Offset | 长度 Length | 类型 Type | 方向 Direction | 信号 Signal | 说明 Note |
| --- | --- | --- | --- | --- | --- |
| 0 | 2 | Int | IN | IN_通讯心跳 | 视觉每心跳周期翻转一次 / Vision toggles once per heartbeat cycle |
| 2 | 2 | Int | OUT | OUT_结果 | 3=OK, 2=NG, 0=重置 / 3=OK, 2=NG, 0=reset |
| 4 | 2 | Int | OUT | OUT_触发拍照 | 上升沿触发，值=triggerValue 对应流程 / Rising-edge trigger; value = triggerValue for the corresponding flow |
| 6 | 2 | Int | OUT | 传相机作业号 | 非 0 且变化则切换配方 / Switch recipe when non-zero and changed |
| 8 | 2 | Int | IN | 读相机作业号 | 回显当前配方号 / Echo of current recipe number |
| 10 | 40 | Real[10] | IN | IN_X[0..9] | 定位类：焊点 X 坐标 (mm) / Locating: weld-spot X coordinates (mm) |
| 50 | 40 | Real[10] | IN | IN_Y[0..9] | 定位类：焊点 Y 坐标 (mm) / Locating: weld-spot Y coordinates (mm) |

**尺寸测量工位（type=measure）的 X/Y 语义不同** / **The X/Y semantics differ for the dimension-measurement station (type=measure)**:

| 偏移 Offset | 信号 Signal | 含义 Meaning |
| --- | --- | --- |
| 10 | IN_X[0] | 面1(B1)对称度 / Surface 1 (B1) symmetry |
| 14 | IN_X[1] | 面2(A1)对称度 / Surface 2 (A1) symmetry |
| 18 | IN_X[2] | 面3(B2)对称度 / Surface 3 (B2) symmetry |
| 22 | IN_X[3] | 面4(A2)对称度 / Surface 4 (A2) symmetry |
| 26 | IN_X[4] | B面平均对称度 / Average symmetry of B surfaces |
| **30** | **IN_X[5]** | **面1宽度 / Surface 1 width** |
| **34** | **IN_X[6]** | **面2宽度 / Surface 2 width** |
| **38** | **IN_X[7]** | **面3宽度 / Surface 3 width** |
| **42** | **IN_X[8]** | **面4宽度 / Surface 4 width** |
| 50 | IN_Y[0] | 面1高度 / Surface 1 height |
| 54 | IN_Y[1] | 面2高度 / Surface 2 height |
| 58 | IN_Y[2] | 面3高度 / Surface 3 height |
| 62 | IN_Y[3] | 面4高度 / Surface 4 height |
| 66 | IN_Y[4] | A面平均对称度 / Average symmetry of A surfaces |
| 70 | IN_Y[5] | A面平均高度 / Average height of A surfaces |
| 74 | IN_Y[6] | A面平均宽度 / Average width of A surfaces |

握手流程（规则：**谁接收谁清 0**——视觉接收拍照触发，就由视觉清触发位；PLC 接收结果，就由 PLC 清结果位）：/ Handshake flow (rule: **whoever receives clears to 0** — the vision side receives the capture trigger, so it clears the trigger bit; the PLC receives the result, so it clears the result bit):

1. 视觉每 500ms 翻转心跳；/ The vision side toggles the heartbeat every 500 ms;
2. PLC 把 `OUT_触发拍照` 由 0 置为触发值（面号）——视觉 50ms 轮询检测**上升沿**，仅触发一次（处理期间触发位保持非 0，不会重复拍照）；/ The PLC sets `OUT_触发拍照` from 0 to the trigger value (surface number) — the vision side polls every 50 ms for the **rising edge** and triggers only once (during processing the trigger bit stays non-zero, so no repeated capture);
3. 视觉 MVS 拍照 → 机器视觉计算 → 回写 IN_X/IN_Y、面 N 宽度与 `OUT_结果`（3=OK/2=NG）；/ Vision captures via MVS → machine vision computes → writes back IN_X/IN_Y, surface-N width, and `OUT_结果` (3=OK/2=NG);
4. **视觉**在结果就绪后把 `OUT_触发拍照` 清 0（下降沿即告知 PLC 本次完成，PLC 看到时结果已有效）；/ **Vision** clears `OUT_触发拍照` to 0 after the result is ready (the falling edge tells the PLC this cycle is done; by the time the PLC sees it, the result is already valid);
5. **PLC** 读到 `OUT_结果` 并取走数据后，把 `OUT_结果` 清 0，回到待机，等待下一次触发。/ **PLC** reads `OUT_结果`, takes the data, then clears `OUT_结果` to 0, returning to standby and waiting for the next trigger.

## 运行模式与点检 / Run Modes and Checks

### 运行模式（运行 → 模式选择器）/ Run Modes (Run → Mode Selector)

| 模式 Mode | 说明 Note | 取图 Capture | 机器视觉 Vision | 结果 Result | 存图 Save Image | PLC 握手 PLC Handshake |
| --- | --- | --- | --- | --- | --- | --- |
| 带料模式 `material` | 正常生产，完整执行 相机取图 → 机器视觉 → 存图 → 结果回写 / Normal production, full chain: capture → vision → save → write-back | **MVS 实时拍照 / MVS live capture** | 执行 / Executed | 真实判定 / Real judgment | `{ts}_raw.jpg` | `writeResult` |
| 空跑模式 `dryRun` | 无相机/无料时调试，屏蔽取图与视觉 / Debugging without camera/material; capture and vision bypassed | 白图 / White image | 跳过 / Skipped | 强制 OK / Forced OK | 不存图 / Not saved | `writeDryRunMeasure` |
| 存图模式 `capture` | 在空跑基础上用 MVS SDK 拍照存图，验证取图链路 / On top of dry-run, capture and save images with the MVS SDK to validate the capture chain | **MVS SDK 拍照 / MVS SDK capture** | 跳过 / Skipped | 强制 OK / Forced OK | 按面命名 / Named by surface | `writeDryRunMeasure` |
| 测试模式 `test` | 测试管理器提供图片/文件夹，跑视觉+MQTT，忽略PLC / Test Manager provides image/folder, runs vision + MQTT, ignores PLC | 图片文件 / Image files | 执行 / Executed | 真实判定 / Real judgment | 不存图 / Not saved | **忽略 / Ignored** |

空跑模式用于验证 **PLC 触发 → 数据记录（data/records.csv）→ 结果回写 PLC** 整条链路：触发到达后流程不拍照、不跑算法，直接返回模拟 OK 并走 HMI 状态更新、记录落盘、PLC 结果回写。模式为进程级开关，切换即时生效并持久化，工具栏右侧有模式指示（空跑为黄色警告，存图为蓝色相机图标，测试为紫色烧瓶图标）。/ Dry-run mode validates the whole chain **PLC trigger → data record (data/records.csv) → result write-back to PLC**: after the trigger arrives, the flow does not capture or run algorithms but directly returns a simulated OK, going through HMI status update, record persistence, and PLC result write-back. The mode is a process-level switch; switching takes effect immediately and is persisted. There is a mode indicator at the right of the toolbar (dry-run: yellow warning; capture: blue camera icon; test: purple flask icon).

空跑模式下，HMI 画面与 MQTT 图像报文使用一张**对应相机分辨率的全白图**（从流程 `remark` 中解析 `WxH`，如 `9344x7000`），便于在画面上与真实取图直观区分；测量工站的 MQTT 图像报文也携带该全白图的 base64。/ In dry-run mode, the HMI view and MQTT image messages use an **all-white image at the camera resolution** (parsed as `WxH` from the flow `remark`, e.g. `9344x7000`) so it is visually distinct from real captures on the screen; the measurement station's MQTT image message also carries the base64 of this all-white image.

存图模式在空跑基础上，用 [MvsGrabber](src/main/java/com/autoweld/camera/MvsGrabber.java) 调用海康 MVS SDK 以 35000us 曝光拍照，取图后按面号命名存图。设备发现走双路：①原生 GigE/USB 枚举（真机，需网卡同网段）；②GenTL 虚拟 Producer（`MvProducerVIR.cti`，虚拟相机走该路径无需 IP 网络配置）。同序列号去重时优先 GenTL 通道。兼容新旧两版 MVS 运行时（对新版 `MV_CC_Initialize` / `MV_CC_SaveImageToFileEx` 捕获 `UnsatisfiedLinkError` 自动回退旧版 API）。每个相机序列号对应一个 `MvsGrabber` 实例（缓存），Handle 保持打开复用；脱机时 `MvsGrabber.closeAll()` 清理。/ Capture mode, on top of dry-run, uses [MvsGrabber](src/main/java/com/autoweld/camera/MvsGrabber.java) to call the Hikrobot MVS SDK for capture at 35000 µs exposure, saving images named by surface number after capture. Device discovery uses two paths: ① native GigE/USB enumeration (real cameras, NIC must be on the same subnet); ② GenTL virtual Producer (`MvProducerVIR.cti`; virtual cameras need no IP network configuration on this path). When deduplicating by serial number, the GenTL channel is preferred. Compatible with both old and new MVS runtimes (catches `UnsatisfiedLinkError` on new `MV_CC_Initialize` / `MV_CC_SaveImageToFileEx` and falls back to the old API automatically). Each camera serial number corresponds to one cached `MvsGrabber` instance whose Handle stays open for reuse; `MvsGrabber.closeAll()` cleans up when going offline.

测量工位存图命名格式：`D:/CCD图片/{配方号}/{yyyyMMdd}/配方{N}_面{N}_原图_{时间戳}.jpg` 与 `配方{N}_面{N}_渲染图_{时间戳}.jpg`（渲染图与原图内容相同，不跑视觉）。非测量工位按常规命名 `{ts}_raw.jpg` / `{ts}_render.jpg`。/ Measurement-station image naming format: `D:/CCD图片/{recipeNo}/{yyyyMMdd}/配方{N}_面{N}_原图_{timestamp}.jpg` and `配方{N}_面{N}_渲染图_{timestamp}.jpg` (the rendered image has the same content as the raw image; no vision is run). Non-measurement stations use the conventional naming `{ts}_raw.jpg` / `{ts}_render.jpg`.

**整件-尺寸测量（测量工站）空跑/存图握手**：该工站 DB97 内含 面1～面4 四个流程（triggerValue 1～4，对应主画面 面1～面4，HMI 端口 11101～11104）。PLC 先下发作业号切配方，再向拍照位依次写 1→2→3→4 触发各面；每个面流程在空跑/存图模式下主动完成完整握手：① 回复作业号（偏移8 回显，确认切配方）→ ② 主动将拍照位置 0（偏移4）→ ③ 把该面**对称度点 X[N-1]**（偏移 10+(N-1)*4）、**高度点 Y[N-1]**（偏移 50+(N-1)*4）与**宽度点**（偏移 **30+(N-1)*4**，即面1→30、面2→34、面3→38、面4→42）写为面号 N（大端 Real）→ ④ 回复 OK 信号（偏移2 = 3）。带料模式下宽度由 `MeasurePipeline` 实测值写入同一偏移。PLC 侧延时约 200ms 后再触发下一面。空跑/存图模式下网关不再因拍照位下降沿清零 OUT_结果（由流程自行管理握手）。可用虚拟 PLC 的 `seq 97 1` 命令自动跑该序列。/ **Assembly-Dimension Measurement (measurement station) dry-run/capture handshake**: this station's DB97 contains four flows for surfaces 1–4 (triggerValue 1–4, corresponding to the main screen surfaces 1–4 and HMI ports 11101–11104). The PLC first sends the job number to switch recipes, then writes 1→2→3→4 to the trigger address to trigger each surface; each surface flow actively completes the full handshake in dry-run/capture mode: ① reply job number (echo at offset 8, confirming recipe switch) → ② actively clear the trigger address to 0 (offset 4) → ③ write this surface's **symmetry point X[N-1]** (offset 10+(N-1)*4), **height point Y[N-1]** (offset 50+(N-1)*4), and **width point** (offset **30+(N-1)*4**, i.e. surface 1→30, surface 2→34, surface 3→38, surface 4→42) as the surface number N (big-endian Real) → ④ reply OK signal (offset 2 = 3). In material mode, the width is written to the same offset from the `MeasurePipeline` measured value. The PLC side waits about 200 ms before triggering the next surface. In dry-run/capture mode the gateway no longer clears OUT_结果 on the trigger-bit falling edge (the flow manages the handshake itself). You can use the virtual PLC's `seq 97 1` command to run this sequence automatically.

### 测试管理器（运行 → 测试管理器）/ Test Manager (Run → Test Manager)

测试管理器用于在**测试模式**下用本地图片/图片文件夹驱动当前工位的任意流程，跑完整机器视觉链路（含 MQTT 发送），但**忽略 PLC 信号与结果回写**，专门用于离线验证视觉算法与 MQTT 数据链路。/ The Test Manager drives any flow of the current station with local images/image folders in **test mode**, running the full machine-vision chain (including MQTT publishing) while **ignoring PLC signals and result write-back**; it is dedicated to offline validation of vision algorithms and the MQTT data chain.

- **入口**：运行 → 测试管理器（若当前不是测试模式，会提示自动切换）。/ **Entry**: Run → Test Manager (if not currently in test mode, it prompts to auto-switch).
- **流程选择**：下拉框列出当前工位下所有流程（如测量工站的面1～面4）。/ **Flow selection**: the dropdown lists all flows under the current station (e.g. surfaces 1–4 of the measurement station).
- **图像源**：单张图片 或 图片文件夹（自动收集 jpg/jpeg/png/bmp，按文件名排序）。/ **Image source**: a single image or an image folder (jpg/jpeg/png/bmp are collected automatically, sorted by file name).
- **单次运行**：对所选图片（或文件夹内全部图片）依次跑一次视觉，日志区显示每张图的 OK/NG 与结果描述。/ **Single run**: runs vision once for each selected image (or all images in the folder); the log area shows OK/NG and result description for each image.
- **连续运行**：循环跑图片列表，间隔可设（100～60000ms），可随时停止。/ **Continuous run**: loops the image list with a settable interval (100–60000 ms); can be stopped at any time.
- **输出**：每次运行走 `Flow.testTrigger()` → 读取图片 → 跑 `MeasurePipeline`/`LocatePipeline` → 更新 HMI 画面 → 记录 `data/records.csv` → 测量工站发布 MQTT（Image/Data/Log 三类报文）。PLC 触发被屏蔽（`FlowManager.onTrigger` 在测试模式直接 return）。/ **Output**: each run goes through `Flow.testTrigger()` → read image → run `MeasurePipeline`/`LocatePipeline` → update HMI view → record `data/records.csv` → measurement station publishes MQTT (Image/Data/Log message types). PLC triggering is masked (`FlowManager.onTrigger` returns directly in test mode).

### MQTT 数据推送（测量工站）/ MQTT Data Push (Measurement Station)

测量工站每次流程完成后，除回写 PLC 外，还会把 图像 / 测量数据 / 日志 三类 XML 报文发布到 MQTT Broker（默认 `tcp://127.0.0.1:8907`，在 通讯→MQTT通讯 中配置，默认启用），供上位机或 `MQTT数据记录` 工具消费。发布由 [MqttPublisher](src/main/java/com/autoweld/mqtt/MqttPublisher.java) 单线程异步执行，连接失败自动重试且不影响视觉主流程与 PLC 回写。/ After each flow completes, besides writing back to the PLC, the measurement station also publishes three types of XML messages — image / measurement data / logs — to the MQTT broker (default `tcp://127.0.0.1:8907`, configured in Communication → MQTT Communication, enabled by default) for the host PC or the `MQTT数据记录` tool to consume. Publishing is executed asynchronously by [MqttPublisher](src/main/java/com/autoweld/mqtt/MqttPublisher.java) on a single thread; connection failures are retried automatically and do not affect the vision main flow or PLC write-back.

| 主题 Topic | 根元素 Root Element | 说明 Note |
| --- | --- | --- |
| `/autoweld/measure/image/raw` | `ImageMessage` | 图像 JPEG 的 base64（`ImageData`），含 `ProductNumber`/`SurfaceNumber`/`ImageWidth`/`ImageHeight` / base64 of the JPEG image (`ImageData`), with `ProductNumber`/`SurfaceNumber`/`ImageWidth`/`ImageHeight` |
| `/autoweld/measure/data/raw` | `DataMessage` | 测量数据：`ProductHeight`/`ProductWidth`/`Symmetry`，以及以输入点为中心推算的基线端点、左右测量点、顶点坐标 / Measurement data: `ProductHeight`/`ProductWidth`/`Symmetry`, plus baseline endpoints, left/right measurement points, and vertex coordinates derived around the input points |
| `/autoweld/measure/logs/raw` | `LogMessage` | 检测完成日志（`Message`），含 OK/NG 与结果描述 / Inspection-completion log (`Message`), including OK/NG and result description |

XML 格式见上方"XML 消息格式"说明；旧版无根元素的报文会被接收端自动包裹 `<root>` 兼容。/ See the "XML 消息格式" note above for the XML format; legacy messages without a root element are automatically wrapped in `<root>` by the receiver for compatibility.

#### MQTT 订阅端测试脚本 / MQTT Subscriber Test Script

提供 [scripts/mqtt_subscriber.py](scripts/mqtt_subscriber.py)，用于验证视觉软件发布的 MQTT 报文：/ [scripts/mqtt_subscriber.py](scripts/mqtt_subscriber.py) is provided to verify the MQTT messages published by the vision software:

```bash
pip install paho-mqtt
python scripts/mqtt_subscriber.py
python scripts/mqtt_subscriber.py --broker tcp://127.0.0.1:8907
python scripts/mqtt_subscriber.py --prefix autoweld --save-images images/recv --log-recv recv.log
```

- 订阅 `/autoweld/measure/data/raw`、`image/raw`、`logs/raw` 三个主题，实时打印解析后的关键字段（配方号 / 面号 / 高度 / 宽度 / 对称度 / 日志消息）。/ Subscribes to the three topics `/autoweld/measure/data/raw`, `image/raw`, `logs/raw`, printing parsed key fields in real time (recipe number / surface number / height / width / symmetry / log message).
- `--save-images <dir>`：把 `ImageMessage` 的 base64 解码为 jpg 落盘（文件名 `配方_面_时间戳.jpg`）。/ `--save-images <dir>`: decodes the `ImageMessage` base64 to jpg files (file name `配方_面_时间戳.jpg`).
- `--log-recv <file>`：把收到的原始报文追加到文件，便于事后核对。/ `--log-recv <file>`: appends received raw messages to a file for later verification.
- `--broker` / `--prefix`：与软件侧 MQTT 配置保持一致。/ `--broker` / `--prefix`: keep consistent with the software-side MQTT configuration.

### 点检管理器（运行 → 点检管理器）/ Check Manager (Run → Check Manager)

不依赖 PLC / 相机，直接用标准参考图跑机器视觉管线，验证视觉软件逻辑是否正常：/ Independent of PLC / camera, it runs the machine-vision pipeline directly with standard reference images to verify the vision software logic:

- **OK 点检**：读取参考图（`定位参考图.bmp` / `测量参考图.jpg`，优先 jar 同目录，其次 `images/locate`、`images/measure`），跑对应定位/测量管线，期望判定 **OK**。/ **OK check**: reads the reference image (`定位参考图.bmp` / `测量参考图.jpg`, first in the jar's directory, then `images/locate`, `images/measure`), runs the corresponding locate/measure pipeline, and is expected to be judged **OK**.
- **NG 点检**：用同尺寸黑屏图（模拟无料/无目标），跑同一管线，期望粗定位失败、判定 **NG**。/ **NG check**: uses a black image of the same size (simulating no material/no target), runs the same pipeline, and is expected to fail coarse locating and be judged **NG**.

点检在后台线程执行，对话框实时回显渲染图与判定日志，实际结果与期望一致才算"通过"；渲染图同步保存到 `check-output/`。管线类型按当前所选工站自动选择（测量工站用测量管线，其余用定位管线）。/ Checks run on a background thread; the dialog shows the rendered image and judgment log in real time, and it "passes" only when the actual result matches the expectation; rendered images are also saved to `check-output/`. The pipeline type is chosen automatically by the currently selected station (measurement station uses the measure pipeline, others use the locate pipeline).

### 视觉流程脚本编辑器（机器视觉 → 视觉流程脚本编辑器）/ Vision Flow Script Editor (Machine Vision → Vision Flow Script Editor)

为每个配方的每个流程编写 JavaScript 视觉脚本（QuickJS 引擎），脚本保存在配方 JSON 的 `visionScripts` 字段中；流程未保存脚本时使用内置硬编码管线。/ Write JavaScript vision scripts (QuickJS engine) for each flow of each recipe; scripts are saved in the recipe JSON's `visionScripts` field; flows without a saved script use the built-in hard-coded pipeline.

- **配方下拉框**：仅列出当前所选机台所属工站的配方（按配方号升序）。/ **Recipe dropdown**: lists only the recipes of the station the currently selected machine belongs to (ascending by recipe number).
- **流程下拉框按工站类型显示**：/ **Flow dropdown varies by station type**:
  - 测量工位（type=measure）：**面1 / 面2 / 面3 / 面4**（流程 ID = 面号 1～4）；/ Measurement station (type=measure): **Surface 1 / Surface 2 / Surface 3 / Surface 4** (flow ID = surface number 1–4);
  - 定位工位（type=locate）：**正面**（流程 ID=1）/ **背面**（流程 ID=2）。/ Locating station (type=locate): **Front** (flow ID=1) / **Back** (flow ID=2).
  - 选择流程后自动加载该配方该流程已保存的脚本；`on_trigger` 回调内 `this.camera` 自动取该流程配置的相机序列号。/ After selecting a flow, the saved script for that recipe and flow is auto-loaded; inside the `on_trigger` callback, `this.camera` automatically takes the camera serial number configured for that flow.
- **脚本入口（二选一）**：/ **Script entry (choose one)**:
  - `function process(image)`：编辑器"运行测试"入口，`image` 为 `{width, height}`；/ `function process(image)`: the editor's "Run Test" entry; `image` is `{width, height}`;
  - `function on_trigger()`：PLC 触发拍照回调，通过 `Capture(this.camera, 曝光us)` 拍照，拍照后图像自动设为当前工作图像。/ `function on_trigger()`: the PLC capture-trigger callback; captures via `Capture(this.camera, 曝光us)`, and the captured image automatically becomes the current working image.
- **可用工具**：`MakeRect` / `RegionIntersect` / `RegionUnion` / `RegionSubtract` / `DrawRegion`（区域布尔运算，区域可直接作为各工具 ROI）/ `FindLine` / `FindCircle` / `FindVertex` / `EdgeIntersect` / `PointToLine` / `LineToLine` / `TemplateMatch` / `FindBlobs` / `PositionFix` / `DrawLine` / `DrawCircle` / `DrawPoint` / `DrawCross` / `DrawRect` / `DrawText` / `Capture` / `WriteXlsx` / `GetTimeStamp` 等；"模板"下拉框可一键插入各工具的示例脚本。/ **Available tools**: `MakeRect` / `RegionIntersect` / `RegionUnion` / `RegionSubtract` / `DrawRegion` (region boolean ops; regions can be used directly as tool ROIs) / `FindLine` / `FindCircle` / `FindVertex` / `EdgeIntersect` / `PointToLine` / `LineToLine` / `TemplateMatch` / `FindBlobs` / `PositionFix` / `DrawLine` / `DrawCircle` / `DrawPoint` / `DrawCross` / `DrawRect` / `DrawText` / `Capture` / `WriteXlsx` / `GetTimeStamp`, etc.; the "模板" dropdown can insert sample scripts for each tool with one click.
- **标定转换**：`LoadCalib(path)` 加载标定 XML（自动加载配方"标定文件1"字段）、`PixelToWorld(px,py)` / `WorldToPixel(wx,wy)` 像素↔物理坐标转换、`GetPixelPrecision()` 返回像素精度。/ **Calibration transforms**: `LoadCalib(path)` loads a calibration XML (auto-loads the recipe's "标定文件1" field); `PixelToWorld(px,py)` / `WorldToPixel(wx,wy)` convert between pixel and physical coordinates; `GetPixelPrecision()` returns the pixel precision.
- **`process` 返回值**：脚本返回的字典会被发送到 PLC 与 MQTT——测量工站返回 `{ok, message, height, width, symmetry, topPoint, baseLineLeftPoint, baseLineRightPoint, leftPoint, rightPoint, points}`（5 个关键点为 `{x,y}` 像素坐标，对应 MQTT DataMessage 的 TopPoint/BaseLineLeftPoint/BaseLineRightPoint/LeftPoint/RightPoint），定位工站返回 `{ok, message, points:[{x,y,wx,wy}]}`（x/y 像素，wx/wy 物理坐标）。配方中存在该流程脚本时运行时走脚本路径，否则回退内置视觉管线。/ **`process` return value**: the dictionary returned by the script is sent to the PLC and MQTT — the measurement station returns `{ok, message, height, width, symmetry, topPoint, baseLineLeftPoint, baseLineRightPoint, leftPoint, rightPoint, points}` (the 5 key points are `{x,y}` pixel coordinates, corresponding to TopPoint/BaseLineLeftPoint/BaseLineRightPoint/LeftPoint/RightPoint in the MQTT DataMessage); the locating station returns `{ok, message, points:[{x,y,wx,wy}]}` (x/y in pixels, wx/wy in physical coordinates). When the recipe has a script for the flow, the runtime takes the script path; otherwise it falls back to the built-in vision pipeline.
- **变量读写**（对应变量管理器中的**全部字段**，包括固定字段与自定义变量，均存储在配方中）：/ **Variable read/write** (corresponds to **all fields** in the Variable Manager, including fixed fields and custom variables, all stored in the recipe):
  - 固定字段（变量管理器中加粗行）可用**中文名**或**英文名**引用（如 `GetFloatVar("曝光1")` 或 `GetFloatVar("exposure1")`），写入时使用字段固有类型（`type` 参数被忽略）；/ Fixed fields (bold rows in the Variable Manager) can be referenced by **Chinese name** or **English name** (e.g. `GetFloatVar("曝光1")` or `GetFloatVar("exposure1")`); writes use the field's inherent type (the `type` parameter is ignored);
  - 自定义变量按用户定义的变量名引用，`SetVar` 的 `解析类型` 为 `string`/`float`/`int`/`bool`；/ Custom variables are referenced by the user-defined variable name; `SetVar`'s `解析类型` is `string`/`float`/`int`/`bool`;
  - `GetStringVar("变量名")`：以字符串返回，不存在返回 `""`；/ `GetStringVar("变量名")`: returns a string; returns `""` if not present;
  - `GetFloatVar("变量名")`：以浮点数返回，不存在或解析失败返回 `0`；/ `GetFloatVar("变量名")`: returns a float; returns `0` if not present or parsing fails;
  - `GetIntVar("变量名")`：以整数返回（四舍五入），不存在或解析失败返回 `0`；/ `GetIntVar("变量名")`: returns an integer (rounded); returns `0` if not present or parsing fails;
  - `GetBoolVar("变量名")`：以布尔值返回（`"true"`/`"1"`/`"yes"` 为 `true`），否则 `false`；/ `GetBoolVar("变量名")`: returns a boolean (`"true"`/`"1"`/`"yes"` are `true`), otherwise `false`;
  - `SetVar("变量名", "解析类型", "字符串值")`：设置（固定字段写入对应 Recipe 字段；自定义变量不存在则新建）并写回配方文件，返回 `{success, name, value}`。值统一以字符串形式存储，与变量管理器一致。/ `SetVar("变量名", "解析类型", "字符串值")`: sets (fixed fields write to the corresponding Recipe field; custom variables are created if missing) and writes back to the recipe file, returning `{success, name, value}`. Values are uniformly stored as strings, consistent with the Variable Manager.
- **系数变量**：系数管理器的系数文件（`D:/CCD标定/配方N_*/面N.txt`）会在配方加载时自动注入为只读自定义变量（`面1_像素精度`、`面1_高度系数`、`面1_宽度系数`、`面1_对称度系数` 等），脚本可直接 `GetFloatVar("面1_像素精度")` 读取，不在配方中持久化。/ **Coefficient variables**: coefficient files from the Coefficient Manager (`D:/CCD标定/配方N_*/面N.txt`) are automatically injected on recipe load as read-only custom variables (`面1_像素精度`, `面1_高度系数`, `面1_宽度系数`, `面1_对称度系数`, etc.); scripts can read them directly via `GetFloatVar("面1_像素精度")`, and they are not persisted in the recipe.
- **测试与保存**：通过"浏览"选择本地图像（或直接把图片文件拖入测试图片区/ROI 画布），也可用"模板图片"选择 jar 内置参考图（测量配方 1～17、面1～面4），点击"运行测试"在"效果图 / 结果"区回显渲染结果图并在控制台输出日志；右侧 ROI 编辑器为「测试图片 | 效果图 | ROI 画布」三个并排图片区（均为图片浏览控件：标题栏"适合/放大/缩小"按钮、滚轮缩放、鼠标拖动平移、支持拖入图片打开），在 ROI 画布框选区域后会在其下方代码区生成对应工具代码，**不会自动插入脚本**，需用户自行从该代码区复制（Ctrl+C 或"复制代码"按钮）后粘贴到脚本中。ROI 工具栏支持「导入标注/导出标注」X-AnyLabeling（LabelMe 兼容）JSON：仅使用 JSON 的 `imageData`（base64 内嵌图像，忽略 imagePath），导入时内嵌图像自动作为测试图、标注形状（rectangle/line/point/circle/rotation/polygon/linestrip）自动转为 ROI（分辨率不一致时按比例换算），导出时把当前图像与 ROI 写回 JSON。"保存脚本"将脚本写回所选配方+流程（也可另存为 `.js` 文件）。/ **Test & save**: select a local image via "Browse" (or drag an image file directly into the test-image area / ROI canvas); you can also use "模板图片" to choose the jar's built-in reference images (measurement recipes 1–17, surfaces 1–4); click "运行测试" to show the rendered result image in the "效果图 / 结果" area and output logs to the console; the ROI editor on the right has three side-by-side image areas — 「测试图片 | 效果图 | ROI 画布」 (all are image viewer controls: title-bar "适合/放大/缩小" buttons, mouse-wheel zoom, drag-to-pan, drag-in image to open); after selecting a region on the ROI canvas, the corresponding tool code is generated in the code area below it and is **not automatically inserted into the script** — the user must copy it from that code area (Ctrl+C or the "复制代码" button) and paste it into the script. The ROI toolbar supports 「导入标注/导出标注」 X-AnyLabeling (LabelMe-compatible) JSON: only the JSON's `imageData` is used (base64-embedded image; imagePath is ignored); on import, the embedded image automatically becomes the test image and annotation shapes (rectangle/line/point/circle/rotation/polygon/linestrip) are auto-converted to ROIs (scaled proportionally if resolutions differ); on export, the current image and ROIs are written back to JSON. "保存脚本" writes the script back to the selected recipe + flow (it can also be saved as a `.js` file).

## 主要界面 / Main UI

| 菜单 Menu | 功能 Function |
| --- | --- |
| 设备 → 机台&工位 / Device → Machine & Station | 选择机台/工位/配方，保存到配置；工站概要表 / Select machine/station/recipe, save to config; station overview table |
| 设备 → 变量管理器 / Device → Variable Manager | 编辑配方标量字段与自定义变量（string/float/int/bool）/ Edit recipe scalar fields and custom variables (string/float/int/bool) |
| 相机 → 相机设置 / Camera → Camera Settings | 相机参数（取图目录 / .sol 方案 / 序列号 / 备注）/ Camera parameters (capture directory / .sol solution / serial number / remarks) |
| 相机 → 标定管理器 / Camera → Calibration Manager | 标定增删、标定计算、XML 导入导出 / Add/remove calibrations, calibration computation, XML import/export |
| 相机 → 系数管理器 / Camera → Coefficient Manager | 测量工位专用，测量系数浏览/应用/保存（仅测量工位显示）/ Measurement-station only: browse/apply/save measurement coefficients (shown only for the measurement station) |
| 运行 → 联机 / Run → Online | 启动所选工位流程（连机生产），运行中禁用 / Start the selected station's flow (production); disabled while running |
| 运行 → 脱机 / Run → Offline | 停止当前工位流程（断机），脱机时禁用 / Stop the current station's flow (disconnect); disabled while offline |
| 运行 → 点检管理器 / Run → Check Manager | OK/NG 点检，参考图跑视觉管线验证算法逻辑 / OK/NG check; run the vision pipeline with reference images to verify algorithm logic |
| 运行 → 测试管理器 / Run → Test Manager | 测试模式下用图片/文件夹驱动流程跑视觉+MQTT，忽略PLC / In test mode, drive flows with images/folders, run vision + MQTT, ignore PLC |
| 运行 → 模式选择器 / Run → Mode Selector | 切换带料 / 空跑 / 存图 / 测试运行模式 / Switch material / dry-run / capture / test run modes |
| 通讯 → PLC通讯 / Communication → PLC Communication | PLC 连接参数 + 通讯点位表（按工站类型区分）/ PLC connection parameters + communication point table (distinguished by station type) |
| 通讯 → PLC报警监控 / Communication → PLC Alarm Monitor | PLC 报警位实时监控 / Real-time monitoring of PLC alarm bits |
| 通讯 → MQTT通讯 / Communication → MQTT Communication | MQTT 连接参数 / MQTT connection parameters |
| 通讯 → MQTT数据记录 / Communication → MQTT Data Recorder | MQTT 数据实时记录与 xlsx 导出 / Real-time MQTT data recording and xlsx export |
| 机器视觉 → 模板图片 / Machine Vision → Template Images | 模板图管理 / Template image management |
| 机器视觉 → ROI区域编辑器 / Machine Vision → ROI Editor | 编辑配方 ROI（定位角点/测量顶点/边缘卡尺等）/ Edit recipe ROIs (locating corners / measurement vertices / edge calipers, etc.) |
| 机器视觉 → 视觉流程脚本编辑器 / Machine Vision → Vision Flow Script Editor | 编辑流程 JS 脚本（可选，默认使用内置管线）/ Edit flow JS scripts (optional; built-in pipeline used by default) |
| 生产数据 → 图片 / Production Data → Images | 历史存图浏览 / Browse historical saved images |
| 生产数据 → 数据 / Production Data → Data | 历史检测记录浏览与导出 / Browse and export historical inspection records |
| 生产数据 → 日志 / Production Data → Logs | 运行日志查看 / View run logs |
| 软件设置 → 默认显示器 / Software Settings → Default Display | 主界面默认显示器选择 / Choose the default display for the main UI |
| 软件设置 → 存图自动清理 / Software Settings → Auto Image Cleanup | 存图保留天数设置 / Set image retention days |

## 项目结构 / Project Structure

```
AutoWeldVisionZulu/
├── src/main/java/com/autoweld/
│   ├── App.java                 # 入口 (GUI/headless/selftest) / Entry (GUI/headless/selftest)
│   ├── config/                  # 配置: AppConfig(统一配置), StationConfig, SoftwareSettings / Config: AppConfig(unified config), StationConfig, SoftwareSettings
│   ├── core/                    # Log, LocalVar, GlobalVar
│   ├── flow/                    # FlowManager, Flow, FlowResult, RunMode(运行模式), StationCheck(点检) / RunMode(run modes), StationCheck(checks)
│   ├── recipe/                  # Recipe, RecipeManager
│   ├── camera/                  # Camera 接口, MvsCamera(带料实时拍照)/MvsGrabber(MVS SDK), FolderCamera, VisionMasterCamera / Camera interface, MvsCamera(material live capture)/MvsGrabber(MVS SDK), FolderCamera, VisionMasterCamera
│   ├── vision/                  # 管线 LocatePipeline/MeasurePipeline, 工具集 / Pipelines LocatePipeline/MeasurePipeline, tool set
│   ├── plc/                     # S7Client, PlcGateway, DbLayout
│   ├── web/                     # HmiServer (内置网页) / HmiServer (built-in web page)
│   ├── storage/                 # ImageStore, RecordsStore
│   └── ui/                      # MainFrame, ImagePanel, dialogs/(各对话框), theme/(Theme/AppFont/Icons) / dialogs/(dialogs), theme/(Theme/AppFont/Icons)
├── src/main/resources/META-INF/services/  # Ikonli IkonHandler/IkonProvider 合并服务文件 / merged service files
├── config/                      # 旧版工站配置 (首次启动自动迁移) / Legacy station configs (auto-migrated on first startup)
├── recipes/station{N}/          # 配方文件 / Recipe files
├── calib/                       # 标定文件 / Calibration files
├── images/locate|measure/       # 文件夹相机/点检用参考图 / Reference images for folder camera / checks
├── check-output/                # 点检渲染图输出 (ok_render.jpg / ng_render.jpg) / Check rendered-image output
├── selftest-output/             # --selftest 渲染图输出 / --selftest rendered-image output
├── scripts/                     # 辅助脚本 (s7_plc_sim.py 虚拟 S7 PLC 主站; mqtt_subscriber.py MQTT 订阅端) / Helper scripts (s7_plc_sim.py virtual S7 PLC master; mqtt_subscriber.py MQTT subscriber)
├── libs/                        # 本地 jar (Ikonli 图标, QuickJS, Paho, RSyntaxTextArea, MvCameraControlWrapper 等) / Local jars (Ikonli icons, QuickJS, Paho, RSyntaxTextArea, MvCameraControlWrapper, etc.)
└── build.gradle
```

## 开发说明 / Development Notes

- 启动画面最短显示 3 秒并显示加载用时 / The splash screen shows for at least 3 seconds and displays load time
- 所有配置读写加锁 + 原子写，避免并发损坏 / All config reads/writes are locked + atomic writes to avoid concurrent corruption
- 相机序列号为空时 VisionMaster SDK 取图会降级为文件夹取图 / When the camera serial number is empty, VisionMaster SDK capture degrades to folder capture
- 自定义变量仅存储，未参与视觉管线运算，可在脚本中引用 / Custom variables are stored only, not involved in vision pipeline computation, and can be referenced in scripts
- 运行模式为进程级开关（`RunMode.current()`），空跑/存图分支在 `Flow.trigger()` 内于取图前返回（`skipVision()` 统一入口）：空跑生成全白图、存图调用 `MvsGrabber` 拍照，两者均强制 OK 并执行 HMI 更新、`RecordsStore` 记录与 PLC 结果回写 / The run mode is a process-level switch (`RunMode.current()`); the dry-run/capture branches return before capture inside `Flow.trigger()` (unified entry `skipVision()`): dry-run generates an all-white image, capture calls `MvsGrabber` to take a photo; both force OK and perform HMI update, `RecordsStore` recording, and PLC result write-back
- 点检逻辑在 `StationCheck.run(measure, expectOk)`：OK 点检读参考图，NG 点检用同尺寸黑屏图；图像会先缩放到 600px 以内并生成缩放模板 / Check logic is in `StationCheck.run(measure, expectOk)`: OK check reads the reference image, NG check uses a same-size black image; the image is first scaled to within 600 px and a scaled template is generated
- **Ikonli 服务文件注意**：`libs/` 下以 `files()` 本地引入的 ikonli jar 不会被 shadowJar 的 `mergeServiceFiles()` 合并，必须手工维护 `src/main/resources/META-INF/services/org.kordamp.ikonli.IkonHandler` 与 `.IkonProvider`，列出 FontAwesome/MaterialDesign 各 Handler/Provider，否则打包后图标不显示 / **Note on Ikonli service files**: ikonli jars locally included via `files()` under `libs/` are not merged by shadowJar's `mergeServiceFiles()`; you must manually maintain `src/main/resources/META-INF/services/org.kordamp.ikonli.IkonHandler` and `.IkonProvider`, listing each FontAwesome/MaterialDesign Handler/Provider, otherwise icons will not display after packaging
