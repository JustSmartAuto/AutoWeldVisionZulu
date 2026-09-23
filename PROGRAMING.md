# AutoWeldVisionZulu 脚本引擎编程指南

内置 QuickJS JavaScript 引擎, 提供视觉工具函数 + 相机拍照 + 数据导出 + 变量读写, 供脚本调用.

- 脚本语言: JavaScript (ES2017)
- 引擎: QuickJS (cn.net.zhijian.quickjs)
- 编辑器: 机器视觉 → 视觉流程脚本编辑器 (RSyntaxTextArea, JS 语法高亮)

---

## 脚本入口

脚本可定义以下入口函数 (二选一):

### process(image) - 编辑器测试入口

编辑器加载测试图像后自动调用, 适合离线开发调试:

```javascript
function process(image) {
    // image.width  图像宽度(像素)
    // image.height 图像高度(像素)
    print("Image: " + image.width + "x" + image.height)

    // 调用视觉工具...
    var line = FindLine(100, 100, 800, 200, "H", "W2B", 30, 20)
    if (line.found) {
        DrawLine(line.px, line.py, line.px + line.dx * 500, line.py + line.dy * 500, 0x00FF00, 2)
    }

    print("Done")
}
```

### on_trigger() - PLC 触发拍照回调

PLC 发出拍照信号时自动调用, 脚本内通过 `Capture(this.camera, 曝光)` 拍照, 再执行视觉处理:

```javascript
function on_trigger() {
    // this.camera - 当前流程的相机序列号 (由系统自动注入)
    var img = Capture(this.camera, 35000)  // 曝光35000us
    if (!img.found) { print("拍照失败"); return }

    // 拍照后图像已自动设为当前工作图像, 可直接调用视觉工具
    var line = FindLine(100, 100, 800, 200, "H", "W2B", 30, 20)
    if (line.found) {
        DrawLine(line.px, line.py, line.px + line.dx * 500, line.py + line.dy * 500, 0x00FF00, 2)
    }

    // 保存测量数据
    var ts = GetTimeStamp("yyyyMMdd_HHmmss")
    WriteXlsx("D:/CCD图片/结果_" + ts + ".csv", "结果",
        ["时间", "宽度"], [[ts, img.width.toFixed(0)]])
}
```

### 脚本上下文 (this 对象)

在 `on_trigger()` 中, `this` 指向全局对象, 以下属性由系统自动注入:

| 属性 | 类型 | 说明 |
|---|---|---|
| `this.camera` | string | 当前流程的相机序列号 (如 "DA12345") |
| `this.flowId` | number | 当前流程ID (面号) |

---

## process 返回值 (PLC / MQTT 数据契约)

`process(image)` 的返回值(字典/对象)会被运行时解析, 并通过 **PLC 通信管理器**回写到 PLC、通过 **MQTT 通信管理器**发布到 broker. 若无返回值或返回非对象, 则视为结果 `ok=false`.

### 测量工站 (measure)

```javascript
return {
    ok: true,                // 判定结果 (true=OK, false=NG)
    message: "高度合格",      // 结果描述(可选)
    height: 12.34,           // 高度 (mm)
    width: 5.67,             // 宽度 (mm)
    symmetry: 0.12,          // 对称度 (mm)
    // MQTT 上报的关键点像素坐标(均可选, 缺失时由运行时按图像比例补全):
    topPoint: {x: 100, y: 200},              // 产品顶点
    baseLineLeftPoint: {x: 100, y: 500},     // 产品基准线左点
    baseLineRightPoint: {x: 800, y: 500},    // 产品基准线右点
    leftPoint: {x: 100, y: 300},             // 产品左点
    rightPoint: {x: 800, y: 300},            // 产品右点
    points: [                // 可选: 各点像素坐标
        {x: 100, y: 200},
        {x: 300, y: 400}
    ]
}
```

> 关键点也支持扁平字段写法: `topX/topY`, `baseLeftX/baseLeftY`, `baseRightX/baseRightY`, `leftX/leftY`, `rightX/rightY`.
> 若关键点未提供, MQTT 仍会按图像比例生成合理坐标, 但建议脚本显式返回以保证数据准确.

数据流:
- `height` / `width` / `symmetry` → `FlowResult.measureHeight/Width/Sym` → MQTT `DataMessage` 的 ProductHeight/ProductWidth/Symmetry 与 PLC 面N宽度偏移
- `topPoint` / `baseLineLeftPoint` / `baseLineRightPoint` / `leftPoint` / `rightPoint` → MQTT `DataMessage` 的 TopPointX/Y, BaseLineLeftPointX/Y, BaseLineRightPointX/Y, LeftPointX/Y, RightPointX/Y
- `points` → `FlowResult.xs[]/ys[]` → PLC `IN_X/IN_Y` (最多 10 点)

### 定位工站 (locate)

```javascript
return {
    ok: true,
    message: "定位完成",
    points: [
        {x: 100, y: 200, wx: 12.3, wy: 45.6},   // x/y=像素坐标, wx/wy=物理坐标(mm)
        {x: 300, y: 400, wx: 78.9, wy: 12.3}
    ]
}
```

数据流:
- 每个点的 `wx`/`wy` (物理坐标) → `FlowResult.xs[]/ys[]` → PLC `IN_X/IN_Y` (最多 10 点)
- 若点未提供 `wx`/`wy`, 则回退使用 `x`/`y`

> **注意**: 只有在配方中为该流程保存了脚本(`visionScripts`)时, 运行时才会走脚本路径; 否则回退到内置视觉管线. 脚本中的 `Draw*` 绘制会叠加到渲染图并随结果上报到 HMI/MQTT.

---

## 工具函数总览

