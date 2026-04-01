/**
 * 风控工作流 · LiteGraph.js（Dify 风浅色编排）
 * 触发 → 多源适配(API/DB/RPA) → 汇聚/ETL → 风控智能体 → 决策 → 回调/审计
 */
(function () {
  var LG_URL = "https://cdn.jsdelivr.net/npm/litegraph.js@0.7.18/build/litegraph.min.js";
  var LG_CSS = "https://cdn.jsdelivr.net/npm/litegraph.js@0.7.18/css/litegraph.css";

  function loadScript(src, cb) {
    var s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.onload = cb;
    s.onerror = function () {
      console.error("LiteGraph load failed:", src);
      cb(new Error("load fail"));
    };
    document.head.appendChild(s);
  }

  function loadCss(href) {
    if (document.querySelector('link[data-pipe-lg="1"]')) return;
    var l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = href;
    l.setAttribute("data-pipe-lg", "1");
    document.head.appendChild(l);
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
        this.properties = { last_run: "", source_system: "", adapter_notes: "" };
        this.size = [236, 92];
        this.color = headerColor || "#155EEF";
        this.bgcolor = "#FFFFFF";
        this.boxcolor = "#E8ECF3";
        this.shape = "round";
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
            setNodeLastRun(n, "GET /api/health → " + JSON.stringify(j));
          })
          .catch(function (e) {
            setNodeLastRun(n, "health 失败: " + e.message);
          });
      },
      "wf/webhook": function () {
        setNodeLastRun(this, "Webhook 模拟触发 " + new Date().toISOString());
      },
      "wf/rest": function () {
        var n = this;
        if (!canHttp()) return;
        fetch(new URL("/api/datasources/status", location.href), { credentials: "same-origin", cache: "no-store" })
          .then(function (r) {
            return r.json();
          })
          .then(function (j) {
            setNodeLastRun(n, "GET /api/datasources/status → " + JSON.stringify(j));
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
            setNodeLastRun(n, "GET /api/integrations/status → " + JSON.stringify(j).slice(0, 300));
          })
          .catch(function (e) {
            setNodeLastRun(n, "integrations 失败: " + e.message);
          });
      },
      "wf/rpa": function () {
        setNodeLastRun(this, "RPA：需对接 UiPath / 影刀等；此处为占位节点");
      },
      "wf/merge2": function () {
        this.setOutputData(0, { a: this.getInputData(0), b: this.getInputData(1), t: Date.now() });
        setNodeLastRun(this, "已合并 2 路输入到输出");
      },
      "wf/merge3": function () {
        this.setOutputData(0, {
          a: this.getInputData(0),
          b: this.getInputData(1),
          c: this.getInputData(2),
          t: Date.now(),
        });
        setNodeLastRun(this, "已合并 3 路输入到输出");
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
        setNodeLastRun(this, "已唤起右侧风控 AI 对话");
        if (typeof window.openChatAndSend === "function")
          window.openChatAndSend(
            "请结合当前节点对接的系统与数据，分析是否存在非经营性采购风险项，并给出可执行建议（条列）。"
          );
      },
      "wf/decision": function () {
        var v = this.getInputData(0);
        this.setOutputData(0, v);
        this.setOutputData(1, v);
        this.setOutputData(2, v);
        setNodeLastRun(this, "决策分流：研判结果已复制到低 / 中 / 高三路（演示）");
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
            setNodeLastRun(n, "GET /api/notifications 条数 ≈ " + c);
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
            setNodeLastRun(n, "GET /api/reports HTML 报告数 = " + c);
          })
          .catch(function (e) {
            setNodeLastRun(n, "reports 失败: " + e.message);
          });
      },
    };

    var types = [
      ["wf/poll", "定时轮询", [["触发", SLOT]], null, "#155EEF"],
      ["wf/webhook", "审批流 Webhook", [["触发", SLOT]], null, "#2563EB"],
      ["wf/rest", "REST API 拉取", [["原始数据", SLOT]], null, "#10B981"],
      ["wf/db", "只读库 SQL", [["原始数据", SLOT]], null, "#8B5CF6"],
      ["wf/rpa", "RPA 抓取", [["原始数据", SLOT]], null, "#F59E0B"],
      [
        "wf/merge2",
        "多源汇聚 · 2 路",
        [["合流", SLOT]],
        [
          ["入 A", SLOT],
          ["入 B", SLOT],
        ],
        "#64748B",
      ],
      [
        "wf/merge3",
        "多源汇聚 · 3 路",
        [["合流", SLOT]],
        [
          ["入 A", SLOT],
          ["入 B", SLOT],
          ["入 C", SLOT],
        ],
        "#64748B",
      ],
      [
        "wf/etl",
        "清洗与标准化",
        [["标准宽表", SLOT]],
        [
          ["触发侧", SLOT],
          ["数据侧", SLOT],
        ],
        "#059669",
      ],
      ["wf/agent", "风控智能体", [["研判", SLOT]], [["标准宽表", SLOT]], "#7C3AED"],
      [
        "wf/decision",
        "决策分流",
        [
          ["低风险", SLOT],
          ["中风险", SLOT],
          ["高风险", SLOT],
        ],
        [["研判", SLOT]],
        "#0891B2",
      ],
      ["wf/callback", "回调 OA / IM", [["已推送", SLOT]], [["任一路径", SLOT]], "#0D9488"],
      ["wf/audit", "日志与审计", null, [["已推送", SLOT]], "#6B7280"],
    ];

    types.forEach(function (row) {
      var Ctor = defNode(row[1], row[2], row[3], row[4]);
      Ctor.title = row[1];
      var fn = exec[row[0]];
      if (fn) Ctor.prototype.onExecute = fn;
      G.registerNodeType(row[0], Ctor);
    });
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

    var poll = add("wf/poll", 60, 40);
    var hook = add("wf/webhook", 60, 160);
    var m2 = add("wf/merge2", 360, 100);
    var rest = add("wf/rest", 60, 300);
    var db = add("wf/db", 60, 420);
    var rpa = add("wf/rpa", 60, 540);
    var m3 = add("wf/merge3", 360, 400);
    var etl = add("wf/etl", 680, 240);
    var agent = add("wf/agent", 980, 250);
    var dec = add("wf/decision", 1240, 220);
    var cb = add("wf/callback", 1500, 250);
    var aud = add("wf/audit", 1760, 250);

    if (poll && m2) poll.connect(0, m2, 0);
    if (hook && m2) hook.connect(0, m2, 1);
    if (m2 && etl) m2.connect(0, etl, 0);
    if (rest && m3) rest.connect(0, m3, 0);
    if (db && m3) db.connect(0, m3, 1);
    if (rpa && m3) rpa.connect(0, m3, 2);
    if (m3 && etl) m3.connect(0, etl, 1);
    if (etl && agent) etl.connect(0, agent, 0);
    if (agent && dec) agent.connect(0, dec, 0);
    if (dec && cb) dec.connect(2, cb, 0);
    if (cb && aud) cb.connect(0, aud, 0);
  }

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
    if (!confirm("重置为默认示例拓扑？")) return;
    buildDefaultGraph(window.__pipeLGraph);
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
          hint.textContent = "节点画布依赖 CDN 加载 LiteGraph.js，请检查网络或稍后重试。";
        }
        return;
      }
      var hintOk = document.getElementById("pipeGraphLoadErr");
      if (hintOk) {
        hintOk.style.display = "none";
        hintOk.textContent = "";
      }
      loadCss(LG_CSS);
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

      graphcanvas.onNodeMoved = scheduleAutosave;

      if (window.__pipeAutosaveInt) clearInterval(window.__pipeAutosaveInt);
      window.__pipeAutosaveInt = setInterval(function () {
        if (document.getElementById("pg-pipe") && document.getElementById("pg-pipe").classList.contains("on")) scheduleAutosave();
      }, 40000);

      startZoomLabelPoll(graphcanvas);

      if (canHttp()) {
        var u = new URL("/api/pipeline/graph", location.href);
        fetch(u.toString(), { credentials: "same-origin", cache: "no-store" })
          .then(function (r) {
            return r.json();
          })
          .then(function (data) {
            if (data && data.litegraph && data.litegraph.nodes && data.litegraph.nodes.length) {
              graph.configure(data.litegraph);
            } else {
              buildDefaultGraph(graph);
            }
            graph.start();
            setTimeout(function () {
              resizeCanvas();
              wfZoomToFit();
            }, 60);
          })
          .catch(function () {
            buildDefaultGraph(graph);
            graph.start();
            setTimeout(function () {
              resizeCanvas();
              wfZoomToFit();
            }, 60);
          });
      } else {
        buildDefaultGraph(graph);
        graph.start();
        setTimeout(function () {
          resizeCanvas();
          wfZoomToFit();
        }, 60);
      }

      window.addEventListener("resize", resizeCanvas);
    }

    if (window.LiteGraph) {
      boot();
      return;
    }
    window.__pipeGraphBooting = true;
    loadScript(LG_URL, function (e) {
      boot(e);
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
        toast("运行完成：下方「运行结果」已展开，可点按钮继续操作");
        if (typeof window.wfOnPipelineRunComplete === "function") window.wfOnPipelineRunComplete();
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
