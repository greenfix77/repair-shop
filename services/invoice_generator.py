import jdatetime
from pathlib import Path

from services.invoice_calculator import calculate_invoice_totals
from ui.status_styles import get_status_color
from core.status import STATUS_PENDING


def generate_print_invoice_html(repair_data: dict, shop_settings: dict) -> str:
    data = repair_data
    settings = shop_settings

    # محاسبات مالی
    fin = calculate_invoice_totals(data)
    parts_cost = fin['parts_cost']
    labor_cost = fin['labor_cost']
    tax_rate = fin['tax_rate']
    discount = fin['discount']
    subtotal = fin['subtotal']
    tax_amount = fin['tax_amount']
    total = fin['total']

    html = f"""
    <!DOCTYPE html>
    <html dir="rtl">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 15mm; }}

            body {{
                font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
                font-size: 11pt;
                color: #000;
                line-height: 1.6;
                direction: rtl;
            }}

            .header {{
                text-align: center;
                border-bottom: 2px solid #000;
                padding-bottom: 10px;margin-bottom: 15px;
            }}
            .header h1 {{ margin: 5px 0; font-size: 18pt; font-weight: bold; }}
            .header p {{ margin: 3px 0; font-size: 9pt; }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 10px auto;
            }}

            th {{
                background-color: #d0d0d0;
                border: 1px solid #000;
                padding: 8px 10px;
                text-align: center;
                font-weight: bold;
                font-size: 10pt;
            }}

            td {{
                border: 1px solid #000;
                padding: 7px 10px;
                text-align: center;
                font-size: 10pt;
            }}

            .td-center {{ text-align: center !important; }}

            .info-table td {{ padding: 6px 10px; }}
            .info-label {{ font-weight: bold; background-color: #f0f0f0; width: 20%; }}

            .financial-summary {{
                width: 45%;
                margin: 10px auto;
                border: 1px solid #000;}}
            .financial-summary td {{ padding: 6px 10px; }}
            .financial-summary .amount {{ text-align: center; font-weight: bold; }}

            .total-row {{
                font-weight: bold;
                background-color: #d0d0d0;
                font-size: 11pt;
            }}

            .notes {{
                margin-top: 12px;
                padding: 10px;
                border: 1px solid #000;
                min-height: 50px;
                text-align: center;
            }}
            .notes-title {{ font-weight: bold; margin-bottom: 5px; }}

            .signature {{
                margin-top: 30px;
                display: table;
                width: 100%;
            }}
            .signature-cell {{
                display: table-cell;
                width: 50%;
                text-align: center;
            }}
            .signature-line {{
                border-top: 1px solid #000;
                width: 180px;
                margin: 40px auto 5px auto;
            }}

            .footer {{
                margin-top: 20px;
                padding-top: 10px;
                border-top: 1px solid #000;
                text-align: center;
                font-size: 9pt;color: #333;
            }}

            .invoice-wrapper {{
                max-width: 180mm;
                margin: 0 auto;
                text-align: right;
            }}</style>
    </head>
    <body>
        <div class="invoice-wrapper">

        <!-- سربرگ (وسط‌چین) -->
        <div class="header">
            <h1>{settings['shop_name']}</h1>
            <p>{settings['address']}</p>
            <p>تلفن: {settings['phone']} | موبایل: {settings['mobile']}</p>
            <p>ایمیل: {settings['email']} | وبسایت: {settings['website']}</p>
        </div>

        <!-- اطلاعات فاکتور -->
        <table class="info-table">
            <tr>
                <td class="info-label">شماره فاکتور:</td>
                <td class="td-center">{data.get('id', 'N/A')}</td><td class="info-label">تاریخ:</td>
                <td class="td-center">{data.get('receive_date', 'N/A')}</td>
            </tr>
            <tr>
                <td class="info-label">نام مشتری:</td>
                <td>{data.get('customer_name', 'N/A')}</td>
                <td class="info-label">تلفن:</td>
                <td class="td-center">{data.get('phone', 'N/A')}</td>
            </tr>
        </table>

        <!-- جدول اصلی -->
        <table>
            <thead>
                <tr>
                    <th style="width:5%;">ردیف</th>
                    <th style="width:30%;">شرح</th>
                    <th style="width:35%;">مشخصات</th>
                    <th style="width:30%;">مبلغ (تومان)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="td-center">1</td>
                    <td>دستگاه</td>
                    <td>{data.get('brand', '')} - {data.get('model', '')}</td>
                    <td class="td-center">-</td>
                </tr>
                <tr>
                    <td class="td-center">2</td>
                    <td>مشکل گزارش‌شده</td>
                    <td colspan="2">{data.get('issue', 'N/A')}</td>
                </tr>
                <tr>
                    <td class="td-center">3</td>
                    <td>هزینه قطعات</td>
                    <td class="td-center">-</td>
                    <td class="td-center">{parts_cost:,}</td>
                </tr>
                <tr>
                    <td class="td-center">4</td>
                    <td>هزینه تعمیر</td>
                    <td class="td-center">-</td>
                    <td class="td-center">{labor_cost:,}</td>
                </tr>
            </tbody>
        </table>

        <!-- جدول مالی -->
        <table class="financial-summary">
            <tr>
                <td>جمع:</td>
                <td class="amount">{subtotal:,} تومان</td>
            </tr>
            <tr>
                <td>مالیات ({tax_rate}%):</td>
                <td class="amount">{int(tax_amount):,} تومان</td>
            </tr>
            <tr>
                <td>تخفیف:</td>
                <td class="amount">{discount:,} تومان</td>
            </tr>
            <tr class="total-row">
                <td>مبلغ قابل پرداخت:</td>
                <td class="amount">{int(total):,} تومان</td>
            </tr>
        </table>

        <!-- یادداشت و گارانتی -->
        <div class="notes">
            <div class="notes-title">یادداشت‌ها:</div>
            <div>{data.get('notes', '-')}</div>
        </div>

        <div class="notes">
            <div class="notes-title">گارانتی:</div>
            <div>{data.get('warranty', '-')}</div>
        </div>

        <!-- امضا -->
        <div class="signature">
            <div class="signature-cell">
                <div class="signature-line"></div>
                <div>امضای مشتری</div>
            </div>
            <div class="signature-cell">
                <div class="signature-line"></div>
                <div>امضای فروشنده</div>
            </div>
        </div>

        <!-- فوتر -->
        <div class="footer">
            <p>این فاکتور توسط سیستم مدیریت تعمیرات صادر شده است.</p>
            <p>تاریخ چاپ: {jdatetime.date.today().strftime('%Y/%m/%d')}</p>
        </div>

        </div>
    </body>
    </html>
    """
    return html


