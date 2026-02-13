import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config.universe import get_nifty500_tickers
from src.data_loader import FundamentalLoader
from src.valuation import ValuationEngine
from src.technical import TechnicalEngine
from src.portfolio import PortfolioManager
from src.history import HistoryEngine

# --- CONFIG ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get("GMAIL_USER")
SENDER_PASSWORD = os.environ.get("GMAIL_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

def generate_report():
    print("⏳ Starting Weekly Scan...")
    tickers = get_nifty500_tickers()
    loader = FundamentalLoader(tickers)
    df_raw = loader.get_key_stats()
    
    if df_raw.empty:
        return "Error: Could not fetch market data."

    # Run Engines
    tech_engine = TechnicalEngine()
    df_tech = tech_engine.add_technical_indicators(df_raw)
    
    val_engine = ValuationEngine(df_raw)
    val_engine.clean_data()
    df_scored = val_engine.get_blended_score(df_tech)
    
    # Get Top Picks (Budget doesn't matter here, just ranking)
    pm = PortfolioManager(100000)
    candidates = pm.select_and_allocate(df_scored, top_n=10)
    
    hist = HistoryEngine()
    stable = hist.filter_stocks(candidates)
    
    # Format HTML Body
    html_content = f"""
    <h2>🇮🇳 Intelligent Investor: Weekly Briefing</h2>
    <p>Date: {datetime.now().strftime('%d %b %Y')}</p>
    <hr>
    <h3>🏆 Top AI Picks for this Week</h3>
    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f2f2f2;">
            <th>Ticker</th>
            <th>Sector</th>
            <th>Price</th>
            <th>Score</th>
        </tr>
    """
    
    for _, row in stable.iterrows():
        html_content += f"""
        <tr>
            <td><b>{row['ticker']}</b></td>
            <td>{row['sector']}</td>
            <td>₹{row['price']:,.2f}</td>
            <td>{int(row['total_score'])}/100</td>
        </tr>
        """
    
    html_content += "</table><br><p><i>Sent automatically by GitHub Actions.</i></p>"
    return html_content

def send_email():
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("❌ Error: Email credentials not found in Environment Variables.")
        return

    report_html = generate_report()
    
    msg = MIMEMultipart()
    msg['From'] = "Intelligent Investor Bot"
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"📈 Weekly Market Report - {datetime.now().strftime('%d %b')}"
    msg.attach(MIMEText(report_html, 'html'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

if __name__ == "__main__":
    send_email()