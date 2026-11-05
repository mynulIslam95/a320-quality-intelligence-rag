"""Evidence-grounded retrieval over synthetic aircraft quality notes."""
import json, os, re, sqlite3, random, urllib.request, urllib.error
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=Path(os.environ.get("QUALITY_DB",ROOT/"data/demo_quality.db"))
DOCS=ROOT/"docs"
AIRCRAFT=re.compile(r"\bSIM-MSN-\d{5}\b",re.I)

class RetrievalError(Exception): pass

def connect():
    return sqlite3.connect(f"file:{DB}?mode=ro",uri=True)

def prepare_demo():
    if DB.exists():return
    DB.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(DB) as db:
        db.executescript("""CREATE TABLE aircraft(aircraft_id TEXT PRIMARY KEY,site TEXT,family TEXT,planned_delivery TEXT);
CREATE TABLE inspections(inspection_id TEXT PRIMARY KEY,aircraft_id TEXT,inspection_date TEXT,area TEXT,result TEXT);
CREATE TABLE findings(finding_id TEXT PRIMARY KEY,inspection_id TEXT,severity TEXT,status TEXT,description TEXT);
CREATE TABLE actions(action_id TEXT PRIMARY KEY,finding_id TEXT,owner TEXT,due_date TEXT,status TEXT);
CREATE TABLE milestones(milestone_id TEXT PRIMARY KEY,aircraft_id TEXT,stage TEXT,target_date TEXT,status TEXT);""")
        rng=random.Random(3202027)
        sites=["Hamburg","Toulouse","Mobile","Tianjin"]
        areas=["Cabin","Fuselage","Electrical","Avionics","Paint","Systems"]
        for a in range(1,121):
            aid=f"SIM-MSN-{10000+a}"
            delivery=(date(2027,1,1)+timedelta(days=a)).isoformat()
            db.execute("INSERT INTO aircraft VALUES(?,?,?,?)",(aid,sites[(a-1)%4],"A321neo" if a%3==0 else "A320neo",delivery))
            for k in range(1,9):
                idx=(a-1)*8+k
                db.execute("INSERT INTO inspections VALUES(?,?,?,?,?)",(f"INSP-{idx:05d}",aid,(date(2026,7,1)+timedelta(days=(idx-1)%120)).isoformat(),areas[(idx-1)%6],rng.choices(["Pass","Fail","Observation"],weights=[65,20,15])[0]))
            for k,stage in enumerate(["Final inspection","Documentation review","Customer handover"],1):
                db.execute("INSERT INTO milestones VALUES(?,?,?,?,?)",(f"MS-{(a-1)*3+k:05d}",aid,stage,delivery,rng.choice(["Planned","Completed","At Risk"])))
        for n,i in enumerate(rng.sample(range(1,961),365),1):
            db.execute("INSERT INTO findings VALUES(?,?,?,?,?)",(f"FND-{n:05d}",f"INSP-{i:05d}",rng.choices(["Low","Medium","High","Critical"],weights=[40,35,20,5])[0],rng.choice(["Open","In Progress","Closed"]),rng.choice(["Surface finish observation","Functional test deviation","Component labeling discrepancy","Documentation mismatch"])))
        for n,i in enumerate(rng.sample(range(1,366),314),1):
            db.execute("INSERT INTO actions VALUES(?,?,?,?,?)",(f"ACT-{n:05d}",f"FND-{i:05d}",f"Coordinator {rng.randint(1,8)}",(date(2026,9,1)+timedelta(days=rng.randrange(160))).isoformat(),rng.choice(["Open","In Progress","Closed"])))

