document.addEventListener('DOMContentLoaded', () => {
    const translateButton = document.getElementById('translate-button');
    translateButton.addEventListener('click', handleTranslateClick);

    const updatePromptButton = document.getElementById('update-prompt-button');
    updatePromptButton.addEventListener('click', handleUpdatePromptClick);

    // Load existing prompt if available
    loadPrompt();

    // Load translations
    loadTranslations();
});

async function handleTranslateClick() {
    const originalText = document.getElementById('original-text-input').value;
    const savedTranslations = loadSavedTranslations();
    const errorMessageDiv = document.getElementById('error-message');
    errorMessageDiv.textContent = '';

    // Get the selected model
    const modelRadios = document.getElementsByName('model');
    let selectedModel = 'qwen'; // Default value
    for (let radio of modelRadios) {
        if (radio.checked) {
            selectedModel = radio.value;
            break;
        }
    }

    try {
        const response = await fetch('/translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                original_sentence: originalText,
                saved_translations: savedTranslations,
                model: selectedModel
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

function displayAlternatives(originalSentence, alternativesArray) {
    const container = document.getElementById('alternatives-container');
    container.innerHTML = '';

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
        editButton.addEventListener('click', () => handleEditClick(index, text, div));
        div.appendChild(editButton);


        const saveButton = document.createElement('button');
        saveButton.className = 'save-button';
        saveButton.textContent = 'Save to File';
        saveButton.addEventListener('click', () => saveTranslationToFile(originalSentence, alternative));
        div.appendChild(saveButton);

        container.appendChild(div);
    });
}

function handleEditClick(index, currentTextElement, alternativeDiv) {
    // Remove any existing save button
    const existingSaveButton = alternativeDiv.querySelector('.save-button');
    if (existingSaveButton) {
        existingSaveButton.remove();
    }

    const originalText = currentTextElement.innerHTML;
    const textarea = document.createElement('textarea');
    textarea.value = originalText;
    textarea.rows = 3;

    currentTextElement.replaceWith(textarea);
    textarea.focus();

    const saveButton = document.createElement('button');
    saveButton.className = 'save-button';
    saveButton.textContent = 'Save to File';
    saveButton.addEventListener('click', () => handleSaveEditClick(index, textarea, originalText, alternativeDiv));
    alternativeDiv.appendChild(saveButton);
}

function handleSaveEditClick(index, textareaElement, originalSentence, alternativeDiv) {
    const editedText = textareaElement.value;
    const pElement = document.createElement('p');
    pElement.innerHTML = editedText;
    textareaElement.replaceWith(pElement);

    // Save the edited translation to file
    saveTranslationToFile(originalSentence, editedText);

    const saveButton = alternativeDiv.querySelector('.save-button');
    saveButton.remove();
}

function saveTranslationToFile(originalSentence, translationText) {
    fetch('/save_translation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ original_sentence: originalSentence, translation: translationText })
    })
    .then(response => {
        if (response.ok) {
            alert('Translation saved to file successfully!');
        } else {
            throw new Error('Failed to save translation');
        }
    })
    .catch(error => {
        console.error('Error saving translation:', error);
        alert('Failed to save translation');
    });
}

async function handleUpdatePromptClick() {
    const promptInput = document.getElementById('prompt-input').value;
    const statusMessage = document.getElementById('prompt-status-message');
    statusMessage.textContent = '';

    if (!promptInput.trim()) {
        statusMessage.textContent = 'Prompt cannot be empty';
        statusMessage.style.color = 'red';
        return;
    }

    try {
        const response = await fetch('/update_prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: promptInput })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Server error: ${response.status}`);
        }

        const data = await response.json();
        if (data.success) {
            statusMessage.textContent = 'Prompt updated successfully';
            // Update the display
            loadPrompt();
        }
    } catch (error) {
        console.error("Error updating prompt:", error);
        statusMessage.textContent = error.message;
        statusMessage.style.color = 'red';
    }
}

function loadPrompt() {
    fetch('/get_prompt')
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to load prompt');
        }
        return response.json();
    })
    .then(data => {
        if (data.prompt) {
            document.getElementById('prompt-input').value = data.prompt;
        }
    })
    .catch(error => {
        console.error('Error loading prompt:', error);
    });
}

function loadTranslations() {
    fetch('/get_translations')
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to load translations');
        }
        return response.json();
    })
    .then(data => {
        if (data.translations) {
            displayTranslations(data.translations);
        }
    })
    .catch(error => {
        console.error('Error loading translations:', error);
    });
}

function displayTranslations(translations) {
    const container = document.getElementById('translations-list');
    container.innerHTML = '';

    translations.forEach((translation, index) => {
        const div = document.createElement('div');
        div.className = 'translation';

        const original = document.createElement('p');
        original.innerHTML = `<strong>Original:</strong> ${translation.original}`;
        div.appendChild(original);

        const translationText = document.createElement('p');
        translationText.innerHTML = `<strong>Translation:</strong> ${translation.translation}`;
        div.appendChild(translationText);

        const editButton = document.createElement('button');
        editButton.className = 'edit-button';
        editButton.textContent = 'Edit';
        editButton.addEventListener('click', () => handleTranslationEditClick(index, translationText, div));
        div.appendChild(editButton);

        container.appendChild(div);
    });
}

function handleTranslationEditClick(index, currentTextElement, translationDiv) {
    // Remove any existing save button
    const existingSaveButton = translationDiv.querySelector('.save-button');
    if (existingSaveButton) {
        existingSaveButton.remove();
    }

    const originalText = currentTextElement.innerHTML;
    const textarea = document.createElement('textarea');
    textarea.value = originalText.match(/<strong>Translation:<\/strong> (.+)/)[1];
    textarea.rows = 3;

    currentTextElement.replaceWith(textarea);
    textarea.focus();

    const saveButton = document.createElement('button');
    saveButton.className = 'save-button';
    saveButton.textContent = 'Save to File';
    saveButton.addEventListener('click', () => handleTranslationSaveEditClick(index, textarea, originalText, translationDiv));
    translationDiv.appendChild(saveButton);
}

function handleTranslationSaveEditClick(index, textareaElement, originalSentenceHtml, translationDiv) {
    const editedText = textareaElement.value;
    const pElement = document.createElement('p');
    pElement.innerHTML = `<strong>Translation:</strong> ${editedText}`;
    textareaElement.replaceWith(pElement);

    // Extract original sentence from the first child element (original paragraph)
    const originalSentence = translationDiv.querySelector('p:first-child').innerHTML.match(/<strong>Original:<\/strong> (.+)/)[1];

    // Save the edited translation to file
    saveTranslationToFile(originalSentence, editedText);

    const saveButton = translationDiv.querySelector('.save-button');
    saveButton.remove();
}
