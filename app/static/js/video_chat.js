document.addEventListener('DOMContentLoaded', () => {
    const localVideo = document.getElementById('local-video');
    const remoteVideo = document.getElementById('remote-video');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-message');
    const chatMessages = document.getElementById('chat-messages');
    const toggleVideoButton = document.getElementById('toggle-video');
    const toggleAudioButton = document.getElementById('toggle-audio');
    const nextChatButton = document.getElementById('next-chat');
    const interestsInput = document.getElementById('interests');
    const updateInterestsButton = document.getElementById('update-interests');
    const remoteStatus = document.getElementById('remote-status');
    const typingIndicator = document.getElementById('typing-indicator');
    const usersOnlineEl = document.getElementById('users-online');
    
    let socket = null;
    let localStream = null;
    let peerConnection = null;
    let connected = false;
    let videoEnabled = true;
    let audioEnabled = true;
    
    // Get interests from session storage (set on the home page)
    const savedInterests = sessionStorage.getItem('chatInterests') || '';
    interestsInput.value = savedInterests;
    
    // WebRTC configuration
    const configuration = {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' }
        ]
    };
    
    // Initialize media stream and WebSocket connection
    async function initialize() {
        try {
            // Get local media stream
            localStream = await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: true
            });
            
            // Display local video
            localVideo.srcObject = localStream;
            
            // Connect to WebSocket server
            connectWebSocket();
        } catch (error) {
            console.error('Error accessing media devices:', error);
            addSystemMessage('Error accessing camera or microphone. Please check permissions.');
        }
    }
    
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
        socket = new WebSocket(`${getWebSocketProtocol()}://${window.location.host}/ws/video`);
        
        socket.onopen = () => {
            // Send interests to server
            socket.send(JSON.stringify({
                type: 'interests',
                interests: interests
            }));
            
            addSystemMessage('Connected to server. Looking for a chat partner...');
        };
        
        socket.onmessage = async (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'system') {
                addSystemMessage(data.message);
                
                // If we've been connected to a stranger
                if (data.message.includes('connected to a stranger') || data.message.includes('connected to a new stranger')) {
                    connected = true;
                    remoteStatus.textContent = 'Connected to stranger';
                    // Offer will be created only when 'webrtc-init' is received to avoid glare
                }
                
                // If our partner disconnected
                if (data.message.includes('disconnected')) {
                    connected = false;
                    remoteStatus.textContent = 'Stranger disconnected';
                    remoteVideo.srcObject = null;
                    closePeerConnection();
                    // Hide typing indicator when disconnected
                    typingIndicator.style.display = 'none';
                    
                    // Automatically find a new chat partner after a short delay
                    setTimeout(() => {
                        addSystemMessage('Looking for a new chat partner...');
                        findNewChat();
                    }, 1500);
                }
            } else if (data.type === 'message') {
                addMessage(data.message, 'received');
                // Hide typing indicator when message is received
                typingIndicator.style.display = 'none';
            } else if (data.type === 'video-signal') {
                handleVideoSignal(data.signal);
            } else if (data.type === 'typing') {
                // Show or hide typing indicator based on stranger's typing status
                typingIndicator.style.display = data.isTyping ? 'block' : 'none';
            } else if (data.type === 'webrtc-init') {
                // We are the designated offerer; start negotiation
                if (!peerConnection) {
                    createPeerConnection();
                }
                try {
                    const offer = await peerConnection.createOffer();
                    await peerConnection.setLocalDescription(offer);
                    socket.send(JSON.stringify({
                        type: 'video-signal',
                        signal: {
                            type: 'offer',
                            sdp: peerConnection.localDescription
                        }
                    }));
                } catch (e) {
                    console.error('Error creating offer:', e);
                }
            } else if (data.type === 'online') {
                // Update users online indicator
                if (usersOnlineEl) {
                    usersOnlineEl.textContent = `Users online: ${data.count}`;
                }
            }
        };
        
        socket.onclose = () => {
            addSystemMessage('Disconnected from server');
            connected = false;
            remoteStatus.textContent = 'Disconnected';
            closePeerConnection();
        };
        
        socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            addSystemMessage('Error connecting to server');
        };
    }
    
    // Create WebRTC peer connection
    function createPeerConnection() {
        // Close existing connection if any
        closePeerConnection();
        
        // Create new connection
        peerConnection = new RTCPeerConnection(configuration);
        
        // Add local stream tracks to peer connection
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });
        
        // Handle ICE candidates
        peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                socket.send(JSON.stringify({
                    type: 'video-signal',
                    signal: {
                        type: 'ice-candidate',
                        candidate: event.candidate
                    }
                }));
            }
        };
        
        // Handle remote stream
        peerConnection.ontrack = (event) => {
            console.log('Track event received:', event);
            remoteVideo.srcObject = event.streams[0];
            remoteVideo.muted = true; // ensure autoplay works across browsers
            remoteStatus.textContent = 'Connected to stranger';
            
            // Force video element to play
            remoteVideo.play().catch(e => {
                console.error('Error playing remote video:', e);
                // Try again with user interaction
                remoteVideo.setAttribute('autoplay', true);
            });
            
            // Debug info
            console.log('Remote video state:', remoteVideo.readyState);
            console.log('Remote video tracks:', event.streams[0]?.getVideoTracks().length);
        };
        
        // Handle connection state changes
        peerConnection.onconnectionstatechange = () => {
            if (peerConnection.connectionState === 'disconnected' || 
                peerConnection.connectionState === 'failed') {
                remoteStatus.textContent = 'Connection lost';
                remoteVideo.srcObject = null;
            }
        };
    }
    
    // Close peer connection
    function closePeerConnection() {
        if (peerConnection) {
            peerConnection.close();
            peerConnection = null;
        }
    }
    
    // Handle incoming WebRTC signals
    async function handleVideoSignal(signal) {
        try {
            if (!peerConnection) {
                createPeerConnection();
            }
            
            if (signal.type === 'offer') {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(signal.sdp));
                const answer = await peerConnection.createAnswer();
                await peerConnection.setLocalDescription(answer);
                
                socket.send(JSON.stringify({
                    type: 'video-signal',
                    signal: {
                        type: 'answer',
                        sdp: peerConnection.localDescription
                    }
                }));
            } else if (signal.type === 'answer') {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(signal.sdp));
            } else if (signal.type === 'ice-candidate') {
                await peerConnection.addIceCandidate(new RTCIceCandidate(signal.candidate));
            }
        } catch (error) {
            console.error('Error handling video signal:', error);
        }
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
    
    // Send a text message
    function sendMessage() {
        const message = messageInput.value.trim();
        if (message && connected && socket) {
            socket.send(JSON.stringify({
                type: 'message',
                message: message
            }));
            addMessage(message, 'sent');
            messageInput.value = '';
            
            // Stop typing indicator when message is sent
            sendTypingStatus(false);
        }
    }
    
    // Typing indicator
    let typingTimeout = null;
    
    messageInput.addEventListener('input', () => {
        if (connected) {
            // Clear previous timeout
            if (typingTimeout) {
                clearTimeout(typingTimeout);
            }
            
            // Send typing status
            sendTypingStatus(true);
            
            // Set timeout to stop typing indicator after 2 seconds of inactivity
            typingTimeout = setTimeout(() => {
                sendTypingStatus(false);
            }, 2000);
        }
    });
    
    function sendTypingStatus(isTyping) {
        if (connected && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                type: 'typing',
                isTyping: isTyping
            }));
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
            remoteStatus.textContent = 'Waiting for someone to connect...';
            remoteVideo.srcObject = null;
            closePeerConnection();
        }
    }
    
    // Toggle video
    function toggleVideo() {
        if (localStream) {
            videoEnabled = !videoEnabled;
            localStream.getVideoTracks().forEach(track => {
                track.enabled = videoEnabled;
            });
            
            if (videoEnabled) {
                toggleVideoButton.classList.remove('disabled');
                toggleVideoButton.classList.add('enabled');
            } else {
                toggleVideoButton.classList.remove('enabled');
                toggleVideoButton.classList.add('disabled');
            }
        }
    }
    
    // Toggle audio
    function toggleAudio() {
        if (localStream) {
            audioEnabled = !audioEnabled;
            localStream.getAudioTracks().forEach(track => {
                track.enabled = audioEnabled;
            });
            
            if (audioEnabled) {
                toggleAudioButton.classList.remove('disabled');
                toggleAudioButton.classList.add('enabled');
            } else {
                toggleAudioButton.classList.remove('enabled');
                toggleAudioButton.classList.add('disabled');
            }
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
    
    toggleVideoButton.addEventListener('click', toggleVideo);
    
    toggleAudioButton.addEventListener('click', toggleAudio);
    
    updateInterestsButton.addEventListener('click', () => {
        // Save interests to session storage
        sessionStorage.setItem('chatInterests', interestsInput.value);
        findNewChat();
    });
    
    // Initialize when page loads
    // Unmute remote audio on first user interaction
    document.body.addEventListener('click', () => {
        if (remoteVideo && remoteVideo.srcObject) {
            remoteVideo.muted = false;
            remoteVideo.play().catch(() => {});
        }
    }, { once: true });
    
    initialize();
});