def generate_web_invoice_html(repair_data: dict, shop_settings: dict) -> str:
    data = repair_data
    settings = shop_settings

    # محاسبات مالی
    fin = calculate_invoice_totals(data)
    parts_cost = fin['parts_cost']
    labor_cost = fin['labor_cost']
    tax_rate = fin['tax_rate']
    discount = fin['discount']
    subtotal = fin['subtotal']
    tax_amount = fin['tax_amount']
    total = fin['total']

    # تعیین رنگ وضعیت
    status = data.get('status', STATUS_PENDING)
    status_color = get_status_color(status)

    # لوگو
    logo_html = ""
    if settings.get('logo') and Path(settings['logo']).exists():
        logo_html = f'<img src="file:///{settings["logo"]}" style="max-width: 120px; max-height: 80px;">'
    html = f"""
        <!DOCTYPE html>
        <html dir="rtl">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 20px;
                    margin: 0;
                    direction: rtl;
                    text-align: center;
                }}
                
                .invoice-container {{
                    width: 100%;
                    max-width: 210mm;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    overflow: hidden;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    direction: rtl;
                }}
                
                .header h1 {{
                    margin: 10px 0;
                    font-size: 28pt;
                    font-weight: bold;
                }}
                
                .header p {{
                    margin: 5px 0;
                    opacity: 0.9;
                }}
                
                .logo {{
                    margin-bottom: 15px;
                }}
                
                .content {{
                    padding: 30px;
                }}
                
                .invoice-meta {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 30px;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 10px;
                    direction: rtl;
                    text-align: center;
                }}
                
                .meta-section {{
                    flex: 1;
                }}
                
                .meta-section h3 {{
                    co                    color: #667eea;
                    margin-bottom: 10px;
                    font-size: 14pt;
                }}
                
                .meta-item {{
                    margin: 8px 0;
                    color: #555;
                }}
                
                .meta-label {{
                    font-weight: bold;
                    color: #333;
                }}
                
                .status-badge {{
                    display: inline-block;
                    background: {status_color};
                    color: white;
                    padding: 8px 20px;
                    border-radius: 25px;
                    font-weight: bold;
                    margin-top: 10px;
                }}
                
                .repair-details {{
                    margin-bottom: 30px;
                    direction: rtl;
                    text-align: center;
                }}
                
                .section-title {{
                    font-size: 16pt;
                    color: #333;
                    margin-bottom: 15px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #667eea;
                }}
                
                .details-card {{
                    background: #f8f9fa;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 15px;
                }}
                
                .details-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                }}
                
                .detail-item {{
                    padding: 10px;
                    background: white;
                    border-radius: 8px;
                    border-right: 4px solid #667eea;
                }}
                
                .detail-label {{
                    font-size: 9pt;
                    color: #666;
                    margin-bottom: 5px;
                }}
                
                .detail-value {{
                    font-size: 11pt;
                    color: #333;
                    font-weight: 600;
                }}
                
                .financial-card {{
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    border-radius: 15px;
                    padding: 25px;
                    margin-bottom: 20px;
                    direction: rtl;
                    text-align: center;
                }}
                
                .financial-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 10px 0;
                    border-bottom: 1px solid rgba(0,0,0,0.1);
                }}
                
                .financial-row.total {{
                    border-bottom: none;
                    margin-top: 15px;
                    padding-top: 15px;
                    border-top: 2px solid #667eea;
                    font-size: 16pt;
                    font-weight: bold;
                    color: #667eea;
                }}
                
                .notes-section {{
                    background: #fff8e1;
                    border-right: 4px solid #ffc107;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                    direction: rtl;
                    text-align: center;
                }}
                
                .warranty-section {{
                    background: #e8f5e9;
                    border-right: 4px solid #4caf50;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                    direction: rtl;
                    text-align: center;
                }}
                
                .footer {{
                    background: #f8f9fa;
                    padding: 20px 30px;
                    text-align: center;
                    color: #666;
                    border-top: 1px solid #eee;
                    direction: rtl;
                }}
            </style>
        </head>
        <body>
            <div class="invoice-container">
                <div class="header">
                    <div class="logo">{logo_html}</div>
                    <h1>{settings['shop_name']}</h1>
                    <p>{settings['address']}</p>
                    <p>📞 {settings['phone']} | 📱 {settings['mobile']}</p>
                    <p>✉️ {settings['email']} | 🌐 {settings['website']}</p>
                </div>
                
                <div class="content">
                    <div class="invoice-meta">
                        <div class="meta-section">
                            <h3>اطلاعات فاکتور</h3>
                            <div class="meta-item"><span class="meta-label">شماره:</span> {data.get('id', 'N/A')}</div>
                            <div class="meta-item"><span class="meta-label">تاریخ پذیرش:</span> {data.get('receive_date', 'N/A')}</div>
                            <div class="status-badge">{status}</div>
                        </div>
                        
                        <div class="meta-section">
                            <h3>اطلاعات مشتری</h3>
                            <div class="meta-item"><span class="meta-label">نام:</span> {data.get('customer_name', 'N/A')}</div>
                            <div class="meta-item"><span class="meta-label">تلفن:</span> {data.get('phone', 'N/A')}</div>
                            <div class="meta-item"><span class="meta-label">تاریخ تحویل:</span> {data.get('delivery_date', 'N/A')}</div>
                        </div>
                    </div>
                    
                    <div class="repair-details">
                        <h2 class="section-title">جزئیات تعمیر</h2>
                        <div class="details-card">
                            <div class="details-grid">
                                <div class="detail-item">
                                    <div class="detail-label">برند دستگاه</div>
                                    <div class="detail-value">{data.get('brand', '-')}</div>
                                </div>
                                <div class="detail-item">
                                    <div class="detail-label">مدل دستگاه</div>
                                    <div class="detail-value">{data.get('model', '-')}</div>
                                </div>
                                <div class="detail-item">
                                    <div class="detail-label">ایراد گزارش شده</div>
                                    <div class="detail-value">{data.get('issue', '-')}</div>
                                </div>
                                <div class="detail-item">
                                    <div class="detail-label">وضعیت فعلی</div>
                                    <div class="detail-value">{status}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="financial-card">
                        <h2 class="section-title">خلاصه مالی</h2>
                        <div class="financial-row">
                            <span>هزینه قطعات</span>
                            <span>{parts_cost:,} تومان</span>
                        </div>
                        <div class="financial-row">
                            <span>هزینه تعمیر</span>
                            <span>{labor_cost:,} تومان</span>
                        </div>
                        <div class="financial-row">
                            <span>جمع کل</span>
                            <span>{subtotal:,} تومان</span>
                        </div>
                        <div class="financial-row">
                            <span>مالیات ({tax_rate}%)</span>
                            <span>{int(tax_amount):,} تومان</span>
                        </div>
                        <div class="financial-row">
                            <span>تخفیف</span>
                            <span>{discount:,} تومان</span>
                        </div>
                        <div class="financial-row total">
                            <span>مبلغ نهایی</span>
                            <span>{int(total):,} تومان</span>
                        </div>
                    </div>
                    
                    <div class="notes-section">
                        <h3 style="margin-top: 0;">یادداشت‌ها</h3>
                        <p>{data.get('notes', 'یادداشتی ثبت نشده است.')}</p>
                    </div>
                    
                    <div class="warranty-section">
                        <h3 style="margin-top: 0;">شرایط گارانتی</h3>
                        <p>{data.get('warranty', 'بدون گارانتی')}</p>
                    </div>
                </div>
                
                <div class="footer">
                    <p>از اعتماد شما سپاسگزاریم</p>
                    <p>تاریخ صدور: {jdatetime.date.today().strftime('%Y/%m/%d')}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    return html
