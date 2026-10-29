"""Minimal conversation email copy with a fixed trusted website origin."""

from uuid import UUID

from app.contracts.domain_types import NotificationClaim

SITE_ORIGIN = "https://clip-iisc.site"


def render_notification(claim: NotificationClaim) -> tuple[str, str]:
    """Return generic subject and text linked only to the claimed conversation.

    The caller supplies a server-validated claim. No listing, message, contact,
    OTP or provider data is available to the template or included in its output.
    """
    if (
        not isinstance(claim, NotificationClaim)
        or not isinstance(claim.conversation_id, UUID)
        or claim.conversation_id.version != 4
    ):
        raise ValueError("Invalid conversation notification")
    link = f"{SITE_ORIGIN}/my/conversations/{claim.conversation_id}"
    if claim.event_kind == "new_conversation":
        return (
            "A new conversation on CLIP",
            f"Someone started a conversation with you on CLIP.\n\nOpen your conversation: {link}\n",
        )
    if claim.event_kind == "unread_reminder":
        return (
            "You have an unread message on CLIP",
            f"You have an unread message in a CLIP conversation.\n\nOpen your conversation: {link}\n",
        )
    raise ValueError("Invalid conversation notification")