| 序号 | 函数名 | 说明 |
|---|---|---|
| 0 | `MakeRect` / `RegionIntersect` / `RegionUnion` / `RegionSubtract` / `DrawRegion` | 区域(矩形集合)布尔运算, 可作为各工具 ROI |
| 1 | `FindLine` | 找线工具 (卡尺扫描 + 最小二乘拟合, ROI 支持区域) |
| 2 | `FindCircle` | 找圆工具 (HoughCircles, ROI 支持区域) |
| 3 | `FindVertex` | 找顶点工具 (卡尺扫描首个边缘点, ROI 支持区域) |
| 4 | `EdgeIntersect` | 边缘交点工具 (两线交点) |
| 5 | `PointToLine` | 点到线距离工具 |
| 6 | `LineToLine` | 线到线距离工具 (平行度/距离/交点) |
| 7 | `DrawLine` / `DrawCircle` / `DrawText` / `DrawPoint` / `DrawRect` / `DrawCross` / `DrawRegion` | 几何绘制工具 |
| 8 | `TemplateMatch` | 模板匹配工具 (Canny + matchTemplate) |
| 9 | `FindBlobs` | 斑点工具 (连通域分析, ROI 支持区域) |
| 10 | `PositionFix` | 位置修正工具 (刚体变换偏移) |
| 11 | `Capture` | 相机拍照工具 (指定曝光, 返回图像) |
| 12 | `WriteXlsx` | 数据写入Excel工具 (CSV兼容, Excel可打开) |
| 13 | `GetStringVar` / `GetFloatVar` / `GetIntVar` / `GetBoolVar` / `SetVar` | 变量管理器读写 (固定字段 + 自定义变量 + 系数) |
| 14 | `LoadCalib` / `PixelToWorld` / `WorldToPixel` / `GetPixelPrecision` | 标定转换 (像素坐标 <-> 物理坐标) |

颜色格式: `0xRRGGBB` 数字 或 `"#RRGGBB"` 字符串 (如 `0x00FF00` = 绿色)

---

## 0. 区域布尔运算 - Region

区域是一个或多个轴对齐矩形的集合 (矩形布尔运算结果可能是多块, 例如大矩形减去中间矩形 = 左右两块)。
`FindLine` / `FindVertex` / `FindBlobs` / `FindCircle` 的 ROI 参数除了传统的 `x, y, w, h` 四个数值外,
也可以直接传入区域对象: 找线/找顶点会对区域内每块分别采点后统一拟合, 找斑点对每块分别分析后合并结果,
找圆取区域外接矩形。

```javascript
var region = MakeRect(x, y, w, h)          // 构造区域 (返回 {region:true, count, rects:[...]})
var r1 = RegionIntersect(a, b)             // 交集
var r2 = RegionUnion(a, b)                 // 并集 (分离的多块区域可一起采点/拟合)
var r3 = RegionSubtract(a, b)              // 差集 (典型: 大搜索区 减去 屏蔽区)
DrawRegion(region, 0x00FFFF, 1)            // 绘制区域 (逐块画矩形框, thickness 可省略)
```

| 函数 | 说明 |
|---|---|
| `MakeRect(x, y, w, h)` | 构造矩形区域, 返回区域对象 |
| `RegionIntersect(a, b)` | 两区域交集 (逐对矩形求交) |
| `RegionUnion(a, b)` | 两区域并集 (自动剔除被完全包含的块) |
| `RegionSubtract(a, b)` | 区域差集 a − b (一个矩形被遮挡最多切成 左/右/上/下 4 块) |
| `DrawRegion(region, color, thickness?)` | 在结果图上逐块绘制区域矩形框 |

典型用法 —— 顶点搜索区减去中间屏蔽区, 只在左右两条竖带内找顶点:

```javascript
var vertexRoi = RegionSubtract(
    MakeRect(2100, 3089, 5189, 511),   // 产品顶点搜索区域
    MakeRect(2466, 2978, 4512, 766))   // 屏蔽区
DrawRegion(vertexRoi, 0xFFFFFF, 1)
var vertex = FindVertex(vertexRoi, 20, 80)   // 区域直接作为 ROI
```

典型用法 —— 两个分离的基线交点搜索区取并集, 一次拟合整条基准线:

```javascript
var baseRoi = RegionUnion(MakeRect(1969, 6073, 302, 278),
                          MakeRect(7226, 6122, 176, 176))
var baseLine = FindLine(baseRoi, "V", "W2B", 30, 24, "first", 3)
```

> 说明: 区域布尔在纯 Java 侧按轴对齐矩形精确切割, 无栅格化误差; 并集中残留的重叠块仅重复采点, 不影响最小二乘拟合。

---

## 1. FindLine - 找线工具

在 ROI 内沿卡尺条扫描边缘点, 最小二乘法拟合直线.

```javascript
var r = FindLine(x, y, w, h, scanDir, polarity, threshold, strips, edgeSelect, minPoints)
// 或: FindLine(region, scanDir, polarity, threshold, strips, edgeSelect, minPoints)
//     —— region 为 MakeRect/区域布尔运算结果, 多块区域内分别采点后统一拟合
```

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `x` | number | 必填 | ROI 左上角 X |
| `y` | number | 必填 | ROI 左上角 Y |
| `w` | number | 必填 | ROI 宽度 |
| `h` | number | 必填 | ROI 高度 |
| `scanDir` | string | `"H"` | 扫描方向: `"H"`=水平扫描(找竖直边), `"V"`=垂直扫描(找水平边) |
| `polarity` | string | `"W2B"` | 极性: `"W2B"`=白到黑, `"B2W"`=黑到白 |
| `threshold` | int | `30` | 灰度差阈值 |
| `strips` | int | `20` | 卡尺条数 (越多越密, 耗时越长) |
| `edgeSelect` | string | `"first"` | 边缘选择: `"first"`=首个边缘, `"best"`=最强边缘 |
| `minPoints` | int | `2` | 最少有效点数, 不足则判定失败 |

返回值:

```javascript
{
    found: true,           // 是否找到直线
    px: 256.0,            // 直线起点 X
    py: 128.0,            // 直线起点 Y
    dx: 1.0,              // 方向向量 X (单位化)
    dy: 0.0,              // 方向向量 Y (单位化)
    rms: 0.52,            // 拟合 RMS 误差(像素)
    points: [             // 采到的边缘点列表
        { x: 100, y: 128 },
        { x: 150, y: 129 },
        // ...
    ]
}
```

参考代码:

