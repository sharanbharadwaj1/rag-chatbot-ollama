const API_URL = "http://localhost:8000/api"; // This will be our backend URL

document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('pdfUpload');
    const uploadStatus = document.getElementById('uploadStatus');

    // This function runs whenever the user selects a file
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            // If a file is chosen, display its name
            uploadStatus.textContent = `Selected: ${this.files[0].name}`;
            uploadStatus.style.color = '#e0e0e0'; // Use a brighter color for visibility
        } else {
            // If no file is chosen (e.g., the user clicks "cancel")
            uploadStatus.textContent = 'Upload a document to build your knowledge base.';
            uploadStatus.style.color = 'var(--subtle-text-color)'; // Revert to the default color
        }
    });
});
// To something like this (using the URL you copied):
// const API_URL = "https://zqdv8lvl-8000.inc1.devtunnels.ms/api";
// NEW: A global variable to store the conversation history
let chatHistory = [];


async function uploadFile() {
    const fileInput = document.getElementById('pdfUpload');
    const status = document.getElementById('uploadStatus');
    const spinner = document.querySelector('#uploadStatusContainer .spinner');
    const uploadButton = document.getElementById('uploadButton');
    const chooseFileBtn = document.getElementById('chooseFileBtn');

    if (fileInput.files.length === 0) {
        status.textContent = 'Please select a file first.';
        return;
    }

    // --- Start of new logic ---
    // Update UI to show processing is starting
    status.textContent = 'Processing document... this may take a moment.';
    spinner.style.display = 'block';
    uploadButton.disabled = true;
    chooseFileBtn.disabled = true;
    fileInput.disabled = true;
    // --- End of new logic ---

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const response = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Server responded with ${response.status}: ${errorText || response.statusText}`);
        }

        const result = await response.json();
        
        status.textContent = result.message || "Upload successful, but no message received.";
        fileInput.value = ''; // Clear the file input

    } catch (error) {
        console.error('An error occurred during upload:', error);
        status.textContent = `Upload failed: ${error.message}`;
    } finally {
        // --- Start of new logic ---
        // Always hide spinner and re-enable buttons when done
        spinner.style.display = 'none';
        uploadButton.disabled = false;
        chooseFileBtn.disabled = false;
        fileInput.disabled = false;
        
        // After success or failure, revert the 'Selected: ...' text if no new file is chosen
        if (fileInput.files.length === 0) {
             setTimeout(() => {
                if (status.textContent.includes("successful") || status.textContent.includes("failed")) {
                   status.textContent = 'Upload another document to add to the knowledge base.';
                }
            }, 3000); // Revert message after 3 seconds
        }
        // --- End of new logic ---
    }
}

async function askQuestion() {
    const input = document.getElementById('chatInput');
    const answerContainer = document.getElementById('answerContainer');
    const sourceContainer = document.getElementById('sourceContainer');
    const askButton = document.getElementById('askButton');
    const query = input.value;

    if (!query) return;

    // --- Create and display the user's message ---
    const userMessage = document.createElement('div');
    userMessage.className = 'message user';
    userMessage.textContent = query;
    answerContainer.appendChild(userMessage);
    input.value = '';

    // --- Create and display the bot's "thinking" indicator ---
    const botThinkingMessage = document.createElement('div');
    botThinkingMessage.className = 'message bot';
    botThinkingMessage.innerHTML = `
        <div class="typing-indicator">
            <span></span><span></span><span></span>
        </div>
    `;
    answerContainer.appendChild(botThinkingMessage);
    
    // --- Scroll to the bottom of the chat ---
    answerContainer.scrollTop = answerContainer.scrollHeight;

    // --- Disable the ask button while the bot is thinking ---
    askButton.disabled = true;

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                query: query,
                chat_history: chatHistory 
            }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Server responded with ${response.status}: ${errorText || response.statusText}`);
        }

        const result = await response.json();
        
        // --- Update the "thinking" message with the real answer ---
        botThinkingMessage.innerHTML = result.answer.replace(/\n/g, '<br>');

        // --- Update the source display ---
        sourceContainer.innerHTML = ''; // Clear previous sources
        if (result.sources && result.sources.length > 0) {
            result.sources.forEach((source, index) => {
                const sourceDiv = document.createElement('div');
                sourceDiv.innerHTML = `
                    <strong>Source ${index + 1} (from ${source.metadata.source || 'N/A'}):</strong>
                    <p>${source.content.replace(/\n/g, '<br>')}</p>
                `;
                sourceContainer.appendChild(sourceDiv);
            });
        } else {
            sourceContainer.innerHTML = "<p>No specific sources were retrieved for this answer.</p>";
        }
        
        // --- Update chat history ---
        chatHistory.push([query, result.answer]);

    } catch (error) {
        console.error('An error occurred during chat:', error);
        botThinkingMessage.textContent = `Sorry, an error occurred: ${error.message}`;
    } finally {
        // --- Re-enable the ask button ---
        askButton.disabled = false;
        // --- Scroll to the bottom again after the response ---
        answerContainer.scrollTop = answerContainer.scrollHeight;
    }
}