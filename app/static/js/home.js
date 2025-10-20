document.addEventListener('DOMContentLoaded', () => {
    const videoInterestsInput = document.getElementById('video-interests');
    const textInterestsInput = document.getElementById('text-interests');
    const startVideoButton = document.getElementById('start-video-chat');
    const startTextButton = document.getElementById('start-text-chat');
    
    // Handle video chat button click
    startVideoButton.addEventListener('click', () => {
        const interests = videoInterestsInput.value.trim();
        // Store interests in session storage to use in the video chat page
        sessionStorage.setItem('chatInterests', interests);
        // Navigate to video chat page
        window.location.href = '/video-chat';
    });
    
    // Handle text chat button click
    startTextButton.addEventListener('click', () => {
        const interests = textInterestsInput.value.trim();
        // Store interests in session storage to use in the text chat page
        sessionStorage.setItem('chatInterests', interests);
        // Navigate to text chat page
        window.location.href = '/text-chat';
    });
});