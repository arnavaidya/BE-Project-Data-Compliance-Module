import { useState, useCallback, useMemo, useRef } from "react";
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell
} from "recharts";

/* ─────────────────────────────────────────────────────────────────────────────
   THEME & TOKENS
───────────────────────────────────────────────────────────────────────────── */
const T = {
  bg: "#0c0e12",
  surface: "#141821",
  surfaceHi: "#1c2030",
  border: "#2a2f3d",
  text: "#c8cdd8",
  textDim: "#6b7280",
  amber: "#f59e0b",
  amberDim: "#f59e0b22",
  red: "#ef4444",
  redDim: "#ef444422",
  green: "#22c55e",
  greenDim: "#22c55e22",
  sky: "#38bdf8",
  skyDim: "#38bdf822",
  violet: "#a78bfa",
  violetDim: "#a78bfa22",
};

const severityColor = { critical: T.red, high: T.amber, medium: T.sky, low: T.green };
const severityBg    = { critical: T.redDim, high: T.amberDim, medium: T.skyDim, low: T.greenDim };
const statusColor   = { compliant: T.green, non_compliant: T.red, pending: T.amber, skipped: T.textDim };

/* ─────────────────────────────────────────────────────────────────────────────
   BACKEND API FUNCTIONS
───────────────────────────────────────────────────────────────────────────── */
async function scanDatasetFromBackend(datasetJson) {
  try {
    const response = await fetch('http://127.0.0.1:8000/compliance/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dataset: datasetJson,
        regulations: ["GDPR", "HIPAA", "CCPA", "ISO27001", "PCI_DSS"],
        strict_mode: false
      })
    });
    
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    alert(`Failed to scan dataset: ${error.message}\n\nMake sure backend is running:\nhttp://127.0.0.1:8000`);
    return null;
  }
}

async function scanCSVFile(file, metadata) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('dataset_name', metadata.name || '');
    formData.append('owner', metadata.owner || '');
    formData.append('tags', metadata.tags || '');
    formData.append('regulations', 'GDPR,HIPAA,CCPA,ISO_27001,PCI_DSS');
    formData.append('strict_mode', 'false');
    
    const response = await fetch('http://127.0.0.1:8000/csv/scan', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Backend returned ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    alert(`Failed to scan CSV: ${error.message}\n\nMake sure backend is running:\nhttp://127.0.0.1:8000`);
    return null;
  }
}

/* ─────────────────────────────────────────────────────────────────────────────
   TINY REUSABLE COMPONENTS
───────────────────────────────────────────────────────────────────────────── */
function Badge({ severity }) {
  return (
    <span style={{
      display:"inline-block", fontSize:11, fontWeight:700, letterSpacing:"0.06em",
      textTransform:"uppercase", padding:"3px 8px", borderRadius:4,
      background: severityBg[severity], color: severityColor[severity], border:`1px solid ${severityColor[severity]}44`
    }}>
      {severity}
    </span>
  );
}

