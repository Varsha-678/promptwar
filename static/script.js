document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const messagesContainer = document.getElementById('chat-messages');
    const sampleQuestionsContainer = document.getElementById('sample-questions');
    const infoCardsContainer = document.getElementById('info-cards-container');

    // Fetch initial info
    fetch('/api/info')
        .then(response => response.json())
        .then(data => {
            renderSampleQuestions(data.sample_questions);
            renderInfoCards(data.event_data);
        })
        .catch(err => {
            console.error("Failed to load info", err);
            infoCardsContainer.innerHTML = '<div class="loading-state">Failed to load event data.</div>';
        });

    function renderSampleQuestions(questions) {
        sampleQuestionsContainer.innerHTML = '';
        questions.forEach(q => {
            const btn = document.createElement('button');
            btn.className = 'question-chip';
            btn.textContent = q;
            btn.type = 'button';
            btn.onclick = () => {
                userInput.value = q;
                chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            };
            sampleQuestionsContainer.appendChild(btn);
        });
    }

    function renderInfoCards(data) {
        infoCardsContainer.innerHTML = '';
        
        // Sessions Card
        if (data.sessions && data.sessions.length > 0) {
            const card = document.createElement('div');
            card.className = 'info-card';
            const nextSession = data.sessions[0];
            card.innerHTML = `
                <h3>Upcoming Session</h3>
                <p><strong>${nextSession.title}</strong></p>
                <p>Time: ${nextSession.time} | Location: ${nextSession.hall}</p>
                <p>Topic: ${nextSession.tag}</p>
            `;
            infoCardsContainer.appendChild(card);
        }

        // Help Desk Card
        if (data.facilities && data.facilities['help desk']) {
            const card = document.createElement('div');
            card.className = 'info-card';
            card.innerHTML = `
                <h3>Help Desk</h3>
                <p>${data.facilities['help desk']}</p>
            `;
            infoCardsContainer.appendChild(card);
        }

        // Food Card
        if (data.facilities && data.facilities['food']) {
            const card = document.createElement('div');
            card.className = 'info-card';
            card.innerHTML = `
                <h3>Food & Dining</h3>
                <p>${data.facilities['food']}</p>
            `;
            infoCardsContainer.appendChild(card);
        }
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message) return;

        // Add user message
        appendMessage(message, 'user');
        userInput.value = '';

        // Add typing indicator
        const typingId = appendTypingIndicator();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            const data = await response.json();
            
            removeElement(typingId);
            if (data.reply) {
                appendMessage(data.reply, 'ai');
            } else {
                appendMessage("Sorry, I didn't understand that.", 'ai');
            }
        } catch (err) {
            console.error(err);
            removeElement(typingId);
            appendMessage("Sorry, there was an error connecting to the server.", 'ai');
        }
    });

    function appendMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `message ${sender}-message`;
        div.innerHTML = `<p>${text}</p>`;
        messagesContainer.appendChild(div);
        scrollToBottom();
    }

    function appendTypingIndicator() {
        const id = 'typing-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.className = 'message ai-message typing-indicator';
        div.textContent = 'Thinking...';
        messagesContainer.appendChild(div);
        scrollToBottom();
        return id;
    }

    function removeElement(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
});
