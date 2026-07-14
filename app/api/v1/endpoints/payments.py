from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import order_service, payment_service

router = APIRouter(prefix="/payments", tags=["Orders & Payment"])


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Stripe webhook (внутрішній)",
    description=(
        "Приймає події від Stripe. На подію `checkout.session.completed` позначає "
        "відповідне замовлення як `paid`.\n\n"
        "Не викликається напряму користувачами — налаштовується в Stripe Dashboard "
        "як webhook endpoint. Перевіряє підпис через `Stripe-Signature` заголовок."
    ),
)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = payment_service.verify_webhook_event(payload, sig_header)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Недійсний підпис webhook"
        )

    if event["type"] == "checkout.session.completed":
        session_id = event["data"]["object"]["id"]
        await order_service.mark_order_paid_by_session_id(db, session_id)

    return {"status": "ok"}
