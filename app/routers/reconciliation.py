from datetime import datetime, timedelta, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.core.config import get_settings
from app.core.security import get_current_user
from app.services.deterministic_matching import DeterministicMatcher
from app.services.grok_reasoning import GrokReasoningService
from app.services.finance_intent import gather_evidence

router=APIRouter(tags=["reconciliation"])


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if type(value).__name__ == "ObjectId":
        return str(value)
    return value


def owner(user_id,user):
    if user_id!=user["google_sub"]: raise HTTPException(403,"You may access only your own records.")

@router.post("/demo-data/{user_id}")
async def create_demo_data(user_id:str,request:Request,user:dict=Depends(get_current_user)):
    """Create a small linked Razorpay-like dataset for local project demonstrations."""
    owner(user_id,user); db=request.app.state.mongo.database; now=datetime.now(timezone.utc)
    invoices=[
        {"razorpay_invoice_id":"inv_demo_001","invoice_number":"INV-DEMO-001","customer_name":"Aarav Shah","customer_email":"aarav@example.com","amount":125000,"amount_paid":125000,"status":"paid","currency":"INR","issued_at":now-timedelta(hours=3)},
        {"razorpay_invoice_id":"inv_demo_002","invoice_number":"INV-DEMO-002","customer_name":"Priya Mehta","customer_email":"priya@example.com","amount":75000,"amount_paid":0,"status":"issued","currency":"INR","issued_at":now-timedelta(days=2)},
        {"razorpay_invoice_id":"inv_demo_003","invoice_number":"INV-DEMO-003","customer_name":"Neel Patel","customer_email":"neel@example.com","amount":50000,"amount_paid":0,"status":"issued","currency":"INR","issued_at":now-timedelta(days=1)},
    ]
    payments=[
        {"razorpay_payment_id":"pay_demo_001","invoice_id":"inv_demo_001","settlement_id":"set_demo_001","email":"aarav@example.com","amount":125000,"status":"captured","currency":"INR","method":"card","captured_at":now-timedelta(hours=2)},
        {"razorpay_payment_id":"pay_demo_002","invoice_id":"inv_demo_002","settlement_id":"set_demo_001","email":"priya@example.com","amount":35000,"status":"captured","currency":"INR","method":"upi","captured_at":now-timedelta(days=1)},
    ]
    settlements=[{"razorpay_settlement_id":"set_demo_001","amount":156950,"fees":3125,"tax":563,"status":"processed","currency":"INR","utr":"DEMO-UTR-001","settled_at":now-timedelta(hours=1)}]
    for collection,key,records in [("invoices","razorpay_invoice_id",invoices),("payments","razorpay_payment_id",payments),("settlements","razorpay_settlement_id",settlements)]:
        for record in records:
            record.update({"user_id":user_id,"raw":dict(record),"synced_at":now,"created_at":now,"updated_at":now})
            await getattr(db,collection).update_one({"user_id":user_id,key:record[key]},{"$set":record},upsert=True)
    return {"message":"Demo data created. Run reconciliation next.","invoices":len(invoices),"payments":len(payments),"settlements":len(settlements)}

