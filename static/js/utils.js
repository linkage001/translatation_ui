function highlightDifferences(baseString, comparisonStringsArray) {
    const diffMatchPatch = new diff_match_patch();
    let highlightedTexts = [];

    for (let i = 0; i < comparisonStringsArray.length; i++) {
        const diffs = diffMatchPatch.diff_main(baseString, comparisonStringsArray[i]);
        diffMatchPatch.diff_cleanupSemantic(diffs);
        const highlighted = diffs.map(part => {
            if (part[0] === DIFF_DELETE) {
                return `<span class="diff-delete">${part[1]}</span>`;
            } else if (part[0] === DIFF_INSERT) {
                return `<span class="diff-insert">${part[1]}</span>`;
            } else {
                return part[1];
            }
        }).join('');
        highlightedTexts.push(highlighted);
    }

    return highlightedTexts;
}


function loadSavedTranslations() {
    const translations = localStorage.getItem('savedTranslations');
    return translations ? JSON.parse(translations) : [];
}

function displaySavedTranslations() {
    const translations = loadSavedTranslations();
    if (translations.length > 0) {
        console.log("Saved translations (being sent as context):", translations);
    } else {
        console.log("No saved translations yet.");
    }
}

// Include diff_match_patch library
const diff_match_patch = (function() {
    // diff_match_patch code here (can be loaded from a CDN or included directly)
    // For brevity, this example assumes the library is included elsewhere
})();
