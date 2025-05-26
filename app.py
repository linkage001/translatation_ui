from flask import Flask, render_template, request, jsonify
from qwen_local import LLM
import json

app = Flask(__name__)
llm_instance = LLM()  # Initialize with None or appropriate arguments

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
def translate_text():
    data = request.get_json()
    original_sentence = data.get('original_sentence')
    saved_translations_context = data.get('saved_translations', [])

    if not original_sentence:
        return jsonify({'error': 'No sentence provided'}), 400

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
    with open('translation.txt', 'r') as f:
        context_str = f.read()
    prompt = f"""{context_str}Considering the examples above, translate the following sentence into 4 different variations, showing subtle nuances where possible using a JSON blob inside a code block like the example below:
```    
{{
  "original_phrase": "The big red fox ate a steak at McDonalds.",
  "translations": [
      "A grande raposa vermelha comeu um bife no McDonald's.",
      "A raposa grande e ruiva comeu um bife no McDonald's.",
      "A raposa vermelha e grande devorou um filé no McDonald's.",
      "Uma raposa grande, de pelo avermelhado, comeu um bife no McDonald's."
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
        with open('translation.txt', 'a') as f:
            f.write(f"Original: {original_sentence}\n")
            f.write(f"Translation: {translation}\n\n")
        return jsonify({'success': 'Translation saved successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
