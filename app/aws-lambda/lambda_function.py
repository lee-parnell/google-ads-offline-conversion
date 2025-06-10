import json
import os
import logging
import boto3

from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key, Attr
import services
from config import kommo_config


# .env constants
TABLE_PREFIX = os.getenv("TABLE_PREFIX", "default")
CLICK_LOG_TTL_MINUTES = int(os.getenv("CLICK_LOG_TTL_MINUTES", "15"))

logger = logging.getLogger()
logger.setLevel("INFO")


dynamodb = boto3.resource("dynamodb")
click_log_table = dynamodb.Table(f"{TABLE_PREFIX}_click_logs")


# services
kommo_service = services.KommoService(config=kommo_config)


def lambda_handler(event, context):
    logger.info("Incoming event: %s", json.dumps(event))

    path = event.get("rawPath", "/")
    method = event.get("requestContext")["http"]["method"]

    if path == "/outbound-click-logs" and method == "POST":
        return click_log_handler(event)

    if path == "/update-lead" and method == "POST":
        return update_lead_handler()

    return {"statusCode": 404, "message": "Invalid path"}

def click_log_handler(event):
    body = json.loads(event["body"] or {})
    gclid = body.get("gclid", None)

    if not gclid:
        logger.error("Event object does not have gclid field.")
        return {
            "statucCode": 400,
            "message": "Missing required parameter gclid",
        }

    return persist_clicklog_to_db(body)

def update_lead_handler():
    response = click_log_table.query(
        KeyConditionExpression=Key("pk").eq("click"),
        FilterExpression=Attr("matched").eq(False),
        ScanIndexForward=False,
        Limit=1,
    )

    return update_lead(items=response.get("Items", []))

def persist_clicklog_to_db(event):
    created_at = datetime.now()
    expires_at = created_at + timedelta(minutes=CLICK_LOG_TTL_MINUTES)

    try:
        click_log_table.put_item(
            Item={
                "pk": "click",
                "page_path": event.get("page_path"),
                "gclid": event.get("gclid"),
                "created_at": int(created_at.timestamp()),
                "expires_at": int(expires_at.timestamp()),
                "matched": False,
            }
        )

        logger.info(
            "Successfully persisted click log into table. gclid:%s",
            event.get("gclid"),
        )

        return {
            "statusCode": 200,
            "message": "Click log persisted successfully.",
        }
    except RuntimeError as e:
        logger.error(
            "Something went wrong while persisting the click log. \
            Exception: %s",
            e,
        )

        return {
            "statusCode": 500,
            "message": "Something went wrong while persisting the click log.",
        }


def update_lead(items):
    lead_id = kommo_service.get_latest_incoming_lead_id()
    if not items:
        try:
            kommo_service.update_lead(
                lead_id=lead_id,
                source="organic",
            )

            logger.info("Lead updated with organic source.")

            return {
                "statusCode": 200,
                "message": "Lead updated with organic source.",
            }
        except RuntimeError as e:
            logger.error(
                "Lead with organic source could not be updated. \
                         Exception: %s",
                e,
            )

            return {
                "statusCode": 500,
                "message": "Lead with organic source could not be updated.",
            }

    if datetime.now().timestamp() <= items[0]["expires_at"]:
        expires_at = items[0]["expires_at"]
        gclid = items[0]["gclid"]
        page_path = items[0]["page_path"]

        try:
            click_log_table.update_item(
                Key={"pk": "click", "expires_at": expires_at},
                UpdateExpression="SET matched = :matched",
                ExpressionAttributeValues={":matched": True},
            )

            kommo_service.update_lead(
                lead_id=lead_id,
                source="cpc",
                gclid=gclid,
                page_path=page_path
            )

            logger.info("Lead updated with cpc source.")

            return {
                "statusCode": 200,
                "message": "Lead updated with matched gclid.",
            }
        except RuntimeError as e:
            logger.error(
                "Lead with cpc source could not be updated. \
                         Exception: %s",
                e,
            )

            return {
                "statusCode": 500,
                "message": "Lead with cpc source could not be updated.",
            }
