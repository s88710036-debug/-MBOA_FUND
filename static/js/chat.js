function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

window.initChat = function(conversationId, currentUser) {
  const messagesEl = document.getElementById('messages');
  const input = document.getElementById('messageInput');
  const form = document.getElementById('sendForm');

  async function fetchMessages(){
    try{
      const res = await fetch(`/chat/api/conversation/${conversationId}/messages/`);
      if(!res.ok) return;
      const data = await res.json();
      messagesEl.innerHTML = '';
      data.messages.forEach(m => {
        const div = document.createElement('div');
        div.style.padding = '6px 0';
        div.innerHTML = `<strong>${m.sender}:</strong> ${m.content}`;
        messagesEl.appendChild(div);
      });
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }catch(e){
      console.error(e);
    }
  }

  form.addEventListener('submit', async function(e){
    e.preventDefault();
    const content = input.value.trim();
    if(!content) return;
    try{
      const res = await fetch(`/chat/api/conversation/${conversationId}/send/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({content})
      });
      if(res.ok){
        input.value = '';
        await fetchMessages();
      }else{
        console.error('failed to send', res.status);
      }
    }catch(err){ console.error(err); }
  });

  // initial
  fetchMessages();
  // polling every 2.5s
  setInterval(fetchMessages, 2500);
};