```javascript
function process(image) {
    // 在 (50,50) 到 (550,250) 的 ROI 内, 水平扫描白到黑边缘
    var line = FindLine(50, 50, 500, 200, "H", "W2B", 30, 20, "first", 2)

    if (line.found) {
        // 绘制找到的直线 (绿色, 延长 200 像素)
        DrawLine(line.px - 200, line.py, line.px + 200, line.py, 0x00FF00, 2)

        // 显示拟合精度和有效点数
        DrawText(10, 30, "RMS=" + line.rms.toFixed(3) + " pts=" + line.points.length, 0xFFFF00, 0.6)

        // 标记起点
        DrawPoint(line.px, line.py, 0xFF0000)
    } else {
        DrawText(10, 30, "Line not found", 0xFF0000, 0.6)
    }
}
```

---

## 2. FindCircle - 找圆工具

在 ROI 内使用 HoughCircles 检测圆形.

```javascript
var r = FindCircle(x, y, w, h, dp, minDist, param1, param2, minRadius, maxRadius)
```

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `x, y, w, h` | number | 必填 | ROI 矩形 |
| `dp` | number | `1.2` | 累加器分辨率与图像分辨率之比 |
| `minDist` | number | ROI 短边/2 | 检测圆心间最小距离 |
| `param1` | number | `100` | Canny 高阈值 |
| `param2` | number | `30` | 累加器阈值 (越小越灵敏) |
| `minRadius` | int | `0` | 最小半径 |
| `maxRadius` | int | `0` | 最大半径 (0=不限) |

返回值:

```javascript
{
    found: true,
    circles: [
        { cx: 300.0, cy: 200.0, radius: 50.0 },
        { cx: 500.0, cy: 300.0, radius: 80.0 },
        // ...
    ]
}
```

参考代码:

```javascript
function process(image) {
    var r = FindCircle(100, 100, 600, 400, 1.2, 100, 100, 30, 20, 200)

    if (r.found) {
        for (var i = 0; i < r.circles.length; i++) {
            var c = r.circles[i]
            // DrawCircle 会自动绘制, 这里补充标注半径
            DrawText(c.cx, c.cy, "R=" + c.radius.toFixed(0), 0x00FF00, 0.5)
        }
        print("Found " + r.circles.length + " circles")
    }
}
```

---

## 3. FindVertex - 找顶点工具

在 ROI 内自上而下扫描, 找首个白到黑边缘点作为顶点.

```javascript
var r = FindVertex(x, y, w, h, threshold, strips)
// 或: FindVertex(region, threshold, strips)  —— region 为 MakeRect/区域布尔运算结果
```

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `x, y, w, h` | number | 必填 | ROI 矩形 |
| `threshold` | int | `20` | 灰度差阈值 |
| `strips` | int | `60` | 扫描条数 |

返回值:

```javascript
{
    found: true,
    x: 256.0,
    y: 50.0,
    points: [
        { x: 100, y: 50 },
        // ...
    ]
}
```

参考代码:

```javascript
function process(image) {
    var v = FindVertex(100, 50, 500, 300, 20, 60)

    if (v.found) {
        DrawCross(v.x, v.y, 0xFF0000, 10)
        DrawText(v.x + 10, v.y - 10,
            "V(" + v.x.toFixed(1) + "," + v.y.toFixed(1) + ")", 0xFFFFFF, 0.5)
    }
}
```

---

## 4. EdgeIntersect - 边缘交点工具

计算两条直线的交点.

```javascript
var r = EdgeIntersect(px1, py1, dx1, dy1, px2, py2, dx2, dy2)
```

| 参数 | 说明 |
|---|---|
| `px1, py1, dx1, dy1` | 第一条直线的起点和方向向量 |
| `px2, py2, dx2, dy2` | 第二条直线的起点和方向向量 |

返回值:

```javascript
{
    found: true,
    x: 256.0,
    y: 128.0
}
```

参考代码:

```javascript
function process(image) {
    // 找两条直线
    var l1 = FindLine(50, 50, 500, 200, "H", "W2B", 30, 20)
    var l2 = FindLine(50, 50, 200, 500, "V", "W2B", 30, 20)

    if (l1.found && l2.found) {
        // 求交点
        var p = EdgeIntersect(l1.px, l1.py, l1.dx, l1.dy,
                              l2.px, l2.py, l2.dx, l2.dy)
        if (p.found) {
            DrawCross(p.x, p.y, 0xFF00FF, 10)
            DrawText(p.x + 10, p.y + 10,
                "Intersect(" + p.x.toFixed(1) + "," + p.y.toFixed(1) + ")", 0xFFFFFF, 0.5)
        }
    }
}
```

---

## 5. PointToLine - 点到线距离工具

计算点到直线的垂直距离.

```javascript
var r = PointToLine(px, py, linePx, linePy, lineDx, lineDy)
```

返回值:

```javascript
{ distance: 15.32 }  // 像素
```

参考代码:

```javascript
function process(image) {
    var line = FindLine(50, 50, 500, 200, "H", "W2B", 30, 20)
    var vertex = FindVertex(100, 50, 500, 300, 20, 60)

    if (line.found && vertex.found) {
        var d = PointToLine(vertex.x, vertex.y, line.px, line.py, line.dx, line.dy)
        DrawText(10, 30, "Distance=" + d.distance.toFixed(2) + "px", 0x00FF00, 0.6)
    }
}
```

---

## 6. LineToLine - 线到线距离工具

计算两条直线的平行度、距离或交点.

```javascript
var r = LineToLine(px1, py1, dx1, dy1, px2, py2, dx2, dy2)
```

返回值 (平行时):

```javascript
{
    parallel: true,
    angleDeg: 0.5,       // 夹角(度)
    distance: 120.0      // 垂直距离(像素)
}
```

返回值 (非平行时):

```javascript
{
    parallel: false,
    angleDeg: 45.0,
    intersect: { x: 256.0, y: 128.0 }
}
```

参考代码:

