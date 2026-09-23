# 更新日志 (CHANGELOG)

版本号格式：`YY.M.Patch`（年.月.修订号）。最新版本见 [MainFrame.java](src/main/java/com/autoweld/ui/MainFrame.java) 的 `VERSION` 常量。

## [26.9.8] — 2026-09-08

### 新增
- **带料模式切换为 MVS 实时拍照**：新增 [MvsCamera](src/main/java/com/autoweld/camera/MvsCamera.java)（`Camera` 接口的海康 MVS 实现，薄封装已验证的 `MvsGrabber` 同步取图链路）；[CameraFactory](src/main/java/com/autoweld/camera/CameraFactory.java) 按 `cameraType` 选相机：留空/`auto`（默认）配了相机序列号即走 MVS，`mvs` 强制 MVS，`folder` 离线静态图，`vm` VisionMaster。现有 `config/station*.json` 无需改动即自动使用 MVS 实时相机；配方曝光（`exposure1`，微秒）透传到相机。
- **视觉脚本 `process()` 返回值数据契约**：脚本返回字典自动回写 PLC 与 MQTT——测量类返回 `height/width/symmetry` 及 `topPoint/baseLineLeftPoint/baseLineRightPoint/leftPoint/rightPoint` 关键点；定位类返回 `points:[{x,y,wx,wy}]`（像素+物理坐标）。内置管线与脚本共用同一 `FlowResult` 链路。
- **测量关键点上报**：[FlowResult](src/main/java/com/autoweld/flow/FlowResult.java) 新增产品顶点、基准线左/右点、产品左/右点 5 组坐标，内置测量管线填充真实几何点，随 MQTT `DataMessage`（`TopPointX/Y`、`BaseLineLeft/RightPointX/Y`、`Left/RightPointX/Y`）上报。
- **标定转换脚本函数**：`LoadCalib(path)`、`PixelToWorld(px,py)`、`WorldToPixel(wx,wy)`、`GetPixelPrecision()`，复用 XML 标定矩阵；加载配方时自动加载「标定文件1」。
- **脚本变量读写函数**：`GetStringVar/GetFloatVar/GetIntVar/GetBoolVar("变量名")` 与 `SetVar("变量名","解析类型","字符串值")`，支持变量管理器全部字段（固定字段中/英文名、自定义变量），`SetVar` 即时写回配方。
- **系数管理器联动变量**：系数文件（`D:/CCD标定/配方N_*/面N.txt`）在配方加载时自动注入为只读自定义变量（`面1_像素精度`、`面1_高度系数`、`面1_宽度系数`、`面1_对称度系数` 等），脚本可直接 `GetFloatVar` 读取，变量管理器中只读展示、不持久化。
- **测量失败默认值**：测量工位变量管理器新增「默认面N高度/宽度/对称度」（N=1～4，float，默认 **1.0**，仅测量工位显示）。视觉判定 NG 或拍照/算法异常时，PLC 与 MQTT 回发该面配置的默认值而非随机数，关键点坐标置 0。
- **是否视觉端判断开关**：测量工位变量管理器新增 bool「是否视觉端判断」（`visionJudgesOk`，默认 **false**）。为 `false` 时视觉端不做 OK/NG 判定、结果一律强制 OK，测量数据照常回发，由上位机判定；为 `true` 时恢复视觉公差判定。
- **测量工位完整脚本示例**：脚本编辑器模板新增「测量工位完整示例」——基准线分左右两段查找（避开中间遮挡）、找顶点、找左右线、边缘交点定位基准线端点、点到线距离测高度/宽度、基准线中垂线测左右距离、`abs(左-右)` 得对称度，像素距离乘以系数管理器像素精度换算毫米并按数据契约返回。
- **脚本区域布尔运算**：脚本引擎新增区域（轴对齐矩形集合）API：`MakeRect(x,y,w,h)` 构造区域，`RegionIntersect/RegionUnion/RegionSubtract(a,b)` 做交集/并集/差集，`DrawRegion(region,color,thick)` 绘制。纯 Java 侧矩形精确切割（差集最多切左/右/上/下 4 块），无栅格化误差。`FindLine/FindVertex/FindBlobs/FindCircle` 的 ROI 除 `x,y,w,h` 四数值外可直接传区域对象：找线/找顶点对多块区域分别采点后统一拟合、斑点逐块分析合并、找圆取外接框。典型场景：顶点大搜索区 `RegionSubtract` 中间屏蔽区（剩左右竖带）、两个分离的基线交点搜索区 `RegionUnion` 后一次拟合整条基准线。
- **测量模板对齐真实标注**：「测量工位完整示例」模板改用 `images/measure/配方1/面1.json`（X-AnyLabeling 标注，9344×7000）的真实 ROI——顶点搜索区减屏蔽区、左右竖边与基线交点区并集，并新增「Region 区域布尔运算」函数模板。极性按背光照明设定（产品黑色/背景白色：左线 W2B、右线 B2W、基线 B2W）。
- **配方1测量脚本**：`recipes/station2/1.json` 新增 `visionScripts` 字段，面1～面4 各含完整测量脚本（ROI 来自对应标注文件 `images/measure/配方1/面N.json`），含区域布尔运算、背光极性、像素精度换算、可视化与数据契约返回。
- **脚本编辑器测试图拖入**：测试图片区支持图片文件拖入加载，并与 ROI 编辑器画布并排显示（撤销原独立第二栏）；ROI 编辑器加载/拖入图片同步为测试图源。
- **ROI 编辑器导入/导出 X-AnyLabeling 标注**：工具栏新增「导入标注」「导出标注」按钮，使用 LabelMe 兼容 JSON（Gson 解析/生成）。**仅使用 `imageData`（base64 内嵌图像），不使用 `imagePath`**：导入时从 imageData 解码图像作为测试图（无 imageData 直接报错提示），shapes 自动转换为 ROI；导出时当前图像编码为 PNG base64 写入 imageData、ROI 转为 shapes（imagePath 置空）。形状映射：`rectangle`↔矩形、`line`↔线段、`point`↔点、`circle`↔圆（圆心+圆周点）、`rotation/linestrip/polygon`↔多边形；导入时按标注分辨率与图像实际分辨率比例自动换算坐标。导入的图像写临时文件并走统一测试图加载入口，导入后可直接「运行测试」。