def build_documents():
    prepare_demo()
    DOCS.mkdir(parents=True,exist_ok=True)
    with connect() as db:
        db.row_factory=sqlite3.Row
        aircraft=db.execute("SELECT * FROM aircraft ORDER BY aircraft_id").fetchall()
        for a in aircraft:
            aid=a["aircraft_id"]
            findings=db.execute("""SELECT f.finding_id,f.severity,f.status,f.description,i.area,ac.action_id,ac.owner,ac.due_date,ac.status action_status FROM findings f JOIN inspections i ON f.inspection_id=i.inspection_id LEFT JOIN actions ac ON ac.finding_id=f.finding_id WHERE i.aircraft_id=? ORDER BY f.finding_id""",(aid,)).fetchall()
            milestones=db.execute("SELECT stage,target_date,status FROM milestones WHERE aircraft_id=? ORDER BY milestone_id",(aid,)).fetchall()
            lines=[f"# Synthetic quality record: {aid}",f"Site: {a['site']}",f"Aircraft family: {a['family']}",f"Planned delivery: {a['planned_delivery']}","","## Findings"]
            if not findings:lines.append("No findings recorded.")
            for f in findings:
                lines.append(f"- {f['finding_id']}: {f['severity']}; {f['status']}; {f['area']}; {f['description']}.")
                if f["action_id"]:lines.append(f"  Corrective action {f['action_id']}: {f['action_status']}; owner {f['owner']}; due {f['due_date']}.")
            lines.extend(["","## Milestones"])
            for m in milestones:lines.append(f"- {m['stage']}: {m['status']}; target {m['target_date']}.")
            (DOCS/f"{aid}.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    return len(aircraft)

def search(question,limit=5):
    question=question.strip()
    if not question:raise ValueError("Question is required")
    if not DOCS.exists() or len(list(DOCS.glob("SIM-MSN-*.md"))) != 120:build_documents()
    ids=list(dict.fromkeys(x.upper() for x in AIRCRAFT.findall(question)))
    if len(ids)>3:raise ValueError("Ask about up to three aircraft")
    if ids:
        return [{"source":f"{aid}.md","aircraft_id":aid,"text":(DOCS/f"{aid}.md").read_text()[:12000]} for aid in ids if (DOCS/f"{aid}.md").exists()][:limit]
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE VIRTUAL TABLE documents USING fts5(source UNINDEXED,content)")
        for path in sorted(DOCS.glob("SIM-MSN-*.md")):
            db.execute("INSERT INTO documents VALUES(?,?)",(path.name,path.read_text()))
        terms=re.findall(r"[a-zA-Z0-9]{3,}",question)[:10]
        if not terms:return []
        stopwords={"what","which","where","when","does","with","from","about","show","find","give","the","and","for","are","how","all","have","that","this","quality","aircraft","records","record","synthetic"}
        terms=[t.lower() for t in terms if t.lower() not in stopwords]
        if not terms:return []
        query=" OR ".join('"'+t+'"' for t in dict.fromkeys(terms))
        rows=db.execute("SELECT source,content FROM documents WHERE documents MATCH ? ORDER BY bm25(documents) LIMIT ?",(query,limit)).fetchall()
        return [{"source":name,"aircraft_id":name[:-3],"text":content[:12000]} for name,content in rows]

def make_prompt(question,documents):
    snippets="\n\n".join(f"[SOURCE {i}: {d['source']}]\n{d['text']}" for i,d in enumerate(documents,1))
    return ("Answer questions about fictional aircraft quality records. Use ONLY the sources. Do not invent findings, approvals or causes. Cite source filenames in square brackets. Never interpret these records as airworthiness clearance.\n\nQUESTION: "+question+"\n\nSOURCES:\n"+snippets)

def gemini_answer(question,documents):
    key=os.environ.get("GEMINI_API_KEY","").strip()
    if not key:raise RetrievalError("GEMINI_API_KEY is not configured. Uncheck Use Gemini API for retrieval-only mode.")
    model=os.environ.get("GEMINI_MODEL","gemini-2.5-flash")
    if not re.fullmatch(r"[a-zA-Z0-9._-]+",model):raise RetrievalError("Invalid model name")
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body={"contents":[{"parts":[{"text":make_prompt(question,documents)}]}],"generationConfig":{"temperature":0,"maxOutputTokens":800}}
    req=urllib.request.Request(url,data=json.dumps(body).encode(),headers={"Content-Type":"application/json","x-goog-api-key":key},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=25) as response:result=json.load(response)
        parts=result.get("candidates",[{}])[0].get("content",{}).get("parts",[])
        text="".join(p.get("text","") for p in parts).strip()
        if not text:raise RetrievalError("Gemini returned no answer")
        return text
    except urllib.error.HTTPError as e:raise RetrievalError(f"Gemini API returned HTTP {e.code}") from e
    except (urllib.error.URLError,TimeoutError) as e:raise RetrievalError("Gemini API connection failed") from e

def answer(question,use_gemini=False):
    docs=search(question)
    if not docs:return {"answer":"No matching synthetic quality record found. Cannot answer from the available documents.","citations":[],"grounded":False,"mode":"retrieval"}
    citations=[{"source":d["source"],"aircraft_id":d["aircraft_id"]} for d in docs]
    if use_gemini:
        generated=gemini_answer(question,docs)
        # Model output is unverified even when supplied with retrieved evidence.
        return {"answer":generated,"citations":citations,"grounded":False,"mode":"gemini","warning":"AI-generated text may contain unsupported claims. Verify against the cited source documents."}
    return {"answer":"Retrieved synthetic quality documents. Enable Gemini to generate a grounded answer.","citations":citations,"grounded":True,"mode":"retrieval","excerpts":[d["text"][:1500] for d in docs]}
