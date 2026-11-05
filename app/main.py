from fastapi import FastAPI,HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,Field
from .core import answer,build_documents,DOCS,RetrievalError

app=FastAPI(title="A320 Quality Intelligence",version="1.0.0")
class Question(BaseModel):
    question:str=Field(min_length=3,max_length=500)
    use_gemini:bool=False

@app.on_event("startup")
def prepare():
    build_documents()

@app.get("/api/health")
def health():return {"status":"ok","documents":len(list(DOCS.glob("SIM-MSN-*.md")))}

@app.post("/api/ask")
def ask(body:Question):
    try:return answer(body.question,body.use_gemini)
    except (ValueError,RetrievalError) as e:raise HTTPException(status_code=400,detail=str(e)) from e

@app.get("/",response_class=HTMLResponse)
def home():
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>A320 Quality Intelligence</title><style>
*{box-sizing:border-box}body{font-family:system-ui,Arial,sans-serif;background:#f4f7fb;color:#14263e;margin:0}.shell{max-width:960px;margin:auto;padding:40px 20px}.top{color:#48749c;letter-spacing:.12em;font-size:12px;font-weight:700}h1{font-size:36px;margin:12px 0}p{color:#60728a}.panel{background:#fff;border:1px solid #dce4ef;border-radius:16px;padding:25px;margin-top:24px;box-shadow:0 8px 30px #1025400a}textarea{width:100%;min-height:115px;padding:15px;border:1px solid #cbd6e4;border-radius:10px;font:inherit;resize:vertical}button{background:#194d79;color:white;border:0;border-radius:9px;padding:12px 20px;cursor:pointer;margin-top:14px}label{font-size:13px;color:#526780;margin-left:15px}.answer{white-space:pre-wrap;line-height:1.6}.sources{display:flex;gap:8px;flex-wrap:wrap}.source{background:#e9f1f8;border-radius:7px;padding:8px;font-size:12px}.notice{font-size:12px;color:#7c5161}.hidden{display:none}</style></head><body><main class="shell"><div class="top">SYNTHETIC A320 QUALITY DATA / INTELLIGENCE</div><h1>Quality Intelligence Assistant</h1><p>Ask evidence-based questions about fictional aircraft findings, actions and milestones.</p><section class="panel"><form id="form"><textarea id="question" required minlength="3" placeholder="What are the open findings and corrective actions for SIM-MSN-10042?"></textarea><div><button id="send">Ask question</button><label><input id="gemini" type="checkbox" checked> Use Gemini API</label></div></form><p class="notice">Requires GEMINI_API_KEY for generated answers. Uncheck to inspect retrieved evidence without an API key.</p></section><section class="panel hidden" id="result"><h2>Answer</h2><div class="answer" id="answer"></div><h3>Retrieved sources</h3><div class="sources" id="sources"></div></section><p class="notice">Independent portfolio project. All data is fictional. Not affiliated with Airbus or Skywise. Not for operational or airworthiness decisions.</p></main><script>
const el=id=>document.getElementById(id);el('form').onsubmit=async e=>{e.preventDefault();el('send').disabled=true;el('result').classList.remove('hidden');el('answer').textContent='Searching...';el('sources').replaceChildren();try{const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:el('question').value,use_gemini:el('gemini').checked})});const d=await r.json();if(!r.ok)throw Error(d.detail||'Request failed');el('answer').textContent=d.answer+(d.excerpts?'\\n\\n'+d.excerpts.join('\\n\\n'):'');(d.citations||[]).forEach(s=>{const span=document.createElement('span');span.className='source';span.textContent=s.source;el('sources').appendChild(span)})}catch(err){el('answer').textContent=err.message}finally{el('send').disabled=false}};</script></body></html>"""