```javascript
function process(image) {
    var l1 = FindLine(50, 50, 500, 200, "H", "W2B", 30, 20)
    var l2 = FindLine(50, 300, 500, 200, "H", "W2B", 30, 20)

    if (l1.found && l2.found) {
        var r = LineToLine(l1.px, l1.py, l1.dx, l1.dy,
                           l2.px, l2.py, l2.dx, l2.dy)

        if (r.parallel) {
            DrawText(10, 30, "Parallel dist=" + r.distance.toFixed(2)
                + " angle=" + r.angleDeg.toFixed(1), 0x00FF00, 0.6)
        } else if (r.intersect) {
            DrawCross(r.intersect.x, r.intersect.y, 0xFF00FF, 10)
            DrawText(10, 30, "Angle=" + r.angleDeg.toFixed(1), 0xFFFF00, 0.6)
        }
    }
}
```

---

## 7. Draw* - 几何绘制工具

在渲染图上叠加可视化结果. 所有 Draw 函数无返回值.

### DrawLine

```javascript
DrawLine(x1, y1, x2, y2, color, thickness)
```

```javascript
DrawLine(100, 100, 500, 100, 0x00FF00, 2)      // 绿色直线
DrawLine(100, 100, 500, 100, "#FF0000", 3)     // 红色粗线
```

### DrawCircle

```javascript
DrawCircle(cx, cy, radius, color, thickness)
```

```javascript
DrawCircle(256, 256, 50, 0x00FF00, 2)          // 绿色圆
```

### DrawText

```javascript
DrawText(x, y, text, color, scale)
```

```javascript
DrawText(10, 30, "OK", 0xFFFF00, 0.6)          // 黄色文字
DrawText(10, 60, "Score=0.95", "#00FFFF", 0.5) // 青色文字
```

### DrawPoint

```javascript
DrawPoint(x, y, color)
```

```javascript
DrawPoint(256, 128, 0xFF0000)                  // 红色点
```

### DrawRect

```javascript
DrawRect(x, y, w, h, color, thickness)
```

```javascript
DrawRect(100, 100, 200, 150, 0x00FFFF, 1)     // 青色矩形框
```

### DrawCross

```javascript
DrawCross(x, y, color, length)
```

```javascript
DrawCross(256, 128, 0xFF00FF, 10)             // 品红十字
```

### 颜色常量参考

| 颜色 | 0xRRGGBB | 说明 |
|---|---|---|
| 绿 | `0x00FF00` | 默认绘制色 |
| 红 | `0xFF0000` | 标记/错误 |
| 蓝 | `0x0000FF` | |
| 青 | `0x00FFFF` | 找线结果默认色 |
| 黄 | `0xFFFF00` | 文字默认色 |
| 品红 | `0xFF00FF` | 交点默认色 |
| 白 | `0xFFFFFF` | |

---

## 8. TemplateMatch - 模板匹配工具

Canny 边缘 + matchTemplate, 支持角度范围搜索.

```javascript
var r = TemplateMatch(tplX, tplY, tplW, tplH,
                      searchX, searchY, searchW, searchH,
                      angleMin, angleMax, angleStep, minScore)
```

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `tplX, tplY, tplW, tplH` | number | 必填 | 模板 ROI (从原图截取作为模板) |
| `searchX, searchY, searchW, searchH` | number | 必填 | 搜索 ROI |
| `angleMin` | number | `-5` | 最小旋转角度 |
| `angleMax` | number | `5` | 最大旋转角度 |
| `angleStep` | number | `1` | 角度步长 (越小越精, 越慢) |
| `minScore` | number | `0.5` | 最小匹配分数 (0~1) |

返回值:

```javascript
{
    found: true,
    cx: 256.0,       // 匹配中心 X
    cy: 128.0,       // 匹配中心 Y
    angle: 2.0,      // 匹配角度
    score: 0.87     // 匹配分数
}
```

参考代码:

```javascript
function process(image) {
    // 从 (100,100) 截取 80x80 模板, 在 (0,0,800,600) 范围内搜索
    var r = TemplateMatch(100, 100, 80, 80,
                          0, 0, 800, 600,
                          -5, 5, 1, 0.5)

    if (r.found) {
        DrawText(r.cx, r.cy,
            "score=" + r.score.toFixed(2) + " angle=" + r.angle.toFixed(1),
            0x00FF00, 0.5)
    } else {
        DrawText(10, 30, "Not matched", 0xFF0000, 0.6)
    }
}
```

---

## 9. FindBlobs - 斑点工具

二值化 + 连通域分析, 按面积过滤.

```javascript
var r = FindBlobs(x, y, w, h, minArea, maxArea, threshold)
```

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `x, y, w, h` | number | 必填 | ROI 矩形 |
| `minArea` | number | `10` | 最小面积(像素) |
| `maxArea` | number | `1e9` | 最大面积(像素) |
| `threshold` | number | `128` | 二值化阈值 |

返回值:

```javascript
{
    found: true,
    blobs: [
        { cx: 150.0, cy: 200.0, area: 500.0, w: 20.0, h: 25.0 },
        { cx: 300.0, cy: 400.0, area: 1200.0, w: 35.0, h: 40.0 },
        // ...
    ]
}
```

参考代码:

```javascript
function process(image) {
    var r = FindBlobs(0, 0, 1000, 800, 50, 100000, 128)

    if (r.found) {
        for (var i = 0; i < r.blobs.length; i++) {
            var b = r.blobs[i]
            DrawText(b.cx, b.cy, "A=" + b.area.toFixed(0), 0xFFFF00, 0.4)
        }
        print("Found " + r.blobs.length + " blobs")
    }
}
```

---

## 10. PositionFix - 位置修正工具

通过参考锚点/角度和当前锚点/角度计算刚体变换偏移量.

```javascript
var r = PositionFix(refX, refY, refAngle, curX, curY, curAngle)
```

| 参数 | 说明 |
|---|---|
| `refX, refY` | 参考锚点坐标 |
| `refAngle` | 参考角度(度) |
| `curX, curY` | 当前锚点坐标 |
| `curAngle` | 当前角度(度) |

返回值:

```javascript
{
    offsetX: 2.5,      // X 方向偏移
    offsetY: -1.3,     // Y 方向偏移
    offsetAngle: 0.5   // 角度偏移(度)
}
```

参考代码:

