document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-message');
    const chatMessages = document.getElementById('chat-messages');
    const nextChatButton = document.getElementById('next-chat');
    const backHomeButton = document.getElementById('back-home');
    const interestsInput = document.getElementById('interests');
    const updateInterestsButton = document.getElementById('update-interests');
    const connectionStatus = document.getElementById('connection-status');
    
    let socket = null;
    let connected = false;
    
    // Get interests from session storage (set on the home page)
    const savedInterests = sessionStorage.getItem('chatInterests') || '';
    interestsInput.value = savedInterests;
    
    // Initialize WebSocket connection
    function connectWebSocket() {
        // Close existing connection if any
        if (socket) {
            socket.close();
        }
        
        // Get interests as an array
        const interests = interestsInput.value
            .split(',')
            .map(interest => interest.trim())
            .filter(interest => interest.length > 0);
        
        // Connect to WebSocket
        socket = new WebSocket(`${getWebSocketProtocol()}://${window.location.host}/ws/text`);
        
        socket.onopen = () => {
            // Send interests to server
            socket.send(JSON.stringify({
                type: 'interests',
                interests: interests
            }));
            
            addSystemMessage('Connected to server. Looking for a chat partner...');
            connectionStatus.textContent = 'Connected to server';
            connectionStatus.classList.add('connected');
        };
        
        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'system') {
                addSystemMessage(data.message);
                
                // If we've been connected to a stranger
                if (data.message.includes('connected to a stranger')) {
                    connected = true;
                    connectionStatus.textContent = 'Chatting';
                    connectionStatus.classList.add('connected');
                }
                
                // If our partner disconnected
                if (data.message.includes('disconnected')) {
                    connected = false;
                    connectionStatus.textContent = 'Disconnected';
                    connectionStatus.classList.remove('connected');
                }
            } else if (data.type === 'message') {
                addMessage(data.message, 'received');
            }
        };
        
        socket.onclose = () => {
            addSystemMessage('Disconnected from server');
            connectionStatus.textContent = 'Disconnected';
            connectionStatus.classList.remove('connected');
            connected = false;
        };
        
        socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            addSystemMessage('Error connecting to server');
            connectionStatus.textContent = 'Error';
            connectionStatus.classList.remove('connected');
        };
    }
    
    // Helper to determine WebSocket protocol (ws or wss)
    function getWebSocketProtocol() {
        return window.location.protocol === 'https:' ? 'wss' : 'ws';
    }
    
    // Add a message to the chat
    function addMessage(message, type) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', type);
        messageElement.textContent = message;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Add a system message
    function addSystemMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('system-message');
        messageElement.textContent = message;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Send a message
    function sendMessage() {
        const message = messageInput.value.trim();
        if (message && connected && socket) {
            socket.send(JSON.stringify({
                type: 'message',
                message: message
            }));
            addMessage(message, 'sent');
            messageInput.value = '';
        }
    }
    
    // Find a new chat partner
    function findNewChat() {
        if (socket) {
            const interests = interestsInput.value
                .split(',')
                .map(interest => interest.trim())
                .filter(interest => interest.length > 0);
            
            socket.send(JSON.stringify({
                type: 'find-new',
                interests: interests
            }));
            
            addSystemMessage('Looking for a new chat partner...');
            connected = false;
        }
    }
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    nextChatButton.addEventListener('click', findNewChat);
    
    backHomeButton.addEventListener('click', () => {
        window.location.href = '/';
    });
    
    updateInterestsButton.addEventListener('click', () => {
        // Save interests to session storage
        sessionStorage.setItem('chatInterests', interestsInput.value);
        findNewChat();
    });
    
    // Connect when page loads
    connectWebSocket();
});