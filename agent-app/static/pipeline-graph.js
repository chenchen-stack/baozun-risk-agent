/**
 * 风控工作流 · LiteGraph.js（Dify 风浅色编排）
 * 触发 → 多源适配(API/DB/RPA) → 汇聚/ETL → 风控智能体 → 决策 → 回调/审计
 */
(function () {
  /** 优先同源 vendor（Render / 企业网关常拦外站 CDN）；失败再试 jsDelivr */
  var LG_SCRIPT_URLS = [
    "/static/vendor/litegraph/litegraph.min.js",
    "https://cdn.jsdelivr.net/npm/litegraph.js@0.7.18/build/litegraph.min.js",
  ];
  var LG_CSS_URLS = [
    "/static/vendor/litegraph/litegraph.css",
    "https://cdn.jsdelivr.net/npm/litegraph.js@0.7.18/css/litegraph.css",
  ];

  function loadScript(src, cb) {
    var s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.onload = function () {
      cb(null);
    };
    s.onerror = function () {
      console.error("LiteGraph script failed:", src);
      cb(new Error("load fail: " + src));
    };
    document.head.appendChild(s);
  }

  function loadLiteGraphScript(cb) {
    var i = 0;
    function next(prevErr) {
      if (window.LiteGraph) return cb(null);
      if (i >= LG_SCRIPT_URLS.length) return cb(prevErr || new Error("no LiteGraph source"));
      var src = LG_SCRIPT_URLS[i++];
      loadScript(src, function (err) {
        if (window.LiteGraph) return cb(null);
        next(err || prevErr);
      });
    }
    next(null);
  }

  function loadCssPipe() {
    if (document.querySelector('link[data-pipe-lg="1"]')) return;
    var idx = 0;
    function attach() {
      if (idx >= LG_CSS_URLS.length) return;
      var l = document.createElement("link");
      l.rel = "stylesheet";
      l.href = LG_CSS_URLS[idx];
      l.setAttribute("data-pipe-lg", "1");
      l.onerror = function () {
        idx++;
        l.remove();
        attach();
      };
      document.head.appendChild(l);
    }
    attach();
  }

  function injectLitegraphMenuLightCss() {
    if (document.getElementById("pipe-lg-ui-override")) return;
    var st = document.createElement("style");
    st.id = "pipe-lg-ui-override";
    st.textContent =
      ".litegraph .dialog{background:#fff!important;color:#111827!important;border:1px solid #E5E7EB!important;border-radius:12px!important;box-shadow:0 16px 48px rgba(15,23,42,.12)!important}" +
      ".litecontextmenu.litemenubar-panel,.litecontextmenu{background:#fff!important;border:1px solid #E5E7EB!important;border-radius:10px!important;box-shadow:0 8px 28px rgba(15,23,42,.1)!important}" +
      ".litecontextmenu.dark{background:#fff!important}" +
      ".litecontextmenu ul li{color:#374151!important}" +
      ".litecontextmenu ul li:hover{background:#F3F4F6!important;color:#111827!important}" +
      ".litesearchbox{background:#fff!important;border:1px solid #E5E7EB!important;border-radius:10px!important}" +
      ".litesearchbox input{color:#111827!important}";
    document.head.appendChild(st);
  }

  function markGraphDirty() {
    if (window.__pipeLgCanvas && typeof window.__pipeLgCanvas.setDirty === "function") window.__pipeLgCanvas.setDirty(true, true);
  }

  function toast(msg) {
    if (typeof window.wfShowToast === "function") window.wfShowToast(msg);
    else alert(msg);
  }

  function touchAutosaveHint() {
    if (typeof window.__wfTouchAutosave === "function") window.__wfTouchAutosave();
  }

  function setNodeLastRun(node, msg) {
    if (!node.properties) node.properties = {};
    node.properties.last_run = String(msg).slice(0, 480);
    markGraphDirty();
    refreshInspectorIfCurrent(node);
  }

  function refreshInspectorIfCurrent(node) {
    if (window.__pipeInspectorNode && node && window.__pipeInspectorNode.id === node.id) {
      var pre = document.getElementById("wfInpLastRun");
      if (pre) pre.textContent = (node.properties && node.properties.last_run) || "—";
    }
  }

  /** 浅色主题（参考 Dify：白底、蓝连线、柔和阴影） */
  function applyLiteGraphLightTheme(LG) {
    if (!LG || applyLiteGraphLightTheme._ok) return;
    applyLiteGraphLightTheme._ok = true;
    LG.NODE_DEFAULT_BGCOLOR = "#FFFFFF";
    LG.NODE_DEFAULT_BOXCOLOR = "#E5E7EB";
    LG.NODE_DEFAULT_COLOR = "#155EEF";
    LG.NODE_TEXT_COLOR = "#4B5563";
    LG.NODE_TITLE_COLOR = "#FFFFFF";
    LG.NODE_SELECTED_TITLE_COLOR = "#FFFFFF";
    LG.NODE_BOX_OUTLINE_COLOR = "#D1D5DB";
    LG.LINK_COLOR = "#155EEF";
    LG.CONNECTING_LINK_COLOR = "#10B981";
    LG.EVENT_LINK_COLOR = "#8B5CF6";
    LG.DEFAULT_SHADOW_COLOR = "rgba(15,23,42,0.06)";
    LG.WIDGET_BGCOLOR = "#F9FAFB";
    LG.WIDGET_OUTLINE_COLOR = "#E5E7EB";
    LG.WIDGET_TEXT_COLOR = "#374151";
    LG.WIDGET_SECONDARY_TEXT_COLOR = "#9CA3AF";
  }

  function attachDotGridPattern(graphcanvas) {
    var _pat;
    graphcanvas.onDrawBackground = function (ctx, visible_area) {
      if (!_pat) {
        var c = document.createElement("canvas");
        c.width = 22;
        c.height = 22;
        var p = c.getContext("2d");
        p.fillStyle = "rgba(148,163,184,0.38)";
        p.beginPath();
        p.arc(2, 2, 1.15, 0, Math.PI * 2);
        p.fill();
        _pat = ctx.createPattern(c, "repeat");
      }
      if (_pat && visible_area) {
        ctx.fillStyle = _pat;
        ctx.fillRect(visible_area[0], visible_area[1], visible_area[2], visible_area[3]);
      }
    };
  }

  /** wf/* 节点若保持 LiteGraph 默认 ALWAYS，graph.start(0) 会每帧 runStep → onExecute 每秒触发数十次 fetch，极易耗尽浏览器并发槽位（net::ERR_INSUFFICIENT_RESOURCES）。 */
  function normalizePipelineWfModes(graph) {
    if (!graph || !graph._nodes || !window.LiteGraph) return;
    var G = window.LiteGraph;
    for (var i = 0; i < graph._nodes.length; i++) {
      var n = graph._nodes[i];
      if (n && n.type && String(n.type).indexOf("wf/") === 0) n.mode = G.NEVER;
    }
    if (typeof graph.updateExecutionOrder === "function") graph.updateExecutionOrder();
  }

  /** 拖拽节点 / 平移画布 / 拖连线时仅暂收右侧栏，左侧场景/节点库不动，避免布局跳动 */
  var _wfPipeQuiet = { active: false, saved: null, ptr: null };

  function wfEnterPipeQuietMode() {
    if (_wfPipeQuiet.active) return;
    var pg = document.getElementById("pg-pipe");
    var root = document.querySelector("#pg-pipe .wf-studio-body");
    var content = document.querySelector(".content.content-pipe-only");
    if (!pg || !pg.classList.contains("on") || !root) return;
    _wfPipeQuiet.saved = {
      scene: root.classList.contains("wf-coll-scenario"),
      pal: root.classList.contains("wf-coll-palette"),
      ins: root.classList.contains("wf-coll-insp"),
      rd: root.classList.contains("wf-coll-rdock"),
    };
    root.classList.add("wf-coll-insp", "wf-coll-rdock", "wf-pipe-focus");
    var det = document.getElementById("wfTriggerDetails");
    if (det) det.open = false;
    if (content) content.classList.add("wf-pipe-focus");
    if (typeof window.wfSyncLayoutButtons === "function") window.wfSyncLayoutButtons();
    _wfPipeQuiet.active = true;
    if (typeof wfResizePipeSoon === "function") wfResizePipeSoon();
  }

  function wfExitPipeQuietMode() {
    if (!_wfPipeQuiet.active || !_wfPipeQuiet.saved) {
      _wfPipeQuiet.active = false;
      _wfPipeQuiet.saved = null;
      return;
    }
    var root = document.querySelector("#pg-pipe .wf-studio-body");
    var content = document.querySelector(".content.content-pipe-only");
    var s = _wfPipeQuiet.saved;
    if (root) {
      root.classList.remove("wf-pipe-focus");
      root.classList.toggle("wf-coll-scenario", s.scene);
      root.classList.toggle("wf-coll-palette", s.pal);
      root.classList.toggle("wf-coll-insp", s.ins);
      root.classList.toggle("wf-coll-rdock", s.rd);
    }
    if (content) content.classList.remove("wf-pipe-focus");
    if (typeof window.wfSyncLayoutButtons === "function") window.wfSyncLayoutButtons();
    _wfPipeQuiet.saved = null;
    _wfPipeQuiet.active = false;
    if (typeof wfResizePipeSoon === "function") wfResizePipeSoon();
  }

  window.wfExitPipeQuietMode = wfExitPipeQuietMode;

  function wirePipeCanvasQuietMode(canvasEl) {
    if (!canvasEl || wirePipeCanvasQuietMode._done) return;
    wirePipeCanvasQuietMode._done = true;

    function onDocPointerEnd() {
      _wfPipeQuiet.ptr = null;
      if (_wfPipeQuiet.active) wfExitPipeQuietMode();
    }

    document.addEventListener("pointerup", onDocPointerEnd, true);
    document.addEventListener("pointercancel", onDocPointerEnd, true);

    canvasEl.addEventListener("pointerdown", function (e) {
      if (e.button !== 0 && e.button !== 1) return;
      _wfPipeQuiet.ptr = { x: e.clientX, y: e.clientY };
    });

    canvasEl.addEventListener("pointermove", function (e) {
      if (!_wfPipeQuiet.ptr || _wfPipeQuiet.active) return;
      var gc = window.__pipeLgCanvas;
      if (!gc) return;
      var dx = e.clientX - _wfPipeQuiet.ptr.x;
      var dy = e.clientY - _wfPipeQuiet.ptr.y;
      if (dx * dx + dy * dy < 36) return;
      if (gc.node_dragged || gc.dragging_canvas || gc.connecting_node) wfEnterPipeQuietMode();
    });
  }

  function registerNodeTypes() {
    var G = window.LiteGraph;
    if (!G || registerNodeTypes._ok) return;
    registerNodeTypes._ok = true;

    var SLOT = "risk_flow";

    function defNode(title, outs, ins, headerColor) {
      return function NodeImpl() {
        var i, o;
        for (i = 0; ins && i < ins.length; i++) this.addInput(ins[i][0], ins[i][1] || SLOT);
        for (o = 0; outs && o < outs.length; o++) this.addOutput(outs[o][0], outs[o][1] || SLOT);
        this.properties = { last_run: "", source_system: "", adapter_notes: "", obs_hint: "可观测 · 运行日志" };
        this.size = [240, 108];
        this.color = headerColor || "#155EEF";
        this.bgcolor = "#FFFFFF";
        this.boxcolor = "#E8ECF3";
        this.shape = "round";
        this.mode = G.NEVER;
      };
    }

    var exec = {
      "wf/poll": function () {
        var n = this;
        if (!canHttp()) {
          setNodeLastRun(n, "需同源 http(s) 才能请求 API");
          return;
        }
        fetch(new URL("/api/health", location.href), { credentials: "same-origin", cache: "no-store" })
          .then(function (r) {
            return r.json();
          })
          .then(function (j) {
            setNodeLastRun(n, "定时巡检：服务存活 + 可扩展为拉取「预警列表/待办异常」（F17）→ " + JSON.stringify(j));
          })
          .catch(function (e) {
            setNodeLastRun(n, "health 失败: " + e.message);
          });
      },
      "wf/webhook": function () {
        setNodeLastRun(this, "OA 审批流事件：合同/付款节点状态变更（F08 审批链校验入口）· " + new Date().toISOString());
      },
      "wf/rest": function () {
        var n = this;
        if (!canHttp()) return;
        fetch(new URL("/api/datasources/status", location.href), { credentials: "same-origin", cache: "no-store" })
          .then(function (r) {
            return r.json();
          })
          .then(function (j) {
            setNodeLastRun(n, "采购系统侧：数据源状态（可接 PO/申请 REST）→ " + JSON.stringify(j));
          })
          .catch(function (e) {
            setNodeLastRun(n, "datasources 失败: " + e.message);
          });
      },
      "wf/db": function () {
        var n = this;
        if (!canHttp()) return;
        fetch(new URL("/api/integrations/status", location.href), { credentials: "same-origin", cache: "no-store" })
          .then(function (r) {
            return r.json();
          })
          .then(function (j) {
            setNodeLastRun(n, "合同/付款只读库或 SelectDB：集成态摘要 → " + JSON.stringify(j).slice(0, 300));
          })
          .catch(function (e) {
            setNodeLastRun(n, "integrations 失败: " + e.message);
          });
      },
      "wf/rpa": function () {
        setNodeLastRun(this, "RPA 兜底（7.2）：无 API/库时的屏幕流程；对接 UiPath/影刀等 · POC 占位");
      },
      "wf/merge2": function () {
        this.setOutputData(0, { a: this.getInputData(0), b: this.getInputData(1), t: Date.now() });
        setNodeLastRun(this, "调度触发 + OA 审批事件 合流 → 驱动下游拉数");
      },
      "wf/merge3": function () {
        this.setOutputData(0, {
          a: this.getInputData(0),
          b: this.getInputData(1),
          c: this.getInputData(2),
          t: Date.now(),
        });
        setNodeLastRun(this, "采购 + 合同/OA + 付款/财务 三路合流（断点串联）");
      },
      "wf/etl": function () {
        var n = this;
        if (!canHttp()) return;
        fetch(new URL("/api/dashboard", location.href), { credentials: "same-origin", cache: "no-store" })
          .then(function (r) {
            return r.json();
          })
          .then(function (d) {
            var keys = d && typeof d === "object" ? Object.keys(d).slice(0, 8).join(", ") : "";
            setNodeLastRun(n, "GET /api/dashboard 字段示例: " + keys + " …");
          })
          .catch(function (e) {
            setNodeLastRun(n, "dashboard 失败: " + e.message);
          });
      },
      "wf/agent": function () {
        if (window.__pipeRunSeqActive) {
          setNodeLastRun(
            this,
            "批量运行：未自动打开对话（避免与「运行结果」同时占屏）。请在运行结果侧栏点「问 AI 处置」，或取消运行后单点本节点 ▶ 仅执行。"
          );
          return;
        }
        setNodeLastRun(this, "已唤起右侧「非经营性采购风控」对话（对齐需求书 F01–F14 / 第一期 POC）");
        if (typeof window.openChatAndSend === "function")
          window.openChatAndSend(
            "你是宝尊非经营性采购风控 Agent（POC）。请按客户第一期范围：①多源接入采购/OA合同/OA付款（或 SelectDB）；②按单号串联申请→合同→PO→验收→发票→付款；③点出三单匹配（数量±2%、单价±1%、税率须一致）与四流一致（合同主体·付款·发票抬头·物流）是否可能异常；④对照 F06 前序流程、F07 合同类型、F08 审批层级、F09–F11 付款关联与重复/超额；⑤用条列给出可执行处置（冻结付款/补采购申请/升级审批/建工单）。若缺字段请说明需 IT 提供的接口字段。"
          );
      },
      "wf/threeway": function () {
        setNodeLastRun(
          this,
          "三单匹配引擎（F04）：PO·入库(GRN)·发票 数量容差≤2%、单价≤1%、税率须 100% 一致；供应商三方须一致。超差→冻结付款+异常工单（演示逻辑）。"
        );
      },
      "wf/fourflow": function () {
        setNodeLastRun(
          this,
          "四流一致（F05）：合同流·资金流·发票流·物流（收货）主体对齐；双上市合规向金税四期靠拢。不一致→预警+飞书/OA（F13）。"
        );
      },
      "wf/decision": function () {
        var v = this.getInputData(0);
        this.setOutputData(0, v);
        this.setOutputData(1, v);
        this.setOutputData(2, v);
        setNodeLastRun(this, "风险分流：低→放行关注；中→复核；高→拦截+工单（演示复制到三路）");
      },
      "wf/callback": function () {
        var n = this;
        if (!canHttp()) return;
        fetch(new URL("/api/notifications", location.href), { credentials: "same-origin", cache: "no-store" })
          .then(function (r) {
            return r.json();
          })
          .then(function (j) {
            var c = (j.notifications && j.notifications.length) || 0;
            setNodeLastRun(n, "飞书/OA 推送（F13）：通知记录条数 ≈ " + c);
          })
          .catch(function (e) {
            setNodeLastRun(n, "notifications 失败: " + e.message);
          });
      },
      "wf/audit": function () {
        var n = this;
        if (!canHttp()) return;
        fetch(new URL("/api/reports", location.href), { credentials: "same-origin", cache: "no-store" })
          .then(function (r) {
            return r.json();
          })
          .then(function (j) {
            var c = (j.reports && j.reports.length) || 0;
            setNodeLastRun(n, "月度内控报告（F14）HTML 列表条数 = " + c);
          })
          .catch(function (e) {
            setNodeLastRun(n, "reports 失败: " + e.message);
          });
      },
    };

    var types = [
      ["wf/poll", "定时巡检 · 异常队列", [["触发", SLOT]], null, "#155EEF"],
      ["wf/webhook", "OA 审批流事件", [["触发", SLOT]], null, "#2563EB"],
      ["wf/rest", "采购系统 API（PO/申请）", [["原始数据", SLOT]], null, "#10B981"],
      ["wf/db", "SelectDB / 合同·付款只读", [["原始数据", SLOT]], null, "#8B5CF6"],
      ["wf/rpa", "RPA 兜底（无接口系统）", [["原始数据", SLOT]], null, "#F59E0B"],
      [
        "wf/merge2",
        "触发源汇聚（调度+事件）",
        [["合流", SLOT]],
        [
          ["调度触发", SLOT],
          ["审批事件", SLOT],
        ],
        "#64748B",
      ],
      [
        "wf/merge3",
        "三系统数据汇聚",
        [["合流", SLOT]],
        [
          ["采购侧", SLOT],
          ["合同/OA侧", SLOT],
          ["付款/财务侧", SLOT],
        ],
        "#64748B",
      ],
      [
        "wf/etl",
        "主数据对齐 · 标准宽表",
        [["标准宽表", SLOT]],
        [
          ["触发侧", SLOT],
          ["数据侧", SLOT],
        ],
        "#059669",
      ],
      ["wf/threeway", "三单匹配引擎（PO·GRN·票）", [["三单结果", SLOT]], [["标准宽表", SLOT]], "#047857"],
      ["wf/fourflow", "四流一致校验", [["四流结果", SLOT]], [["三单结果", SLOT]], "#0D9488"],
      ["wf/agent", "非经营性采购风控智能体", [["研判", SLOT]], [["四流结果", SLOT]], "#7C3AED"],
      [
        "wf/decision",
        "风险等级分流（低/中/高）",
        [
          ["低风险", SLOT],
          ["中风险", SLOT],
          ["高风险", SLOT],
        ],
        [["研判", SLOT]],
        "#0891B2",
      ],
      ["wf/callback", "飞书 / OA 工单推送", [["已推送", SLOT]], [["任一路径", SLOT]], "#0D9488"],
      ["wf/audit", "审计留痕 · 月报接口", null, [["已推送", SLOT]], "#6B7280"],
    ];

    types.forEach(function (row) {
      var Ctor = defNode(row[1], row[2], row[3], row[4]);
      Ctor.title = row[1];
      var fn = exec[row[0]];
      if (fn) Ctor.prototype.onExecute = fn;
      G.registerNodeType(row[0], Ctor);
    });

    var OBS_DEFAULTS = {
      "wf/poll": "调度 · 增量水位",
      "wf/webhook": "事件 · 投递健康",
      "wf/rest": "接口 · 延迟/错误率",
      "wf/db": "库表 · 同步位点",
      "wf/rpa": "RPA · 执行轨迹",
      "wf/merge2": "汇聚 · 双源去重",
      "wf/merge3": "汇聚 · 三源对齐",
      "wf/etl": "主数据 · 对账条数",
      "wf/threeway": "规则引擎 · 三单命中",
      "wf/fourflow": "规则引擎 · 四流命中",
      "wf/agent": "智能体 · 研判轨迹",
      "wf/decision": "策略 · 分流统计",
      "wf/callback": "闭环 · 推送回执",
      "wf/audit": "审计 · 月报/底稿",
    };

    function patchWfObservabilityDraw() {
      Object.keys(OBS_DEFAULTS).forEach(function (typeName) {
        var info = G.registered_node_types[typeName];
        if (!info || !info.prototype) return;
        var prev = info.prototype.onDrawForeground;
        info.prototype.onDrawForeground = function (ctx) {
          if (prev) prev.apply(this, arguments);
          if (this.flags && this.flags.collapsed) return;
          var hint =
            (this.properties && this.properties.obs_hint) || OBS_DEFAULTS[typeName] || "可观测 · 日志";
          ctx.save();
          ctx.fillStyle = "#94A3B8";
          ctx.font = "10px system-ui,-apple-system,'Segoe UI','PingFang SC',sans-serif";
          var y = (this.size && this.size[1] ? this.size[1] : 92) - 8;
          ctx.fillText(hint.slice(0, 28), 10, y);
          ctx.restore();
        };
      });
    }
    patchWfObservabilityDraw();
  }

  /** 按场景覆盖节点标题/说明/可观测文案（同一拓扑，多场景演示） */
  function applyScenarioPreset(graph, sceneId) {
    if (!graph || !graph._nodes) return;
    var sid = sceneId || "scene-proc";
    var PRESETS = {
      "scene-proc": {
        "wf/poll": {
          adapter_notes: "1～5 分钟增量：待办/异常队列（厂商无 WebHook 时主路径）",
          obs_hint: "调度 · 增量水位监控",
        },
        "wf/webhook": {
          adapter_notes: "合同/付款审批节点推送（对方开放回调时准实时）",
          obs_hint: "事件 · 订阅健康度",
        },
        "wf/merge2": {
          title: "触发源汇聚（调度+事件）",
          obs_hint: "汇聚 · 去重与就绪信号",
        },
        "wf/merge3": {
          title: "三系统数据汇聚",
          adapter_notes: "采购 + 合同/OA + 付款/财务 三路合流",
          obs_hint: "汇聚 · 断点串联监控",
        },
        "wf/threeway": { obs_hint: "规则引擎 · F04 三单命中" },
        "wf/fourflow": { obs_hint: "规则引擎 · F05 四流命中" },
      },
      "scene-expense": {
        "wf/poll": {
          adapter_notes: "费控/OA 报销单待办 · 1～5 分钟增量（无推送接口时）",
          obs_hint: "调度 · 报销待办堆积",
        },
        "wf/webhook": {
          adapter_notes: "报销提交/驳回/通过事件（若费控开放回调）",
          obs_hint: "事件 · 审批 SLA",
        },
        "wf/merge2": {
          title: "费控触发汇聚（调度+事件）",
          obs_hint: "汇聚 · 员工+科目维度",
        },
        "wf/rest": { adapter_notes: "费控系统 API：报销单头行、发票影像索引", obs_hint: "接口 · 票据拉取" },
        "wf/db": { adapter_notes: "预算科目执行率只读视图", obs_hint: "库表 · 预算执行快照" },
        "wf/merge3": {
          title: "费控·预算·发票 三源汇聚",
          adapter_notes: "报销 + 预算额度 + 发票验真结果",
          obs_hint: "汇聚 · 三单前置数据",
        },
        "wf/etl": {
          title: "主数据对齐 · 报销宽表",
          adapter_notes: "员工、部门、科目、供应商归一",
          obs_hint: "主数据 · 对齐条数",
        },
        "wf/threeway": {
          title: "三单匹配（申请·报销·发票）",
          obs_hint: "规则引擎 · 超额/串号",
        },
        "wf/fourflow": {
          title: "四流一致（事由·资金·票·附件）",
          obs_hint: "规则引擎 · 主体/金额一致性",
        },
        "wf/agent": {
          title: "费用报销风控智能体",
          obs_hint: "智能体 · 政策/票据研判",
        },
      },
      "scene-contract": {
        "wf/poll": {
          adapter_notes: "合同台账/付款计划 · 定时对齐在途与已付",
          obs_hint: "调度 · 超付风险扫描",
        },
        "wf/webhook": { adapter_notes: "付款申请节点状态（OA 推送或轮询补偿）", obs_hint: "事件 · 付款闸口" },
        "wf/merge2": { title: "履约触发汇聚（计划+审批）", obs_hint: "汇聚 · 应付日历" },
        "wf/rest": { adapter_notes: "采购订单与收货（对账履约进度）", obs_hint: "接口 · PO/GRN" },
        "wf/db": { adapter_notes: "合同金额、变更单、付款条款只读库", obs_hint: "库表 · 合同余额" },
        "wf/merge3": {
          title: "合同·履约·付款 三源汇聚",
          adapter_notes: "合同总额 vs 在途付款 vs 发票",
          obs_hint: "汇聚 · 超合同线索",
        },
        "wf/threeway": { title: "三单匹配（合同·订单·付款）", obs_hint: "规则引擎 · 累计付款/订单" },
        "wf/fourflow": { title: "四流一致（签约·付款·票·收货）", obs_hint: "规则引擎 · 主体链路" },
        "wf/agent": { title: "合同履约风控智能体", obs_hint: "智能体 · 违约/超付解释" },
      },
      "scene-supplier": {
        "wf/poll": {
          adapter_notes: "采购中标/投标库 · 定时增量（关联企业图谱）",
          obs_hint: "调度 · 中标率偏离",
        },
        "wf/webhook": { adapter_notes: "供应商准入审批事件（可选）", obs_hint: "事件 · 准入闸口" },
        "wf/merge2": { title: "供应商风险触发汇聚", obs_hint: "汇聚 · 内外部信号" },
        "wf/rest": { adapter_notes: "采购招投标与供应商主数据 API", obs_hint: "接口 · 投标明细" },
        "wf/db": { adapter_notes: "工商/关联关系只读库或第三方风控视图", obs_hint: "库表 · 关联边" },
        "wf/merge3": {
          title: "投标·主体·外部风险 三源汇聚",
          adapter_notes: "同标段多投标方 + 股权穿透",
          obs_hint: "汇聚 · 围标特征输入",
        },
        "wf/etl": { title: "主数据对齐 · 供应商宽表", adapter_notes: "统一社会信用代码、别名、集团", obs_hint: "主数据 · 实体解析" },
        "wf/threeway": { title: "围标线索规则（报价·时间·IP）", obs_hint: "规则引擎 · 相似度命中" },
        "wf/fourflow": { title: "关系一致性（投标·收款·联系人）", obs_hint: "规则引擎 · 异常关联" },
        "wf/agent": { title: "供应商风险智能体", obs_hint: "智能体 · 解释与取证建议" },
      },
    };

    var preset = PRESETS[sid] || PRESETS["scene-proc"];
    for (var i = 0; i < graph._nodes.length; i++) {
      var n = graph._nodes[i];
      if (!n || !n.type) continue;
      var ov = preset[n.type];
      if (!ov) continue;
      if (ov.title) n.title = ov.title;
      if (!n.properties) n.properties = {};
      if (ov.adapter_notes != null) n.properties.adapter_notes = ov.adapter_notes;
      if (ov.obs_hint) n.properties.obs_hint = ov.obs_hint;
    }
  }

  function buildDefaultGraph(graph) {
    var G = window.LiteGraph;
    graph.clear();

    function add(type, x, y) {
      var n = G.createNode(type);
      if (!n) return null;
      n.pos = [x, y];
      graph.add(n);
      return n;
    }

    var poll = add("wf/poll", 40, 40);
    var hook = add("wf/webhook", 40, 160);
    var m2 = add("wf/merge2", 320, 100);
    var rest = add("wf/rest", 40, 320);
    var db = add("wf/db", 40, 440);
    var rpa = add("wf/rpa", 40, 560);
    var m3 = add("wf/merge3", 320, 460);
    var etl = add("wf/etl", 600, 280);
    var tw = add("wf/threeway", 900, 280);
    var ff = add("wf/fourflow", 1120, 280);
    var agent = add("wf/agent", 1340, 280);
    var dec = add("wf/decision", 1580, 260);
    var cb = add("wf/callback", 1820, 280);
    var aud = add("wf/audit", 2060, 280);

    if (poll && m2) poll.connect(0, m2, 0);
    if (hook && m2) hook.connect(0, m2, 1);
    if (m2 && etl) m2.connect(0, etl, 0);
    if (rest && m3) rest.connect(0, m3, 0);
    if (db && m3) db.connect(0, m3, 1);
    if (rpa && m3) rpa.connect(0, m3, 2);
    if (m3 && etl) m3.connect(0, etl, 1);
    if (etl && tw) etl.connect(0, tw, 0);
    if (tw && ff) tw.connect(0, ff, 0);
    if (ff && agent) ff.connect(0, agent, 0);
    if (agent && dec) agent.connect(0, dec, 0);
    if (dec && cb) dec.connect(2, cb, 0);
    if (cb && aud) cb.connect(0, aud, 0);

    function tag(n, sys, note) {
      if (!n || !n.properties) return;
      n.properties.source_system = sys;
      n.properties.adapter_notes = note;
    }
    tag(poll, "调度", "轮询待处理异常/队列（事中监控）");
    tag(hook, "OA", "合同/付款审批节点 Webhook");
    tag(rest, "采购系统", "PO、采购申请 REST/API");
    tag(db, "SelectDB", "合同与付款只读视图/SQL");
    tag(rpa, "RPA", "无接口时的屏幕兜底");
    tag(etl, "主数据", "申请·合同·PO·验收·发票·付款 主键对齐");
    tag(tw, "规则引擎", "F04 三单匹配阈值");
    tag(ff, "规则引擎", "F05 四流一致");
    tag(agent, "大模型", "火山/千问 · 非经营性采购研判");
    tag(dec, "策略", "低/中/高 → 放行/复核/拦截");
    tag(cb, "飞书/OA", "F12/F13 工单与推送");
    tag(aud, "内控", "F14 月报 / 审计底稿入口");
  }

  window.wfBuildGraphForActiveScene = function (graph) {
    if (!graph) graph = window.__pipeLGraph;
    if (!graph) return;
    buildDefaultGraph(graph);
    var sid = (typeof window.__wfActiveSceneId !== "undefined" && window.__wfActiveSceneId) || "scene-proc";
    applyScenarioPreset(graph, sid);
  };

  function resizeCanvas() {
    var host = document.querySelector("#pg-pipe .pipe-lg-host") || document.querySelector(".pipe-lg-host");
    var canvas = document.getElementById("pipeGraphCanvas");
    if (!host || !canvas || !window.__pipeLgCanvas) return;
    var rect = host.getBoundingClientRect();
    var w = Math.max(480, Math.floor(rect.width) || host.clientWidth || 800);
    var h = Math.max(480, Math.floor(rect.height) || host.clientHeight || Math.floor(window.innerHeight * 0.72));
    var gc = window.__pipeLgCanvas;
    try {
      if (typeof gc.resize === "function") gc.resize(w, h);
      else {
        canvas.width = w;
        canvas.height = h;
        if (gc.bgcanvas) {
          gc.bgcanvas.width = w;
          gc.bgcanvas.height = h;
        }
      }
    } catch (e) {
      canvas.width = w;
      canvas.height = h;
    }
    if (typeof gc.setDirty === "function") gc.setDirty(true, true);
  }

  window.__wfCanvasTool = "pointer";

  window.wfSetCanvasTool = function (mode) {
    window.__wfCanvasTool = mode === "hand" ? "hand" : "pointer";
    var gc = window.__pipeLgCanvas;
    if (gc) {
      gc.allow_dragnodes = window.__wfCanvasTool !== "hand";
    }
    var c = document.getElementById("pipeGraphCanvas");
    if (c) c.style.cursor = window.__wfCanvasTool === "hand" ? "grab" : "";
    document.querySelectorAll(".wf-canvas-tool [data-tool]").forEach(function (btn) {
      btn.classList.toggle("on", btn.getAttribute("data-tool") === window.__wfCanvasTool);
    });
  };

  var _saveT = null;
  function scheduleAutosave() {
    if (!canHttp()) return;
    clearTimeout(_saveT);
    _saveT = setTimeout(saveGraphToServerSilent, 1200);
    touchAutosaveHint();
  }

  function canHttp() {
    return typeof location !== "undefined" && (location.protocol === "http:" || location.protocol === "https:");
  }

  function getGraphPayload() {
    if (!window.__pipeLGraph) return null;
    return { litegraph: window.__pipeLGraph.serialize(), version: 1, saved_at: new Date().toISOString() };
  }

  window.wfGetGraphPayload = getGraphPayload;

  window.wfApplyGraphPayload = function (data) {
    if (!data || !data.litegraph || !window.__pipeLGraph) return false;
    try {
      window.__pipeLGraph.configure(data.litegraph);
      normalizePipelineWfModes(window.__pipeLGraph);
      window.__pipeLGraph.stop();
      window.__pipeLGraph.start();
      resizeCanvas();
      if (typeof window.wfZoomToFit === "function") window.wfZoomToFit();
      if (typeof window.__wfTouchAutosave === "function") window.__wfTouchAutosave();
      return true;
    } catch (e) {
      console.warn("wfApplyGraphPayload", e);
      return false;
    }
  };

  window.savePipelineGraphToServer = function () {
    if (!canHttp()) {
      toast("请通过 http(s) 访问主应用后再保存");
      return;
    }
    var body = getGraphPayload();
    if (!body) return;
    var u = new URL("/api/pipeline/graph", location.href);
    fetch(u.toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body),
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function () {
        toast("编排已保存到服务器（data/pipeline_graph.json）");
      })
      .catch(function (e) {
        toast("保存失败：" + e.message);
      });
  };

  function saveGraphToServerSilent() {
    var body = getGraphPayload();
    if (!body || !canHttp()) return;
    var u = new URL("/api/pipeline/graph", location.href);
    fetch(u.toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body),
    }).catch(function () {});
  }

  window.loadPipelineGraphFromServer = function () {
    if (!canHttp()) return;
    var u = new URL("/api/pipeline/graph", location.href);
    fetch(u.toString(), { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data && data.litegraph && window.__pipeLGraph) {
          window.__pipeLGraph.configure(data.litegraph);
          normalizePipelineWfModes(window.__pipeLGraph);
          window.__pipeLGraph.stop();
          window.__pipeLGraph.start();
          resizeCanvas();
          toast("已从服务器加载编排");
        } else {
          toast("服务器上暂无保存的编排");
        }
      })
      .catch(function (e) {
        toast("加载失败：" + e.message);
      });
  };

  window.resetPipelineGraphDefault = function () {
    if (!window.__pipeLGraph) return;
    if (!confirm("重置为当前场景的默认示例拓扑？")) return;
    if (typeof window.wfBuildGraphForActiveScene === "function") window.wfBuildGraphForActiveScene(window.__pipeLGraph);
    else buildDefaultGraph(window.__pipeLGraph);
    normalizePipelineWfModes(window.__pipeLGraph);
    window.__pipeLGraph.stop();
    window.__pipeLGraph.start();
    resizeCanvas();
    toast("已恢复示例拓扑");
  };

  window.exportPipelineGraphJson = function () {
    var body = getGraphPayload();
    if (!body) return;
    var blob = new Blob([JSON.stringify(body, null, 2)], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "pipeline_graph_" + new Date().toISOString().slice(0, 10) + ".json";
    a.click();
    URL.revokeObjectURL(a.href);
  };

  window.importPipelineGraphJson = function () {
    var inp = document.createElement("input");
    inp.type = "file";
    inp.accept = ".json,application/json";
    inp.onchange = function () {
      var f = inp.files && inp.files[0];
      if (!f) return;
      var fr = new FileReader();
      fr.onload = function () {
        try {
          var data = JSON.parse(fr.result);
          if (data.litegraph && window.__pipeLGraph) {
            window.__pipeLGraph.configure(data.litegraph);
            normalizePipelineWfModes(window.__pipeLGraph);
            window.__pipeLGraph.stop();
            window.__pipeLGraph.start();
            resizeCanvas();
            toast("已导入 JSON");
          } else alert("JSON 中缺少 litegraph 字段");
        } catch (e) {
          alert("解析失败：" + e.message);
        }
      };
      fr.readAsText(f);
    };
    inp.click();
  };

  window.pausePipelineGraph = function () {
    if (typeof window.wfExitPipeQuietMode === "function") window.wfExitPipeQuietMode();
    window.__pipeRunSeqActive = false;
    if (typeof window.wfSetRunHint === "function") window.wfSetRunHint("");
    if (window.__pipeAutosaveInt) {
      clearInterval(window.__pipeAutosaveInt);
      window.__pipeAutosaveInt = null;
    }
    if (window.__pipeZoomPoll) {
      clearInterval(window.__pipeZoomPoll);
      window.__pipeZoomPoll = null;
    }
    if (window.__pipeLGraph) window.__pipeLGraph.stop();
  };

  window.resumePipelineGraph = function () {
    if (window.__pipeLGraph) {
      window.__pipeLGraph.start();
      resizeCanvas();
      if (window.__pipeLgCanvas) startZoomLabelPoll(window.__pipeLgCanvas);
    }
    if (!window.__pipeAutosaveInt && window.__pipeLGraph) {
      window.__pipeAutosaveInt = setInterval(function () {
        if (document.getElementById("pg-pipe") && document.getElementById("pg-pipe").classList.contains("on")) scheduleAutosave();
      }, 40000);
    }
  };

  /** 属性面板「功能详细设计」：按节点类型的可折叠小节（写入 node.properties.design_*） */
  var WF_INSPECTOR_DESIGN = {
    _default: [
      {
        key: "design_capability",
        label: "能力目标与边界",
        rows: 3,
        hint: "本节点职责、前置条件、明确不处理的例外场景。",
        ph: "例：仅消费上游标准宽表；不直连核心账务写库。",
      },
      {
        key: "design_io",
        label: "输入 / 输出契约",
        rows: 4,
        hint: "字段名、主键、版本；与需求书条款（如 F01–F14）对齐处可注明编号。",
        ph: "例：入参 { po_number, risk_level, evidence[] }；出参 HTTP 200 + 业务码。",
      },
      {
        key: "design_integration",
        label: "对接与配置",
        rows: 3,
        hint: "URL、鉴权、多环境、Feature Flag。",
        ph: "例：生产/演练双通道；Header X-Request-Id 链路追踪。",
      },
      {
        key: "design_reliability",
        label: "可靠性 · 幂等 · 安全",
        rows: 3,
        hint: "重试策略、去重键、超时、敏感字段脱敏。",
        ph: "例：同一工单 24h 内重复推送走幂等返回；PII 不落日志明文。",
      },
      {
        key: "design_observability",
        label: "可观测与告警",
        rows: 2,
        hint: "日志关键字、指标名、告警阈值与值班群。",
        ph: "例：投递失败率 >5% / 5m → P2 告警。",
      },
    ],
    "wf/poll": [
      {
        key: "design_capability",
        label: "调度巡检范围",
        rows: 2,
        hint: "拉取哪些队列/状态机；与「无 WebHook」兜底策略的关系。",
        ph: "例：待处理异常列表、审批待办增量；间隔 1～5 分钟可配置。",
      },
      {
        key: "design_io",
        label: "增量水位与断点",
        rows: 3,
        hint: "cursor / updated_since / 最大条数；首跑全量策略。",
        ph: "例：SELECT … WHERE updated_at > :last_sync ORDER BY id LIMIT 500。",
      },
      {
        key: "design_integration",
        label: "数据源与鉴权",
        rows: 3,
        hint: "REST 路径、只读账号、代理与白名单。",
        ph: "例：/api/v1/tasks/pending；OAuth2 Client Credentials。",
      },
      {
        key: "design_reliability",
        label: "容错",
        rows: 2,
        hint: "失败退避、与下游汇聚节点的就绪信号。",
        ph: "例：连续 3 次失败冻结调度并告警，避免打爆对端。",
      },
      {
        key: "design_observability",
        label: "监控",
        rows: 2,
        hint: "每轮拉取条数、耗时、错误码分布。",
        ph: "例：metrics: poll_batch_size, poll_latency_ms。",
      },
    ],
    "wf/webhook": [
      {
        key: "design_capability",
        label: "事件订阅范围",
        rows: 2,
        hint: "审批创建/通过/驳回等事件类型。",
        ph: "例：OA 合同审批、付款申请节点状态变更。",
      },
      {
        key: "design_io",
        label: "回调报文契约",
        rows: 4,
        hint: "Body 结构、签名校验、幂等 Id。",
        ph: "例：HMAC-SHA256 + timestamp；event_id 全局唯一。",
      },
      {
        key: "design_integration",
        label: "暴露端点",
        rows: 3,
        hint: "我方接收 URL、TLS、IP 白名单。",
        ph: "例：POST /integrations/oa/callback；mTLS 可选。",
      },
      {
        key: "design_reliability",
        label: "投递保障",
        rows: 2,
        hint: "厂商重试行为、我方快速 200 与异步落库。",
        ph: "例：先 ACK 再写队列，避免厂商超时重放。",
      },
      {
        key: "design_observability",
        label: "可观测",
        rows: 2,
        hint: "事件量、延迟、验签失败次数。",
        ph: "例：按 event_type 分面看板。",
      },
    ],
    "wf/rest": [
      {
        key: "design_capability",
        label: "API 能力",
        rows: 2,
        hint: "PO、申请单、供应商等对象范围。",
        ph: "例：分页列表 + 单号详情；只读。",
      },
      {
        key: "design_io",
        label: "OpenAPI 映射",
        rows: 4,
        hint: "路径、Query、与内部标准字段映射。",
        ph: "例：po_number ← data.orderNo；金额单位分→元。",
      },
      {
        key: "design_integration",
        label: "运行配置",
        rows: 2,
        hint: "Base URL、Headers、超时。",
        ph: "例：PROCUREMENT_REST_* 环境变量对齐。",
      },
      {
        key: "design_reliability",
        label: "限流与缓存",
        rows: 2,
        hint: "QPS、熔断、短期缓存。",
        ph: "例：429 时指数退避；热点单号 60s 缓存。",
      },
      {
        key: "design_observability",
        label: "监控",
        rows: 2,
        hint: "HTTP 状态、P95 延迟。",
        ph: "",
      },
    ],
    "wf/db": [
      {
        key: "design_capability",
        label: "只读视图范围",
        rows: 2,
        hint: "合同、付款、台账等表或视图。",
        ph: "例：v_contract_payment_readonly。",
      },
      {
        key: "design_io",
        label: "SQL 与字段",
        rows: 4,
        hint: "SELECT 列表、JOIN 键、与主数据对齐字段。",
        ph: "例：WHERE biz_date >= :cursor ORDER BY id。",
      },
      {
        key: "design_integration",
        label: "连接与权限",
        rows: 2,
        hint: "DSN、只读账号、SelectDB/MySQL。",
        ph: "例：SELECTDB_MYSQL_DSN；禁止 DDL/DML。",
      },
      {
        key: "design_reliability",
        label: "一致性",
        rows: 2,
        hint: "延迟只读、与业务库的同步时差说明。",
        ph: "例：T+0 近实时 binlog 同步；对账窗口。",
      },
      {
        key: "design_observability",
        label: "监控",
        rows: 2,
        hint: "慢查询、扫描行数。",
        ph: "",
      },
    ],
    "wf/rpa": [
      {
        key: "design_capability",
        label: "RPA 覆盖范围",
        rows: 2,
        hint: "无 API 系统上的页面/导出流程。",
        ph: "例：UiPath/影刀；登录态与二次验证策略。",
      },
      {
        key: "design_io",
        label: "抓取产物",
        rows: 3,
        hint: "文件、表格、截图；解析为结构化 JSON。",
        ph: "",
      },
      {
        key: "design_integration",
        label: "机器人编排",
        rows: 2,
        hint: "队列、并发、运行窗口（避开业务高峰）。",
        ph: "",
      },
      {
        key: "design_reliability",
        label: "健壮性",
        rows: 2,
        hint: "页面变更检测、人工兜底工单。",
        ph: "",
      },
      {
        key: "design_observability",
        label: "可观测",
        rows: 2,
        hint: "成功率、平均耗时、失败截图归档。",
        ph: "",
      },
    ],
    "wf/merge2": [
      {
        key: "design_capability",
        label: "汇聚语义",
        rows: 2,
        hint: "调度与事件双源合流；去重与时间对齐规则。",
        ph: "例：同一单据以事件优先、轮询补偿缺失。",
      },
      {
        key: "design_io",
        label: "合流键",
        rows: 3,
        hint: "主键：单号/流程实例 ID；冲突解决策略。",
        ph: "",
      },
      {
        key: "design_integration",
        label: "实现要点",
        rows: 2,
        hint: "内存合并 vs 消息总线。",
        ph: "",
      },
      {
        key: "design_reliability",
        label: "背压",
        rows: 2,
        hint: "队列堆积阈值。",
        ph: "",
      },
      {
        key: "design_observability",
        label: "监控",
        rows: 2,
        hint: "双源延迟差、重复条数。",
        ph: "",
      },
    ],
    "wf/merge3": [
      {
        key: "design_capability",
        label: "三源汇聚",
        rows: 2,
        hint: "采购 / 合同·OA / 付款·财务 断点串联。",
        ph: "例：任一路径先到则部分就绪，全齐才下游。",
      },
      {
        key: "design_io",
        label: "对齐键与宽表字段",
        rows: 4,
        hint: "PO、合同号、付款单号映射。",
        ph: "",
      },
      {
        key: "design_integration",
        label: "实现",
        rows: 2,
        hint: "流式 Join 或批窗口。",
        ph: "",
      },
      {
        key: "design_reliability",
        label: "缺失容忍",
        rows: 2,
        hint: "超时未齐单如何标记、是否进异常看板。",
        ph: "",
      },
      {
        key: "design_observability",
        label: "监控",
        rows: 2,
        hint: "齐套率、等待时长分布。",
        ph: "",
      },
    ],
    "wf/etl": [
      {
        key: "design_capability",
        label: "主数据对齐",
        rows: 2,
        hint: "申请·合同·PO·验收·发票·付款 主键归一。",
        ph: "例：生成标准宽表供规则引擎消费。",
      },
      {
        key: "design_io",
        label: "清洗规则",
        rows: 4,
        hint: "去重、撤销单、币种税率、别名表。",
        ph: "",
      },
      {
        key: "design_integration",
        label: "存储",
        rows: 2,
        hint: "落库/内存；与 dashboard API 字段对齐。",
        ph: "",
      },
      {
        key: "design_reliability",
        label: "质量",
        rows: 2,
        hint: "脏数据隔离、死信。",
        ph: "",
      },
      {
        key: "design_observability",
        label: "监控",
        rows: 2,
        hint: "对齐成功率、字段空值率。",
        ph: "",
      },
    ],
    "wf/threeway": [
      {
        key: "design_capability",
        label: "三单匹配（F04）",
        rows: 2,
        hint: "PO · GRN · 发票；容差与冻结条件。",
        ph: "例：数量 ±2%、单价 ±1%、税率须一致；超差冻结付款。",
      },
      {
        key: "design_io",
        label: "规则参数",
        rows: 4,
        hint: "阈值表版本、供应商白名单例外。",
        ph: "",
      },
      {
        key: "design_integration",
        label: "规则引擎",
        rows: 2,
        hint: "内置引擎 / 外接 Drools 等。",
        ph: "",
      },
      {
        key: "design_reliability",
        label: "审计",
        rows: 2,
        hint: "命中依据可追溯、证据包。",
        ph: "",
      },
      {
        key: "design_observability",
        label: "指标",
        rows: 2,
        hint: "命中率、人工复核占比。",
        ph: "",
      },
    ],
    "wf/fourflow": [
      {
        key: "design_capability",
        label: "四流一致（F05）",
        rows: 2,
        hint: "合同流·资金流·发票流·物流/收货 主体一致。",
        ph: "例：签约主体、付款申请方、发票销方、收货信息。",
      },
      {
        key: "design_io",
        label: "比对维度",
        rows: 4,
        hint: "同一合同项下付款发起人溯源等客户原话场景。",
        ph: "",
      },
      {
        key: "design_integration",
        label: "外部数据",
        rows: 2,
        hint: "金税/工商接口可选。",
        ph: "",
      },
      {
        key: "design_reliability",
        label: "解释性",
        rows: 2,
        hint: "输出结构化差异列表供 Agent 引用。",
        ph: "",
      },
      {
        key: "design_observability",
        label: "监控",
        rows: 2,
        hint: "不一致单量趋势。",
        ph: "",
      },
    ],
    "wf/agent": [
      {
        key: "design_capability",
        label: "智能体职责",
        rows: 3,
        hint: "非经营性采购研判；规则 + LLM 分工。",
        ph: "例：结构化结论必须来自规则命中；LLM 仅生成说明与建议动作。",
      },
      {
        key: "design_io",
        label: "提示词与工具",
        rows: 4,
        hint: "可调用的 MCP/API；输出 JSON Schema。",
        ph: "",
      },
      {
        key: "design_integration",
        label: "模型与网关",
        rows: 2,
        hint: "DeepSeek / 火山；Key 与限流。",
        ph: "",
      },
      {
        key: "design_reliability",
        label: "安全与合规",
        rows: 2,
        hint: "敏感字段脱敏、留痕、人工复核闸口。",
        ph: "",
      },
      {
        key: "design_observability",
        label: "可观测",
        rows: 2,
        hint: "Token、延迟、工具调用成功率。",
        ph: "",
      },
    ],
    "wf/decision": [
      {
        key: "design_capability",
        label: "分流策略",
        rows: 2,
        hint: "低 / 中 / 高 → 放行 / 复核 / 拦截。",
        ph: "",
      },
      {
        key: "design_io",
        label: "决策表",
        rows: 4,
        hint: "条件矩阵、优先级、默认分支。",
        ph: "",
      },
      {
        key: "design_integration",
        label: "与工单/审批联动",
        rows: 2,
        hint: "自动过审阈值、升级 CFO 规则。",
        ph: "",
      },
      {
        key: "design_reliability",
        label: "override",
        rows: 2,
        hint: "人工覆盖审计。",
        ph: "",
      },
      {
        key: "design_observability",
        label: "监控",
        rows: 2,
        hint: "各分支占比。",
        ph: "",
      },
    ],
    "wf/callback": [
      {
        key: "design_capability",
        label: "推送能力（F12/F13）",
        rows: 2,
        hint: "飞书机器人通知、OA 工单创建/回写。",
        ph: "例：高风险单强制创建工单并 @ 采购负责人。",
      },
      {
        key: "design_io",
        label: "消息体与字段映射",
        rows: 4,
        hint: "标题、摘要、风险等级、跳转链接、业务单号。",
        ph: "例：{ title, text, po_number, wo_id, feishu_msg_type }。",
      },
      {
        key: "design_integration",
        label: "通道配置",
        rows: 3,
        hint: "FEISHU_WEBHOOK_URL、OA_WEBHOOK_URL；多租户路由。",
        ph: "例：按部门路由不同 Webhook；演练环境开关。",
      },
      {
        key: "design_reliability",
        label: "幂等 · 重试 · 超时",
        rows: 3,
        hint: "同一工单多次推送策略；HTTP 超时与重试上限。",
        ph: "例：Idempotency-Key = hash(wo_id+action)；3 次重试。",
      },
      {
        key: "design_observability",
        label: "投递监控与告警",
        rows: 2,
        hint: "成功率、失败样本、飞书侧错误码。",
        ph: "例：连续失败触发备用通道或短信兜底（若采购）。",
      },
    ],
    "wf/audit": [
      {
        key: "design_capability",
        label: "审计留痕（F14）",
        rows: 2,
        hint: "月报 HTML、审计底稿导出、不可篡改存储（可选）。",
        ph: "",
      },
      {
        key: "design_io",
        label: "报表结构",
        rows: 4,
        hint: "章节、指标、附录数据源。",
        ph: "",
      },
      {
        key: "design_integration",
        label: "存储与访问",
        rows: 2,
        hint: "reports/ 目录、下载权限。",
        ph: "",
      },
      {
        key: "design_reliability",
        label: "归档策略",
        rows: 2,
        hint: "保留周期、脱敏版本。",
        ph: "",
      },
      {
        key: "design_observability",
        label: "监控",
        rows: 2,
        hint: "生成失败告警。",
        ph: "",
      },
    ],
  };

  function renderInspectorDesignSections(node) {
    var mount = document.getElementById("wfInspDesignMount");
    var wrap = document.getElementById("wfInspDesignWrap");
    var intro = document.getElementById("wfInspDesignIntro");
    if (!mount) return;
    mount.innerHTML = "";
    if (!node || !node.type || String(node.type).indexOf("wf/") !== 0) {
      if (wrap) wrap.style.display = "none";
      return;
    }
    if (wrap) wrap.style.display = "";
    if (intro) intro.style.display = "";
    var schema = WF_INSPECTOR_DESIGN[node.type] || WF_INSPECTOR_DESIGN._default;
    if (!node.properties) node.properties = {};
    schema.forEach(function (sec, idx) {
      var det = document.createElement("details");
      det.className = "wf-insp-details";
      det.open = idx === 0;
      var sum = document.createElement("summary");
      sum.textContent = sec.label;
      det.appendChild(sum);
      var ta = document.createElement("textarea");
      ta.className = "wf-insp-design-ta";
      ta.rows = sec.rows || 3;
      ta.placeholder = sec.ph || "";
      ta.value = node.properties[sec.key] != null ? String(node.properties[sec.key]) : "";
      ta.addEventListener("input", function () {
        if (!window.__pipeInspectorNode || window.__pipeInspectorNode.id !== node.id) return;
        if (!node.properties) node.properties = {};
        node.properties[sec.key] = ta.value;
        markGraphDirty();
        touchAutosaveHint();
      });
      det.appendChild(ta);
      if (sec.hint) {
        var hp = document.createElement("p");
        hp.className = "wf-insp-design-hint";
        hp.textContent = sec.hint;
        det.appendChild(hp);
      }
      mount.appendChild(det);
    });
  }

  function wireInspector(graphcanvas) {
    if (wireInspector._ok) return;
    wireInspector._ok = true;
    var empty = document.getElementById("wfInspEmpty");
    var body = document.getElementById("wfInspBody");
    var titleEl = document.getElementById("wfInspTitle");
    var inpSys = document.getElementById("wfInpSys");
    var inpNotes = document.getElementById("wfInpNotes");
    var inpRun = document.getElementById("wfInpLastRun");

    function fillFromNode(node) {
      window.__pipeInspectorNode = node;
      if (!node) {
        if (empty) empty.style.display = "";
        if (body) body.style.display = "none";
        renderInspectorDesignSections(null);
        return;
      }
      if (empty) empty.style.display = "none";
      if (body) body.style.display = "flex";
      if (titleEl) titleEl.textContent = node.title || node.type || "节点";
      if (inpSys) {
        inpSys.oninput = null;
        inpSys.value = (node.properties && node.properties.source_system) || "";
        inpSys.oninput = function () {
          if (!window.__pipeInspectorNode || window.__pipeInspectorNode.id !== node.id) return;
          if (!node.properties) node.properties = {};
          node.properties.source_system = inpSys.value;
          markGraphDirty();
          touchAutosaveHint();
        };
      }
      if (inpNotes) {
        inpNotes.oninput = null;
        inpNotes.value = (node.properties && node.properties.adapter_notes) || "";
        inpNotes.oninput = function () {
          if (!window.__pipeInspectorNode || window.__pipeInspectorNode.id !== node.id) return;
          if (!node.properties) node.properties = {};
          node.properties.adapter_notes = inpNotes.value;
          markGraphDirty();
          touchAutosaveHint();
        };
      }
      if (inpRun) inpRun.textContent = (node.properties && node.properties.last_run) || "尚无运行记录";
      renderInspectorDesignSections(node);
    }

    graphcanvas.onSelectionChange = function () {
      var sel = graphcanvas.selected_nodes;
      var keys = Object.keys(sel || {});
      if (keys.length !== 1) {
        fillFromNode(null);
        return;
      }
      fillFromNode(sel[keys[0]]);
    };
  }

  window.wfAddNode = function (type) {
    var g = window.__pipeLGraph;
    var gc = window.__pipeLgCanvas;
    var G = window.LiteGraph;
    if (!g || !gc || !G) {
      toast("画布未就绪");
      return;
    }
    var n = G.createNode(type);
    if (!n) {
      toast("未知节点类型：" + type);
      return;
    }
    var c = gc.canvas;
    var pos = gc.ds.convertCanvasToOffset([c.width * 0.38, c.height * 0.36]);
    n.pos = [pos[0] + (Math.random() * 40 - 20), pos[1] + (Math.random() * 40 - 20)];
    g.add(n);
    if (typeof gc.selectNodes === "function") gc.selectNodes([n]);
    markGraphDirty();
    scheduleAutosave();
    toast("已添加节点，可拖拽连线");
  };

  window.wfZoomToFit = function () {
    var g = window.__pipeLGraph;
    var gc = window.__pipeLgCanvas;
    if (!gc) return;
    if (!g || !g._nodes || !g._nodes.length) {
      gc.ds.scale = 1;
      gc.ds.offset = [0, 0];
      gc.setDirty(true, true);
      return;
    }
    var minX = Infinity,
      minY = Infinity,
      maxX = -Infinity,
      maxY = -Infinity;
    g._nodes.forEach(function (n) {
      minX = Math.min(minX, n.pos[0]);
      minY = Math.min(minY, n.pos[1]);
      maxX = Math.max(maxX, n.pos[0] + n.size[0]);
      maxY = Math.max(maxY, n.pos[1] + n.size[1]);
    });
    var gw = maxX - minX + 120;
    var gh = maxY - minY + 120;
    var cw = gc.canvas.width;
    var ch = gc.canvas.height;
    var s = Math.min(cw / gw, ch / gh, 1.2) * 0.92;
    s = Math.max(0.25, Math.min(s, 1.5));
    gc.ds.scale = s;
    gc.ds.offset[0] = -minX + (cw / s - gw) * 0.5 + 40;
    gc.ds.offset[1] = -minY + (ch / s - gh) * 0.5 + 40;
    gc.setDirty(true, true);
  };

  window.wfZoomDelta = function (d) {
    var gc = window.__pipeLgCanvas;
    if (!gc) return;
    var ns = gc.ds.scale * (1 + d);
    ns = Math.max(0.2, Math.min(ns, 2.2));
    gc.setZoom(ns, [gc.canvas.width * 0.5, gc.canvas.height * 0.5]);
  };

  window.wfRunSelectedNode = function () {
    var gc = window.__pipeLgCanvas;
    if (!gc || !gc.selected_nodes) return;
    var keys = Object.keys(gc.selected_nodes);
    if (keys.length !== 1) {
      toast("请选中一个节点");
      return;
    }
    var n = gc.selected_nodes[keys[0]];
    if (typeof n.onExecute === "function") {
      try {
        n.onExecute();
      } catch (e) {
        console.warn(e);
      }
      markGraphDirty();
      refreshInspectorIfCurrent(n);
      toast("已执行当前节点");
    }
  };

  function startZoomLabelPoll(graphcanvas) {
    if (window.__pipeZoomPoll) clearInterval(window.__pipeZoomPoll);
    window.__pipeZoomPoll = setInterval(function () {
      if (!document.getElementById("pg-pipe") || !document.getElementById("pg-pipe").classList.contains("on")) return;
      var el = document.getElementById("wfZoomPct");
      if (el && graphcanvas && graphcanvas.ds) el.textContent = Math.round(graphcanvas.ds.scale * 100) + "%";
    }, 200);
  }

  window.initPipelineGraphEditor = function () {
    var canvas = document.getElementById("pipeGraphCanvas");
    if (!canvas || !document.getElementById("pg-pipe").classList.contains("on")) return;
    if (window.__pipeGraphBooting && !window.LiteGraph) return;

    function boot(err) {
      window.__pipeGraphBooting = false;
      if (err || !window.LiteGraph) {
        console.error(err || "LiteGraph missing");
        var hint = document.getElementById("pipeGraphLoadErr");
        if (hint) {
          hint.style.display = "block";
          hint.textContent =
            "未能加载 LiteGraph 画布脚本。已尝试本站 /static/vendor/litegraph/ 与 CDN；请确认已部署 vendor 文件或网络可访问 jsDelivr。";
        }
        return;
      }
      var hintOk = document.getElementById("pipeGraphLoadErr");
      if (hintOk) {
        hintOk.style.display = "none";
        hintOk.textContent = "";
      }
      loadCssPipe();
      injectLitegraphMenuLightCss();
      applyLiteGraphLightTheme(window.LiteGraph);
      registerNodeTypes();

      if (window.__pipeLGraph) {
        resumePipelineGraph();
        return;
      }

      var graph = new window.LGraph();
      graph.onAfterChange = function () {
        scheduleAutosave();
        clearTimeout(window.__wfSceneLocSaveT);
        window.__wfSceneLocSaveT = setTimeout(function () {
          if (
            typeof window.wfPersistSceneGraph === "function" &&
            typeof window.wfGetActiveSceneId === "function"
          ) {
            window.wfPersistSceneGraph(window.wfGetActiveSceneId());
          }
        }, 2000);
      };
      var graphcanvas = new window.LGraphCanvas(canvas, graph);
      graphcanvas.background_image = null;
      graphcanvas.clear_background = true;
      graphcanvas.clear_background_color = "#F4F5F8";
      graphcanvas.render_canvas_border = false;
      graphcanvas.render_curved_connections = true;
      graphcanvas.links_render_mode = window.LiteGraph.SPLINE_LINK;
      graphcanvas.round_radius = 10;
      graphcanvas.default_connection_color = {
        input_off: "#9CA3AF",
        input_on: "#155EEF",
        output_off: "#9CA3AF",
        output_on: "#155EEF",
      };
      graphcanvas.default_link_color = "#155EEF";

      attachDotGridPattern(graphcanvas);
      wireInspector(graphcanvas);

      window.__pipeLGraph = graph;
      window.__pipeLgCanvas = graphcanvas;

      graphcanvas.allow_searchbox = true;
      graphcanvas.allow_dragcanvas = true;
      try {
        canvas.focus();
      } catch (e1) {}
      if (typeof window.wfSetCanvasTool === "function") window.wfSetCanvasTool("pointer");

      graphcanvas.onNodeMoved = scheduleAutosave;

      if (window.__pipeAutosaveInt) clearInterval(window.__pipeAutosaveInt);
      window.__pipeAutosaveInt = setInterval(function () {
        if (document.getElementById("pg-pipe") && document.getElementById("pg-pipe").classList.contains("on")) scheduleAutosave();
      }, 40000);

      startZoomLabelPoll(graphcanvas);
      wirePipeCanvasQuietMode(canvas);

      function finishGraphBoot() {
        normalizePipelineWfModes(graph);
        graph.start();
        setTimeout(function () {
          resizeCanvas();
          wfZoomToFit();
        }, 60);
        if (typeof window.wfRefreshScenarioRail === "function") window.wfRefreshScenarioRail();
      }

      var localPayload =
        typeof window.wfLoadActiveSceneGraph === "function" ? window.wfLoadActiveSceneGraph() : null;
      if (localPayload && localPayload.litegraph && localPayload.litegraph.nodes && localPayload.litegraph.nodes.length) {
        graph.configure(localPayload.litegraph);
        finishGraphBoot();
      } else if (canHttp()) {
        var u = new URL("/api/pipeline/graph", location.href);
        fetch(u.toString(), { credentials: "same-origin", cache: "no-store" })
          .then(function (r) {
            return r.json();
          })
          .then(function (data) {
            if (data && data.litegraph && data.litegraph.nodes && data.litegraph.nodes.length) {
              graph.configure(data.litegraph);
              if (typeof window.wfMigrateServerGraphToActiveScene === "function")
                window.wfMigrateServerGraphToActiveScene(data);
            } else if (typeof window.wfBuildGraphForActiveScene === "function") {
              window.wfBuildGraphForActiveScene(graph);
            } else {
              buildDefaultGraph(graph);
              applyScenarioPreset(graph, window.__wfActiveSceneId || "scene-proc");
            }
            finishGraphBoot();
          })
          .catch(function () {
            if (typeof window.wfBuildGraphForActiveScene === "function") window.wfBuildGraphForActiveScene(graph);
            else {
              buildDefaultGraph(graph);
              applyScenarioPreset(graph, window.__wfActiveSceneId || "scene-proc");
            }
            finishGraphBoot();
          });
      } else {
        if (typeof window.wfBuildGraphForActiveScene === "function") window.wfBuildGraphForActiveScene(graph);
        else {
          buildDefaultGraph(graph);
          applyScenarioPreset(graph, window.__wfActiveSceneId || "scene-proc");
        }
        finishGraphBoot();
      }

      window.addEventListener("resize", resizeCanvas);
    }

    if (window.LiteGraph) {
      boot();
      return;
    }
    window.__pipeGraphBooting = true;
    loadLiteGraphScript(function (err) {
      boot(err);
    });
  };

  window.resizePipelineGraphEditor = resizeCanvas;

  function setNodeRunGlow(n, on) {
    if (!n) return;
    if (n._wfSaveBox === undefined) n._wfSaveBox = n.boxcolor;
    n.boxcolor = on ? "#93C5FD" : n._wfSaveBox;
    markGraphDirty();
  }

  window.runPipelineGraphOnce = function () {
    var g = window.__pipeLGraph;
    if (!g || !g._nodes || !g._nodes.length) {
      toast("画布未就绪");
      return;
    }
    if (window.__pipeRunSeqActive) {
      toast("请等待当前运行结束");
      return;
    }
    window.__pipeRunSeqActive = true;
    var nodes = g._nodes.slice();
    var i = 0;
    var prev = null;
    function hint(s) {
      if (typeof window.wfSetRunHint === "function") window.wfSetRunHint(s);
    }
    function clearHintLater() {
      setTimeout(function () {
        if (typeof window.wfSetRunHint === "function") window.wfSetRunHint("");
      }, 1800);
    }
    hint("开始运行…");
    function step() {
      if (prev) setNodeRunGlow(prev, false);
      if (i >= nodes.length) {
        window.__pipeRunSeqActive = false;
        markGraphDirty();
        hint("运行完成");
        clearHintLater();
        if (typeof window.wfOnPipelineRunComplete === "function") window.wfOnPipelineRunComplete();
        else toast("运行完成");
        return;
      }
      var n = nodes[i];
      prev = n;
      setNodeRunGlow(n, true);
      hint("执行：" + (n.title || n.type || "节点"));
      if (typeof n.onExecute === "function") {
        try {
          n.onExecute();
        } catch (e) {
          console.warn("onExecute", n.type, e);
        }
      }
      i++;
      setTimeout(step, 220);
    }
    step();
  };
})();
