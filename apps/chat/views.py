import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Conversation, Message


@login_required
def room(request, conversation_id):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    if request.user not in conversation.participants.all():
        return JsonResponse({"error": "forbidden"}, status=403)
    return render(request, "chat/room.html", {"conversation": conversation})


@login_required
def get_messages(request, conversation_id):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    if request.user not in conversation.participants.all():
        return JsonResponse({"error": "forbidden"}, status=403)
    messages = conversation.messages.select_related("sender").order_by("created_at")
    data = [
        {
            "id": m.pk,
            "sender": m.sender.get_full_name() or m.sender.username,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]
    return JsonResponse({"messages": data})


@login_required
@require_POST
def send_message(request, conversation_id):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    if request.user not in conversation.participants.all():
        return JsonResponse({"error": "forbidden"}, status=403)

    # accept JSON body or form-encoded
    try:
        payload = json.loads(request.body.decode()) if request.body else {}
    except Exception:
        payload = {}

    content = payload.get("content") or request.POST.get("content")
    if not content:
        return JsonResponse({"error": "empty"}, status=400)

    msg = Message.objects.create(conversation=conversation, sender=request.user, content=content)
    return JsonResponse(
        {
            "id": msg.pk,
            "sender": msg.sender.get_full_name() or msg.sender.username,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }
    )
