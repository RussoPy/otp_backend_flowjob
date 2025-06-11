from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from twilio.rest import Client
import os
from dotenv import load_dotenv
import logging

# Load env
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OTP_BACKEND")

# Validate Twilio env vars on startup
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_SERVICE_SID = os.getenv("TWILIO_SERVICE_SID")

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_SERVICE_SID]):
    logger.warning("⚠️ Missing one or more Twilio environment variables!")
    logger.warning(f"TWILIO_ACCOUNT_SID: {'✅' if TWILIO_ACCOUNT_SID else '❌'}")
    logger.warning(f"TWILIO_AUTH_TOKEN: {'✅' if TWILIO_AUTH_TOKEN else '❌'}")
    logger.warning(f"TWILIO_SERVICE_SID: {'✅' if TWILIO_SERVICE_SID else '❌'}")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

app = FastAPI()

# Request models
class SendOTPRequest(BaseModel):
    phone_number: str
    user_id: str

class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp_code: str
    user_id: str

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ Uncaught Exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "שגיאה פנימית בשרת. נסה שוב או פנה לתמיכה."}
    )

@app.post("/api/twilio/send-otp/")
async def send_otp(data: SendOTPRequest, request: Request):
    logger.info(f"📲 Send OTP requested by user {data.user_id}")
    logger.debug(f"Headers: {request.headers}")
    logger.debug(f"Body: {data.dict()}")

    if not data.phone_number.startswith("+972"):
        logger.warning("📛 Bad phone number format")
        raise HTTPException(status_code=400, detail="פורמט מספר טלפון לא תקין. חייב להתחיל ב־+972")

    if not data.user_id:
        logger.warning("📛 Missing user_id")
        raise HTTPException(status_code=400, detail="חסר מזהה משתמש (user_id).")

    try:
        verification = client.verify.v2.services(TWILIO_SERVICE_SID).verifications.create(
            to=data.phone_number,
            channel="sms"
        )
        logger.info(f"✅ OTP sent to {data.phone_number} | SID: {verification.sid}")
        return {"success": True, "sid": verification.sid}
    except Exception as e:
        logger.error(f"❌ Twilio send error: {str(e)}")
        raise HTTPException(status_code=500, detail="שליחת הקוד נכשלה. ודא שהמספר תקין ונסה שוב.")

@app.post("/api/twilio/verify-otp/")
async def verify_otp(data: VerifyOTPRequest, request: Request):
    logger.info(f"🔐 Verify OTP for user {data.user_id}")
    logger.debug(f"Headers: {request.headers}")
    logger.debug(f"Body: {data.dict()}")

    if not data.phone_number.startswith("+972"):
        logger.warning("📛 Bad phone number format on verify")
        raise HTTPException(status_code=400, detail="פורמט מספר טלפון לא תקין.")

    if not data.otp_code.isdigit() or len(data.otp_code) != 6:
        logger.warning("📛 Invalid OTP format")
        raise HTTPException(status_code=400, detail="קוד האימות חייב להכיל 6 ספרות.")

    try:
        check = client.verify.v2.services(TWILIO_SERVICE_SID).verification_checks.create(
            to=data.phone_number,
            code=data.otp_code
        )
        if check.status == "approved":
            logger.info(f"✅ OTP verified for {data.phone_number}")
            return {"success": True}
        else:
            logger.warning(f"❌ Wrong or expired OTP for {data.phone_number}")
            raise HTTPException(status_code=400, detail="הקוד שגוי או שפג תוקף.")
    except Exception as e:
        logger.error(f"❌ Twilio verify error: {str(e)}")
        raise HTTPException(status_code=500, detail="אימות הקוד נכשל. נסה שוב.")

@app.get("/")
async def root():
    return {"message": "✅ OTP Backend is live. Use /api/twilio/send-otp/ and /verify-otp/"}
