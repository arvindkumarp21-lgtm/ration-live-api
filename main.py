from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from playwright.sync_api import sync_playwright
import re

app = FastAPI(title="Gujarat PDS Playwright Live Scraping API")

SECRET_API_KEY = "GUJ_PDS_2026_SECURE_KEY"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "online", "message": "Playwright PDS Live Server Active"}

@app.get("/api/ration/{card_no}")
def fetch_live_ration_card(card_no: str, x_api_key: str = Header(default="")):
    if not re.fullmatch(r"\d{15}", card_no):
        raise HTTPException(status_code=400, detail="ફક્ત ૧૫ અંકનો માન્ય રેશન કાર્ડ નંબર દાખલ કરો")

    try:
        with sync_playwright() as p:
            # હેડલેસ મોડમાં બ્રાઉઝર ચાલુ કરવું (Render અથવા લોકલ પીસી બંને પર ચાલશે)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # IPDS ગુજરાતનું રેશન કાર્ડ વિગત વાળું પેજ ખોલવું
            page.goto("https://ipds.gujarat.gov.in/Register/frm_RationCardDetails.aspx", timeout=30000)
            
            # રેશન કાર્ડ નંબરના બોક્સમાં નંબર નાખવો
            page.fill("input#ctl00_ContentPlaceHolder1_txtRationCardNo", card_no)
            
            # સર્ચ બટન પર ક્લિક કરવું
            page.click("input#ctl00_ContentPlaceHolder1_btnSearch")
            
            # પરિણામ લોડ થવા માટે થોડી રાહ જોવી
            try:
                page.wait_for_selector("table", timeout=10000)
            except:
                browser.close()
                raise HTTPException(status_code=404, detail="આ રેશન કાર્ડ નંબરની વિગત IPDS પોર્ટલ પર મળી નથી.")

            # પેજ પરથી HTML ડેટા મેળવવો
            html_content = page.content()
            browser.close()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            
            tables = soup.find_all("table")
            members = []
            head_name = ""
            category = "NFSA - PHH (અગ્રતા ધરાવતા કુટુંબો)"
            address = "ગુજરાત"
            fps_name = "સસ્તા અનાજની દુકાન"

            for tbl in tables:
                rows = tbl.find_all("tr")
                for r in rows[1:]:
                    cols = [c.get_text(strip=True) for c in r.find_all(["td", "th"])]
                    if len(cols) >= 3 and any(cols):
                        m_name = cols[1] if len(cols) > 1 else cols[0]
                        m_rel = cols[2] if len(cols) > 2 else "સભ્ય"
                        m_ekyc = "Done"
                        if not head_name:
                            head_name = m_name
                        members.append({"name": m_name, "relation": m_rel, "ekyc": m_ekyc})

            if members:
                return {
                    "status": "success",
                    "card_number": card_no,
                    "head_name": head_name,
                    "category": category,
                    "address": address,
                    "fps_name": fps_name,
                    "entitlement": "IPDS લાઈવ પોર્ટલ ડેટા",
                    "members": members
                }
            else:
                raise HTTPException(status_code=404, detail="આ રેશન કાર્ડ નંબર પર કોઈ સભ્યની માહિતી ઉપલબ્ધ નથી.")

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"લાઈવ સ્કેપિંગ એરર: {str(e)}")
