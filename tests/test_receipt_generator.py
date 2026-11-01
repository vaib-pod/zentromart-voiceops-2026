"""Verification boundary and PDF generation tests for synthetic order receipts."""
import pytest
from src.receipt_generator import build_receipt_pdf, receipt_filename, money
from src.core import Agent


def test_unverified_order_cannot_generate_receipt():
    order={'order_id':'69520867','verified':False,'found':True,
           'items':[{'title':'Example','sku':'SKU-1','qty':'1','unit_price_inr':'9'}]}
    with pytest.raises(PermissionError):
        build_receipt_pdf(order)


def test_verified_order_generates_pdf_using_actual_order_tool():
    agent=Agent()
    s='receipt-test'
    first=agent.respond('I need help with my order 69520867',session_id=s,allow_ticket=False)
    assert first['verified'] is False
    # This delivery pincode is part of the synthetic fixture, not a real person's secret.
    second=agent.respond('160017',session_id=s,allow_ticket=False)
    assert second['verified'] is True
    verified=agent.sessions[s].safe_order
    pdf=build_receipt_pdf(verified)
    assert pdf.startswith(b'%PDF-')
    assert len(pdf)>2500
    assert receipt_filename('69520867')=='ZentroMart_Order_69520867_Receipt.pdf'
    assert verified['order_id']=='69520867'
    assert verified['items'][0]['title'].startswith('Mixwell')
    assert money(verified['total_inr'])=='INR 3,778.00'


def test_bad_filename_and_amount_rejected():
    with pytest.raises(ValueError): receipt_filename('../something')
    with pytest.raises(ValueError): money('not-a-price')