### 改动
- **PLC 握手规则「谁接收谁清0」**：视觉接收拍照触发，结果就绪后由**视觉**把 `OUT_触发拍照` 清 0（[PlcGateway.writeResult/writeDryRunMeasure](src/main/java/com/autoweld/plc/PlcGateway.java)）；PLC 接收结果后由 **PLC** 清 `OUT_结果`，视觉不再在下降沿清结果位。处理期间触发位保持非 0，上升沿仅触发一次，杜绝重复拍照。[scripts/s7_plc_sim.py](scripts/s7_plc_sim.py) 的 auto-ack 同步改为「等视觉清触发后由模拟 PLC 清结果位」。
- **测量结果 PLC 落槽显式化**：`writeResult` 新增 `(db, face, heightMm, widthMm, symMm, xs, ys, ok)` 重载，面 N 对称度→`IN_X[N-1]`、高度→`IN_Y[N-1]`、宽度→偏移 `30+(N-1)*4`，与空跑握手口径一致，修正了非面1宽度错位。
- **MQTT 不再随机伪造测量数据**：`publishMeasure` 新增 `allowRandomCoords` 参数——仅空跑/存图模式随机补坐标；带料/测试/异常模式缺失坐标一律置 0，`ProductHeight/Width/Symmetry` 不再随机兜底（NaN→0）。
- **变量管理器字段全中文**：固定字段显示名改为中文（配方名称、拍照距离、曝光、标定文件、像素精度、粗定位参数、公差等），字段读写逻辑不变；脚本同时支持中/英文名。
- **变量管理器按工站过滤**：测量专用字段（失败默认值、是否视觉端判断）仅在测量工位显示，定位工位自动隐藏。
- **脚本编辑器流程下拉框按工站区分**：测量工位显示「面1～面4」，定位工位显示「正面/背面」。
- **ROI 生成代码不自动插入**：ROI 框选生成的代码只显示在 ROI 代码区，不再自动插入脚本光标位置，由用户自行复制（Ctrl+C 或「复制代码」按钮）粘贴。
- **ROI 编辑器图片浏览控件化**：新增可复用图片浏览控件 [ImageBrowserPanel](src/main/java/com/autoweld/ui/ImageBrowserPanel.java)（标题栏「适合/放大/缩小」按钮、滚轮以鼠标为中心缩放、鼠标拖动平移、图片文件拖入打开、缩放百分比与图像尺寸角标）。ROI 编辑区布局调整为「测试图片 | 效果图 | ROI 画布」三区并排，测试图片区与效果图展示区均使用该控件；运行测试的渲染结果显示在独立效果图区，不再覆盖测试图片，便于对照原图查看效果。
- **版本号**：软件版本与 fatjar 版本统一更新为 `26.9.8`。

