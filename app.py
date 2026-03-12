import os
import json
from fastapi import FastAPI, Request
import httpx
import boto3
import os

from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY") 
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")

STRAVA_CLIENT_TOKEN =  os.getenv("STRAVA_CLIENT_TOKEN")


s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

@app.get("/activities-webhook")
async def verify(request: Request):
    challenge = request.query_params.get("hub.challenge")
    return {"hub.challenge": challenge}

@app.post("/activities-webhook")
async def receive_webhook(request: Request):
    payload = await request.json()
    
    activity_id = payload.get("object_id")
    activity_type = payload.get("object_type")
    
    if activity_type != "activity":
        return {"status": "ignored"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers={"Authorization": f"Bearer {STRAVA_CLIENT_TOKEN}"}
        )
        activity_data = response.json()
        
        # ✅ Save locally per activity
        os.makedirs("activities", exist_ok=True)
        local_path = f"activities/{activity_id}.json"
        with open(local_path, "w") as f:
            json.dump(activity_data, f, indent=4)
        
        # ✅ Upload to S3
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=f"activities/{activity_id}.json",
            Body=json.dumps(activity_data),
            ContentType="application/json"
        )
    
    return {"status": "saved"}