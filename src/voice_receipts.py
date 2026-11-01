"""Route conversational receipt requests through the existing verified Agent.

This module performs *no* order lookups of its own. The underlying agent and
its lookup_order tool are the only authorities for verification. The UI must
only offer the returned PDF while that same session remains verified.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from src.receipt_generator import build_receipt_pdf, receipt_filename

_REQUEST = re.compile(r"\b(?:invoice|receipt|bill)\b|रसीद|बिल|इनवॉइस", re.I)
_ORDER = re.compile(r"(?<!\d)\d{8}(?!\d)")
_PROOF = re.compile(r"(?<!\d)(?:\d{4}|\d{6})(?!\d)")
_CANCEL = re.compile(r"\b(?:never\s?mind|cancel (?:my |the )?(?:receipt|invoice|bill)(?: request)?|forget (?:my |the )?(?:receipt|invoice|bill))\b", re.I)
_DIGIT_WORDS = {
    'zero':'0','oh':'0','o':'0','one':'1','two':'2','three':'3',
    'four':'4','five':'5','six':'6','seven':'7','eight':'8','nine':'9',
    'शून्य':'0','जीरो':'0','ज़ीरो':'0','एक':'1','दो':'2','तीन':'3',
    'चार':'4','पांच':'5','पाँच':'5','छह':'6','छः':'6',
    'सात':'7','आठ':'8','नौ':'9',
}
_TOKENS = re.compile(r'[\u0900-\u097F]+|[A-Za-z]+|[0-9]+')


def _digit(token: str) -> str | None:
    if len(token)==1:
        try:
            return str(unicodedata.digit(token))
        except (ValueError,TypeError):
            pass
    return _DIGIT_WORDS.get(token.casefold())


def normalize_spoken_digits(message: str) -> str:
    """Join spoken digit runs of length 4, 6 or 8 (English or Hindi).

    E.g. 'six nine five two zero eight six seven' -> '69520867'.
    More complex utterances such as 'sixty nine...' should be restated as
    individual digits, to avoid guessing customer verification values.
    """
    tokens=list(_TOKENS.finditer(message))
    replacements=[]
    j=0
    while j<len(tokens):
        start=j
        digits=[]
        while j<len(tokens):
            if j>start and not re.fullmatch(r'[\s,.-]+',message[tokens[j-1].end():tokens[j].start()]):
                break
            value=_digit(tokens[j].group())
            if value is None:
                break
            digits.append(value)
            j+=1
        if len(digits) in (4,6,8):
            replacements.append((tokens[start].start(),tokens[j-1].end(),''.join(digits)))
        elif j==start:
            j+=1
    result=message
    for a,b,v in reversed(replacements):
        result=result[:a]+v+result[b:]
    return result


@dataclass
class ReceiptTurn:
    answer: str
    decision: str
    pending: bool
    user_display: str
    receipt_pdf: bytes | None = None
    receipt_order_id: str | None = None
    receipt_name: str | None = None


def _session(agent: Any, session_id: str):
    return agent.sessions.get(session_id)


def _trusted_order(s: Any) -> dict | None:
    """Require server-side verification and a matching tool-provided order."""
    if not s or not s.verified or not s.order_id:
        return None
    data=s.safe_order
    if not isinstance(data,dict):
        return None
    if data.get('found') is not True or data.get('verified') is not True:
        return None
    if str(data.get('order_id'))!=str(s.order_id):
        return None
    return data


def verified_receipt_for_session(agent: Any, session_id: str, order_id: str) -> bool:
    """Recheck before rendering any past download button."""
    session=_session(agent,session_id)
    return str(getattr(session,'order_id',None))==str(order_id) and _trusted_order(session) is not None


def route_message(agent: Any, session_id: str, message: str, receipt_pending: bool=False) -> ReceiptTurn:
    """Use for typed and transcribed turns alike. No direct PDF until verified.

    Incoming 4/6 digit proofs are never echoed or stored in the visible chat
    log by the caller; returns a safely masked `user_display` value.
    """
    original=str(message).strip()
    if not original:
        return ReceiptTurn('Please repeat your question.','clarify',receipt_pending,'')
    normalized=normalize_spoken_digits(original)
    s=_session(agent,session_id)
    wants_receipt=bool(_REQUEST.search(normalized))
    pending=receipt_pending or wants_receipt
    order_match=_ORDER.search(normalized)
    # Mask proof before sending anything to the chat UI.
    has_proof=bool(_PROOF.search(normalized))
    user_display=('Verification details submitted securely.'
                  if s and s.order_id and not s.verified and has_proof and not order_match
                  else original)

    if receipt_pending and _CANCEL.search(normalized) and not order_match:
        return ReceiptTurn('Okay, I have stopped the receipt request. You can ask another question.',
                           'answer',False,user_display)

    if not pending:
        result=agent.respond(normalized,session_id=session_id,allow_ticket=False)
        return ReceiptTurn(result['answer'],result['decision'],False,user_display)

    # Ask for the order number without revealing any order/customer information.
    if order_match:
        oid=order_match.group()
        if not (s and s.verified and s.order_id==oid):
            # Restrict the agent turn to an order lookup; it will enforce proof
            # and never trust the mere presence of a spoken number.
            result=agent.respond(f'I need help with my order {oid}',
                                 session_id=session_id,allow_ticket=False)
            s=_session(agent,session_id)
            if not s.verified:
                if s.attempts>=2 or s.phase=='verification_blocked':
                    return ReceiptTurn('Verification is blocked after failed attempts. '
                                       'I cannot generate a receipt. Please contact support.',
                                       'refuse',True,user_display)
                return ReceiptTurn('To prepare the receipt for order '+oid+
                                   ', please say the registered phone’s last four digits '
                                   'or the six-digit delivery PIN.',
                                   'clarify',True,user_display)
    elif not s or not s.order_id:
        return ReceiptTurn('Sure. Please say your eight-digit order ID, one digit at a time, '
                           'so I can prepare your PDF receipt.','clarify',True,user_display)
    elif not s.verified:
        if s.attempts>=2 or s.phase=='verification_blocked':
            return ReceiptTurn('Verification is blocked after failed attempts. '
                               'I cannot generate a receipt. Please contact support.',
                               'refuse',True,user_display)
        # Preserve Agent-side attempt limits, proof verification, and tool use.
        result=agent.respond(normalized,session_id=session_id,allow_ticket=False)
        s=_session(agent,session_id)
        # The original Agent keeps in-memory history; redact the secret there too.
        if has_proof and s and s.history:
            s.history[-1]['customer']='[verification details redacted]'
        if not s.verified:
            return ReceiptTurn(result['answer'],result['decision'],True,user_display)
    else:
        # Already verified in this session and requested a receipt.
        pass

    s=_session(agent,session_id)
    verified=_trusted_order(s)
    if verified is None:
        return ReceiptTurn('The order could not be verified. No receipt was generated.',
                           'refuse',True,user_display)
    try:
        pdf=build_receipt_pdf(verified)
        filename=receipt_filename(s.order_id)
    except (ValueError,PermissionError,TypeError):
        return ReceiptTurn('The order is verified, but I could not prepare its PDF receipt. '
                           'Please try again or contact support.',
                           'abstain',True,user_display)
    return ReceiptTurn('Your order has been verified and its PDF receipt is ready. '
                       'Use the Download receipt button below to save it. '
                       'This is an order receipt, not a GST tax invoice.',
                       'answer',False,user_display,pdf,str(s.order_id),filename)
