import time
import json
import os
import logging
import boto3
import base64

from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key, Attr
from services.google_ads_service import GoogleAdsService
from urllib.parse import parse_qsl, unquote

import services
import config

# .env constants
TABLE_PREFIX = os.getenv("TABLE_PREFIX", "default")
CLICK_LOG_TTL_MINUTES = int(os.getenv("CLICK_LOG_TTL_MINUTES", "15"))

# aws resources
dynamodb = boto3.resource("dynamodb")
click_log_table = dynamodb.Table(f"{TABLE_PREFIX}_click_logs")  # type: ignore

# configs
kommo_config, google_ads_config = config.load_config()

# services
kommo_service = services.KommoService(config=kommo_config)
google_ads_service = services.GoogleAdsService(config=google_ads_config)

# logger
logger = logging.getLogger()
logger.setLevel("INFO")


def lambda_handler(event, context):
    logger.info("Incoming event: %s", json.dumps(event))

    path = event.get("rawPath", "/")
    method = event.get("requestContext")["http"]["method"]

    if path == "/run-salesbots" and method == "POST":
        return run_salesbots_handler()

    if path == "/outbound-click-logs" and method == "POST":
        return click_log_handler(event)

    if path == "/update-lead" and method == "POST":
        query_string_params = event.get("queryStringParameters", {})
        multi_query_string_params = (
            event.get("multiValueQueryStringParameters", {}) or {}
        )

        conversion_type_key = query_string_params.get("conversion_type")
        conversion_type = GoogleAdsService.ConversionType[
            conversion_type_key.upper()
        ]

        is_conversion_adjustment = (
            query_string_params.get("is_adjustment") == "True"
        )
        is_manual_import = query_string_params.get("is_manual") == "True"

        custom_fields = multi_query_string_params.get("custom_fields", [])

        if is_conversion_adjustment:
            return upload_conversion_adjustment_handler(
                event=event,
                conversion_type=conversion_type,
            )

        if (
            custom_fields
            or conversion_type
            == GoogleAdsService.ConversionType.MESSAGE_RECEIVED
        ):
            if is_manual_import:
                return upload_conversion_handler(
                    event=event,
                    conversion_type=conversion_type,
                    lead_id=extract_incoming_lead_id(event),
                )

            custom_fields = {key: True for key in custom_fields}
            return update_lead_handler(
                conversion_type=conversion_type,
                event=event,
                custom_fields=custom_fields,
            )

        return upload_conversion_handler(
            event=event, conversion_type=conversion_type
        )

    return {"statusCode": 404, "message": "Invalid path"}


def click_log_handler(event):
    body = json.loads(event["body"] or {})
    gclid, gbraid = body.get("gclid"), body.get("gbraid")

    if not (gclid or gbraid):
        logger.error("Event object does not have gclid or gbraid field.")
        return {
            "statusCode": 400,
            "message": "Missing required parameter gclid and gbraid",
        }

    return persist_clicklog_to_db(body)


def update_lead_handler(conversion_type, event, custom_fields):
    response = (
        click_log_table.query(
            KeyConditionExpression=Key("pk").eq("click"),
            FilterExpression=Attr("matched").eq(False),
            ScanIndexForward=False,
            Limit=1,
        )
        if conversion_type is not GoogleAdsService.ConversionType.DISABLED
        else None
    )

    custom_fields = {key: True for key in custom_fields}

    return update_lead(
        items=response.get("Items", []) if response else None,
        conversion_type=conversion_type,
        lead_id=(
            extract_lead_id_from_task_webhook(event)
            if custom_fields.get("task")
            else extract_incoming_lead_id(event)
        ),
        custom_fields=custom_fields,
    )


