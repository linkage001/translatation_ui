from flask import Flask, render_template, request, jsonify
from qwen_local import LLM as QwenLLM
from gemini import LLM as GeminiLLM
import json
import yaml
import os

app = Flask(__name__)
llm_instance = QwenLLM()  # Default to Qwen

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
def translate_text():
    data = request.get_json()
    original_sentence = data.get('original_sentence')
    saved_translations_context = data.get('saved_translations', [])
    model_choice = data.get('model', 'qwen')  # Default to 'qwen' if not provided

    if not original_sentence:
        return jsonify({'error': 'No sentence provided'}), 400

    # Select the appropriate LLM instance based on user choice
    if model_choice == 'gemini':
        llm_instance = GeminiLLM()
    else:
        llm_instance = QwenLLM()

    prompt = build_prompt_with_context(original_sentence, saved_translations_context)
    print(f"Using model: {model_choice}")
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
        if os.path.exists('translations.yaml'):
            with open('translations.yaml', 'r', encoding="utf-8") as f:
                translations = yaml.safe_load(f) or []
                for entry in translations:
                    context_str += f"Original: {entry.get('original', '')}\n"
                    context_str += f"Translation: {entry.get('translation', '')}\n\n"
    except Exception as e:
        print(f"Error reading translations.yaml: {e}")

    with open('glossary.txt', 'r', encoding="utf-8") as f:
        glossary = f.read()

    try:
        with open('user_prompt.txt', 'r', encoding="utf-8") as f:
            user_editable_prompt = f.read().strip()
    except FileNotFoundError:
        user_editable_prompt = """Traduza a frase abaixo de 4 formas diferentes considerando as nuances possíveis e as diferenças de interpretação semântica."""

    prompt = f"""{context_str}{glossary}{user_editable_prompt} Utilize um JSON blob dentro de um code block como no exemplo abaixo:
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

    if not original_sentence or not translation:
        return jsonify({'error': 'Missing data'}), 400

    try:
        translations = []
        if os.path.exists('translations.yaml'):
            with open('translations.yaml', 'r', encoding="utf-8") as f:
                translations = yaml.safe_load(f) or []

        new_entry = {
            'original': original_sentence,
            'translation': translation
        }
        translations.append(new_entry)

        with open('translations.yaml', 'w', encoding="utf-8") as f:
            yaml.dump(translations, f, default_flow_style=False, allow_unicode=True)

        return jsonify({'success': 'Translation saved successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_prompt', methods=['POST'])
def update_prompt():
    data = request.get_json()
    new_prompt = data.get('prompt')

    if not new_prompt:
        return jsonify({'error': 'No prompt provided'}), 400

    try:
        with open('user_prompt.txt', 'w', encoding="utf-8") as f:
            f.write(new_prompt)
        return jsonify({'success': 'Prompt updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_prompt', methods=['GET'])
def get_prompt():
    try:
        with open('user_prompt.txt', 'r', encoding="utf-8") as f:
            prompt = f.read().strip()
        return jsonify({'prompt': prompt}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5002)