function StatusPill({ status }) {
  const labels = { compliant:"✓ Compliant", non_compliant:"✕ Non-Compliant", pending:"⟳ Pending", skipped:"— Skipped" };
  return (
    <span style={{
      display:"inline-flex", alignItems:"center", gap:4, fontSize:11, fontWeight:600,
      padding:"3px 9px", borderRadius:20, letterSpacing:"0.04em",
      background: statusColor[status] + "18", color: statusColor[status],
      border:`1px solid ${statusColor[status]}33`
    }}>
      {labels[status]}
    </span>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   FILE UPLOAD ZONE
───────────────────────────────────────────────────────────────────────────── */
function UploadZone({ onLoad }) {
  const ref = useRef();
  const [drag, setDrag] = useState(false);
  const [scanning, setScanning] = useState(false);

  const handleFile = async (file) => {
    if (!file) return;
    
    const fileName = file.name.toLowerCase();
    
    // Handle CSV files
    if (fileName.endsWith('.csv')) {
      setScanning(true);
      const result = await scanCSVFile(file, {
        name: file.name.replace('.csv', ''),
        owner: '',
        tags: ''
      });
      setScanning(false);
      if (result) {
        onLoad(result);
      }
      return;
    }
    
    // Handle JSON files
    if (!fileName.endsWith('.json')) {
      alert("Please drop a .json or .csv file.");
      return;
    }
    
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const data = JSON.parse(e.target.result);
        
        // Check if it's a scan result (has findings + summary) or a dataset
        if (data.findings && data.summary) {
          // It's a scan result - load directly
          onLoad(data);
        } else if (data.dataset || data.columns) {
          // It's a dataset - scan it via backend
          setScanning(true);
          const result = await scanDatasetFromBackend(data.dataset || data);
          setScanning(false);
          if (result) {
            onLoad(result);
          }
        } else {
          alert("Invalid JSON format.\n\nExpected either:\n• Scan result (with 'findings' and 'summary')\n• Dataset (with 'dataset' or 'columns')");
        }
      } catch (err) {
        setScanning(false);
        alert("Invalid JSON – could not parse.");
      }
    };
    reader.readAsText(file);
  };

  return (
    <div
      onDrop={e => { e.preventDefault(); setDrag(false); handleFile(e.dataTransfer.files[0]); }}
      onDragOver={e => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onClick={() => !scanning && ref.current.click()}
      style={{
        border:`2px dashed ${drag ? T.amber : T.border}`,
        borderRadius:12, padding:"48px 24px", textAlign:"center", cursor: scanning ? "wait" : "pointer",
        background: drag ? T.amberDim : T.surface, transition:"all .2s", userSelect:"none",
        opacity: scanning ? 0.6 : 1
      }}
    >
      <input ref={ref} type="file" accept=".json,.csv" style={{display:"none"}} onChange={e => handleFile(e.target.files[0])} disabled={scanning} />
      {scanning ? (
        <>
          <div style={{fontSize:32, marginBottom:8}}>⏳</div>
          <div style={{color: T.text, fontWeight:600, fontSize:15}}>Scanning training data with Microsoft Presidio...</div>
          <div style={{color: T.textDim, fontSize:13, marginTop:6}}>Detecting PII/PHI across all columns</div>
        </>
      ) : (
        <>
          <div style={{fontSize:32, marginBottom:8}}>📊</div>
          <div style={{color: T.text, fontWeight:600, fontSize:16, marginBottom:8}}>
            Upload Training Data CSV for Compliance Check
          </div>
          <div style={{color: T.text, fontSize:14, marginBottom:12}}>
            Drop your <span style={{color:T.amber, fontWeight:600}}>CSV file</span> here or click to browse
          </div>
          <div style={{color: T.textDim, fontSize:12, lineHeight:1.6}}>
            ✓ Detects PII/PHI automatically (emails, phones, SSNs, credit cards, etc.)<br/>
            ✓ Checks GDPR, HIPAA, CCPA, ISO 27001, PCI-DSS compliance<br/>
            ✓ Also accepts: JSON datasets or pre-scanned results
          </div>
        </>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   HEADER BAR
───────────────────────────────────────────────────────────────────────────── */
function Header({ data, onReset }) {
  return (
    <div style={{
      display:"flex", justifyContent:"space-between", alignItems:"center",
      borderBottom:`1px solid ${T.border}`, paddingBottom:16, marginBottom:28
    }}>
      <div>
        <div style={{display:"flex", alignItems:"center", gap:10}}>
          <span style={{fontSize:22, fontWeight:800, color:"#fff", letterSpacing:"-0.02em"}}>Compliance Dashboard</span>
          <StatusPill status={data.overall_status} />
        </div>
        <div style={{color:T.textDim, fontSize:13, marginTop:4}}>
          Dataset <code style={{color:T.sky}}>{data.dataset_id}</code> · Scan <code style={{color:T.violet}}>{data.scan_id.slice(0,8)}…</code>
        </div>
      </div>
      <button onClick={onReset} style={{
        padding:"7px 16px", borderRadius:6, border:`1px solid ${T.border}`,
        background:T.surfaceHi, color:T.text, fontSize:13, cursor:"pointer", fontWeight:600
      }}>← Load another file</button>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   SUMMARY CARDS ROW
───────────────────────────────────────────────────────────────────────────── */
function SummaryCards({ data }) {
  const findings = data.findings;
  const total    = findings.length;
  const critQty  = findings.filter(f => f.severity === "critical").length;
  const highQty  = findings.filter(f => f.severity === "high").length;
  const nonComp  = findings.filter(f => f.status === "non_compliant").length;

  const cards = [
    { label:"Total Rules Checked", value: total,   accent: T.sky,    icon:"📋" },
    { label:"Violations",          value: nonComp, accent: T.red,    icon:"✕"  },
    { label:"Critical Flags",      value: critQty, accent: T.red,    icon:"🔴" },
    { label:"High Severity",       value: highQty, accent: T.amber,  icon:"🟠" },
  ];

  return (
    <div style={{display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:14, marginBottom:28}}>
      {cards.map(c => (
        <div key={c.label} style={{
          background:T.surface, border:`1px solid ${T.border}`, borderRadius:10,
          padding:"16px 18px", borderTop:`3px solid ${c.accent}`
        }}>
          <div style={{display:"flex", justifyContent:"space-between", alignItems:"flex-start"}}>
            <div style={{color:T.textDim, fontSize:12, fontWeight:600, textTransform:"uppercase", letterSpacing:"0.05em"}}>{c.label}</div>
            <span style={{fontSize:18}}>{c.icon}</span>
          </div>
          <div style={{color:"#fff", fontSize:28, fontWeight:800, marginTop:6, letterSpacing:"-0.02em"}}>{c.value}</div>
        </div>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   REGULATION STATUS GRID
───────────────────────────────────────────────────────────────────────────── */
function RegulationStatusBar({ data }) {
  const labels = { GDPR:"GDPR", HIPAA:"HIPAA", CCPA:"CCPA", ISO27001:"ISO 27001", PCI_DSS:"PCI-DSS" };
  return (
    <div style={{display:"flex", gap:10, flexWrap:"wrap", marginBottom:28}}>
      {Object.entries(data.summary).map(([reg, st]) => (
        <div key={reg} style={{
          display:"flex", alignItems:"center", gap:8,
          background:T.surface, border:`1px solid ${statusColor[st]}44`, borderRadius:8,
          padding:"8px 14px", flex:"1 1 auto", minWidth:120
        }}>
          <div style={{width:10, height:10, borderRadius:"50%", background:statusColor[st], boxShadow:`0 0 6px ${statusColor[st]}88`}} />
          <span style={{color:"#fff", fontSize:14, fontWeight:700}}>{labels[reg] || reg}</span>
          <span style={{color:statusColor[st], fontSize:11, fontWeight:600, marginLeft:"auto"}}>{st.replace("_"," ")}</span>
        </div>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   RADAR CHART
───────────────────────────────────────────────────────────────────────────── */
function RadarScore({ data }) {
  const rulesPerReg = {};
  data.findings.forEach(f => {
    rulesPerReg[f.regulation] = rulesPerReg[f.regulation] || { total:0, pass:0 };
    rulesPerReg[f.regulation].total++;
    if (f.status === "compliant" || f.status === "skipped") rulesPerReg[f.regulation].pass++;
  });
  const labels = { GDPR:"GDPR", HIPAA:"HIPAA", CCPA:"CCPA", ISO27001:"ISO 27001", PCI_DSS:"PCI-DSS" };
  const radarData = Object.entries(rulesPerReg).map(([reg, v]) => ({
    subject: labels[reg] || reg,
    score: Math.round((v.pass / v.total) * 100)
  }));

  return (
    <div style={{background:T.surface, border:`1px solid ${T.border}`, borderRadius:10, padding:"20px 16px 12px"}}>
      <div style={{color:"#fff", fontSize:14, fontWeight:700, marginBottom:2, textAlign:"center"}}>Compliance Score</div>
      <div style={{color:T.textDim, fontSize:11, textAlign:"center", marginBottom:8}}>rules passed per framework (0–100)</div>
      <ResponsiveContainer width="100%" height={240}>
        <RadarChart data={radarData}>
          <PolarGrid stroke={T.border} />
          <PolarAngleAxis dataKey="subject" tick={{ fill: T.text, fontSize:11, fontWeight:600 }} />
          <PolarRadiusAxis angle={90} domain={[0,100]} tick={{ fill:T.textDim, fontSize:10 }} axisLine={false} />
          <Radar name="Score" dataKey="score" stroke={T.amber} fill={T.amber} fillOpacity={0.18} strokeWidth={2} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   SEVERITY BAR CHART
───────────────────────────────────────────────────────────────────────────── */
function SeverityBar({ data }) {
  const counts = { critical:0, high:0, medium:0, low:0 };
  data.findings.forEach(f => { counts[f.severity] = (counts[f.severity] || 0) + 1; });
  const bars = Object.entries(counts).map(([s, v]) => ({ name: s.charAt(0).toUpperCase()+s.slice(1), value: v, fill: severityColor[s] }));

  return (
    <div style={{background:T.surface, border:`1px solid ${T.border}`, borderRadius:10, padding:"20px 16px 12px"}}>
      <div style={{color:"#fff", fontSize:14, fontWeight:700, marginBottom:12}}>Findings by Severity</div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={bars} layout="vertical" margin={{top:0, right:16, bottom:0, left:56}}>
          <XAxis type="number" tick={{fill:T.textDim, fontSize:11}} axisLine={false} tickLine={false} allowDecimals={false} />
          <YAxis type="category" dataKey="name" tick={{fill:T.text, fontSize:12, fontWeight:600}} axisLine={false} tickLine={false} width={52} />
          <Tooltip
            contentStyle={{background:T.surfaceHi, border:`1px solid ${T.border}`, borderRadius:6, color:T.text, fontSize:12}}
            cursor={{fill:T.border+"55"}}
          />
          <Bar dataKey="value" radius={[0,5,5,0]} barSize={22}>
            {bars.map((b,i) => <Cell key={i} fill={b.fill} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   AFFECTED-COLUMNS HEATMAP
───────────────────────────────────────────────────────────────────────────── */
function ColumnHeatmap({ data }) {
  const colCount = {};
  data.findings.forEach(f => f.affected_columns.forEach(c => { colCount[c] = (colCount[c] || 0) + 1; }));
  if (!Object.keys(colCount).length) return null;

  const sorted = Object.entries(colCount).sort((a,b) => b[1]-a[1]);
  const max = sorted[0][1];

  return (
    <div style={{background:T.surface, border:`1px solid ${T.border}`, borderRadius:10, padding:"18px 18px 16px", marginBottom:28}}>
      <div style={{color:"#fff", fontSize:14, fontWeight:700, marginBottom:3}}>Column Risk Heatmap</div>
      <div style={{color:T.textDim, fontSize:11, marginBottom:14}}>Number of rules that flag each column</div>
      <div style={{display:"flex", gap:8, flexWrap:"wrap"}}>
        {sorted.map(([col, cnt]) => {
          const intensity = cnt / max;
          const bg = intensity > 0.7 ? T.red : intensity > 0.4 ? T.amber : T.sky;
          return (
            <div key={col} style={{
              background: bg + (Math.round(intensity*200).toString(16).padStart(2,"0")),
              border:`1px solid ${bg}55`, borderRadius:8, padding:"10px 16px", display:"flex",
              alignItems:"center", gap:10, minWidth:140
            }}>
              <code style={{color:"#fff", fontSize:13, fontWeight:700}}>{col}</code>
              <span style={{
                marginLeft:"auto", background:"#00000055", color:"#fff",
                fontSize:12, fontWeight:800, padding:"2px 7px", borderRadius:10
              }}>{cnt}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   FINDINGS TABLE
───────────────────────────────────────────────────────────────────────────── */
function FindingsTable({ data }) {
  const [expanded, setExpanded] = useState(null);
  const [filter, setFilter]     = useState("all");

  const groups = useMemo(() => {
    const g = {};
    data.findings.forEach(f => { (g[f.regulation] = g[f.regulation] || []).push(f); });
    return g;
  }, [data]);

  const filterMatch = (f) => {
    if (filter === "all") return true;
    return f.severity === filter || f.status === filter;
  };

  const filterBtns = ["all","critical","high","medium","low","non_compliant","compliant","skipped"];
  const regLabel   = { GDPR:"GDPR", HIPAA:"HIPAA", CCPA:"CCPA", ISO27001:"ISO 27001", PCI_DSS:"PCI-DSS" };

  return (
    <div>
      <div style={{display:"flex", gap:6, flexWrap:"wrap", marginBottom:14}}>
        {filterBtns.map(b => {
          const active = filter === b;
          const color  = b === "all" ? T.sky : (severityColor[b] || statusColor[b] || T.text);
          return (
            <button key={b} onClick={() => setFilter(b)} style={{
              padding:"5px 12px", borderRadius:16, border:`1px solid ${active ? color : T.border}`,
              background: active ? color+"22" : "transparent", color: active ? color : T.textDim,
              fontSize:12, fontWeight:600, cursor:"pointer", textTransform:"capitalize"
            }}>
              {b.replace("_"," ")}
            </button>
          );
        })}
      </div>

      {Object.entries(groups).map(([reg, findings]) => {
        const visible = findings.filter(filterMatch);
        if (!visible.length) return null;
        return (
          <div key={reg} style={{marginBottom:14}}>
            <div style={{
              display:"flex", alignItems:"center", gap:10, padding:"8px 14px",
              background:T.surfaceHi, borderRadius:"8px 8px 0 0", border:`1px solid ${T.border}`, borderBottom:"none"
            }}>
              <span style={{color:"#fff", fontSize:14, fontWeight:800}}>{regLabel[reg]}</span>
              <span style={{color:T.textDim, fontSize:12}}>({visible.length} finding{visible.length!==1?"s":""})</span>
              <StatusPill status={data.summary[reg]} />
            </div>

            <div style={{border:`1px solid ${T.border}`, borderRadius:"0 0 8px 8px", overflow:"hidden"}}>
              {visible.map((f, i) => {
                const key   = f.rule_id;
                const open  = expanded === key;
                return (
                  <div key={key} style={{borderTop: i ? `1px solid ${T.border}` : "none"}}>
                    <div
                      onClick={() => setExpanded(open ? null : key)}
                      style={{
                        display:"flex", alignItems:"center", gap:12, padding:"11px 16px",
                        background: open ? T.surfaceHi : T.surface, cursor:"pointer",
                        transition:"background .15s"
                      }}
                    >
                      <span style={{color:T.textDim, fontSize:11, fontWeight:700, minWidth:82, fontFamily:"monospace"}}>{f.rule_id}</span>
                      <Badge severity={f.severity} />
                      <StatusPill status={f.status} />
                      <span style={{color:T.text, fontSize:13, flex:1, marginLeft:4}}>{f.rule_description}</span>
                      {f.affected_columns.length > 0 &&
                        <span style={{color:T.violet, fontSize:11, fontWeight:600}}>
                          {f.affected_columns.length} col{f.affected_columns.length>1?"s":""}
                        </span>
                      }
                      <span style={{color:T.textDim, fontSize:16, width:18, textAlign:"center", userSelect:"none"}}>
                        {open ? "▲" : "▼"}
                      </span>
                    </div>

                    {open && (
                      <div style={{
                        background:"#111520", borderTop:`1px solid ${T.border}`,
                        padding:"14px 16px 16px", display:"grid",
                        gridTemplateColumns:"1fr 1fr", gap:"12px 24px"
                      }}>
                        <div>
                          <div style={{color:T.textDim, fontSize:11, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:4}}>Details</div>
                          <div style={{color:T.text, fontSize:13, lineHeight:1.5}}>{f.details}</div>
                        </div>
                        <div>
                          <div style={{color:T.textDim, fontSize:11, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:4}}>Remediation</div>
                          <div style={{color:T.green, fontSize:13, lineHeight:1.5}}>{f.remediation}</div>
                        </div>
                        {f.affected_columns.length > 0 && (
                          <div style={{gridColumn:"1/-1"}}>
                            <div style={{color:T.textDim, fontSize:11, fontWeight:700, textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:6}}>Affected Columns</div>
                            <div style={{display:"flex", gap:6, flexWrap:"wrap"}}>
                              {f.affected_columns.map(c => (
                                <span key={c} style={{
                                  background:T.violetDim, border:`1px solid ${T.violet}44`,
                                  borderRadius:5, padding:"3px 10px", color:T.violet, fontSize:12, fontWeight:600, fontFamily:"monospace"
                                }}>{c}</span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   ROOT APP
───────────────────────────────────────────────────────────────────────────── */
export default function App() {
  const [data, setData] = useState(null);

  const load = useCallback((json) => {
    if (!json || !json.findings || !json.summary) {
      alert("Invalid scan result JSON – must contain 'findings' and 'summary'.");
      return;
    }
    setData(json);
  }, []);

  if (!data) {
    return (
      <div style={{
        minHeight:"100vh", background:T.bg, display:"flex", alignItems:"center",
        justifyContent:"center", padding:24, fontFamily:"system-ui, sans-serif"
      }}>
        <div style={{width:"100%", maxWidth:620}}>
          <div style={{textAlign:"center", marginBottom:36}}>
            <div style={{fontSize:40, marginBottom:8}}>🛡️</div>
            <h1 style={{color:"#fff", fontSize:26, fontWeight:800, margin:0, letterSpacing:"-0.02em"}}>
              AI Training-Data <span style={{color:T.amber}}>Compliance</span> Checker
            </h1>
            <p style={{color:T.textDim, fontSize:14, margin:"8px 0 0"}}>
              Powered by <span style={{color:T.sky}}>Microsoft Presidio</span> · Upload CSV training data to scan for PII/PHI violations
            </p>
          </div>
          <UploadZone onLoad={load} />
        </div>
      </div>
    );
  }

  return (
    <div style={{
      minHeight:"100vh", background:T.bg, color:T.text,
      fontFamily:"system-ui, sans-serif", padding:"28px 32px"
    }}>
      <div style={{maxWidth:1200, margin:"0 auto"}}>
        <Header data={data} onReset={() => setData(null)} />
        <SummaryCards data={data} />
        <RegulationStatusBar data={data} />
        <ColumnHeatmap data={data} />

        <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:14, marginBottom:28}}>
          <RadarScore data={data} />
          <SeverityBar data={data} />
        </div>

        <div style={{background:T.surface, border:`1px solid ${T.border}`, borderRadius:10, padding:"20px 18px"}}>
          <div style={{color:"#fff", fontSize:16, fontWeight:700, marginBottom:14}}>All Findings</div>
          <FindingsTable data={data} />
        </div>
      </div>
    </div>
  );
}