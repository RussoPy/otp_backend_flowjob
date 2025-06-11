from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

# Twilio config
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_SERVICE_SID = os.getenv("TWILIO_SERVICE_SID")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

app = FastAPI()

class SendOTPRequest(BaseModel):
    phone_number: str
    user_id: str

class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp_code: str
    user_id: str

@app.post("/api/twilio/send-otp/")
async def send_otp(data: SendOTPRequest):
    try:
        verification = client.verify.v2.services(TWILIO_SERVICE_SID).verifications.create(
            to=data.phone_number,
            channel="sms"
        )
        return {"success": True, "sid": verification.sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/twilio/verify-otp/")
async def verify_otp(data: VerifyOTPRequest):
    try:
        verification_check = client.verify.v2.services(TWILIO_SERVICE_SID).verification_checks.create(
            to=data.phone_number,
            code=data.otp_code
        )
        if verification_check.status == "approved":
            return {"success": True}
        else:
            raise HTTPException(status_code=400, detail="OTP לא נכון או שפג תוקף.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
