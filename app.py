import os
from flask import Flask, render_template, request, jsonify
from gemini import LLM as GeminiLLM
import json
import re
import xml.etree.ElementTree as ET  # Import for XML parsing
import csv  # Import for CSV parsing

app = Flask(__name__)
llm_instance = GeminiLLM()

# Global variables to track current sentence
current_sentence_index = 0
sentences = []


def load_sentences_from_file():
    """Load and split sentences from source.txt file"""
    global sentences
    try:
        with open(r'Jigokuhen-source.txt', 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # Split by Japanese sentence endings (。！？) optionally followed by whitespace or quotation marks
            # Also handles classical Japanese endings like 。」 or 。』
            # This regex keeps the punctuation with the sentence
            sentences = re.split(r'(?<=[。！？])(?:[」』）\s]*(?=\s*[^」』）\s])|(?<=[。！？])\s*$)', content)
            # Alternative simpler approach for Japanese text:
            # sentences = re.split(r'(?<=[。！？])\s*', content)

            # Filter out empty sentences and clean up
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 1]

            # Additional cleanup: remove sentences that are just punctuation or whitespace
            sentences = [s for s in sentences if re.search(r'[ぁ-んァ-ヶ一-龯]', s)]
        return True
    except FileNotFoundError:
        print("source.txt file not found. Please create it with your source text.")
        return False
    except Exception as e:
        print(f"Error loading sentences: {e}")
        return False


def load_references_from_csv(file_path='glossary.csv'):
    """
    Loads reference data from a CSV file and formats it as a string
    suitable for the prompt's reference section.
    Expected CSV format: Japanese Term,Portuguese Translation
    Example:
    堀川の大殿様,O Grande Senhor de Horikawa (personagem principal)
    良秀,Yoshihide, o Pintor (protagonista)
    """
    references = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) == 2:
                    japanese_term = row[0].strip()
                    portuguese_translation = row[1].strip()
                    references[japanese_term] = portuguese_translation

        # Format the references into the desired string format for the prompt
        # This creates a flat list under 'reference:'
        reference_str = "reference:\n"
        for term, translation in references.items():
            reference_str += f"    - {term}: \"{translation}\"\n"
        return reference_str
    except FileNotFoundError:
        print(f"References CSV file not found at {file_path}. Prompt will not include references.")
        return ""
    except Exception as e:
        print(f"Error loading references from CSV: {e}")
        return ""


@app.route('/')
def index():
    # Load sentences when the app starts
    if not load_sentences_from_file():
        return "Error: source.txt file not found. Please create it with your source text.", 500
    return render_template('index.html')


@app.route('/get_current_sentence', methods=['GET'])
def get_current_sentence():
    """Get the current sentence to translate"""
    global current_sentence_index, sentences

    if current_sentence_index >= len(sentences):
        return jsonify({
            'sentence': '',
            'index': current_sentence_index,
            'total': len(sentences),
            'completed': True
        })

    return jsonify({
        'sentence': sentences[current_sentence_index],
        'index': current_sentence_index,
        'total': len(sentences),
        'completed': False
    })


@app.route('/next_sentence', methods=['POST'])
def next_sentence():
    """Move to the next sentence"""
    global current_sentence_index
    current_sentence_index += 1
    return get_current_sentence()


@app.route('/previous_sentence', methods=['POST'])
def previous_sentence():
    """Move to the previous sentence"""
    global current_sentence_index
    if current_sentence_index > 0:
        current_sentence_index -= 1
    return get_current_sentence()


@app.route('/translate', methods=['POST'])
def translate_text():
    data = request.get_json()
    original_sentence = data.get('original_sentence')
    saved_translations_context = data.get('saved_translations', [])
    llm_instance = GeminiLLM()

    prompt = build_prompt_with_context(original_sentence, saved_translations_context)
    print(prompt)

    try:
        answer = llm_instance.completion(prompt)
        print(answer)
        if "```" in answer:
            answer = "{" + answer.split("```")[1].split("{")[1]
            alternatives = json.loads(answer)["translations"]
        else:
            alternatives = json.loads(answer)["translations"]
        print(str(alternatives))
        if not isinstance(alternatives, list) or len(alternatives) != 4:
            return jsonify({'error': 'LLM did not return the expected format'}), 500
        return jsonify({'alternatives': alternatives})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def build_prompt_with_context(original_sentence, saved_translations):
    context_str = ""
    try:
        with open('translation.txt', 'r', encoding='utf-8') as f:
            context_str = f.read()
    except FileNotFoundError:
        # If translation.txt doesn't exist yet, start with empty context
        context_str = ""

    # Load references from the CSV file
    references_from_csv = load_references_from_csv()

    prompt = f"""{context_str}{references_from_csv}
Considerando as traduções anteriores e a lista de referências, traduza a frase abaixo de 4 formas diferentes considerando as nuances possíveis e as diferenças de interpretação semântica. Pesquise o nome de entidades utilizando blob JSON dentro de um bloco de código como no exemplo abaixo:
```
{{
  "original_phrase": "堀川の大殿様のやうな方は、これまでは固より、後の世には恐らく二人とはいらつしやいますまい。",
  "translations": [
      "Uma pessoa como o senhor feudal de Horikawa, claro que até hoje nunca houve igual, e no futuro, provavelmente, não haverá sequer mais um como ele.",
      "Alguém como o grande senhor de Horikawa — já era raro até agora, e no futuro, é quase certo que não haverá outro com tal dignidade.",
      "Pessoas como o senhor de Horikawa eram raras até hoje, e provavelmente não haverá duas no futuro.",
      "Homens como o nobre de Horikawa — já únicos até agora — jamais dividirão este mundo com um igual em tempos vindouros."
  ]
}}
```
\n\nOriginal sentence: {original_sentence}\n\n
"""
    return prompt


