// const API_URL = "http://localhost:8000/api"; // This will be our backend URL


// To something like this (using the URL you copied):
const API_URL = "https://zqdv8lvl-8000.inc1.devtunnels.ms/api";
// NEW: A global variable to store the conversation history
let chatHistory = [];


async function uploadFile() {
    const fileInput = document.getElementById('pdfUpload');
    const status = document.getElementById('uploadStatus');

    if (fileInput.files.length === 0) {
        status.textContent = 'Please select a file first.';
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    status.textContent = 'Uploading...';
    try {
        const response = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData,
    });

    // Step 1: Check for HTTP errors (e.g., 404 Not Found, 500 Internal Server Error)
        if (!response.ok) {
            // Try to get a more detailed error message from the response body
            const errorText = await response.text(); // Use .text() as we can't assume JSON
            throw new Error(`Server responded with ${response.status}: ${errorText || response.statusText}`);
    }

        const result = await response.json();

    // Step 2: Handle the successful JSON response
    // Checks for FastAPI's validation error format
        if (result.detail) {
            status.textContent = `Error: ${result.detail}`;
        } else {
            status.textContent = result.message || "Upload successful, but no message received.";
        }
        }
    catch (error) {
        // Step 3: Log the full technical error to the console for debugging
        console.error('An error occurred during upload:', error);

        // Step 4: Display a user-friendly message in the UI
        // This now catches both network errors and the server errors we threw above
        status.textContent = `Upload failed: ${error.message}`;
    }
    }

async function askQuestion() {
    const input = document.getElementById('chatInput');
    const answerContainer = document.getElementById('answerContainer'); // We'll display history here
    const query = input.value;

    if (!query) return;

    // Display user's question immediately
    answerContainer.innerHTML += `<p><strong>You:</strong> ${query}</p>`;
    answerContainer.innerHTML += `<p><strong>Bot:</strong> Thinking...</p>`;
    input.value = ''; // Clear input

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            // MODIFIED: Send the query AND the current chat history
            body: JSON.stringify({ 
                query: query,
                chat_history: chatHistory 
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        
        // Update the "Thinking..." message with the real answer
        answerContainer.lastElementChild.innerHTML = `<strong>Bot:</strong> ${result.answer}`;
        // UPDATE THE SOURCE DISPLAY
        sourceContainer.innerHTML = ''; // Clear previous sources
        result.sources.forEach((source, index) => {
            sourceContainer.innerHTML += `
                <div>
                    <strong>Source ${index + 1}:</strong>
                    <p>${source.content.replace(/\n/g, '<br>')}</p>
                </div>
                <hr>`;
        });
        // MODIFIED: Update our global chat history with the latest turn
        // The API returns a list of LangChain message objects, we need to adapt it
        // A simple way is to just keep our own track
        chatHistory.push([query, result.answer]);

    } catch (error) {
        answerContainer.lastElementChild.innerHTML = `<strong>Bot:</strong> Failed to get an answer. ${error}`;
    }
}

// async function askQuestion() {
//     const input = document.getElementById('chatInput');
//     const answerP = document.getElementById('answer');
//     const query = input.value;

//     if (!query) {
//         answerP.textContent = 'Please enter a question.';
//         return;
//     }

//     answerP.textContent = 'Thinking...';
//     try {
//         const response = await fetch(`${API_URL}/chat`, {
//             method: 'POST',
//             headers: { 'Content-Type': 'application/json' },
//             body: JSON.stringify({ query: query }),
//         });
//         const result = await response.json();
//         answerP.textContent = result.answer;
//     } catch (error) {
//         answerP.textContent = 'Failed to get an answer.';
//     }
// }