```javascript
function process(image) {
    // 模板匹配找到当前工件位置
    var tpl = TemplateMatch(100, 100, 80, 80, 0, 0, 800, 600, -10, 10, 1, 0.5)

    if (tpl.found) {
        // 参考点 (标准位置), 当前点 (匹配位置)
        var fix = PositionFix(400, 300, 0, tpl.cx, tpl.cy, tpl.angle)

        DrawText(10, 30,
            "Offset X=" + fix.offsetX.toFixed(2) +
            " Y=" + fix.offsetY.toFixed(2) +
            " A=" + fix.offsetAngle.toFixed(2),
            0x00FF00, 0.6)
    }
}
```

---

## 11. Capture - 相机拍照工具

通过 MVS SDK 控制相机拍照, 支持指定曝光时间. 拍照后图像自动设为当前工作图像, 可直接调用视觉工具.

```javascript
var r = Capture(cameraSn, exposure)
```

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `cameraSn` | string | 必填 | 相机序列号, 通常传 `this.camera` |
| `exposure` | number | `35000` | 曝光时间(us), 测量工站默认35ms |

返回值:

```javascript
{
    found: true,       // 是否拍照成功
    width: 9344.0,    // 图像宽度(像素)
    height: 7000.0    // 图像高度(像素)
}
```

参考代码:

```javascript
function on_trigger() {
    // 拍照: 使用当前流程相机, 曝光35000us
    var img = Capture(this.camera, 35000)

    if (!img.found) {
        print("拍照失败")
        return
    }

    print("拍照成功: " + img.width + "x" + img.height)

    // 拍照后图像已自动设为当前工作图像, 可直接调用视觉工具
    var line = FindLine(100, 100, 800, 200, "H", "W2B", 30, 20)
    if (line.found) {
        DrawLine(line.px, line.py, line.px + 500, line.py, 0x00FF00, 2)
    }
}
```

> **注意**: `Capture` 需要真实相机连接, 编辑器中若无相机会返回 `{error: "拍照异常: ..."}`.
> 在 `on_trigger` 中, `this.camera` 由系统根据当前流程自动注入.

---

## 12. WriteXlsx - 数据写入Excel工具

将测量数据写入 CSV 文件 (UTF-8 编码, Excel 可直接打开). 文件不存在时自动创建, 已存在时追加数据行.

```javascript
var r = WriteXlsx(filePath, sheetName, headers, rows)
```

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `filePath` | string | 必填 | 文件路径 (建议 .csv 扩展名) |
| `sheetName` | string | `"Sheet1"` | 工作表名称 (CSV中仅作标识) |
| `headers` | array | 必填 | 表头字符串数组, 如 `["时间","宽度"]` |
| `rows` | array | 必填 | 数据行二维数组, 如 `[["20260907", "9344"]]` |

返回值:

```javascript
{
    success: true,
    file: "D:/CCD图片/结果.csv",
    rows: 1.0       // 写入的数据行数
}
```

参考代码:

```javascript
function on_trigger() {
    var img = Capture(this.camera, 35000)
    if (!img.found) return

    // 测量处理...
    var line = FindLine(100, 100, 800, 200, "H", "W2B", 30, 20)
    var width = line.found ? line.rms.toFixed(3) : "N/A"

    // 保存到CSV (Excel兼容)
    var ts = GetTimeStamp("yyyyMMdd_HHmmss")
    var path = "D:/CCD图片/测量结果_" + GetTimeStamp("yyyyMMdd") + ".csv"

    WriteXlsx(path, "测量结果",
        ["时间", "相机", "图像宽度", "图像高度", "RMS"],
        [[ts, this.camera, img.width.toFixed(0), img.height.toFixed(0), width]])

    print("数据已保存: " + path)
}
```

> **注意**: `WriteXlsx` 实现为 CSV 格式 (逗号分隔, UTF-8 编码), 可被 Excel/WPS 直接打开.
> 同一文件多次调用会追加数据行, 表头仅在文件首次创建时写入.

---

## 13. 变量操作 - 读写变量管理器

脚本可读写**变量管理器**中的所有字段, 包括固定字段和用户自定义变量. 变量统一以字符串形式存储在配方 JSON 中; 读取时按指定类型解析, 写入时固定字段使用其固有类型.

### 支持的字段范围

- **固定字段** (变量管理器中加粗显示, 不可删除): 如 `配方名称`、`曝光1`、`像素精度1`、`高度公差` 等. 脚本中可用**中文名**或**英文名**(如 `曝光1` 或 `exposure1`)引用.
- **自定义变量** (用户在变量管理器中新建): 按用户定义的变量名引用, 类型为 `string`/`float`/`int`/`bool`.

### 读取函数

```javascript
var s = GetStringVar("变量名")   // 字符串, 不存在返回 ""
var f = GetFloatVar("变量名")    // 浮点数, 不存在或解析失败返回 0
var i = GetIntVar("变量名")      // 整数(四舍五入), 不存在或解析失败返回 0
var b = GetBoolVar("变量名")     // 布尔值, "true"/"1"/"yes" 为 true, 否则 false
```

参数 `变量名` 可以是固定字段的中文名/英文名, 或自定义变量名.

### 写入函数

```javascript
var r = SetVar("变量名", "解析类型", "字符串值")
```

| 参数 | 类型 | 说明 |
|---|---|---|
| `变量名` | string | 固定字段(中文名/英文名)或自定义变量名 |
| `解析类型` | string | 自定义变量用: `string`/`float`/`int`/`bool`; 固定字段忽略此参数, 使用字段固有类型 |
| `字符串值` | string | 要写入的值, 统一字符串形式 |

返回值:

```javascript
{ success: true, name: "曝光1", value: "35000" }   // 成功
{ error: "SetVar 数值解析失败: ..." }              // 失败
```

### 行为说明

- **固定字段**: 写入时按字段固有类型解析 (float 字段会 `Double.parseDouble`, 解析失败返回错误). 例如 `SetVar("曝光1", "", "35000")` 会把 `exposure1` 设为 35000.0.
- **自定义变量**: 不存在则自动新建; 已存在则更新值与类型.
- **持久化**: 每次 `SetVar` 调用都会立即将配方写回磁盘 (`recipes/station{N}/{配方号}.json`), 生产环境脚本中频繁调用可能影响性能, 建议仅在需要持久化状态时使用.
- **读取固定字段示例**: `GetFloatVar("曝光1")` 或 `GetFloatVar("exposure1")` 均返回当前配方的曝光1值.

