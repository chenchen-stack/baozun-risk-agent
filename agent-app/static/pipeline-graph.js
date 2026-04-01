/**
 * 风控工作流 · 真实节点编排画布（LiteGraph.js）
 * 支持：拖拽、连线、右键添加节点、缩放平移；保存/加载至服务端。
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

  function registerNodeTypes() {
    var G = window.LiteGraph;
    if (!G || registerNodeTypes._ok) return;
    registerNodeTypes._ok = true;

    var SLOT = "risk_flow";

    function defNode(title, outs, ins, color) {
      return function NodeImpl() {
        var i, o;
        for (i = 0; ins && i < ins.length; i++) this.addInput(ins[i][0], ins[i][1] || SLOT);
        for (o = 0; outs && o < outs.length; o++) this.addOutput(outs[o][0], outs[o][1] || SLOT);
        this.properties = {};
        this.size = [200, 68];
        this.color = color || "#2d3a4f";
        this.bgcolor = "#1a2332";
      };
    }

    var types = [
      ["wf/poll", "定时轮询", [["触发", SLOT]], null, "#1e3a5f"],
      ["wf/webhook", "Webhook 事件", [["触发", SLOT]], null, "#1e3a5f"],
      ["wf/rest", "REST 适配", [["原始数据", SLOT]], null, "#1a4d7a"],
      ["wf/db", "只读库 SQL", [["原始数据", SLOT]], null, "#3d2a5c"],
      ["wf/rpa", "RPA 抓取", [["原始数据", SLOT]], null, "#5c4a1a"],
      [
        "wf/merge2",
        "合并(2路)",
        [["出", SLOT]],
        [
          ["入A", SLOT],
          ["入B", SLOT],
        ],
        "#2a3f3f",
      ],
      [
        "wf/merge3",
        "合并(3路)",
        [["出", SLOT]],
        [
          ["入A", SLOT],
          ["入B", SLOT],
          ["入C", SLOT],
        ],
        "#2a3f3f",
      ],
      [
        "wf/etl",
        "ETL 标准化",
        [["宽表", SLOT]],
        [
          ["触发侧", SLOT],
          ["数据侧", SLOT],
        ],
        "#1a4d4a",
      ],
      ["wf/agent", "风控 Agent", [["研判", SLOT]], [["宽表", SLOT]], "#0d5c4f"],
      [
        "wf/decision",
        "决策分流",
        [
          ["低", SLOT],
          ["中", SLOT],
          ["高", SLOT],
        ],
        [["研判", SLOT]],
        "#5c1a3a",
      ],
      ["wf/callback", "回调 OA/飞书", [["已推送", SLOT]], [["任一风险档", SLOT]], "#2d5018"],
      ["wf/audit", "审计与月报", null, [["已推送", SLOT]], "#3a3a3a"],
    ];

    types.forEach(function (row) {
      var Ctor = defNode(row[1], row[2], row[3], row[4]);
      Ctor.title = row[1];
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

    var poll = add("wf/poll", 80, 40);
    var hook = add("wf/webhook", 80, 140);
    var m2 = add("wf/merge2", 340, 90);
    var rest = add("wf/rest", 80, 280);
    var db = add("wf/db", 80, 380);
    var rpa = add("wf/rpa", 80, 480);
    var m3 = add("wf/merge3", 340, 380);
    var etl = add("wf/etl", 620, 220);
    var agent = add("wf/agent", 900, 230);
    var dec = add("wf/decision", 1140, 200);
    var cb = add("wf/callback", 1380, 230);
    var aud = add("wf/audit", 1620, 230);

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
    var host = document.querySelector(".pipe-lg-host");
    var canvas = document.getElementById("pipeGraphCanvas");
    if (!host || !canvas || !window.__pipeLgCanvas) return;
    var w = Math.max(640, host.clientWidth || host.offsetWidth);
    var h = Math.max(420, Math.min(720, Math.floor(window.innerHeight * 0.62)));
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
      alert("请通过 http(s) 访问主应用后再保存");
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
        alert("编排已保存到服务器 data/pipeline_graph.json");
      })
      .catch(function (e) {
        alert("保存失败：" + e.message);
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
        } else {
          alert("服务器上暂无保存的编排，已保留当前画布");
        }
      })
      .catch(function (e) {
        alert("加载失败：" + e.message);
      });
  };

  window.resetPipelineGraphDefault = function () {
    if (!window.__pipeLGraph) return;
    if (!confirm("重置为默认示例拓扑？")) return;
    buildDefaultGraph(window.__pipeLGraph);
    window.__pipeLGraph.stop();
    window.__pipeLGraph.start();
    resizeCanvas();
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
    if (window.__pipeAutosaveInt) {
      clearInterval(window.__pipeAutosaveInt);
      window.__pipeAutosaveInt = null;
    }
    if (window.__pipeLGraph) window.__pipeLGraph.stop();
  };

  window.resumePipelineGraph = function () {
    if (window.__pipeLGraph) {
      window.__pipeLGraph.start();
      resizeCanvas();
    }
    if (!window.__pipeAutosaveInt && window.__pipeLGraph) {
      window.__pipeAutosaveInt = setInterval(function () {
        if (document.getElementById("pg-pipe") && document.getElementById("pg-pipe").classList.contains("on")) scheduleAutosave();
      }, 40000);
    }
  };

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
      registerNodeTypes();

      if (window.__pipeLGraph) {
        resumePipelineGraph();
        return;
      }

      var graph = new window.LGraph();
      var graphcanvas = new window.LGraphCanvas(canvas, graph);
      graphcanvas.background_image = null;
      graphcanvas.clear_background = true;
      if (graphcanvas.bgcolor !== undefined) graphcanvas.bgcolor = "#0c1222";

      window.__pipeLGraph = graph;
      window.__pipeLgCanvas = graphcanvas;

      graphcanvas.onNodeMoved = scheduleAutosave;

      if (window.__pipeAutosaveInt) clearInterval(window.__pipeAutosaveInt);
      window.__pipeAutosaveInt = setInterval(function () {
        if (document.getElementById("pg-pipe") && document.getElementById("pg-pipe").classList.contains("on")) scheduleAutosave();
      }, 40000);

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
            setTimeout(resizeCanvas, 50);
          })
          .catch(function () {
            buildDefaultGraph(graph);
            graph.start();
            setTimeout(resizeCanvas, 50);
          });
      } else {
        buildDefaultGraph(graph);
        graph.start();
        setTimeout(resizeCanvas, 50);
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
})();