### 修复
- **带料模式测量工站四个面拍到同一张旧图**：相机连续取流（TriggerMode=Off）但按 PLC 触发逐面拍照、取图间隔数秒以上，旧帧堆积在 SDK 内部帧队列（30 节点，堆满后新帧被丢弃、队列冻结在旧帧），`GetOneFrameTimeout` 出队的是触发前的陈旧帧（面2～面4 均取到面1 位置的画面）。修复：[MvsGrabber](src/main/java/com/autoweld/camera/MvsGrabber.java) 每次取图前先 `MV_CC_ClearImageBuffer` 清空帧队列，再阻塞等待清缓冲之后新采集的帧，并以帧号（frameNum）兜底识别重复旧帧重试；`grabJpg`/`setExposure` 改为实例级串行，避免 4 个面流程（同一相机序列号共享单例 Handle 与取图缓冲）并发取图互相覆盖。
- **MVS 回调取图像素错位（波纹/「麻花」）**：回调模式下 JNI 图像缓冲与帧头对象被 SDK 内部线程复用，Java 侧无法保证数据与帧头同帧。改为与已验证工具 `utils/mvs-grab` 一致的**同步取图** `MV_CC_GetOneFrameTimeout`（直接写入按 PayloadSize 分配的缓冲并从同一缓冲保存），删除整套回调中转；新增丢包帧重试（最多 3 次），并在取流前加固传输层（`SetImageNodeNum(30)`、GigE 丢包重传、最优包大小，均容错兼容虚拟相机/USB/旧运行时）。

## [26.9.7] — 2026-09-07

### 新增
- **运行菜单**：菜单栏新增「运行」菜单，包含「联机」「脱机」「点检管理器」「模式选择器」。原工具栏启动/停止按钮移入运行菜单并改名为联机/脱机。
- **运行模式（模式选择器）**：支持「带料模式」（正常生产）与「空跑模式」（屏蔽相机取图与机器视觉，仅验证 PLC 触发 → 数据记录 → 结果回写链路）。模式即时生效并持久化到 `software.runMode`，开机自动恢复，工具栏右侧有模式指示。
- **点检管理器**：支持「OK 点检」与「NG 点检」，不依赖 PLC/相机，直接用标准参考图跑视觉管线验证算法逻辑；渲染图保存到 `check-output/`。
- **测量工站 MQTT 数据推送**：测量工站每次流程完成后，除回写 PLC 外，异步发布图像 / 测量数据 / 日志三类 XML 报文到 MQTT Broker（默认 `tcp://127.0.0.1:8907`）。
- **MQTT 订阅端测试脚本**：[scripts/mqtt_subscriber.py](scripts/mqtt_subscriber.py)，订阅并解析测量数据/图像/日志报文，支持图像落盘与原始报文存档。
- **虚拟 S7 PLC 主站**：[scripts/s7_plc_sim.py](scripts/s7_plc_sim.py)，纯 Python S7 服务端，注册 DB92/93/97/98 与报警 DB11，支持自动应答、序列触发（`seq 97 1`）等交互命令。
- **界面图标化**：使用 Ikonli (FontAwesome 5 / MaterialDesign) 为所有菜单、按钮、说明标签添加矢量图标；[Icons.java](src/main/java/com/autoweld/ui/theme/Icons.java) 统一入口。
- **窗口图标回退**：`visionmaster.png` 加载失败时自动回退为 Ikonli 矢量图标，确保窗口与任务栏图标始终可见。

### 改动
- **测量工站扩展为 4 个面**：DB97 承载面1～面4（triggerValue 1～4），对应主画面 面1～面4，HMI 端口 11101～11104。
- **空跑模式握手**：测量工站空跑时，每个面流程主动完成「回复作业号 → 清零拍照位 → 写该面高度/对称度点 = 面号 → 回复 OK」完整握手；空跑模式下网关不再因拍照位下降沿清零 OUT_结果。
- **空跑模式全白图**：空跑时 HMI 画面与 MQTT 图像报文使用对应相机分辨率（从流程 `remark` 解析 `WxH`）的全白图，便于与真实取图区分。
- **依赖本地化**：Ikonli 相关 jar 放入 `libs/`，`build.gradle` 改为本地 `files()` 依赖；手工维护 `META-INF/services/` 下的 Ikonli 服务文件以修复 `mergeServiceFiles()` 不合并本地 jar 的问题。

### 修复
- `visionmaster.png` 文件名拼写错误导致窗口/托盘图标不显示的问题。
- Ikonli 服务文件未合并导致 FontAwesome/MaterialDesign 图标包运行时无法被 ServiceLoader 发现的问题。

## 历史版本

26.9.6 及更早版本为本次迭代前的基线版本，包含机台/工位配置、PLC 通讯、文件夹/VisionMaster 相机取图、定位/测量视觉管线、配方与变量管理、标定与系数管理、报警监控、HMI 网页、数据浏览与日志等基础功能。详细改动未单独记录。
