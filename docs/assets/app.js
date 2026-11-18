/* Buildless, aggregate-only explorer. No external libraries or respondent data. */
"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const finite = Number.isFinite;
  const num = (x, digits = 2) => finite(x) ? x.toLocaleString("en-GB", {minimumFractionDigits: digits, maximumFractionDigits: digits}) : "—";
  const signed = (x, digits = 2) => finite(x) ? `${x > 0 ? "+" : x < 0 ? "−" : ""}${num(Math.abs(x), digits)}` : "—";
  const count = x => num(x, 0);
  const pct = x => finite(x) ? `${num(x * 100, 0)}%` : "unavailable";
  const interval = row => `${signed(row.lower)} to ${signed(row.upper)}`;
  const median = values => {const x = values.filter(finite).sort((a,b) => a-b); return x.length ? (x[Math.floor((x.length-1)/2)] + x[Math.ceil((x.length-1)/2)])/2 : null;};
  const arr = x => Array.isArray(x) ? x : x == null ? [] : [x];
  const colour = r => r.lower > 0 ? "#5B1A18" : r.upper < 0 ? "#C3454D" : "#98847b";
  const ns = "http://www.w3.org/2000/svg";
  const defaults = {predictor:"index", outcome:"Q04a", adjustment:"demographics", weighting:"weighted", estimator:"linear", study:"GBR_2024", tab:"compare", sort:"effect", timing:"before", coverage:"0.8", allTrust:false};
  let state = {...defaults}, catalog, current, sensitivity, requestNumber = 0;
  const embedded = document.getElementById("embedded-results");
  const offlineResults = embedded ? JSON.parse(embedded.textContent) : null;
  const cache = new Map();
  const studyMap = new Map();
  const svgText = (x,y,text,extra="") => `<text x="${x}" y="${y}" class="svg-text" ${extra}>${esc(text)}</text>`;
  const svg = (w,h,content,label) => `<svg xmlns="${ns}" viewBox="0 0 ${w} ${h}" role="group" aria-label="${esc(label)}">${content}</svg>`;
  const line = (x1,y1,x2,y2,extra="") => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" ${extra}/>`;
  const stat = (label,value,note,style="") => `<div class="stat"><span>${esc(label)}</span><strong class="${style}">${esc(value)}</strong><small>${esc(note)}</small></div>`;
  const note = (title,content) => `<div class="note-card"><h4>${esc(title)}</h4><p>${content}</p></div>`;
  const option = (value,label) => `<option value="${esc(value)}">${esc(label)}</option>`;
  const currentOutcome = () => catalog.outcomes.find(o => o.id === state.outcome);
  const currentPredictor = () => catalog.predictors.find(p => p.id === state.predictor);
  const key = () => [state.predictor,state.outcome,state.adjustment,state.weighting,state.estimator].join("__");
  const units = () => state.estimator === "linear" ? "Agreement score difference (0–1)" : "Probability of agreement difference (0–1)";
  const shortModel = () => state.estimator === "linear" ? "Linear" : "Logistic";

  async function getJSON(file) {
    if (offlineResults) {
      if (!(file in offlineResults)) throw new Error(`The standalone copy is missing ${file}.`);
      return offlineResults[file];
    }
    if (!cache.has(file)) cache.set(file, fetch(`results/${file}.json`).then(response => {
      if (!response.ok) throw new Error(`Cannot load ${file} (HTTP ${response.status}).`);
      return response.json();
    }).catch(error => {cache.delete(file); throw error;}));
    return cache.get(file);
  }

  function readURL() {
    const params = new URLSearchParams(location.search);
    for (const name of Object.keys(defaults)) if (params.has(name)) state[name] = name === "allTrust" ? params.get(name) === "true" : params.get(name);
    const allowed = {
      predictor:catalog.predictors.map(p => p.id), outcome:catalog.outcomes.map(o => o.id),
      adjustment:Object.keys(catalog.adjustments), weighting:Object.keys(catalog.weighting), estimator:Object.keys(catalog.estimators),
      study:catalog.studies.map(s => s.study), tab:["compare","detail","context","robustness","findings"],
      sort:["effect","name"], timing:["before","after"], coverage:["0.5","0.8","1"]
    };
    for (const [name,values] of Object.entries(allowed)) if (!values.includes(state[name])) state[name] = defaults[name];
  }

  function writeURL() {
    const params = new URLSearchParams();
    for (const [name,value] of Object.entries(state)) if (value !== defaults[name]) params.set(name,String(value));
    try {history.replaceState(null,"",`${location.pathname}${params.size ? "?"+params.toString() : ""}${location.hash}`);}
    catch { /* Some file:// viewers restrict history; exploration still works. */ }
  }

  function syncControls() {
    const reading = state.tab === "findings";
    $("explorer").classList.toggle("reading-mode", reading);
    $("status").hidden = reading;
    document.querySelector(".spec-strip").hidden = reading;
    for (const name of ["predictor","outcome","estimator","adjustment","weighting","study","sort","timing","coverage"]) $(name).value = state[name];
    $("robust-study").value = state.study;
    $("all-trust").checked = state.allTrust;
    const o = currentOutcome();
    $("statement").textContent = `“${o.statement}”`;
    $("predictor-hint").textContent = state.predictor === "index" ? "Equal-weight mean of parliament, government, and parties. All three responses required." : "One representative institution. Recoded so higher values mean more trust.";
    $("estimator-hint").textContent = state.estimator === "linear" ? "Five categories recoded 0–1. Higher means more agreement." : "Strongly/somewhat agree versus neutral or disagree. Predictions are probabilities.";
    $("spec-description").textContent = `${o.id} · ${shortModel()} · ${catalog.adjustments[state.adjustment]} · ${state.weighting === "weighted" ? "Original weights" : "Unweighted"}`;
    document.querySelectorAll("[data-tab]").forEach(button => {
      const active = button.dataset.tab === state.tab;
      button.setAttribute("aria-selected",String(active)); button.tabIndex = active ? 0 : -1;
      $(`panel-${button.dataset.tab}`).hidden = !active;
    });
    $("comparison-subtitle").textContent = `${currentPredictor().label} and ${o.label.toLowerCase()}. Higher estimates always mean more agreement with the statement.`;
    $("forest-unit").textContent = units();
  }

  function tickRange(min,max,target=5) {
    if (!finite(min) || !finite(max) || min === max) {min = -.1; max = .1;}
    const span = max-min, raw = span / target, power = 10 ** Math.floor(Math.log10(raw));
    const ratio = raw / power;
    const step = (ratio <= 1 ? 1 : ratio <= 2 ? 2 : ratio <= 2.5 ? 2.5 : ratio <= 5 ? 5 : 10) * power;
    const lo = Math.floor(min/step)*step, hi = Math.ceil(max/step)*step;
    const ticks = [];
    for (let v=lo; v <= hi + step/10; v+=step) ticks.push(Math.abs(v)<step/100 ? 0 : v);
    return {min:lo,max:hi,ticks};
  }

  function axisFor(rows, includeZero=true) {
    const lows = rows.map(r => r.lower).filter(finite), highs = rows.map(r => r.upper).filter(finite);
    if (includeZero) {lows.push(0); highs.push(0);}
    const min = Math.min(...lows), max = Math.max(...highs), padding = (max-min)*.06 || .05;
    return tickRange(min-padding,max+padding);
  }

  function renderTable(target,headers,rows) {
    $(target).innerHTML = `<table><thead><tr>${headers.map(x=>`<th scope="col">${esc(x)}</th>`).join("")}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(x=>`<td>${esc(x)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  }

  function focusStudy(study) {
    state.study = study; state.tab = "detail"; writeURL(); syncControls(); render();
    $("tab-detail").focus({preventScroll:true});
  }

  function bindStudyPoints(target) {
    $(target).querySelectorAll("[data-study]").forEach(point => {
      point.addEventListener("click",()=>focusStudy(point.dataset.study));
      point.addEventListener("keydown",event=>{if (["Enter"," "].includes(event.key)) {event.preventDefault(); focusStudy(point.dataset.study);}});
    });
  }

  function renderCompare() {
    const good = current.rows.filter(r=>r.status === "ok");
    const sorted = [...good].sort((a,b)=>state.sort === "name" ? studyMap.get(a.study).label.localeCompare(studyMap.get(b.study).label) : b.estimate-a.estimate);
    const med = median(good.map(r=>r.estimate));
    const positive = good.filter(r=>r.lower>0).length, negative = good.filter(r=>r.upper<0).length;
    $("comparison-stats").innerHTML = stat("Median study association",signed(med),"Equal-study median; not a pooled effect",med>=0?"positive":"negative") +
      stat("Intervals excluding zero",`${positive+negative} / ${good.length}`,`${positive} positive · ${negative} negative`) +
      stat("Respondents in these models",count(good.reduce((sum,r)=>sum+r.n,0)),`${good.length} of ${catalog.studies.length} election studies available`);
    if (!good.length) {$("forest").innerHTML = '<p class="empty">No models are available for this specification.</p>'; $("forest-axis").innerHTML=""; return;}
    const width=760, left=215, right=655, rowHeight=35, axis=axisFor(good), x=v=>left+(v-axis.min)/(axis.max-axis.min)*(right-left);
    let header = svgText(16,23,"ELECTION STUDY",'font-size="9" letter-spacing="1" fill="#795d56"');
    header += svgText(738,23,"N",'font-size="9" text-anchor="end" fill="#795d56"');
    for (const t of axis.ticks) header += svgText(x(t),23,signed(t), 'font-size="9" text-anchor="middle" fill="#795d56"');
    $("forest-axis").innerHTML = svg(width,36,header,"Association axis and sample size");
    let content="";
    for (const t of axis.ticks) content += line(x(t),0,x(t),sorted.length*rowHeight+8,`stroke="${t===0?"#bfa093":"#f0e1d3"}" ${t===0?'stroke-dasharray="4 4"':''}`);
    sorted.forEach((r,i)=>{
      const y=i*rowHeight+22, s=studyMap.get(r.study), c=colour(r);
      const title = `${s.label}: ${signed(r.estimate)}, 95% interval ${interval(r)}, N ${count(r.n)}. Open study detail.`;
      content += `<g class="study-row" role="button" tabindex="0" data-study="${esc(r.study)}" aria-label="${esc(title)}"><title>${esc(title)}</title><rect x="0" y="${i*rowHeight+3}" width="760" height="34" rx="3" fill="transparent"/>`;
      content += svgText(16,y+4,s.label,'font-size="11" fill="#5B1A18"');
      content += line(x(r.lower),y,x(r.upper),y,`stroke="${c}" stroke-width="2"`);
      content += line(x(r.lower),y-3,x(r.lower),y+3,`stroke="${c}"`)+line(x(r.upper),y-3,x(r.upper),y+3,`stroke="${c}"`);
      content += `<circle cx="${x(r.estimate)}" cy="${y}" r="4" fill="${c}"/>`;
      content += svgText(738,y+4,count(r.n),'font-size="10" text-anchor="end" fill="#795d56"')+"</g>";
    });
    $("forest").innerHTML=svg(width,sorted.length*rowHeight+8,content,"Country associations with 95% confidence intervals. Select a study for details.");
    bindStudyPoints("forest");
    renderTable("results-table",["Study","Association","95% interval","N","Kish effective N"],sorted.map(r=>[studyMap.get(r.study).label,signed(r.estimate,3),`${num(r.lower,3)} to ${num(r.upper,3)}`,count(r.n),count(r.effective_n)]));
    const bad = current.rows.filter(r=>r.status!=="ok");
    $("unavailable").textContent = bad.length ? `Unavailable: ${bad.map(r=>`${studyMap.get(r.study).label} (${r.reason}; N = ${count(r.n)})`).join("; ")}. See the study detail and missingness audit.` : "All election studies are available for this specification.";
  }

  function plotAxes({width=760,height=350,left=70,right=26,top=24,bottom=60,xAxis,yAxis,xLabel,yLabel,yFormat=signed}) {
    const x=v=>left+(v-xAxis.min)/(xAxis.max-xAxis.min)*(width-left-right);
    const y=v=>height-bottom-(v-yAxis.min)/(yAxis.max-yAxis.min)*(height-top-bottom);
    let content="";
    yAxis.ticks.forEach(t=>{content+=line(left,y(t),width-right,y(t),`stroke="${Math.abs(t)<1e-9?"#bba092":"#f1e1d2"}" ${Math.abs(t)<1e-9?'stroke-dasharray="4 4"':''}`)+svgText(left-10,y(t)+3,yFormat(t),'font-size="10" text-anchor="end" fill="#795d56"');});
    xAxis.ticks.forEach(t=>{content+=line(x(t),height-bottom,x(t),height-bottom+5,'stroke="#cbb09e"')+svgText(x(t),height-bottom+23,num(t,0),'font-size="10" text-anchor="middle" fill="#795d56"');});
    content+=svgText((left+width-right)/2,height-10,xLabel,'font-size="11" text-anchor="middle" fill="#76554b"');
    content+=`<text transform="translate(16 ${(top+height-bottom)/2}) rotate(-90)" class="svg-text" font-size="10" text-anchor="middle" fill="#76554b">${esc(yLabel)}</text>`;
    return {x,y,content,width,height};
  }

  function renderDetail() {
    const r=current.rows.find(r=>r.study===state.study), s=studyMap.get(state.study);
    $("detail-title").textContent=s.label;
    $("curve-subtitle").textContent=state.estimator==="linear"?"Agreement score on a 0–1 scale":"Probability of strongly or somewhat agreeing";
    if (r.status!=="ok") {
      $("detail-stats").innerHTML=stat("Estimation sample",count(r.n),`Out of ${count(s.n)} respondents`)+stat("Model status","Unavailable",r.reason)+stat("Trust index reliability",num(s.index_alpha),"Unweighted Cronbach's alpha");
      $("curve").innerHTML=`<p class="empty">${esc(r.reason)}. This study is retained in the catalogue; the selected model is not estimated.</p>`;
    } else {
      $("detail-stats").innerHTML=stat("Lowest → highest trust",signed(r.estimate),`95% interval: ${interval(r)}`,r.estimate>=0?"positive":"negative")+
        stat("Complete cases",count(r.n),`${pct(r.n/s.n)} of ${count(s.n)} respondents`)+stat("Kish effective N",count(r.effective_n),"Weight dispersion only; not full design effect");
      const ys=[...r.curve.flatMap(p=>[p.lower,p.upper]),...r.observed.map(p=>p.estimate).filter(finite),0,1];
      const ya=tickRange(Math.min(...ys),Math.max(...ys),5);
      const axes=plotAxes({xAxis:{min:0,max:1,ticks:[]},yAxis:ya,xLabel:currentPredictor().label,yLabel:state.estimator==="linear"?"Mean agreement score":"Probability of agreement",yFormat:num});
      const {x,y}=axes; let body=axes.content;
      const band=[...r.curve.map(p=>`${x(p.x)},${y(p.upper)}`),...r.curve.toReversed().map(p=>`${x(p.x)},${y(p.lower)}`)].join(" ");
      body+=`<polygon points="${band}" fill="#F1BB7B" opacity=".8"/><polyline points="${r.curve.map(p=>`${x(p.x)},${y(p.estimate)}`).join(" ")}" fill="none" stroke="#5B1A18" stroke-width="2.5"/>`;
      for (const p of r.curve) body+=`<circle cx="${x(p.x)}" cy="${y(p.estimate)}" r="4" fill="#5B1A18"><title>${esc(`Prediction ${num(p.estimate,3)}; 95% interval ${num(p.lower,3)} to ${num(p.upper,3)}`)}</title></circle>`;
      for (const p of r.observed) if(finite(p.estimate)) body+=`<circle cx="${x(p.x)}" cy="${y(p.estimate)}" r="4.5" fill="#fff" stroke="#9b8176" stroke-width="1.8"><title>${esc(`Observed mean ${num(p.estimate,3)}; N ${count(p.n)}`)}</title></circle>`;
      const labels=["Lowest","Lower","Higher","Highest"];
      r.curve.forEach((p,i)=>{body+=svgText(x(p.x),axes.height-37,labels[i],'font-size="10" text-anchor="middle" fill="#795d56"');});
      $("curve").innerHTML=svg(axes.width,axes.height,body,`Predicted and observed agreement across trust levels in ${s.label}`);
    }
    const source=state.weighting==="weighted"?`${s.weight_note} (${s.weight_variable}).` : "Unit weights selected. Original weights are available in the weighted specification where supplied.";
    const support=r.status==="ok"?`Observed trust range: ${num(r.observed_min_x)}–${num(r.observed_max_x)}. Lowest third: ${count(r.low_trust_n)} respondents; highest third: ${count(r.high_trust_n)}. Formula: ${r.formula}.` : "The missingness audit records availability for every input. Cases are excluded only for variables required by the current specification.";
    const omitted=arr(r.dropped_controls).length?` Omitted constant controls: ${arr(r.dropped_controls).join(", ")}.`:"";
    const warnings=arr(r.warnings).length?` Model warnings: ${arr(r.warnings).join("; ")}.`:"";
    $("study-notes").innerHTML=note("Sample & weights",esc(source)+`<br>${esc(support+omitted+warnings)}`)+note("Measurement & cabinet context",`Trust index α = ${num(s.index_alpha)} (unweighted complete-case reliability). This does not establish measurement invariance.<br>Pre-election cabinet: ${num(s.ideology_before)} / 10, ${pct(s.coverage_before)} covered.<br>Post-election cabinet: ${num(s.ideology_after)} / 10, ${pct(s.coverage_after)} covered.`);
  }

  function renderContext() {
    const threshold=Number(state.coverage), c=current.context.find(c=>c.timing===state.timing&&c.threshold===threshold);
    const included=new Set(arr(c.studies));
    const rows=current.rows.filter(r=>r.status==="ok"&&included.has(r.study));
    $("context-stats").innerHTML=stat("Eligible election studies",count(c.n),`At least ${pct(threshold)} of portfolios positioned`)+stat("Distinct countries",count(c.clusters),"Repeated elections/regions share a cluster")+stat("Change per ideology point",c.status==="ok"?signed(c.estimate,3):"Unavailable",c.status==="ok"?`95% interval: ${signed(c.lower,3)} to ${signed(c.upper,3)}`:c.reason);
    if(c.status!=="ok") $("context-chart").innerHTML=`<p class="empty">${esc(c.reason)}.</p>`;
    else {
      const axis=axisFor([...rows,...c.line]);
      const a=plotAxes({xAxis:{min:0,max:10,ticks:[0,2,4,6,8,10]},yAxis:axis,xLabel:"Derived cabinet ideology · left (0) → right (10)",yLabel:"Lowest → highest trust association",height:390});
      let body=a.content;
      body+=`<polygon points="${c.line.map(p=>`${a.x(p.x)},${a.y(p.upper)}`).concat(c.line.toReversed().map(p=>`${a.x(p.x)},${a.y(p.lower)}`)).join(" ")}" fill="#F1BB7B"/><polyline points="${c.line.map(p=>`${a.x(p.x)},${a.y(p.estimate)}`).join(" ")}" fill="none" stroke="#D67236" stroke-width="2"/>`;
      rows.forEach(r=>{
        const s=studyMap.get(r.study), xv=s[`ideology_${state.timing}`], tooltip=`${s.label}: cabinet ${num(xv)}, association ${signed(r.estimate)}; 95% interval ${interval(r)}; coverage ${pct(s[`coverage_${state.timing}`])}`;
        body+=`<g class="study-row" tabindex="0" role="button" data-study="${esc(r.study)}" aria-label="${esc(tooltip)}"><title>${esc(tooltip)}</title>${line(a.x(xv),a.y(r.lower),a.x(xv),a.y(r.upper),'stroke="#dfaa7f" stroke-width="1.2"')}<circle cx="${a.x(xv)}" cy="${a.y(r.estimate)}" r="5" fill="${colour(r)}" stroke="white" stroke-width="1.5"/>${svgText(a.x(xv)+8,a.y(r.estimate)+3,r.study.substring(0,3),'font-size="9" fill="#79574b"')}</g>`;
      });
      $("context-chart").innerHTML=svg(a.width,a.height,body,"Trust associations versus government ideology, with an exploratory fitted line"); bindStudyPoints("context-chart");
    }
    $("context-notes").innerHTML=note("A derived measure, with gaps",`Cabinet position uses expert party ideology and portfolio counts. A position represents only the covered share of the cabinet. The ${pct(threshold)} threshold retains ${count(c.n)} studies for this specification. Missing party positions and independent ministers can make the covered share selective.`)+note("What this comparison can tell us",`An upward line means more positive trust associations under cabinets placed further right. The comparison is ecological and observational. Cabinet timing is relative to the election, not matched to individual interview dates. Small country counts, first-stage uncertainty, and cross-country confounding limit inference.`);
    renderTable("context-table",["Study","Cabinet position","Portfolio coverage","Included?"],catalog.studies.map(s=>[s.label,num(s[`ideology_${state.timing}`]),pct(s[`coverage_${state.timing}`]),included.has(s.study)?"Yes":current.rows.find(r=>r.study===s.study).status!=="ok"?"Model unavailable":"Coverage / position unavailable"]));
  }

  async function renderRobustness() {
    const outcome=state.outcome;
    $("robust-chart").innerHTML='<p class="empty">Loading sensitivity estimates…</p>';
    try {
      const data=await getJSON(`sensitivity_${outcome}`);
      if(state.outcome!==outcome||state.tab!=="robustness")return;
      sensitivity=data;
      const selected=data.filter(r=>r.study===state.study&&r.estimator===state.estimator&&(state.allTrust||r.predictor===state.predictor));
      const rows=selected.filter(r=>r.status==="ok").sort((a,b)=>a.estimate-b.estimate);
      const positive=rows.filter(r=>r.lower>0).length, negative=rows.filter(r=>r.upper<0).length;
      $("robust-title").textContent=`${studyMap.get(state.study).label} · ${currentOutcome().id}`;
      $("robust-stats").innerHTML=stat("Available specifications",`${rows.length} / ${selected.length}`,`${shortModel()} model family held fixed`)+stat("Estimate range",rows.length?`${signed(rows[0].estimate)} to ${signed(rows.at(-1).estimate)}`:"—",state.allTrust?"Trust measure, controls & weights vary":"Controls & weights vary")+stat("Intervals excluding zero",`${positive+negative} / ${rows.length}`,`${positive} positive · ${negative} negative`);
      if(!rows.length){$("robust-chart").innerHTML='<p class="empty">No sensitivity models are available for this study and model family.</p>';}
      else {
        const width=760,height=320,left=68,right=25,top=25,bottom=60,axis=axisFor(rows);
        const x=i=>left+(i+.5)/rows.length*(width-left-right), y=v=>height-bottom-(v-axis.min)/(axis.max-axis.min)*(height-top-bottom);
        let body="";
        axis.ticks.forEach(t=>{body+=line(left,y(t),width-right,y(t),`stroke="${t===0?"#bba092":"#f1e1d2"}" ${t===0?'stroke-dasharray="4 4"':''}`)+svgText(left-10,y(t)+3,signed(t),'font-size="10" text-anchor="end" fill="#795d56"');});
        rows.forEach((r,i)=>{
          const tooltip=`${i+1}. ${catalog.predictors.find(p=>p.id===r.predictor).label}; ${catalog.adjustments[r.adjustment]}; ${r.weighting}; ${signed(r.estimate)}, 95% interval ${interval(r)}, N ${count(r.n)}`;
          body+=`<g><title>${esc(tooltip)}</title>${line(x(i),y(r.lower),x(i),y(r.upper),`stroke="${colour(r)}" stroke-width="2"`)}<circle cx="${x(i)}" cy="${y(r.estimate)}" r="4" fill="${colour(r)}"/></g>`+svgText(x(i),height-bottom+22,i+1,'font-size="10" text-anchor="middle" fill="#795d56"');
        });
        body+=svgText((left+width-right)/2,height-10,"Specifications ordered by association · see table for choices",'font-size="10" text-anchor="middle" fill="#795d56"');
        $("robust-chart").innerHTML=svg(width,height,body,"Sensitivity estimates across declared modelling specifications");
      }
      renderTable("robust-table",["#","Trust measure","Adjustment","Weighting","Association","95% interval","N"],rows.map((r,i)=>[i+1,catalog.predictors.find(p=>p.id===r.predictor).label,catalog.adjustments[r.adjustment],r.weighting,signed(r.estimate,3),`${num(r.lower,3)} to ${num(r.upper,3)}`,count(r.n)]));
    } catch(error) {$("robust-chart").innerHTML=`<p class="empty">${esc(error.message)}</p>`;}
  }

  function render() {
    if(!current)return;
    if(state.tab==="compare")renderCompare();
    if(state.tab==="detail")renderDetail();
    if(state.tab==="context")renderContext();
    if(state.tab==="robustness")renderRobustness();
  }

  async function loadSpec() {
    const generation=++requestNumber, specKey=key();
    current=null;
    $("explorer").setAttribute("aria-busy","true");
    $("status").textContent="Loading this specification…"; $("download").disabled=true; $("error").hidden=true;
    try {
      const result=await getJSON(specKey);
      if(generation!==requestNumber)return;
      current=result; syncControls(); render();
      $("explorer").setAttribute("aria-busy","false");
      $("status").textContent=`${result.rows.filter(r=>r.status==="ok").length} election-study models loaded · aggregate results`;
      $("download").disabled=false;
    } catch(error) {
      if(generation!==requestNumber)return;
      current=null;
      $("explorer").setAttribute("aria-busy","false");
      $("error").textContent=`${error.message} Serve the docs folder over HTTP, or check that all results files were published.`;$("error").hidden=false;
      $("status").textContent="This specification could not be loaded.";
    }
  }

  function exportCSV() {
    if(!current)return;
    const headers=["study","study_label","predictor","outcome","adjustment","weighting","weight_variable","estimator","status","n","effective_n","estimate","lower_95","upper_95","p_value","reason","source_version"];
    const rows=current.rows.map(r=>[r.study,studyMap.get(r.study).label,state.predictor,state.outcome,state.adjustment,state.weighting,state.weighting==="weighted"?studyMap.get(r.study).weight_variable:"unit",state.estimator,r.status,r.n,r.effective_n,r.estimate,r.lower,r.upper,r.p_value,r.reason,catalog.source_version]);
    const quote=x=>`"${String(x??"").replace(/"/g,'""')}"`;
    const body=[headers,...rows].map(row=>row.map(quote).join(",")).join("\r\n");
    const url=URL.createObjectURL(new Blob([body],{type:"text/csv;charset=utf-8"}));
    const a=document.createElement("a");a.href=url;a.download=`trust-democracy__${key()}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);
  }

  function attachEvents() {
    for(const name of ["predictor","outcome","adjustment","weighting","estimator"])$(name).addEventListener("change",()=>{state[name]=$(name).value;writeURL();syncControls();loadSpec();});
    for(const name of ["study","sort","timing","coverage"])$(name).addEventListener("change",()=>{state[name]=$(name).value;writeURL();syncControls();render();});
    $("robust-study").addEventListener("change",()=>{state.study=$("robust-study").value;writeURL();syncControls();render();});
    $("all-trust").addEventListener("change",()=>{state.allTrust=$("all-trust").checked;writeURL();render();});
    document.querySelectorAll("[data-tab]").forEach(button=>{
      button.addEventListener("click",()=>{state.tab=button.dataset.tab;writeURL();syncControls();render();});
      button.addEventListener("keydown",event=>{
        const tabs=[...document.querySelectorAll("[data-tab]")],i=tabs.indexOf(button);
        let next;
        if(event.key==="ArrowRight")next=tabs[(i+1)%tabs.length];
        if(event.key==="ArrowLeft")next=tabs[(i+tabs.length-1)%tabs.length];
        if(event.key==="Home")next=tabs[0];if(event.key==="End")next=tabs.at(-1);
        if(next){event.preventDefault();next.click();next.focus();}
      });
    });
    $("forest").addEventListener("scroll",()=>{$("forest-axis").scrollLeft=$("forest").scrollLeft;},{passive:true});
    $("reset").addEventListener("click",()=>{state={...defaults};writeURL();syncControls();loadSpec();});
    $("download").addEventListener("click",exportCSV);
    $("share").addEventListener("click",async()=>{
      writeURL();try{await navigator.clipboard.writeText(location.href);$("share").textContent="Link copied ✓";setTimeout(()=>{$("share").textContent="Copy a link to this view ↗";},2200);}catch{$("status").textContent="Copy the address from your browser to share this exact view.";}
    });
    addEventListener("popstate",()=>{state={...defaults};readURL();syncControls();loadSpec();});
  }

  async function init() {
    try {
      catalog=await getJSON("catalog");
      catalog.studies.forEach(s=>studyMap.set(s.study,s));readURL();
      $("predictor").innerHTML=catalog.predictors.map(p=>option(p.id,p.label)).join("");
      const groups=[...new Set(catalog.outcomes.map(o=>o.group))];
      $("outcome").innerHTML=groups.map(group=>`<optgroup label="${esc(group)}">${catalog.outcomes.filter(o=>o.group===group).map(o=>option(o.id,`${o.id} · ${o.label}`)).join("")}</optgroup>`).join("");
      for(const name of ["estimator","adjustment","weighting"])$(name).innerHTML=Object.entries(catalog[name==="estimator"?"estimators":name==="adjustment"?"adjustments":"weighting"]).map(([key,label])=>option(key,label)).join("");
      const studies=[...catalog.studies].sort((a,b)=>a.label.localeCompare(b.label)).map(s=>option(s.study,s.label)).join("");
      $("study").innerHTML=studies;$("robust-study").innerHTML=studies;
      $("study-count").textContent=catalog.studies.length;$("respondent-count").textContent=count(catalog.respondents);
      const doi=String(catalog.doi).replace(/^doi:/,"");
      $("citation").innerHTML=`The Comparative Study of Election Surveys. CSES Module 6 Third Advance Release [dataset and documentation]. Embedded version: ${esc(catalog.source_version)}. <a href="https://doi.org/${esc(doi)}" target="_blank" rel="noopener">${esc(doi)}</a>. Analysis built ${esc(catalog.generated)}. Data are preliminary.`;
      attachEvents();syncControls();await loadSpec();
    } catch(error) {$("error").hidden=false;$("error").textContent=`The data catalogue could not be loaded: ${error.message} Open this site using a local HTTP server rather than a file URL.`;$("status").textContent="Unable to load the dashboard.";}
  }
  init();
})();
