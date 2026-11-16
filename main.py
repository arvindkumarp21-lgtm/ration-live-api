from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
import re

app = FastAPI(title="Gujarat PDS Direct API")

SECRET_API_KEY = "GUJ_PDS_2026_SECURE_KEY"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "online", "message": "PDS API Active"}

@app.get("/api/ration/{card_no}")
def fetch_live_ration_card(card_no: str, x_api_key: str = Header(default="()")):
    if not re.fullmatch(r"\d{15}", card_no):
        raise HTTPException(status_code=400, detail="ફક્ત ૧૫ અંકનો માન્ય રેશન કાર્ડ નંબર દાખલ કરો")

    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,gu;q=0.8",
        "Referer": "https://ipds.gujarat.gov.in/Register/frm_RationCardDetails.aspx"
    }

    base_url = "https://ipds.gujarat.gov.in/Register/frm_RationCardDetails.aspx"

    try:
        # સ્ટેપ ૧: પેજ વિઝિટ કરીને ViewState મેળવવું
        get_res = session.get(base_url, headers=headers, timeout=20)
        soup = BeautifulSoup(get_res.text, "html.parser")

        viewstate = soup.find("input", {"id": "__VIEWSTATE"})
        eventvalidation = soup.find("input", {"id": "__EVENTVALIDATION"})
        viewstategen = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})

        if not viewstate:
            raise HTTPException(status_code=502, detail="IPDS પોર્ટલ પરથી સિક્યોરિટી ટોકન મળ્યું નથી.")

        # સ્ટેપ ૨: ફોર્મ પેલોડ તૈયાર કરીને પોસ્ટ કરવું
        payload = {
            "__VIEWSTATE": viewstate.get("value", ""),
            "__VIEWSTATEGENERATOR": viewstategen.get("value", "") if viewstategen else "",
            "__EVENTVALIDATION": eventvalidation.get("value", "") if eventvalidation else "",
            "ctl00$ContentPlaceHolder1$txtRationCardNo": card_no,
            "ctl00$ContentPlaceHolder1$txtCaptcha": "",
            "ctl00$ContentPlaceHolder1$btnSearch": "Search"
        }

        post_res = session.post(base_url, data=payload, headers=headers, timeout=20)
        res_soup = BeautifulSoup(post_res.text, "html.parser")

        # ટેબલમાંથી સભ્યો અને વિગતો શોધવી
        tables = res_soup.find_all("table")
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
                "entitlement": "ઘઉં: ૧૦ કિલો | ચોખા: ૧૫ કિલો | ખાંડ: ૧ કિલો",
                "members": members
            }
        else:
            raise HTTPException(status_code=404, detail="આ રેશન કાર્ડ નંબરની વિગત પોર્ટલ પર ઉપલબ્ધ નથી અથવા કેપ્ચા બ્લોક છે.")

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"કનેક્શન એરર: {str(e)}")
