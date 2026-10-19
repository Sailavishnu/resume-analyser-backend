"""Persisted direct messaging for student and HR accounts."""
from datetime import datetime, timezone
import re

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo.database import Database

from app.cloud import collections as C
from app.cloud.mongodb import get_database
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/messages", tags=["Messages"])


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


def _user_card(user):
    name = user.get("full_name") or "User"
    email = user.get("email", "")
    return {"id": str(user["_id"]), "name": name, "username": user.get("username") or email.split("@", 1)[0],
            "email": email, "role": user.get("role"), "isVerified": bool(user.get("is_verified"))}


def _normalize_message(doc):
    return {"id": str(doc["_id"]), "conversationId": str(doc["conversation_id"]),
            "authorId": str(doc["author_id"]), "body": doc["body"],
            "createdAt": doc["created_at"].isoformat(), "readBy": [str(x) for x in doc.get("read_by", [])],
            "deleted": bool(doc.get("deleted", False))}


def persist_message(db, sender_id, conversation_id, body):
    if not ObjectId.is_valid(str(sender_id)) or not ObjectId.is_valid(str(conversation_id)):
        return None, None
    body = (body or "").strip()
    if not body or len(body) > 5000:
        return None, None
    sender = ObjectId(sender_id)
    conv_id = ObjectId(conversation_id)
    conv = db["conversations"].find_one({"_id": conv_id, "participants": sender})
    if not conv:
        return None, None
    now = datetime.now(timezone.utc)
    doc = {"conversation_id": conv_id, "author_id": sender, "body": body, "created_at": now,
           "read_by": [sender], "deleted": False, "hidden_for": []}
    result = db["messages"].insert_one(doc)
    db["conversations"].update_one({"_id": conv_id}, {"$set": {"updated_at": now}, "$pull": {"hidden_for": sender}})
    doc["_id"] = result.inserted_id
    recipient = next((participant for participant in conv["participants"] if participant != sender), None)
    if recipient:
        sender_doc = db[C.USERS].find_one({"_id": sender}, {"full_name": 1}) or {}
        recipient_doc = db[C.USERS].find_one({"_id": recipient}, {"role": 1}) or {}
        notification = {
            "user_id": recipient, "type": "message", "title": "New message",
            "message": f"{sender_doc.get('full_name') or 'A user'}: {body[:160]}", "icon": "message",
            "action_url": f"/{recipient_doc.get('role', 'student')}/messages?chat={conversation_id}",
            "related_entity_type": "conversation", "related_entity_id": str(conversation_id),
            "priority": "medium", "is_read": False, "created_at": now,
        }
        notification["_id"] = db[C.NOTIFICATIONS].insert_one(notification).inserted_id
        notification = {"id": str(notification["_id"]), "user_id": str(recipient), "type": notification["type"],
                        "title": notification["title"], "message": notification["message"],
                        "icon": notification["icon"], "action_url": notification["action_url"],
                        "related_entity_type": "conversation", "related_entity_id": str(conv_id),
                        "priority": notification["priority"], "is_read": False, "created_at": now.isoformat()}
    else:
        notification = None
    return _normalize_message(doc), notification


@router.get("/users")
async def search_message_users(query: str = Query(min_length=1, max_length=100),
                               current=Depends(get_current_user), db: Database = Depends(get_database)):
    if current.get("role") not in {"student", "hr"}:
        raise HTTPException(403, "Messaging is available to students and HR accounts")
    needle = re.escape(query.strip().lstrip("@"))
    if not needle:
        return {"data": []}
    role_filter = ["student", "hr"] if current["role"] == "student" else ["student"]
    users = db[C.USERS].find({"_id": {"$ne": ObjectId(current["id"])}, "role": {"$in": role_filter}, "is_active": {"$ne": False}, "$or": [
        {"username": {"$regex": f"^{needle}", "$options": "i"}},
        {"full_name": {"$regex": needle, "$options": "i"}},
        {"email": {"$regex": f"^{needle}", "$options": "i"}},
    ]}, {"password_hash": 0}).limit(20)
    return {"data": [_user_card(u) for u in users]}


@router.get("/conversations")
async def list_conversations(current=Depends(get_current_user), db: Database = Depends(get_database)):
    if current.get("role") not in {"student", "hr"}:
        raise HTTPException(403, "Messaging is available to students and HR accounts")
    me = ObjectId(current["id"])
    conversations = db["conversations"].find({"participants": me, "hidden_for": {"$ne": me}}).sort("updated_at", -1).limit(100)
    output = []
    for conv in conversations:
        peer_id = next((p for p in conv["participants"] if p != me), None)
        peer = db[C.USERS].find_one({"_id": peer_id}, {"password_hash": 0}) if peer_id else None
        if not peer:
            continue
        latest = db["messages"].find_one({"conversation_id": conv["_id"], "hidden_for": {"$ne": me}}, sort=[("created_at", -1)])
        output.append({"id": str(conv["_id"]), "type": "direct", "peerId": str(peer_id),
                       "peer": _user_card(peer), "participants": [str(p) for p in conv["participants"]],
                       "lastMessage": _normalize_message(latest) if latest else None,
                       "unread": db["messages"].count_documents({"conversation_id": conv["_id"], "author_id": {"$ne": me}, "read_by": {"$ne": me}, "deleted": False, "hidden_for": {"$ne": me}})})
    return {"data": output}


