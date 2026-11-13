"""Subscription status and Stripe Checkout/webhook integration."""
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from app.api.v1.deps import get_current_user
from app.core.config import secret_value, settings
from app.database.session import get_db
from app.models.platform import UserSubscription
from app.models.user import User

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])
_PLANS = [{"id": "free", "name": "Free", "features": ["Coding practice", "Interview practice"]}, {"id": "pro", "name": "Pro", "features": ["Extended practice", "Resume coaching"]}]


class CheckoutRequest(BaseModel):
    success_url: HttpUrl
    cancel_url: HttpUrl


def _origin(url: str) -> str:
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}"


@router.get("/plans")
def plans():
    return _PLANS


@router.get("/me")
def my_subscription(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.query(UserSubscription).filter_by(user_id=user.id).first()
    if not record:
        return {"plan": "free", "status": "active", "provider": None, "current_period_end": None}
    return {"plan": record.plan, "status": record.status, "provider": record.provider, "current_period_end": record.current_period_end}


@router.post("/checkout")
async def checkout(payload: CheckoutRequest, user: User = Depends(get_current_user)):
    if settings.SUBSCRIPTION_PROVIDER.lower() != "stripe" or not secret_value(settings.STRIPE_SECRET_KEY) or not settings.STRIPE_PRICE_ID:
        raise HTTPException(status_code=503, detail="Subscription checkout is not configured")
    allowed = set(settings.cors_origins)
    if _origin(str(payload.success_url)) not in allowed or _origin(str(payload.cancel_url)) not in allowed:
        raise HTTPException(status_code=422, detail="Checkout URLs must use a configured frontend origin")
    form = {
        "mode": "subscription", "line_items[0][price]": settings.STRIPE_PRICE_ID, "line_items[0][quantity]": "1",
        "success_url": str(payload.success_url), "cancel_url": str(payload.cancel_url), "client_reference_id": user.id,
        "metadata[user_id]": user.id, "subscription_data[metadata][user_id]": user.id,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post("https://api.stripe.com/v1/checkout/sessions", data=form, auth=(secret_value(settings.STRIPE_SECRET_KEY), ""))
            response.raise_for_status()
            data = response.json()
        if not data.get("url"):
            raise ValueError("missing checkout URL")
        return {"checkout_url": data["url"], "session_id": data["id"]}
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=503, detail="Could not create a subscription checkout session") from exc


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    if settings.SUBSCRIPTION_PROVIDER.lower() != "stripe" or not secret_value(settings.STRIPE_WEBHOOK_SECRET):
        raise HTTPException(status_code=503, detail="Subscription webhook is not configured")
    body = await request.body()
    if len(body) > 256 * 1024:
        raise HTTPException(status_code=413, detail="Webhook payload is too large")
    header = request.headers.get("stripe-signature", "")
    parts = dict(piece.split("=", 1) for piece in header.split(",") if "=" in piece)
    try:
        timestamp = int(parts["t"])
        supplied = parts["v1"]
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    if abs(int(time.time()) - timestamp) > 300:
        raise HTTPException(status_code=400, detail="Expired webhook signature")
    expected = hmac.new(secret_value(settings.STRIPE_WEBHOOK_SECRET).encode(), str(timestamp).encode() + b"." + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    try:
        event = json.loads(body)
        event_type = event["type"]
        obj = event["data"]["object"]
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid webhook event")
    metadata = obj.get("metadata") or {}
    user_id = metadata.get("user_id") or obj.get("client_reference_id")
    record = db.query(UserSubscription).filter_by(user_id=user_id).first() if user_id else db.query(UserSubscription).filter_by(provider_reference=obj.get("id")).first()
    if event_type == "checkout.session.completed" and user_id:
        # Checkout completion is not authoritative for the subscription entitlement.
        if record is None:
            record = UserSubscription(user_id=user_id)
            db.add(record)
        record.plan = "free"
        record.status = "pending"
        record.provider = "stripe"
        record.provider_reference = obj.get("subscription")
    elif event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
        subscription_reference = obj.get("id")
        if record is None and user_id:
            record = UserSubscription(user_id=user_id)
            db.add(record)
        if record is None:
            return {"received": True, "processed": False}
        record.provider = "stripe"
        record.provider_reference = subscription_reference or record.provider_reference
        record.status = "canceled" if event_type.endswith("deleted") else str(obj.get("status", "past_due"))[:30]
        record.plan = "pro" if record.status in {"active", "trialing"} else "free"
        period_end = obj.get("current_period_end")
        record.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc) if isinstance(period_end, (int, float)) else None
    else:
        return {"received": True, "processed": False}
    db.commit()
    return {"received": True, "processed": True}
