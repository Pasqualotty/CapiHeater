"""
Webhook handler for EfiBank Pix payment confirmations — placeholder for Phase 9.

This would typically be a small Flask/FastAPI app hosted externally
that receives POST callbacks from EfiBank when a Pix payment is confirmed,
then activates the user's license in Supabase.
"""


def handle_pix_webhook(payload: dict) -> bool:
    """Process an EfiBank Pix webhook payload.

    Steps:
    1. Validate the webhook signature
    2. Extract payment info (txid, value, payer)
    3. Match to a pending license activation
    4. Activate the license in Supabase

    Returns True on success.
    """
    raise NotImplementedError("Webhook handler pending (Phase 9)")