### 系数变量 (来自系数管理器)

系数管理器中的系数文件 (`D:/CCD标定/配方{配方号}_*/面{面号}.txt`) 会在配方加载时自动注入为**只读自定义变量**, 变量名格式为 `面{面号}_{系数名}`:

| 变量名示例 | 类型 | 说明 |
|---|---|---|
| `面1_像素精度` | float | 面1的像素精度 (mm/pixel) |
| `面1_高度系数` | float | 面1的高度系数 |
| `面1_宽度系数` | float | 面1的宽度系数 |
| `面1_对称度系数` | float | 面1的对称度系数 |

系数变量在变量管理器中显示为只读(不可编辑/删除), 不持久化到配方 JSON (来源始终为系数管理器文件). 脚本中直接用 `GetFloatVar` 读取:

```javascript
var pp = GetFloatVar("面1_像素精度")      // 0.005
var hc = GetFloatVar("面1_高度系数")       // 1.0
```

参考代码:

```javascript
function process(image) {
    // 读取变量管理器中的阈值(固定字段或自定义变量均可)
    var thresh = GetIntVar("定位阈值")
    var line = FindLine(100, 100, 800, 200, "H", "W2B", thresh, 20)

    if (line.found) {
        // 累加检测次数(自定义变量), 写回配方
        var n = GetIntVar("检测次数")
        SetVar("检测次数", "int", String(n + 1))
        DrawText(20, 30, "count=" + (n + 1), 0xFFFF00, 0.6)
    }

    // 运行时调整曝光(固定字段)
    SetVar("曝光1", "float", "40000")

    // 读取系数管理器注入的系数
    var pp = GetFloatVar("面1_像素精度")
    DrawText(20, 60, "pixelPrecision=" + pp, 0x00FFFF, 0.6)
}
```

---

## 14. 标定转换 - 像素坐标 <-> 物理坐标

脚本可加载标定 XML 文件, 将像素坐标转换为物理(世界)坐标, 或反向转换. 标定文件由**标定管理器**生成 (hik 兼容 XML 格式), 存储路径可配置在配方的"标定文件1"字段中 (变量管理器), 支持绝对路径或相对配方目录的路径.

### 自动加载

当配方设置到流程时, 系统会自动加载配方中 `标定文件1` (`calibFile1`) 指向的标定文件, 脚本可直接调用 `PixelToWorld`.

### 函数

```javascript
var r = LoadCalib("标定文件路径")        // 加载标定XML, 返回 {success, message}
var w = PixelToWorld(px, py)             // 像素 -> 物理, 返回 {ok, x, y, message}
var p = WorldToPixel(wx, wy)             // 物理 -> 像素, 返回 {ok, x, y, message}
var pp = GetPixelPrecision()             // 当前标定的像素精度 (mm/pixel), 无标定返回 0
```

### 参数与返回值

| 函数 | 参数 | 返回 |
|---|---|---|
| `LoadCalib(path)` | `path`: 标定文件路径(绝对或相对配方目录) | `{success: bool, message: string}` |
| `PixelToWorld(px, py)` | `px`,`py`: 像素坐标 | `{ok: bool, x: 物理X, y: 物理Y, message: string}` |
| `WorldToPixel(wx, wy)` | `wx`,`wy`: 物理坐标(mm) | `{ok: bool, x: 像素X, y: 像素Y, message: string}` |
| `GetPixelPrecision()` | 无 | 像素精度 (mm/pixel), 无标定返回 0 |

### 示例

```javascript
function process(image) {
    // 配方"标定文件1"已自动加载, 也可显式加载:
    // LoadCalib("calib/station4_face1.xml")

    var line = FindLine(100, 100, 800, 200, "H", "W2B", 30, 20)
    if (!line.found) {
        return { ok: false, message: "未找到边线" }
    }

    // 把像素交点转成物理坐标
    var w = PixelToWorld(line.px, line.py)
    if (!w.ok) {
        return { ok: false, message: w.message }
    }

    // 定位工站: 返回像素坐标 + 物理坐标
    return {
        ok: true,
        message: "OK",
        points: [
            { x: line.px, y: line.py, wx: w.x, wy: w.y }
        ]
    }
}
```

> **注意**: 标定矩阵不可逆时 `WorldToPixel` 返回 `ok:false`; 未加载标定文件时所有转换函数均返回 `ok:false`/`0`. 建议在脚本开头用 `GetPixelPrecision() > 0` 判断标定是否就绪.

---

## 工具函数

### print

输出到编辑器控制台:

```javascript
print("Hello")              // Hello
print("Score=" + 0.95)      // Score=0.95
```

### GetTimeStamp

返回格式化时间字符串:

```javascript
var ts = GetTimeStamp("yyyyMMdd_HHmmss")     // 20260907_153045
var ts2 = GetTimeStamp("yyyy-MM-dd HH:mm:ss") // 2026-09-07 15:30:45
```

---

## 完整示例: 焊点定位流程