@router.post("/reconcile/{user_id}")
async def reconcile(user_id:str,request:Request,user:dict=Depends(get_current_user)):
    owner(user_id,user)
    db=request.app.state.mongo.database
    try:
        invoices=await db.invoices.find({"user_id":user_id}).to_list(None); payments=await db.payments.find({"user_id":user_id}).to_list(None); settlements=await db.settlements.find({"user_id":user_id}).to_list(None)
        results=DeterministicMatcher().reconcile(invoices,payments,settlements); grok=GrokReasoningService(db,get_settings()); ai=0; ai_errors=[]
        for r in results:
            await db.matches.update_one({"user_id":user_id,"invoice_id":r.invoice_id},{"$set":{**r.to_document(),"user_id":user_id}},upsert=True)
            if r.match_tier==4 and get_settings().groq_api_key:
                invoice=next((x for x in invoices if x.get("razorpay_invoice_id")==r.invoice_id),{})
                candidates=[p for p in payments if p.get("razorpay_payment_id") not in r.payment_ids][:10]
                try:
                    await grok.explain_tier_four(user_id,r,invoice,candidates); ai+=1
                except RuntimeError as error:
                    ai_errors.append({"invoice_id":r.invoice_id,"error":str(error)})
                    await db.exceptions.update_one(
                        {"user_id":user_id,"invoice_id":r.invoice_id,"status":"open"},
                        {"$set":{"category":"unresolved_reconciliation","severity":"medium","details":{"deterministic_result":r.to_document(),"ai_error":str(error)},"updated_at":datetime.now(timezone.utc)},"$setOnInsert":{"created_at":datetime.now(timezone.utc),"status":"open"}},upsert=True,
                    )
        return _json_safe({"reconciled":len(results),"tier4_reasoned":ai,"ai_errors":ai_errors,"results":[r.to_document() for r in results]})
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Reconciliation failed: {type(error).__name__}: {error}") from error

@router.get("/stats/{user_id}")
async def stats(user_id:str,request:Request,user:dict=Depends(get_current_user)):
    owner(user_id,user); db=request.app.state.mongo.database; rows=await db.matches.find({"user_id":user_id}).to_list(None); total=len(rows); tiers={str(i):sum(r.get("match_tier")==i for r in rows) for i in range(1,5)}; now=datetime.now(timezone.utc)
    async def docs(name): return await getattr(db,name).find({"user_id":user_id}).sort("created_at",-1).to_list(50)
    invoices,payments,settlements=await docs("invoices"),await docs("payments"),await docs("settlements")
    def period(items,field,days): return sum(1 for x in items if isinstance(x.get(field),datetime) and x[field]>=now-timedelta(days=days))
    classes={k:sum(r.get("classification")==k for r in rows) for k in ["Paid","Partial","Unpaid","Exception"]}
    matched_payment_ids={payment_id for row in rows for payment_id in row.get("payment_ids",[])}
    open_exceptions=await db.exceptions.find({"user_id":user_id,"status":"open"}).sort("updated_at",-1).to_list(20)
    collected=sum(item.get("amount",0) or 0 for item in payments if item.get("status") in {"captured","authorized"})
    settled=sum(item.get("amount",0) or 0 for item in settlements)
    outstanding=sum(max(0,(item.get("amount",0) or 0)-(item.get("amount_paid",0) or 0)) for item in invoices)
    ai_confidences=[item.get("ai_reasoning",{}).get("confidence") for item in open_exceptions if isinstance(item.get("ai_reasoning"),dict) and isinstance(item["ai_reasoning"].get("confidence"),(int,float))]
    last_reconciled=max((item.get("reconciled_at") for item in rows if isinstance(item.get("reconciled_at"),datetime)),default=None)
    today_start=now.replace(hour=0,minute=0,second=0,microsecond=0)
    return _json_safe({
        "total":total,"matched":tiers["1"]+tiers["2"]+tiers["3"],"match_rate":round((tiers["1"]+tiers["2"]+tiers["3"])/total*100,2) if total else 0,"by_tier":tiers,"classification":classes,
        "counts":{"total_invoices":len(invoices),"total_payments":len(payments),"total_settlements":len(settlements),"fully_paid":classes["Paid"],"partially_paid":classes["Partial"],"unpaid":classes["Unpaid"],"authorized":sum(item.get("status")=="authorized" for item in payments)},
        "amounts":{"total_outstanding":outstanding,"total_collected":collected,"total_settled":settled,"payment_settlement_difference":collected-settled},
        "reconciliation":{"match_rate":round((tiers["1"]+tiers["2"]+tiers["3"])/total*100,2) if total else 0,"total_matched_records":tiers["1"]+tiers["2"]+tiers["3"],"auto_reconciled":tiers["1"]+tiers["2"]+tiers["3"],"ai_resolved":sum(1 for item in open_exceptions if item.get("ai_reasoning")),"unresolved_exceptions":len(open_exceptions),"avg_confidence":round(sum(ai_confidences)/len(ai_confidences)*100,2) if ai_confidences else 0},
        "risk":{"duplicate_payments":0,"unmatched_payments":sum(item.get("razorpay_payment_id") not in matched_payment_ids for item in payments),"pending_payments":sum(item.get("status") in {"authorized","created"} for item in payments),"settlement_exceptions":sum(abs(item.get("settlement_delta") or 0)>100 for item in rows)},
        "throughput":{"records_processed":len(invoices)+len(payments)+len(settlements),"last_reconciled_at":last_reconciled},
        "activity":{"invoices":[period(invoices,"issued_at",1),period(invoices,"issued_at",7),period(invoices,"issued_at",30)],"payments":[period(payments,"captured_at",1),period(payments,"captured_at",7),period(payments,"captured_at",30)]},
        "today":{"invoices":[item for item in invoices if isinstance(item.get("issued_at"),datetime) and item["issued_at"]>=today_start],"payments":[item for item in payments if isinstance(item.get("captured_at"),datetime) and item["captured_at"]>=today_start]},
        "exceptions":open_exceptions,"recent":{"invoices":invoices[:8],"payments":payments[:8],"settlements":settlements[:8]},
    })