@app.route('/save_translation', methods=['POST'])
def save_translation():
    data = request.get_json()
    original_sentence = data.get('original_sentence')
    translation = data.get('translation')

    # IMPORTANT: The target language (e.g., 'es' for Spanish) is not provided
    # in the original request. For a robust TMX file, you should ideally
    # send this from the client (e.g., `data.get('target_language')`).
    # For this example, we'll hardcode 'es' as the target language for the TMX entry.
    target_language_code = "es"  # Placeholder: consider passing this from the client

    # Validate incoming data
    if not original_sentence or not translation:
        return jsonify({'error': 'Missing original_sentence or translation data'}), 400

    # Define file paths
    txt_file_path = 'translation.txt'
    tmx_file_path = 'translation_memory.tmx'

    try:
        # --- Save translated text to .txt file ---
        # Opens the file in append mode ('a'). If the file doesn't exist, it will be created.
        # Each translation is appended with a space, as per your original request.
        with open(txt_file_path, 'a', encoding='utf-8') as f:
            f.write(f"{translation} ")

        # --- Prepare TMX translation unit (tu) ---
        # This XML snippet represents one translation unit with source (en) and target (dynamic) segments.
        tmx_entry = f"""    <tu>
      <tuv xml:lang="en">
        <seg>{original_sentence}</seg>
      </tuv>
      <tuv xml:lang="{target_language_code}">
        <seg>{translation}</seg>
      </tuv>
    </tu>"""

        # --- Save source and target in .tmx file ---
        # This part handles creating the TMX file with its proper header if it doesn't exist,
        # or appending new translation units to an existing TMX file.
        if not os.path.exists(tmx_file_path):
            # If the TMX file does not exist, create it with the full TMX header and the first entry.
            # The header includes metadata about the translation memory.
            tmx_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4">
  <header
    creationtool="GeminiTranslatorApp"
    creationtoolversion="1.0"
    datatype="plaintext"
    segtype="sentence"
    adminlang="en-us"
    srclang="en"
    o-tmf="PythonFlask"
    o-encoding="UTF-8"
  >
  </header>
  <body>
{tmx_entry}
  </body>
</tmx>"""
            with open(tmx_file_path, 'w', encoding='utf-8') as f:
                f.write(tmx_content)
        else:
            # If the TMX file already exists, we need to insert the new entry
            # before the closing </body> tag to maintain valid XML structure.
            with open(tmx_file_path, 'r+', encoding='utf-8') as f:
                lines = f.readlines()  # Read all existing lines
                f.seek(0)  # Move the file pointer to the beginning
                f.truncate()  # Clear the file content (we'll rewrite it)

                inserted = False
                for line in lines:
                    # Look for the </body> tag and insert the new entry just before it.
                    if '</body>' in line and not inserted:
                        f.write(tmx_entry + "\n")  # Add the new TMX entry, followed by a newline
                        inserted = True
                    f.write(line)  # Write the current line back to the file

                # Fallback: If </body> was not found (e.g., malformed file or first entry),
                # append the entry and ensure closing tags are present.
                if not inserted:
                    f.write(tmx_entry + "\n")
                    # Ensure body and tmx closing tags are present if they were missing
                    if not any('</body>' in l for l in lines):
                        f.write("  </body>\n")
                    if not any('</tmx>' in l for l in lines):
                        f.write("</tmx>\n")

        return jsonify({'success': 'Translation saved successfully to .txt and .tmx'}), 200

    except Exception as e:
        # Catch any exceptions during file operations and return an error message.
        return jsonify({'error': str(e)}), 500


@app.route('/get_translations', methods=['GET'])
def get_translations():
    """
    Reads the translation_memory.tmx file, parses it, and returns
    all stored original and translated sentences.
    """
    tmx_file_path = 'translation_memory.tmx'
    translations = []

    if not os.path.exists(tmx_file_path):
        return jsonify({'message': 'No translation memory file found.'}), 404

    try:
        # Parse the TMX XML file
        tree = ET.parse(tmx_file_path)
        root = tree.getroot()

        # Iterate through each translation unit (tu)
        for tu in root.findall('.//tu'):
            original_seg = None
            translated_seg = None
            original_lang = None
            translated_lang = None

            # Find translation unit variants (tuv)
            for tuv in tu.findall('tuv'):
                lang = tuv.get('{http://www.w3.org/XML/1998/namespace}lang')  # Get xml:lang attribute
                seg = tuv.find('seg')  # Find the segment tag

                if seg is not None:
                    if lang == 'en':  # Assuming 'en' is always the source language
                        original_seg = seg.text
                        original_lang = lang
                    else:  # Assuming any other language is the target language
                        translated_seg = seg.text
                        translated_lang = lang

            if original_seg and translated_seg:
                translations.append({
                    'original_sentence': original_seg,
                    'original_language': original_lang,
                    'translated_sentence': translated_seg,
                    'translated_language': translated_lang
                })

        return jsonify(translations), 200

    except ET.ParseError as e:
        return jsonify({'error': f'Failed to parse TMX file: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5002)