def upload_conversion_handler(event, conversion_type, lead_id=None):
    lead_id = (
        extract_incoming_lead_id(event=event) if lead_id is None else lead_id
    )

    try:
        google_ads_service.upload_offline_conversion(
            raw_lead=kommo_service.construct_raw_lead(lead_id=lead_id),
            conversion_type=conversion_type,
        )

        logger.info(
            "Successfully uploaded click conversion. Conversion type: %s",
            conversion_type.conversion_name,
        )

        return {
            "statusCode": 200,
            "message": "Conversion uploaded successfully.",
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


def upload_conversion_adjustment_handler(event, conversion_type):
    try:
        lead_id = extract_incoming_lead_id(event)
        google_ads_service.upload_offline_conversion_adjustment(
            conversion_type=conversion_type, lead_id=lead_id
        )
        logger.info(
            "Successfully uploaded click conversion adjustment. Conversion type: %s",
            conversion_type.conversion_name,
        )

        return {
            "statusCode": 200,
            "message": "Conversion adjustment uploaded successfully.",
        }
    except RuntimeError as e:
        logger.error(
            "Something went wrong while uploading the click conversion adjustment. \
            Exception: %s",
            e,
        )

        return {
            "statusCode": 500,
            "message": "Something went wrong while uploading the click conversion adjustment.",
        }


def run_salesbots_handler():
    now = datetime.now()

    one_day_window = {
        "starts_at": int((now + timedelta(hours=12)).timestamp()),
        "ends_at": int((now + timedelta(hours=36)).timestamp()),
    }

    seven_day_window = {
        "starts_at": int((now + timedelta(hours=156)).timestamp()),
        "ends_at": int((now + timedelta(hours=180)).timestamp()),
    }

    next_day_leads = kommo_service._get_lead_ids_by_pipeline(
        pipeline_id=kommo_config.base_pipeline_id,
        stage_id=kommo_config.appointment_stage_id,
        starts_at=one_day_window["starts_at"],
        ends_at=one_day_window["ends_at"],
    )

    seven_day_leads = kommo_service._get_lead_ids_by_pipeline(
        pipeline_id=kommo_config.base_pipeline_id,
        stage_id=kommo_config.appointment_stage_id,
        starts_at=seven_day_window["starts_at"],
        ends_at=seven_day_window["ends_at"],
    )
    logger.info(
        "Retrieved leads that have due tasks next day: %s", next_day_leads
    )
    logger.info(
        "Retrieved leads that have due tasks next week: %s", seven_day_leads
    )

    kommo_service.run_salesbot_on_leads(
        salesbot_id=kommo_config.salesbot_ids.get("next_day_salesbot_id"),
        lead_ids=next_day_leads,
    )
    kommo_service.run_salesbot_on_leads(
        salesbot_id=kommo_config.salesbot_ids.get("seven_day_salesbot_id"),
        lead_ids=seven_day_leads,
    )


def persist_clicklog_to_db(event):
    created_at = datetime.now()
    expires_at = created_at + timedelta(minutes=CLICK_LOG_TTL_MINUTES)

    try:
        click_log_table.put_item(
            Item={
                "pk": "click",
                "page_path": event.get("page_path"),
                "gclid": event.get("gclid"),
                "gbraid": event.get("gbraid"),
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


def update_lead(items, conversion_type, lead_id, custom_fields):
    if not items:
        try:
            kommo_service.update_lead(
                lead_id=lead_id,
                source=(
                    "organic"
                    if conversion_type
                    is not GoogleAdsService.ConversionType.DISABLED
                    else None
                ),
                **custom_fields,
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
        gclid, gbraid = items[0]["gclid"], items[0].get("gbraid")
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
                gbraid=gbraid,
                page_path=page_path,
                **custom_fields,
            )

            logger.info("Lead updated with cpc source.")

            google_ads_service.upload_offline_conversion(
                raw_lead=kommo_service.construct_raw_lead(lead_id=lead_id),
                conversion_type=conversion_type,
            )

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


def parse_kommo_payload(event):
    body = event.get("body", {})

    decoded_str = base64.b64decode(body).decode("utf-8")
    query_str = unquote(decoded_str)
    return dict(parse_qsl(query_str))


def extract_incoming_lead_id(event):
    payload = parse_kommo_payload(event)

    return payload.get("leads[add][0][id]") or payload.get(
        "leads[status][0][id]"
    )


def extract_lead_id_from_task_webhook(event):
    payload = parse_kommo_payload(event)

    return payload.get("task[add][0][id]") or payload.get("task[update][0][id]")
