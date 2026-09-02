from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.core.config import get_settings
from app.core.security import get_current_user
from app.services.deterministic_matching import DeterministicMatcher
from app.services.grok_reasoning import GrokReasoningService

router=APIRouter(tags=["reconciliation"])
def owner(user_id,user):
    if user_id!=user["google_sub"]: raise HTTPException(403,"You may access only your own records.")

@router.post("/reconcile/{user_id}")
async def reconcile(user_id:str,request:Request,user:dict=Depends(get_current_user)):
    owner(user_id,user); db=request.app.state.mongo.database
    invoices=await db.invoices.find({"user_id":user_id}).to_list(None); payments=await db.payments.find({"user_id":user_id}).to_list(None); settlements=await db.settlements.find({"user_id":user_id}).to_list(None)
    results=DeterministicMatcher().reconcile(invoices,payments,settlements); grok=GrokReasoningService(db,get_settings()); ai=0
    for r in results:
        await db.matches.update_one({"user_id":user_id,"invoice_id":r.invoice_id},{"$set":{**r.to_document(),"user_id":user_id}},upsert=True)
        if r.match_tier==4 and get_settings().xai_api_key:
            invoice=next((x for x in invoices if x.get("razorpay_invoice_id")==r.invoice_id),{})
            candidates=[p for p in payments if p.get("razorpay_payment_id") not in r.payment_ids][:10]
            await grok.explain_tier_four(user_id,r,invoice,candidates); ai+=1
    return {"reconciled":len(results),"tier4_reasoned":ai,"results":[r.to_document() for r in results]}

@router.get("/stats/{user_id}")
async def stats(user_id:str,request:Request,user:dict=Depends(get_current_user)):
    owner(user_id,user); db=request.app.state.mongo.database; rows=await db.matches.find({"user_id":user_id}).to_list(None); total=len(rows); tiers={str(i):sum(r.get("match_tier")==i for r in rows) for i in range(1,5)}; now=datetime.now(timezone.utc)
    async def docs(name): return await getattr(db,name).find({"user_id":user_id}).sort("created_at",-1).to_list(50)
    invoices,payments,settlements=await docs("invoices"),await docs("payments"),await docs("settlements")
    def period(items,field,days): return sum(1 for x in items if isinstance(x.get(field),datetime) and x[field]>=now-timedelta(days=days))
    classes={k:sum(r.get("classification")==k for r in rows) for k in ["Paid","Partial","Unpaid","Exception"]}
    return {"total":total,"matched":tiers["1"]+tiers["2"]+tiers["3"],"match_rate":round((tiers["1"]+tiers["2"]+tiers["3"])/total*100,2) if total else 0,"by_tier":tiers,"classification":classes,"activity":{"invoices":[period(invoices,"issued_at",1),period(invoices,"issued_at",7),period(invoices,"issued_at",30)],"payments":[period(payments,"captured_at",1),period(payments,"captured_at",7),period(payments,"captured_at",30)]},"recent":{"invoices":invoices[:8],"payments":payments[:8],"settlements":settlements[:8]}}

@router.get("/search/{user_id}")
async def search(user_id:str,request:Request,q:str=Query(min_length=1),user:dict=Depends(get_current_user)):
    owner(user_id,user); db=request.app.state.mongo.database; needle=q.strip(); rx={"$regex":needle,"$options":"i"}; out=[]
    for collection,fields in [("invoices",["razorpay_invoice_id","invoice_number","customer_name","customer_email"]),("payments",["razorpay_payment_id","email"]),("settlements",["razorpay_settlement_id","utr"])]:
        docs=await getattr(db,collection).find({"user_id":user_id,"$or":[{f:rx} for f in fields]}).sort("created_at",-1).limit(20).to_list(20)
        out += [{"type":collection[:-1],"record":x} for x in docs]
    return {"items":out}

@router.get("/transactions/{user_id}")
async def transactions(user_id:str,request:Request,classification:str|None=None,skip:int=0,limit:int=Query(50,le=100),user:dict=Depends(get_current_user)):
    owner(user_id,user); q={"user_id":user_id};
    if classification:q["classification"]=classification
    rows=await request.app.state.mongo.database.matches.find(q).skip(skip).limit(limit).to_list(limit)
    return {"items":rows,"skip":skip,"limit":limit}

@router.post("/chat/{user_id}")
async def chat(user_id:str,body:dict,request:Request,user:dict=Depends(get_current_user)):
    owner(user_id,user); question=body.get("question")
    if not isinstance(question,str) or not question.strip(): raise HTTPException(422,"question is required")
    exceptions=await request.app.state.mongo.database.exceptions.find({"user_id":user_id}).to_list(20)
    try: return await GrokReasoningService(request.app.state.mongo.database,get_settings()).answer_exception_question(question,exceptions)
    except RuntimeError as error: raise HTTPException(502,str(error)) from error
