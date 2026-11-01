"""Voice and typed receipt requests must share the Agent's verification boundary."""
from src.core import Agent
from src.voice_receipts import normalize_spoken_digits,route_message,verified_receipt_for_session


def test_spoken_digit_runs_english_hindi_and_raw_number():
    assert normalize_spoken_digits('order six nine five two zero eight six seven')=='order 69520867'
    assert normalize_spoken_digits('my pin is one six zero zero one seven')=='my pin is 160017'
    assert normalize_spoken_digits('मेरा पिन एक छह शून्य शून्य एक सात')=='मेरा पिन 160017'
    assert normalize_spoken_digits('phone 1234')=='phone 1234'
    assert normalize_spoken_digits('return within seven days')=='return within seven days'


def test_voice_request_verifies_before_attaching_pdf():
    agent=Agent()
    sid='voice_receipt_happy'
    first=route_message(agent,sid,'Can you download my invoice?')
    assert first.pending and first.receipt_pdf is None
    assert 'order ID' in first.answer
    second=route_message(agent,sid,'my order is six nine five two zero eight six seven',first.pending)
    assert second.pending and second.receipt_pdf is None
    assert agent.sessions[sid].verified is False
    assert 'phone' in second.answer
    final=route_message(agent,sid,'my PIN is one six zero zero one seven',second.pending)
    assert final.pending is False
    assert final.receipt_pdf.startswith(b'%PDF-')
    assert final.receipt_name=='ZentroMart_Order_69520867_Receipt.pdf'
    assert final.user_display=='Verification details submitted securely.'
    assert verified_receipt_for_session(agent,sid,'69520867')
    assert not verified_receipt_for_session(agent,'another_browser','69520867')


def test_receipt_for_verified_order_without_new_lookup():
    agent=Agent()
    agent.respond('Help with my order 69520867',session_id='ok',allow_ticket=False)
    agent.respond('160017',session_id='ok',allow_ticket=False)
    turn=route_message(agent,'ok','please download my receipt')
    assert turn.receipt_pdf.startswith(b'%PDF-')
    assert turn.pending is False


def test_wrong_verification_never_generates_pdf_and_blocks():
    agent=Agent()
    sid='blocked'
    a=route_message(agent,sid,'Give me the bill for order 69520867')
    assert a.receipt_pdf is None
    b=route_message(agent,sid,'9999',a.pending)
    assert b.receipt_pdf is None
    assert b.user_display=='Verification details submitted securely.'
    c=route_message(agent,sid,'9998',b.pending)
    assert c.receipt_pdf is None
    assert agent.sessions[sid].verified is False
    d=route_message(agent,sid,'160017',c.pending)
    assert d.receipt_pdf is None
    assert not verified_receipt_for_session(agent,sid,'69520867')


def test_changing_order_invalidates_old_pdf_link():
    agent=Agent()
    a=route_message(agent,'one','Download invoice for 69520867')
    b=route_message(agent,'one','160017',a.pending)
    assert b.receipt_pdf
    route_message(agent,'one','Download invoice for order 12345678')
    assert not verified_receipt_for_session(agent,'one','69520867')


def test_retry_request_does_not_bypass_two_attempt_limit():
    agent=Agent()
    sid='retry_blocked'
    a=route_message(agent,sid,'download receipt 69520867')
    b=route_message(agent,sid,'1234',a.pending)
    c=route_message(agent,sid,'5678',b.pending)
    blocked=route_message(agent,sid,'download receipt 69520867',c.pending)
    assert blocked.decision=='refuse'
    assert blocked.receipt_pdf is None
    assert agent.sessions[sid].attempts==2


def test_recognized_hindi_receipt_request():
    agent=Agent()
    t=route_message(agent,'hi','मुझे रसीद चाहिए')
    assert t.pending is True
    assert t.receipt_pdf is None