@router.get("/search/{user_id}")
async def search(
    user_id: str, request: Request,
    q: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
):
    owner(user_id,user); db=request.app.state.mongo.database
    needle=q.strip() if q else None
    if not needle and not date_from and not date_to:
        raise HTTPException(422,"Provide a search query or a date range.")

    date_range={}
    if date_from:
        try: date_range["$gte"]=datetime.fromisoformat(date_from)
        except ValueError: raise HTTPException(422,"date_from must be an ISO date/datetime string.")
    if date_to:
        try: date_range["$lte"]=datetime.fromisoformat(date_to)
        except ValueError: raise HTTPException(422,"date_to must be an ISO date/datetime string.")

    date_field={"invoices":"issued_at","payments":"captured_at","settlements":"settled_at"}
    text_fields={
        "invoices":["razorpay_invoice_id","invoice_number","customer_name","customer_email"],
        "payments":["razorpay_payment_id","email"],
        "settlements":["razorpay_settlement_id","utr"],
    }
    out=[]
    for collection,fields in text_fields.items():
        query={"user_id":user_id}; clauses=[]
        if needle:
            rx={"$regex":needle,"$options":"i"}
            clauses.append({"$or":[{f:rx} for f in fields]})
        if date_range:
            clauses.append({date_field[collection]:date_range})
        if clauses:
            query["$and"]=clauses
        docs=await getattr(db,collection).find(query).sort(date_field[collection],-1).limit(50).to_list(50)
        out += [{"type":collection[:-1],"record":x} for x in docs]
    return _json_safe({"items":out})

@router.get("/transactions/{user_id}")
async def transactions(user_id:str,request:Request,classification:str|None=None,skip:int=0,limit:int=Query(50,le=100),user:dict=Depends(get_current_user)):
    owner(user_id,user); q={"user_id":user_id};
    if classification:q["classification"]=classification
    rows=await request.app.state.mongo.database.matches.find(q).skip(skip).limit(limit).to_list(limit)
    return _json_safe({"items":rows,"skip":skip,"limit":limit})

@router.post("/chat/{user_id}")
async def chat(user_id:str,body:dict,request:Request,user:dict=Depends(get_current_user)):
    owner(user_id,user); question=body.get("question")
    if not isinstance(question,str) or not question.strip(): raise HTTPException(422,"question is required")
    db=request.app.state.mongo.database
    try:
        evidence=await gather_evidence(db,user_id,question)
        return await GrokReasoningService(db,get_settings()).answer_exception_question(question,evidence)
    except RuntimeError as error: raise HTTPException(502,str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Chat failed: {type(error).__name__}: {error}") from error 