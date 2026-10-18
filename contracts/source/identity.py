"""Required internal Identity contact declarations — PD-11 step 8.

These are reviewed interface requirements, not implemented operations or HTTP
mappings. DL-00 must bind the trusted caller, own-contact authorization and
conversation/contact-sharing permissions before a provider is enabled. A user
ID supplied by a consumer is never sufficient authority to disclose contacts.
"""

from pydantic import BaseModel, Field

from app.core.identifiers import UserId


class ShareableContactOptions(BaseModel):
    """Availability flags only; no email, phone or UPI values are disclosed.

    Return only within the authorized contact-sharing flow. Exact trusted-caller
    binding/error semantics require DL-00/Identity review before implementation.
    """

    user_id: UserId
    has_email: bool
    has_phone: bool
    has_upi_id: bool


class SelectedOwnContacts(BaseModel):
    """Only explicitly selected own-contact values may be returned privately.

    All fields are required and nullable; unselected/absent values remain None.
    Repr hides values, but dumps/serialization are still private data and must
    never enter logs, errors or test output. CN-02 handles the separately reviewed
    encrypted sharing flow; this declaration does not select a crypto protocol.
    """

    email: str | None = Field(repr=False)
    phone: str | None = Field(repr=False)
    upi_id: str | None = Field(repr=False)


async def get_shareable_contact_options(user_id: UserId) -> ShareableContactOptions:
    """Declare authorized availability lookup; provide no implementation.

    No persistence, provider or user data is read. DL-00 must specify the trusted
    actor binding and allowed target before ID-01 implements this operation.
    """
    raise NotImplementedError("Identity contact interface is declaration-only")


async def get_selected_own_contacts(
    user_id: UserId, fields: set[str]
) -> SelectedOwnContacts:
    """Declare selected own-contact retrieval through the authorized share flow.

    The implementation must enforce explicit field selection and consent and
    return no unselected values. DL-00 defines caller binding, field validation
    and errors; no arbitrary-ID disclosure or notification-recipient lookup is
    authorized by this signature. This declaration always fails if invoked.
    """
    raise NotImplementedError("Identity contact interface is declaration-only")