@router.post("/conversations/{peer_id}")
async def open_conversation(peer_id: str, current=Depends(get_current_user), db: Database = Depends(get_database)):
    if current.get("role") not in {"student", "hr"} or not ObjectId.is_valid(peer_id) or peer_id == current["id"]:
        raise HTTPException(400, "Invalid message recipient")
    me = ObjectId(current["id"])
    peer_oid = ObjectId(peer_id)
    peer = db[C.USERS].find_one({"_id": peer_oid, "is_active": {"$ne": False}}, {"password_hash": 0})
    allowed_peer_roles = {"student", "hr"} if current.get("role") == "student" else {"student"}
    if not peer or peer.get("role") not in allowed_peer_roles:
        raise HTTPException(404, "Recipient not found")
    participants = sorted([me, peer_oid], key=str)
    conv = db["conversations"].find_one({"participants": participants})
    if conv:
        db["conversations"].update_one({"_id": conv["_id"]}, {"$pull": {"hidden_for": me}})
    else:
        now = datetime.now(timezone.utc)
        result = db["conversations"].insert_one({"participants": participants, "hidden_for": [], "created_at": now, "updated_at": now})
        conv = {"_id": result.inserted_id, "participants": participants}
    return {"data": {"id": str(conv["_id"]), "type": "direct", "peerId": peer_id,
                      "peer": _user_card(peer), "participants": [str(x) for x in participants], "unread": 0}}


@router.get("/conversations/{conversation_id}")
async def get_messages(conversation_id: str, current=Depends(get_current_user), db: Database = Depends(get_database)):
    if not ObjectId.is_valid(conversation_id):
        raise HTTPException(404, "Conversation not found")
    conv_id, me = ObjectId(conversation_id), ObjectId(current["id"])
    if not db["conversations"].find_one({"_id": conv_id, "participants": me}):
        raise HTTPException(404, "Conversation not found")
    unseen = list(db["messages"].find({"conversation_id": conv_id, "author_id": {"$ne": me}, "read_by": {"$ne": me}}, {"_id": 1, "author_id": 1}))
    db["messages"].update_many({"conversation_id": conv_id, "author_id": {"$ne": me}, "read_by": {"$ne": me}}, {"$addToSet": {"read_by": me}})
    if unseen:
        from app.main import sio
        for message in unseen:
            await sio.emit("message:read", {"conversationId": conversation_id, "messageId": str(message["_id"]), "readerId": str(me)},
                           room=f"user:{message['author_id']}")
    # Message alerts have served their purpose once the recipient opens the thread.
    db[C.NOTIFICATIONS].delete_many({"user_id": me, "type": "message", "related_entity_id": str(conv_id)})
    docs = db["messages"].find({"conversation_id": conv_id, "hidden_for": {"$ne": me}}).sort("created_at", 1).limit(500)
    return {"data": [_normalize_message(m) for m in docs]}


@router.post("/conversations/{conversation_id}/messages")
async def post_message(conversation_id: str, payload: MessageCreate, current=Depends(get_current_user), db: Database = Depends(get_database)):
    message, notification = persist_message(db, current["id"], conversation_id, payload.body)
    if not message:
        raise HTTPException(404, "Conversation not found or message invalid")
    conv = db["conversations"].find_one({"_id": ObjectId(conversation_id)})
    from app.main import sio
    for participant in conv["participants"]:
        await sio.emit("message:new", message, room=f"user:{participant}")
    if notification:
        await sio.emit("notification:new", notification, room=f"user:{notification['user_id']}")
    return {"data": message}


@router.delete("/conversations/{conversation_id}/messages/{message_id}")
async def delete_message(conversation_id: str, message_id: str, mode: str = Query("me"), current=Depends(get_current_user), db: Database = Depends(get_database)):
    me = ObjectId(current["id"])
    if not ObjectId.is_valid(conversation_id) or not ObjectId.is_valid(message_id):
        raise HTTPException(404, "Message not found")
    filt = {"_id": ObjectId(message_id), "conversation_id": ObjectId(conversation_id)}
    if mode == "everyone":
        filt["author_id"] = me
        message_doc = db["messages"].find_one(filt, {"created_at": 1})
        if not message_doc or (datetime.now(timezone.utc) - message_doc["created_at"]).total_seconds() > 3600:
            raise HTTPException(403, "Messages can only be unsent by the sender within one hour")
        result = db["messages"].update_one(filt, {"$set": {"deleted": True, "body": ""}})
    else:
        filt["conversation_id"] = ObjectId(conversation_id)
        if not db["conversations"].find_one({"_id": filt["conversation_id"], "participants": me}):
            raise HTTPException(404, "Message not found")
        result = db["messages"].update_one(filt, {"$addToSet": {"hidden_for": me}})
    if not result.matched_count:
        raise HTTPException(404, "Message not found")
    if mode == "everyone":
        conversation = db["conversations"].find_one({"_id": ObjectId(conversation_id)})
        if conversation:
            from app.main import sio
            await sio.emit("message:deleted", {"conversationId": conversation_id, "messageId": message_id},
                           room=f"user:{next((p for p in conversation['participants'] if p != me), me)}")
    return {"message": "Message deleted"}


@router.delete("/conversations/{conversation_id}")
async def hide_conversation(conversation_id: str, current=Depends(get_current_user), db: Database = Depends(get_database)):
    if not ObjectId.is_valid(conversation_id):
        raise HTTPException(404, "Conversation not found")
    result = db["conversations"].update_one({"_id": ObjectId(conversation_id), "participants": ObjectId(current["id"])}, {"$addToSet": {"hidden_for": ObjectId(current["id"])}})
    if not result.matched_count:
        raise HTTPException(404, "Conversation not found")
    return {"message": "Conversation hidden"}


@router.delete("")
async def hide_all_conversations(current=Depends(get_current_user), db: Database = Depends(get_database)):
    me = ObjectId(current["id"])
    db["conversations"].update_many({"participants": me}, {"$addToSet": {"hidden_for": me}})
    return {"message": "Conversations cleared"}
