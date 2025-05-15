import json
import boto3
import requests
import os
from datetime import datetime
from dateutil.parser import parse

def get_secret(secret_name):
    client = boto3.client("secretsmanager", region_name="eu-central-1")
    response = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response["SecretString"])
    return secret["AVIATIONSTACK_API_KEY"]

API_KEY = get_secret("nouvelair/api-key")
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def lambda_handler(event, context):
    try:
        # Step 1: Fetch flight data from Aviationstack
        url = f"http://api.aviationstack.com/v1/flights"
        params = {
            "access_key": API_KEY,
            "airline_iata": "BJ",
            "limit": 100
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        flights = response.json().get("data", [])

        # Step 2: Save to S3
        s3 = boto3.client('s3')
        today = datetime.utcnow().strftime('%Y-%m-%d')
        s3_key = f"raw/nouvelair_flights_{today}.json"
        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=json.dumps(flights))

        # Step 3: Analyze delays and  Delay categories
        on_time = 0
        short_delay = 0
        medium_delay = 0
        long_delay = 0
        total = 0

        for flight in flights:
            sched = flight.get("departure", {}).get("scheduled")
            actual = flight.get("departure", {}).get("actual")

            if sched and actual:
                total += 1
                try:
                    sched_time = parse(sched)
                    actual_time = parse(actual)
                    delay_minutes = (actual_time - sched_time).total_seconds() / 60

                    if delay_minutes <= 0:
                        on_time += 1
                    elif 0 < delay_minutes <= 15:
                        short_delay += 1
                    elif 15 < delay_minutes <= 60:
                        medium_delay += 1
                    else:
                        long_delay += 1
                except Exception as parse_err:
                    print("Parsing error:", parse_err)

        # Step 4: Send summary to Discord
        summary = (
            f"📊 **Nouvelair Daily Summary ({today})**\n"
            f"✈️ Total Flights: {total}\n"
            f"✅ On-Time: {on_time}\n"
            f"🕒 Short Delays (1–15 min): {short_delay}\n"
            f"⏳ Medium Delays (16–60 min): {medium_delay}\n"
            f"🚨 Long Delays (>60 min): {long_delay}\n"
        )


        requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": summary}
        )

        return {
            'statusCode': 200,
            'body': f"Uploaded {s3_key} to {BUCKET_NAME} and sent Discord message."
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': f"Error: {str(e)}"
        }
