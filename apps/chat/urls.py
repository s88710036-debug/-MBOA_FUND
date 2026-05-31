from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("room/<int:conversation_id>/", views.room, name="room"),
    path(
        "api/conversation/<int:conversation_id>/messages/",
        views.get_messages,
        name="get_messages",
    ),
    path(
        "api/conversation/<int:conversation_id>/send/",
        views.send_message,
        name="send_message",
    ),
]
