const messagesEl = document.getElementById('messages');
const inputForm = document.getElementById('inputForm');
const messageInput = document.getElementById('messageInput');
let sessionId = null;

function addMessage(text, cls){
  const div = document.createElement('div');
  div.className = 'message ' + cls;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.parentElement.scrollTop = messagesEl.parentElement.scrollHeight;
}

inputForm.addEventListener('submit', async (e) =>{
  e.preventDefault();
  const text = messageInput.value.trim();
  if(!text) return;
  addMessage(text, 'user');
  messageInput.value = '';

  try{
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({user_query: text, session_id: sessionId})
    });
    const data = await res.json();
    if(data.session_id) sessionId = data.session_id;
    addMessage(data.bot_response || 'No response', 'bot');
  }catch(err){
    addMessage('Error contacting server', 'bot');
  }
});

// optional: show a welcome message
addMessage('Welcome! Ask me anything about the product or policies.', 'bot');

// Summarize button handler
const summarizeBtn = document.getElementById('summarizeBtn');
if (summarizeBtn) {
  summarizeBtn.addEventListener('click', async () => {
    if (!sessionId) {
      addMessage('No session to summarize yet.', 'bot');
      return;
    }
    try {
      const res = await fetch('/summarize', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({session_id: sessionId})
      });
      const data = await res.json();
      addMessage('Summary: ' + (data.summary || data.error), 'bot');
    } catch (err) {
      addMessage('Error summarizing conversation', 'bot');
    }
  });
}