"""Generate a synthetic ZentroMart order receipt from an *already verified* tool result.

Never call this with a raw order ID or unverified CSV data. This deliberately
is not a GST tax invoice: the capstone dataset lacks statutory tax fields.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from html import escape
from io import BytesIO
import re
from typing import Mapping, Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph, Table, TableStyle, KeepTogether

BG = colors.HexColor('#090B1F')
PANEL = colors.HexColor('#111630')
WHITE = colors.HexColor('#FFFFFF')
PALE = colors.HexColor('#C8D4EF')
BLUE = colors.HexColor('#4D83FF')
PURPLE = colors.HexColor('#5E37D9')


def money(value: Any) -> str:
    """Use INR to avoid missing rupee symbols in standard PDF fonts."""
    try:
        amount = Decimal(str(value if value not in (None, '') else '0'))
        if not amount.is_finite():
            raise ValueError('Non-finite order amount')
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('Invalid amount in verified order') from exc
    return f'INR {amount:,.2f}'


def receipt_filename(order_id: str) -> str:
    oid = str(order_id)
    if not re.fullmatch(r'\d{8}', oid):
        raise ValueError('Invalid order ID')
    return f'ZentroMart_Order_{oid}_Receipt.pdf'


def build_receipt_pdf(verified_order: Mapping[str, Any]) -> bytes:
    """Only accepts the trusted dict returned by a successful lookup_order().

    UI must additionally confirm this is the matching order in the current,
    server-side verified Agent session. A dict alone is not an auth token.
    """
    if verified_order.get('verified') is not True or verified_order.get('found') is not True:
        raise PermissionError('Receipt generation requires a verified order')

    oid = str(verified_order.get('order_id') or '')
    receipt_filename(oid)
    items = verified_order.get('items')
    if not isinstance(items, list) or not items:
        raise ValueError('No order line items available')

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=(595.28, 841.89),
                            rightMargin=46, leftMargin=46,
                            topMargin=64, bottomMargin=56,
                            title=f'ZentroMart Order Receipt {oid}',
                            author='ZentroMart VoiceOps (synthetic demo)')

    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(name='ZBrand', fontName='Helvetica-Bold', fontSize=24,
                          leading=30, textColor=WHITE, spaceAfter=4))
    ss.add(ParagraphStyle(name='ZTitle', fontName='Helvetica-Bold', fontSize=13,
                          leading=18, textColor=WHITE))
    ss.add(ParagraphStyle(name='ZSmall', fontName='Helvetica', fontSize=9,
                          leading=14, textColor=PALE))
    ss.add(ParagraphStyle(name='ZCell', fontName='Helvetica', fontSize=9,
                          leading=13, textColor=WHITE))
    ss.add(ParagraphStyle(name='ZCellRight', parent=ss['ZCell'], alignment=TA_RIGHT))
    ss.add(ParagraphStyle(name='ZCellHead', fontName='Helvetica-Bold', fontSize=8,
                          leading=12, textColor=WHITE))
    ss.add(ParagraphStyle(name='ZCellHeadRight', parent=ss['ZCellHead'], alignment=TA_RIGHT))
    ss.add(ParagraphStyle(name='ZWarn', fontName='Helvetica', fontSize=9,
                          leading=14, textColor=PALE, alignment=TA_LEFT))

    story = []
    story.append(Paragraph('ZENTROMART', ss['ZBrand']))
    story.append(Paragraph('ORDER RECEIPT / SYNTHETIC DEMO', ss['ZSmall']))
    story.append(Spacer(1, 24))
    info = [
        [Paragraph('ORDER ID',ss['ZSmall']), Paragraph('ORDER DATE',ss['ZSmall'])],
        [Paragraph(escape(oid),ss['ZTitle']), Paragraph(escape(str(verified_order.get('placed_at') or 'Not recorded')),ss['ZCell'])],
        [Paragraph('CUSTOMER',ss['ZSmall']), Paragraph('PAYMENT / STATUS',ss['ZSmall'])],
        [Paragraph(escape(str(verified_order.get('customer_first_name') or 'Verified customer')),ss['ZCell']),
         Paragraph(escape(str(verified_order.get('payment_method') or '-').upper()) + ' / ' +
                   escape(str(verified_order.get('status') or '-').replace('_',' ').title()),ss['ZCell'])],
    ]
    t=Table(info,colWidths=[252,251],rowHeights=[19,27,19,32])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PANEL),
                           ('LEFTPADDING',(0,0),(-1,-1),15),('RIGHTPADDING',(0,0),(-1,-1),15),
                           ('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    story.append(t)
    story.append(Spacer(1,26))
    story.append(Paragraph('PURCHASED ITEMS',ss['ZTitle']))
    story.append(Spacer(1,10))
    rows=[[
        Paragraph('ITEM / SKU',ss['ZCellHead']),Paragraph('QTY',ss['ZCellHeadRight']),
        Paragraph('UNIT PRICE',ss['ZCellHeadRight']),Paragraph('AMOUNT',ss['ZCellHeadRight'])
    ]]
    for item in items:
        try:
            qty=int(item.get('qty') or 0)
            price=Decimal(str(item.get('unit_price_inr') or 0))
        except (ValueError,InvalidOperation,TypeError) as exc:
            raise ValueError('Invalid line item in verified order') from exc
        if qty<=0 or not price.is_finite() or price<0:
            raise ValueError('Invalid quantity or unit price')
        title=escape(str(item.get('title') or 'Item'))
        sku=escape(str(item.get('sku') or '-'))
        cell=Paragraph(f'{title}<br/><font color="#92A7D9" size="8">{sku}</font>',ss['ZCell'])
        rows.append([cell,Paragraph(str(qty),ss['ZCellRight']),
                     Paragraph(money(price),ss['ZCellRight']),
                     Paragraph(money(price*qty),ss['ZCellRight'])])
    tab=Table(rows,colWidths=[236,46,108,113],hAlign='LEFT',repeatRows=1)
    tab.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),PURPLE),
        ('BACKGROUND',(0,1),(-1,-1),PANEL),
        ('LINEBELOW',(0,1),(-1,-2),0.5,colors.HexColor('#293153')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),13),('BOTTOMPADDING',(0,0),(-1,-1),13),
        ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
    ]))
    story.append(tab)
    story.append(Spacer(1,22))
    summary=[('Subtotal',verified_order.get('subtotal_inr'))]
    coupon=Decimal(str(verified_order.get('coupon_discount_inr') or '0'))
    if coupon:
        summary.append(('Coupon discount',-coupon))
    delivery=Decimal(str(verified_order.get('delivery_fee_inr') or '0'))
    if delivery:
        summary.append(('Delivery fee',delivery))
    cod=Decimal(str(verified_order.get('cod_fee_inr') or '0'))
    if cod:
        summary.append(('COD fee',cod))
    summary.append(('TOTAL',verified_order.get('total_inr')))
    summ=[]
    for label,value in summary:
        bold=label=='TOTAL'
        typ='ZTitle' if bold else 'ZCell'
        numtyp='ZCellRight'
        summ.append([Paragraph(escape(label),ss[typ]),Paragraph(money(value),ss[numtyp])])
    tt=Table(summ,colWidths=[346,157],hAlign='RIGHT')
    tt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PANEL),
                            ('BACKGROUND',(0,len(summ)-1),(-1,len(summ)-1),PURPLE),
                            ('TOPPADDING',(0,0),(-1,-1),11),('BOTTOMPADDING',(0,0),(-1,-1),11),
                            ('LEFTPADDING',(0,0),(-1,-1),16),('RIGHTPADDING',(0,0),(-1,-1),16)]))
    story.append(tt)
    story.append(Spacer(1,26))
    story.append(Paragraph('This document is a synthetic order receipt generated from the ZentroMart capstone dataset. '
                           'It is NOT an official GST tax invoice, tax certificate, or proof of payment.',ss['ZWarn']))

    def page(canvas, pdfdoc):
        canvas.saveState()
        width,height=pdfdoc.pagesize
        canvas.setFillColor(BG)
        canvas.rect(0,0,width,height,fill=1,stroke=0)
        canvas.setFillColor(PURPLE)
        canvas.rect(0,height-9,width,9,fill=1,stroke=0)
        canvas.setStrokeColor(colors.HexColor('#242A4B'))
        canvas.line(46,43,width-46,43)
        canvas.setFont('Helvetica',8)
        canvas.setFillColor(PALE)
        canvas.drawString(46,29,'ZENTROMART  /  VOICEOPS  /  EDUCATIONAL DEMO')
        canvas.drawRightString(width-46,29,f'PAGE {pdfdoc.page}')
        canvas.restoreState()

    doc.build(story,onFirstPage=page,onLaterPages=page)
    return buf.getvalue()
