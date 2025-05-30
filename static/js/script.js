document.addEventListener('DOMContentLoaded', () => {
    const translateButton = document.getElementById('translate-button');
    translateButton.addEventListener('click', handleTranslateClick);

    const prevButton = document.getElementById('prev-button');
    prevButton.addEventListener('click', () => navigateSentence('prev'));

    const nextButton = document.getElementById('next-button');
    nextButton.addEventListener('click', () => navigateSentence('next'));

    // Initial load of the current sentence
    loadAndDisplayCurrentSentence();
});

/**
 * Fetches the current sentence from the Flask backend and displays it.
 * Also updates the progress bar and enables/disables the translate button.
 */
async function loadAndDisplayCurrentSentence() {
    try {
        const response = await fetch('/get_current_sentence');
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        const data = await response.json();
        const originalTextInput = document.getElementById('original-text-input');
        const progressBarText = document.getElementById('progress-text');
        const translateButton = document.getElementById('translate-button');

        if (data.completed) {
            originalTextInput.value = "All sentences translated!";
            progressBarText.textContent = `${data.index} / ${data.total}`;
            translateButton.disabled = true; // Disable translate button if all completed
        } else {
            originalTextInput.value = data.sentence;
            progressBarText.textContent = `${data.index + 1} / ${data.total}`;
            translateButton.disabled = false; // Enable translate button
            // Clear alternatives when a new sentence is loaded to prevent old translations from showing
            document.getElementById('alternatives-container').innerHTML = '';
            document.getElementById('error-message').textContent = '';
        }
    } catch (error) {
        console.error("Error loading current sentence:", error);
        document.getElementById('error-message').textContent = `Error loading sentence: ${error.message}`;
    }
}

/**
 * Navigates to the next or previous sentence by calling the respective Flask endpoint.
 * @param {string} direction - 'next' or 'prev'
 */
async function navigateSentence(direction) {
    try {
        const endpoint = direction === 'next' ? '/next_sentence' : '/previous_sentence';
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        await loadAndDisplayCurrentSentence(); // Load and display the new current sentence
    } catch (error) {
        console.error(`Error navigating to ${direction} sentence:`, error);
        document.getElementById('error-message').textContent = `Error navigating: ${error.message}`;
    }
}

/**
 * Handles the click event for the translate button.
 * Fetches translations from the backend and displays them.
 */
