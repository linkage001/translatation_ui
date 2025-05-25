document.addEventListener('DOMContentLoaded', () => {
    const translateButton = document.getElementById('translate-button');
    translateButton.addEventListener('click', handleTranslateClick);

    // Display saved translations on page load
    // displaySavedTranslations();
});

async function handleTranslateClick() {
    const originalText = document.getElementById('original-text-input').value;
    const savedTranslations = loadSavedTranslations();
    const errorMessageDiv = document.getElementById('error-message');
    errorMessageDiv.textContent = '';

    try {
        const response = await fetch('/translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ original_sentence: originalText, saved_translations: savedTranslations })
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