```javascript
// 焊点定位: 模板匹配粗定位 → 找线确定基准 → 计算焊点坐标
function process(image) {
    // 1. 模板匹配粗定位
    var tpl = TemplateMatch(100, 100, 80, 80, 0, 0, 800, 600, -5, 5, 1, 0.6)

    if (!tpl.found) {
        DrawText(10, 30, "Template not found", 0xFF0000, 0.8)
        print("NG: 模板匹配失败")
        return
    }

    print("Template: cx=" + tpl.cx.toFixed(1) + " cy=" + tpl.cy.toFixed(1)
        + " angle=" + tpl.angle.toFixed(1) + " score=" + tpl.score.toFixed(3))

    // 2. 在匹配位置附近找上边缘直线
    var roiX = tpl.cx - 200
    var roiY = tpl.cy - 100
    var line = FindLine(roiX, roiY, 400, 100, "H", "W2B", 30, 20, "first", 3)

    if (!line.found) {
        DrawText(10, 30, "Line not found", 0xFF0000, 0.8)
        print("NG: 找线失败")
        return
    }

    print("Line: px=" + line.px.toFixed(1) + " py=" + line.py.toFixed(1)
        + " rms=" + line.rms.toFixed(3) + " pts=" + line.points.length)

    // 3. 在直线上找顶点
    var vertex = FindVertex(tpl.cx - 100, line.py - 50, 200, 100, 20, 40)

    if (vertex.found) {
        // 4. 计算顶点到直线的距离
        var dist = PointToLine(vertex.x, vertex.y, line.px, line.py, line.dx, line.dy)

        // 5. 位置修正
        var fix = PositionFix(400, 300, 0, tpl.cx, tpl.cy, tpl.angle)

        // 6. 标注结果
        DrawText(10, 30, "OK", 0x00FF00, 0.8)
        DrawText(10, 60,
            "Dist=" + dist.distance.toFixed(2) +
            " OffsetX=" + fix.offsetX.toFixed(2) +
            " OffsetY=" + fix.offsetY.toFixed(2),
            0xFFFF00, 0.5)

        print("OK: dist=" + dist.distance.toFixed(2)
            + " offsetX=" + fix.offsetX.toFixed(2)
            + " offsetY=" + fix.offsetY.toFixed(2))
    } else {
        DrawText(10, 30, "Vertex not found", 0xFF0000, 0.8)
        print("NG: 顶点查找失败")
    }
}
```

---

## 完整示例: 尺寸测量流程

测量工站推荐流程（与编辑器模板「测量工位完整示例」一致，ROI 来自标注 `images/measure/配方1/面1.json`，9344×7000，**背光照明：产品黑色、背景白色**）：

1. **区域布尔运算构造 ROI**：两个基线交点搜索区 `RegionUnion` 成基准线 ROI（分离区域统一拟合）；产品左/右直线标注位置外扩搜索区与基线交点区 `RegionUnion`，保证竖边延伸到基准线处；顶点搜索区 `RegionSubtract` 屏蔽区，得到左右两条竖带（屏蔽区内不采点）；
2. `FindLine(region, "H", "W2B", ...)` 找工件左线（垂直边，水平扫描，背光极性白→黑=背景→产品）；
3. `FindLine(region, "H", "B2W", ...)` 找工件右线（背光极性黑→白=产品→背景）；
4. `FindLine(region, "V", "B2W", ...)` 找底板基准线（水平边，垂直扫描，背光极性黑→白=产品→背景，两块区域一次拟合）；
5. `FindVertex(region, ...)` 找产品顶点（差集后的左右竖带内取最高边缘点，默认白→黑极性正确）；
6. `EdgeIntersect` 用基准线与左/右线求交得基准线左点、右点；
7. `PointToLine` 计算顶点到基准线距离 = 高度（像素）；
8. 基准线左/右点中点作中垂线（方向为基准线方向旋转 90°：`(-dy, dx)`），左/右线锚点到中垂线距离 = 左/右距离；
9. **宽度** = 左线锚点到右线的垂直距离（点到线）；
10. **对称度** = `abs(左距离 - 右距离)`；
11. 所有像素距离 × 系数管理器像素精度 `面N_像素精度`（`GetFloatVar`）换算成毫米；
12. 返回结果字典（`height/width/symmetry` + 5 个关键点像素坐标），自动发送到 PLC 与 MQTT。

> 说明：`FindLine` 返回的 `(dx,dy)` 为单位方向向量，`PointToLine` 返回的 `distance` 即真实垂直像素距离。左/右线"中点"取拟合线锚点 `(px,py)`（与内置测量管线口径一致）。区域对象可直接作为 FindLine/FindVertex/FindBlobs/FindCircle 的 ROI 参数（替代 x,y,w,h 四个数值），多块区域内分别采点后统一拟合，被遮挡/需屏蔽的场景无需再拆成多次查找。

