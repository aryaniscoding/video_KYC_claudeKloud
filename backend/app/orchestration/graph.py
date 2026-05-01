"""
LangGraph Post-QA Pipeline — triggered after Q&A completes.

Nodes:
  form_assembly → hard_rules → [decline | ml_scoring → offer_matrix → pdf_generation → audit_commit]
  Any node can route to hitl_review on anomaly.

Checkpointing: MemorySaver for dev (swap to AsyncPostgresSaver in prod).
Thread ID = session_token_jti (one graph per session, resumable).
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import TypedDict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

_MODEL_VER_DEFAULT = "v1.0"


# ── State ──────────────────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    session_id: str
    session_token_jti: str
    application_id: str
    policy_ver: str
    model_version: str

    features: dict

    hard_rules_passed: bool
    failing_rule: str | None
    failing_rule_reason: str | None

    pd_score: float
    risk_band: str
    eligible: bool
    shap_values: dict
    top_positive_features: list
    top_negative_features: list

    approved_amount: float | None
    offer: dict | None

    pdf_storage_path: str | None
    pdf_hash: str | None
    download_url: str | None

    next_node: str
    error: str | None
    hitl_reason: str | None
    decline_reason: str | None


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _load_session_app_customer(db, session_id: str, application_id: str):
    from app.models import Session, Application, Customer
    from sqlalchemy import select

    sess_r = await db.execute(select(Session).where(Session.id == uuid.UUID(session_id)))
    session = sess_r.scalar_one()
    app_r = await db.execute(select(Application).where(Application.id == uuid.UUID(application_id)))
    application = app_r.scalar_one()
    cust_r = await db.execute(select(Customer).where(Customer.id == session.customer_id))
    customer = cust_r.scalar_one()
    return session, application, customer


# ── Node: form_assembly ────────────────────────────────────────────────────────

async def node_form_assembly(state: PipelineState) -> PipelineState:
    from app.database import AsyncSessionLocal
    from app.models import Application
    from sqlalchemy import select
    from app.services.decision_service import build_35_features
    from app.services.history_service import run_history_check

    async with AsyncSessionLocal() as db:
        session, application, customer = await _load_session_app_customer(
            db, state["session_id"], state["application_id"]
        )
        history = await run_history_check(customer, db)

        session_dict = {
            "geo_risk_score": session.geo_risk_score,
            "ip_risk_score": session.ip_risk_score,
            "device_risk_score": session.device_risk_score,
            "liveness_score": session.liveness_score,
            "age_consistency_score": session.age_consistency_score,
            "face_confidence": session.face_confidence,
            "avg_response_latency_ms": session.avg_response_latency_ms,
            "hesitation_count": session.hesitation_count,
            "question_retry_count": session.question_retry_count,
            "consent_confidence": session.consent_confidence,
        }
        app_dict = {
            "monthly_income": application.monthly_income,
            "employment_type": application.employment_type,
            "employer_name": application.employer_name,
            "job_tenure_years": application.job_tenure_years,
            "requested_amount": application.requested_amount,
            "preferred_tenure_months": application.preferred_tenure_months,
            "existing_emi_monthly": application.existing_emi_monthly,
            "loan_purpose": application.loan_purpose,
            "extraction_confidence_avg": application.extraction_confidence_avg,
            "inconsistency_score": application.inconsistency_score,
        }
        customer_dict = {
            "credit_score": customer.credit_score,
            "dpd_12m": customer.dpd_12m,
            "dpd_24m": customer.dpd_24m,
            "active_loans_count": customer.active_loans_count,
            "total_outstanding_inr": customer.total_outstanding_inr,
        }
        features = build_35_features(app_dict, session_dict, customer_dict, history)

        # Persist feature vector
        app_obj = await db.get(Application, uuid.UUID(state["application_id"]))
        app_obj.feature_vector = features
        await db.commit()

    state["features"] = features
    state["next_node"] = "hard_rules"
    return state


# ── Node: hard_rules ───────────────────────────────────────────────────────────

async def node_hard_rules(state: PipelineState) -> PipelineState:
    from app.services.decision_service import run_hard_rules
    result = run_hard_rules(state["features"])
    state["hard_rules_passed"] = result["passed"]
    state["failing_rule"] = result["failing_rule"]
    state["failing_rule_reason"] = result["failing_rule_reason"]
    state["next_node"] = "ml_scoring" if result["passed"] else "decline"
    return state


# ── Node: ml_scoring ───────────────────────────────────────────────────────────

async def node_ml_scoring(state: PipelineState) -> PipelineState:
    from app.services.decision_service import run_ml_scoring
    result = run_ml_scoring(state["features"])
    state.update({
        "pd_score": result["pd_score"],
        "risk_band": result["risk_band"],
        "eligible": result["eligible"],
        "shap_values": result["shap_values"],
        "top_positive_features": result["top_positive_features"],
        "top_negative_features": result["top_negative_features"],
        "model_version": result["model_version"],
    })
    if result["risk_band"] == "HIGH":
        state["next_node"] = "hitl_review"
        state["hitl_reason"] = "high_risk_band"
    elif result["risk_band"] == "VERY_HIGH":
        state["next_node"] = "decline"
        state["decline_reason"] = "Risk score above approval threshold"
    else:
        state["next_node"] = "offer_matrix"
    return state


# ── Node: offer_matrix ─────────────────────────────────────────────────────────

async def node_offer_matrix(state: PipelineState) -> PipelineState:
    from app.database import AsyncSessionLocal
    from app.models import Session
    from sqlalchemy import select
    from app.services.decision_service import compute_offer

    # Fetch max_amount from session
    async with AsyncSessionLocal() as db:
        sess_r = await db.execute(select(Session).where(Session.id == uuid.UUID(state["session_id"])))
        session = sess_r.scalar_one()
        max_amount = float(session.max_amount)

    features = state["features"]
    offer = compute_offer(
        risk_band=state["risk_band"],
        monthly_income=features.get("monthly_income", 0),
        requested_amount=features.get("requested_amount", 0),
        max_amount=max_amount,
    )
    state["offer"] = offer
    state["approved_amount"] = offer["approved_amount"] if offer else None
    state["next_node"] = "pdf_generation" if offer else "decline"
    return state


# ── Node: pdf_generation ───────────────────────────────────────────────────────

async def node_pdf_generation(state: PipelineState) -> PipelineState:
    from app.database import AsyncSessionLocal
    from app.models import Session, Application, Customer, Decision, OfferPDF, SessionStatus
    from app.services.pdf_service import generate_offer_pdf
    from app.services.llm_extraction_service import shap_to_plain_english

    # Generate plain-English SHAP reasons via Gemini
    shap_reasons = []
    try:
        offer = state.get("offer") or {}
        shap_reasons = await shap_to_plain_english(
            top_positive=state.get("top_positive_features", []),
            top_negative=state.get("top_negative_features", []),
            application_context=state.get("features", {}),
        )
    except Exception as e:
        logger.warning("SHAP plain-English generation failed: %s", e)

    async with AsyncSessionLocal() as db:
        session, application, customer = await _load_session_app_customer(
            db, state["session_id"], state["application_id"]
        )
        offer_ref_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        offer = state["offer"]

        decision = Decision(
            session_id=session.id,
            application_id=application.id,
            hard_rules_passed=state["hard_rules_passed"],
            failing_rule=state.get("failing_rule"),
            failing_rule_reason=state.get("failing_rule_reason"),
            pd_score=state["pd_score"],
            risk_band=state["risk_band"],
            eligible=True,
            shap_values=state.get("shap_values"),
            top_positive_features=state.get("top_positive_features"),
            top_negative_features=state.get("top_negative_features"),
            model_version=state.get("model_version", _MODEL_VER_DEFAULT),
            approved_amount=state["approved_amount"],
            interest_rate=offer["interest_rate"],
            recommended_tenure_months=offer["recommended_tenure_months"],
            emi_options=offer["emi_options"],
            processing_fee_pct=offer["processing_fee_pct"],
            offer_matrix_version=offer["offer_matrix_version"],
            offer_ref_id=offer_ref_id,
            offer_valid_until=datetime.fromisoformat(offer["offer_valid_until"]),
            decided_at=now,
        )
        db.add(decision)
        await db.flush()   # get decision.id before PDF generation

        pdf_result = await generate_offer_pdf(
            session=session,
            application=application,
            customer=customer,
            decision=decision,
            offer=offer,
            shap_reasons=shap_reasons,
        )

        pdf_record = OfferPDF(
            session_id=session.id,
            decision_id=decision.id,
            offer_ref_id=offer_ref_id,
            storage_path=pdf_result["storage_path"],
            pdf_hash=pdf_result["pdf_hash"],
            download_url=pdf_result["download_url"],
            download_expires_at=pdf_result["download_expires_at"],
            created_at=now,
        )
        db.add(pdf_record)
        session.status = SessionStatus.APPROVED
        await db.commit()

    state["pdf_storage_path"] = pdf_result["storage_path"]
    state["pdf_hash"] = pdf_result["pdf_hash"]
    state["download_url"] = pdf_result["download_url"]
    state["next_node"] = "audit_commit"
    return state


# ── Node: decline ──────────────────────────────────────────────────────────────

async def node_decline(state: PipelineState) -> PipelineState:
    from app.database import AsyncSessionLocal
    from app.models import Session, Application, Decision, SessionStatus

    async with AsyncSessionLocal() as db:
        session, application, _ = await _load_session_app_customer(
            db, state["session_id"], state["application_id"]
        )
        decision = Decision(
            session_id=session.id,
            application_id=application.id,
            hard_rules_passed=state.get("hard_rules_passed", False),
            failing_rule=state.get("failing_rule"),
            failing_rule_reason=state.get("failing_rule_reason") or state.get("decline_reason"),
            pd_score=state.get("pd_score"),
            risk_band=state.get("risk_band"),
            eligible=False,
            shap_values=state.get("shap_values"),
            top_positive_features=state.get("top_positive_features"),
            top_negative_features=state.get("top_negative_features"),
            model_version=state.get("model_version", _MODEL_VER_DEFAULT),
            offer_ref_id=uuid.uuid4(),
            decided_at=datetime.now(timezone.utc),
        )
        db.add(decision)
        session.status = SessionStatus.DECLINED
        await db.commit()

    state["next_node"] = "audit_commit"
    return state


# ── Node: hitl_review ──────────────────────────────────────────────────────────

async def node_hitl_review(state: PipelineState) -> PipelineState:
    from app.database import AsyncSessionLocal
    from app.models import Session, AuditLog, SessionStatus

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        sess_r = await db.execute(select(Session).where(Session.id == uuid.UUID(state["session_id"])))
        session = sess_r.scalar_one()
        session.status = SessionStatus.HITL
        db.add(AuditLog(
            session_id=session.id,
            node_name="hitl_review",
            event_type="hitl_triggered",
            event_data={"reason": state.get("hitl_reason"), "pd_score": state.get("pd_score")},
            policy_ver=state["policy_ver"],
        ))
        await db.commit()

    state["next_node"] = END
    return state


# ── Node: audit_commit ─────────────────────────────────────────────────────────

async def node_audit_commit(state: PipelineState) -> PipelineState:
    from app.database import AsyncSessionLocal
    from app.models import AuditLog

    async with AsyncSessionLocal() as db:
        db.add(AuditLog(
            session_id=uuid.UUID(state["session_id"]),
            node_name="audit_commit",
            event_type="pipeline_complete",
            event_data={
                "features": state.get("features"),
                "shap_values": state.get("shap_values"),
                "pd_score": state.get("pd_score"),
                "risk_band": state.get("risk_band"),
                "approved_amount": state.get("approved_amount"),
                "pdf_hash": state.get("pdf_hash"),
            },
            policy_ver=state["policy_ver"],
            model_version=state.get("model_version"),
        ))
        await db.commit()

    state["next_node"] = END
    return state


# ── Routing ────────────────────────────────────────────────────────────────────

def _route(state: PipelineState) -> str:
    return state["next_node"]


# ── Graph construction ─────────────────────────────────────────────────────────

def _build_graph():
    g = StateGraph(PipelineState)

    g.add_node("form_assembly", node_form_assembly)
    g.add_node("hard_rules", node_hard_rules)
    g.add_node("ml_scoring", node_ml_scoring)
    g.add_node("offer_matrix", node_offer_matrix)
    g.add_node("pdf_generation", node_pdf_generation)
    g.add_node("decline", node_decline)
    g.add_node("hitl_review", node_hitl_review)
    g.add_node("audit_commit", node_audit_commit)

    g.set_entry_point("form_assembly")
    g.add_edge("form_assembly", "hard_rules")
    g.add_conditional_edges("hard_rules", _route, {
        "ml_scoring": "ml_scoring", "decline": "decline",
    })
    g.add_conditional_edges("ml_scoring", _route, {
        "offer_matrix": "offer_matrix",
        "hitl_review": "hitl_review",
        "decline": "decline",
    })
    g.add_conditional_edges("offer_matrix", _route, {
        "pdf_generation": "pdf_generation", "decline": "decline",
    })
    g.add_edge("pdf_generation", "audit_commit")
    g.add_edge("decline", "audit_commit")
    g.add_edge("hitl_review", END)
    g.add_edge("audit_commit", END)

    return g.compile(checkpointer=MemorySaver())


_graph = _build_graph()


# ── Public entry point ─────────────────────────────────────────────────────────

async def run_post_qa_pipeline(session_id: str, session_token_jti: str, application_id: str) -> None:
    """Fire-and-forget: called from Q&A WS after all 8 questions complete."""
    initial: PipelineState = {
        "session_id": session_id,
        "session_token_jti": session_token_jti,
        "application_id": application_id,
        "policy_ver": "v1.0",
        "model_version": _MODEL_VER_DEFAULT,
        "features": {},
        "hard_rules_passed": False,
        "failing_rule": None,
        "failing_rule_reason": None,
        "pd_score": 0.0,
        "risk_band": "",
        "eligible": False,
        "shap_values": {},
        "top_positive_features": [],
        "top_negative_features": [],
        "approved_amount": None,
        "offer": None,
        "pdf_storage_path": None,
        "pdf_hash": None,
        "download_url": None,
        "next_node": "form_assembly",
        "error": None,
        "hitl_reason": None,
        "decline_reason": None,
    }
    config = {"configurable": {"thread_id": session_token_jti}}
    try:
        await _graph.ainvoke(initial, config=config)
        logger.info("Pipeline complete: session=%s", session_token_jti)
    except Exception:
        logger.exception("Pipeline error: session=%s", session_token_jti)
        # Mark session HITL so it doesn't stay stuck in PROCESSING forever
        try:
            from app.database import AsyncSessionLocal
            from app.models import Session, SessionStatus, AuditLog
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                r = await db.execute(select(Session).where(Session.id == uuid.UUID(session_id)))
                sess = r.scalar_one_or_none()
                if sess and sess.status == SessionStatus.PROCESSING:
                    sess.status = SessionStatus.HITL
                    db.add(AuditLog(
                        session_id=sess.id,
                        node_name="pipeline",
                        event_type="hitl_triggered",
                        event_data={"reason": "pipeline_exception"},
                        policy_ver=sess.policy_ver,
                    ))
                    await db.commit()
        except Exception:
            logger.exception("Failed to mark session HITL after pipeline error: session=%s", session_token_jti)