async function handleTranslateClick() {
    const originalText = document.getElementById('original-text-input').value;
    // Note: loadSavedTranslations() currently loads from localStorage.
    // Your Flask app uses translation.txt for context.
    const savedTranslations = loadSavedTranslations();
    const errorMessageDiv = document.getElementById('error-message');
    errorMessageDiv.textContent = '';

    // Get the selected model
    const modelRadios = document.getElementsByName('model');
    let selectedModel = 'gemini'; // Default to gemini, as qwen is disabled in index.html for now
    for (let radio of modelRadios) {
        if (radio.checked) {
            selectedModel = radio.value;
            break;
        }
    }

    // Prevent translation if input is empty or "All sentences translated!"
    if (!originalText || originalText === "All sentences translated!") {
        errorMessageDiv.textContent = "No sentence to translate or all sentences are done.";
        return;
    }

    try {
        const response = await fetch('/translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                original_sentence: originalText,
                saved_translations: savedTranslations,
                model: selectedModel // Pass the selected model to the backend
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Server error: ${response.status}`);
        }

        const data = await response.json();
        if (data.alternatives) {
            displayAlternatives(originalText, data.alternatives);
        }
    } catch (error) {
        console.error("Error translating:", error);
        errorMessageDiv.textContent = error.message;
    }
}

/**
 * Displays the alternative translations received from the backend.
 * Creates 'Edit' and 'Save to File' buttons for each alternative.
 * @param {string} originalSentence - The original sentence that was translated.
 * @param {Array<string>} alternativesArray - An array of translation strings.
 */
function displayAlternatives(originalSentence, alternativesArray) {
    const container = document.getElementById('alternatives-container');
    container.innerHTML = ''; // Clear previous alternatives

    alternativesArray.forEach((alternative, index) => {
        const div = document.createElement('div');
        div.className = 'alternative';

        const header = document.createElement('h3');
        header.textContent = `Alternative ${index + 1}`;
        div.appendChild(header);

        const text = document.createElement('p');
        text.innerHTML = alternative;
        div.appendChild(text);

        const editButton = document.createElement('button');
        editButton.className = 'edit-button';
        editButton.textContent = 'Edit';
        // Pass originalSentence, the paragraph element, and the parent div to handleEditClick
        editButton.addEventListener('click', () => handleEditClick(originalSentence, text, div));
        div.appendChild(editButton);

        container.appendChild(div);
    });
}

/**
 * Handles the click event for the 'Edit' button.
 * Replaces the translation text with a textarea for editing.
 * @param {string} originalSentence - The original sentence associated with this translation.
 * @param {HTMLElement} currentTextElement - The <p> element containing the current translation text.
 * @param {HTMLElement} alternativeDiv - The parent <div> element for the alternative.
 */
function handleEditClick(originalSentence, currentTextElement, alternativeDiv) {
    const originalTextContent = currentTextElement.innerHTML; // Get the current content
    const textarea = document.createElement('textarea');
    textarea.value = originalTextContent;
    textarea.rows = 3;
    textarea.className = 'alternative-textarea'; // Add a class for styling

    currentTextElement.replaceWith(textarea); // Replace <p> with <textarea>
    textarea.focus(); // Focus on the textarea for immediate editing

    // Remove existing edit button
    const editButton = alternativeDiv.querySelector('.edit-button');
    if (editButton) {
        editButton.remove();
    }

    // Add or update the 'Save Edited Translation' button
    let saveButton = alternativeDiv.querySelector('.save-button');
    if (!saveButton) { // If save button doesn't exist, create it
        saveButton = document.createElement('button');
        saveButton.className = 'save-button';
        saveButton.textContent = 'Save Edited Translation';
        alternativeDiv.appendChild(saveButton);
    }
    // Update the event listener for the save button to ensure it uses the latest textarea
    saveButton.onclick = () => handleSaveEditClick(originalSentence, textarea, alternativeDiv);
}

/**
 * Handles the click event for the 'Save Edited Translation' button.
 * Replaces the textarea with a paragraph element and saves the edited text.
 * @param {string} originalSentence - The original sentence associated with this translation.
 * @param {HTMLElement} textareaElement - The <textarea> element containing the edited text.
 * @param {HTMLElement} alternativeDiv - The parent <div> element for the alternative.
 */
function handleSaveEditClick(originalSentence, textareaElement, alternativeDiv) {
    const editedText = textareaElement.value;
    const pElement = document.createElement('p');
    pElement.innerHTML = editedText;
    textareaElement.replaceWith(pElement); // Replace <textarea> with <p>

    // Save the edited translation to file
    saveTranslationToFile(originalSentence, editedText);

    // Re-add the edit button and remove the save button
    let editButton = alternativeDiv.querySelector('.edit-button');
    if (!editButton) { // If edit button doesn't exist, create it
        editButton = document.createElement('button');
        editButton.className = 'edit-button';
        editButton.textContent = 'Edit';
        // Re-attach the event listener for the re-created edit button
        editButton.addEventListener('click', () => handleEditClick(originalSentence, pElement, alternativeDiv));
        alternativeDiv.appendChild(editButton);
    }

    const saveButton = alternativeDiv.querySelector('.save-button');
    if (saveButton) {
        saveButton.remove(); // Remove the save button
    }
}

/**
 * Sends the original sentence and its translation to the backend to be saved to a file.
 * @param {string} originalSentence - The original sentence.
 * @param {string} translationText - The translated text to save.
 */
function saveTranslationToFile(originalSentence, translationText) {
    fetch('/save_translation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ original_sentence: originalSentence, translation: translationText })
    })
    .then(response => {
        if (response.ok) {
            // Using a custom modal or message box would be better than alert() in a real app
            // For now, sticking to alert() as per previous context, but noting the improvement area.
            alert('Translation saved to file successfully!');
        } else {
            throw new Error('Failed to save translation');
        }
    })
    .catch(error => {
        console.error('Error saving translation:', error);
        alert('Failed to save translation: ' + error.message);
    });
}
