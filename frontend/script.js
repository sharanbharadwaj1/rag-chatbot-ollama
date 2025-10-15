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

// function updateKnowledgeBaseList() {
        
//     console.log("Updating knowledge base list with sources:", knowledgeBaseSources);

//     const listContainer = document.getElementById('knowledgeBaseList');
//     if (knowledgeBaseSources.length === 0) {
//         listContainer.innerHTML = '<ul><li>No sources loaded yet.</li></ul>';
//         return;
//     }

//     const ul = document.createElement('ul');
//     knowledgeBaseSources.forEach(sourceName => {
//         const li = document.createElement('li');
//         // Add a small icon based on the source type
//         const icon = sourceName.toLowerCase().endsWith('.pdf') ? '📄' : '🌐';
//         li.textContent = `${icon} ${sourceName}`;
//         ul.appendChild(li);
//     });
//     listContainer.innerHTML = '';
//     listContainer.appendChild(ul);
// }

// To something like this (using the URL you copied):
// const API_URL = "https://zqdv8lvl-8000.inc1.devtunnels.ms/api";
// NEW: A global variable to store the conversation history
let chatHistory = [];
// let knowledgeBaseSources = [];

async function uploadFile() {
    const fileInput = document.getElementById('pdfUpload');
    const status = document.getElementById('uploadStatus');
    const spinner = document.getElementById('uploadSpinner');
    const uploadButton = document.getElementById('uploadButton');
    const chooseFileBtn = document.getElementById('chooseFileBtn');

    if (fileInput.files.length === 0) {
        status.textContent = 'Please select a file first.';
        return;
    }

    const filename = fileInput.files[0].name; // Get filename

    status.textContent = 'Processing document... this may take a moment.';
    spinner.style.display = 'block';
    uploadButton.disabled = true;
    chooseFileBtn.disabled = true;
    fileInput.disabled = true;

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
        status.textContent = result.message || "Upload successful!";
        
        // --- NEW LOGIC ---
        // if (!knowledgeBaseSources.includes(filename)) {
        //     knowledgeBaseSources.push(filename);
        // }
        // updateKnowledgeBaseList();
        // --- END NEW LOGIC ---
        
        fileInput.value = '';

    } catch (error) {
        console.error('An error occurred during upload:', error);
        status.textContent = `Upload failed: ${error.message}`;
    } finally {
        spinner.style.display = 'none';
        uploadButton.disabled = false;
        chooseFileBtn.disabled = false;
        fileInput.disabled = false;
        setTimeout(() => {
            if (status.textContent.includes("successful") || status.textContent.includes("failed")) {
                status.textContent = 'Upload another document to add to the knowledge base.';
            }
        }, 3000);
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

// ADD THIS NEW FUNCTION TO YOUR SCRIPT.JS FILE

async function ingestWebsite() {
    const urlInput = document.getElementById('urlInput');
    const status = document.getElementById('ingestStatus');
    const spinner = document.getElementById('ingestSpinner');
    const ingestButton = document.getElementById('ingestUrlButton');
    const url = urlInput.value.trim();

    if (!url) {
        status.textContent = 'Please enter a URL first.';
        return;
    }

    status.textContent = 'Ingesting content... this may take a moment.';
    spinner.style.display = 'block';
    ingestButton.disabled = true;
    urlInput.disabled = true;

    try {
        const response = await fetch(`${API_URL}/ingest-website`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Server responded with ${response.status}: ${errorText || response.statusText}`);
        }

        const result = await response.json();
        status.textContent = result.message || "Ingestion successful!";

        // // --- NEW LOGIC ---
        // if (!knowledgeBaseSources.includes(url)) {
        //     knowledgeBaseSources.push(url);
        // }
        // updateKnowledgeBaseList();
        // // --- END NEW LOGIC ---

        urlInput.value = '';

    } catch (error) {
        console.error('An error occurred during ingestion:', error);
        status.textContent = `Ingestion failed: ${error.message}`;
    } finally {
        spinner.style.display = 'none';
        ingestButton.disabled = false;
        urlInput.disabled = false;
    }
}