```javascript
function process(image) {
    var faceNo = 1   // 当前面号(1~4), 决定读取哪一面的像素精度系数

    // 1. 区域布尔运算构造搜索区(坐标对应标注 shapes)
    var baseRoi = RegionUnion(
        MakeRect(1969, 6073, 302, 278),     // 基线左边缘交点搜索区
        MakeRect(7226, 6122, 176, 176))     // 基线右边缘交点搜索区
    var leftRoi  = RegionUnion(MakeRect(2080, 4950, 200, 1100), MakeRect(1969, 6073, 302, 278))
    var rightRoi = RegionUnion(MakeRect(7200, 4950, 220, 1100), MakeRect(7226, 6122, 176, 176))
    var vertexRoi = RegionSubtract(
        MakeRect(2100, 3089, 5189, 511),    // 产品顶点搜索区域
        MakeRect(2466, 2978, 4512, 766))    // 屏蔽区

    // 2. 特征查找(背光照明: 产品黑色, 背景白色; 左线W2B/右线B2W/基线B2W)
    var leftLine  = FindLine(leftRoi,  "H", "W2B", 30, 40, "first", 5)
    var rightLine = FindLine(rightRoi, "H", "B2W", 30, 40, "first", 5)
    var baseLine  = FindLine(baseRoi,  "V", "B2W", 30, 24, "first", 3)
    var vertex    = FindVertex(vertexRoi, 20, 80)

    if (!leftLine.found || !rightLine.found || !baseLine.found || !vertex.found) {
        return { ok: false, message: "特征查找失败: 左线=" + leftLine.found + " 右线=" + rightLine.found
                 + " 基准线=" + baseLine.found + " 顶点=" + vertex.found }
    }

    // 3. 边缘交点: 基准线左点 / 右点
    var baseLeft = EdgeIntersect(baseLine.px, baseLine.py, baseLine.dx, baseLine.dy,
                                 leftLine.px, leftLine.py, leftLine.dx, leftLine.dy)
    var baseRight = EdgeIntersect(baseLine.px, baseLine.py, baseLine.dx, baseLine.dy,
                                  rightLine.px, rightLine.py, rightLine.dx, rightLine.dy)
    if (!baseLeft.found || !baseRight.found) {
        return { ok: false, message: "基准线交点计算失败" }
    }

    // 4. 基准线中垂线(过左/右点中点, 方向 (-dy, dx))
    var midX = (baseLeft.x + baseRight.x) / 2
    var midY = (baseLeft.y + baseRight.y) / 2
    var perpDx = -baseLine.dy
    var perpDy =  baseLine.dx

    // 5. 像素距离
    var heightPx    = PointToLine(vertex.x, vertex.y, baseLine.px, baseLine.py, baseLine.dx, baseLine.dy).distance
    var leftDistPx  = PointToLine(leftLine.px, leftLine.py, midX, midY, perpDx, perpDy).distance
    var rightDistPx = PointToLine(rightLine.px, rightLine.py, midX, midY, perpDx, perpDy).distance
    var widthPx     = PointToLine(leftLine.px, leftLine.py,
                                  rightLine.px, rightLine.py, rightLine.dx, rightLine.dy).distance
    var symPx       = Math.abs(leftDistPx - rightDistPx)

    // 6. 像素精度(系数管理器: 面N_像素精度) 换算毫米
    var precision = GetFloatVar("面" + faceNo + "_像素精度")
    if (!precision || precision <= 0) precision = 0.02
    var heightMm = heightPx * precision
    var widthMm  = widthPx  * precision
    var symMm    = symPx    * precision

    // 7. 可视化
    DrawRegion(vertexRoi, 0xFFFFFF, 1)
    DrawRegion(baseRoi, 0x808080, 1)
    DrawLine(baseLine.px - baseLine.dx * 3000, baseLine.py - baseLine.dy * 3000,
             baseLine.px + baseLine.dx * 3000, baseLine.py + baseLine.dy * 3000, 0x00FF00, 3)
    DrawLine(midX - perpDx * 2000, midY - perpDy * 2000,
             midX + perpDx * 2000, midY + perpDy * 2000, 0xFFFF00, 2)
    DrawCross(vertex.x, vertex.y, 0xFF0000, 15)
    DrawCross(baseLeft.x, baseLeft.y, 0xFF00FF, 12)
    DrawCross(baseRight.x, baseRight.y, 0xFF00FF, 12)
    DrawText(20, 40,
        "H=" + heightMm.toFixed(3) + " W=" + widthMm.toFixed(3) + " Sym=" + symMm.toFixed(3) + "mm",
        0xFFFF00, 0.9)

    // 8. 返回结果(发送 PLC 与 MQTT); 关键点为像素坐标
    return {
        ok: true,
        message: "高度=" + heightMm.toFixed(3) + " 宽度=" + widthMm.toFixed(3)
                 + " 对称度=" + symMm.toFixed(3),
        height: heightMm,
        width: widthMm,
        symmetry: symMm,
        topPoint:           { x: vertex.x,     y: vertex.y },
        baseLineLeftPoint:  { x: baseLeft.x,   y: baseLeft.y },
        baseLineRightPoint: { x: baseRight.x,  y: baseRight.y },
        leftPoint:          { x: leftLine.px,  y: leftLine.py },
        rightPoint:         { x: rightLine.px, y: rightLine.py }
    }
}
```

> 极性 `W2B/B2W` 依工件与背景明暗方向调整，找不到边时先翻转极性再调阈值；ROI 坐标按实际标注/工件调整。

---

## 脚本编辑器使用

菜单: 机器视觉 → 视觉流程脚本编辑器

1. 工具栏「配方」下拉框仅显示当前工站的配方
2. 工具栏「流程」下拉框按工站类型显示: 测量工站为 **面1/面2/面3/面4**, 定位工站为 **正面/背面**
3. 选择配方+流程后, 自动加载已保存的脚本; 保存脚本时按配方+流程ID存储
4. 工具栏「浏览」选择测试图像 (定义了 `on_trigger` 时可跳过, 使用相机拍照)
5. 在左侧编辑器编写 JavaScript 脚本 (或从「函数模板」下拉插入预置代码)
6. 点击「运行测试」, 后台执行脚本 (优先调用 `on_trigger`, 其次 `process`)
7. 右侧预览渲染结果图 (原图 + 绘制叠加)
8. 底部控制台显示 print 输出和错误信息
9. 点击「保存脚本」保存到配方 (或导出 .js 文件)

预置模板: 测量工位完整示例 / Region区域布尔运算 / FindLine / FindCircle / FindVertex / TemplateMatch / FindBlobs / LineToLine / EdgeIntersect / on_trigger

---

## 多流程脚本架构

一个配方可包含多个流程的独立脚本, 存储在配方 JSON 的 `visionScripts` 字段 (Map: 流程ID → 脚本).

### 配方 JSON 结构

```json
{
    "recipeId": 1,
    "recipeName": "标准件",
    "visionScripts": {
        "1": "function on_trigger() { ... }",
        "2": "function on_trigger() { ... }",
        "3": "function on_trigger() { ... }",
        "4": "function on_trigger() { ... }"
    }
}
```

- 键: 流程ID (字符串, 对应 `StationConfig.Flow.flowId`, 如测量工站的面号 1-4)
- 值: JavaScript 脚本文本
- 空脚本 = 使用内置硬编码视觉管线 (`LocatePipeline` / `MeasurePipeline`)

### 脚本选择逻辑

1. PLC 触发拍照 → `FlowManager` 匹配 `dbNumber` / `triggerValue` → 找到对应 `Flow`
2. 加载配方的 `visionScripts[flowId]` 脚本
3. 脚本非空 → 执行 JS 引擎, 调用 `on_trigger()` (或 `process(image)`)
4. 脚本为空 → 走内置管线 (`LocatePipeline.run()` 或 `MeasurePipeline.run()`)

### 相机序列号注入

`this.camera` 的值来自 `StationConfig.Flow.cameraSn`, 在流程初始化时由 `VisionScriptApi.setCameraSn()` 注入:
- 测量工站: 每个面(流程)对应一个相机序列号
- 定位/焊接工站: 每个流程对应一个相机序列号
- 在 `on_trigger()` 中通过 `Capture(this.camera, 曝光)` 拍照
