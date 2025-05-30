import os
from flask import Flask, render_template, request, jsonify
from gemini import LLM as GeminiLLM
import json
import re
import xml.etree.ElementTree as ET # Import for XML parsing

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

    prompt = f"""{context_str}reference:
  personagens_principais:
    - 堀川の大殿様: "O Grande Senhor de Horikawa (personagem principal)"
    - 良秀: "Yoshihide, o Pintor (protagonista)"
    - 猿秀: "\"Macaco Yoshihide\" (apelido depreciativo)"
    - 若殿様: "O Jovem Senhor (filho do Grande Senhor)"
    - 良秀の娘: "A Filha de Yoshihide"
    - 御姫様: "A Princesa (filha do Grande Senhor)"

  figuras_históricas_chinesas:
    - 始皇帝: "Qin Shi Huang, o Primeiro Imperador da China"
    - 煬帝: "Imperador Yang da Dinastia Sui"
    - 華陀: "Hua Tuo, o Famoso Médico Chinês"

  divindades_e_figuras_budistas:
    - 大威徳明王: "Yamantaka, o Rei da Sabedoria Destruidor da Morte"
    - 不動明王: "Acala, o Rei da Sabedoria Imóvel"
    - 吉祥天: "Lakshmi, a Deusa da Beleza e Fortuna"
    - 稚児文殊: "Manjushri Criança, o Bodhisattva da Sabedoria"
    - 十王: "Os Dez Reis do Inferno"
    - 牛頭馬頭: "Cabeça de Boi e Cabeça de Cavalo (guardiões infernais)"
    - 権者: "Avatar (manifestação divina)"
    - 福徳の大神: "O Grande Deus da Fortuna e Virtude"

  figuras_japonesas:
    - 融の左大臣: "Minamoto no Tōru, o Ministro da Esquerda"
    - 川成: "Kose no Kawanari (pintor do período Heian)"
    - 金岡: "Kose Kanaoka (pintor do período Heian)"
    - 横川の僧都様: "O Bispo de Yokawa"
    - 檜垣の巫女: "A Sacerdotisa de Higaki"

  criaturas_e_seres_míticos:
    - 智羅永寿: "Chira Eijū (nome de um tengu)"
    - 霊狐: "A Raposa Espiritual"
    - 三面六臂の鬼: "O Demônio de Três Faces e Seis Braços"
    - 獅子王: "O Rei Leão"
    - 神巫: "A Sacerdotisa Xamã"

  locais_e_estruturas:
    locais_no_japao:
      - 堀川: "Horikawa (distrito em Kyoto)"
      - 二条大宮: "Nijō Ōmiya (área em Kyoto)"
      - 陸奥の塩竈: "Shiogama na Província de Mutsu"
      - 東三条の河原院: "A Vila Kawara em Higashi Sanjō"
      - 洛中: "Dentro da Capital (Kyoto)"
      - 長良の橋: "A Ponte de Nagara"
      - 丹波の国: "A Província de Tanba"
      - 横川: "Yokawa (no Monte Hiei)"
      - 龍蓋寺: "Templo Ryūgai"
      - 鞍馬: "Monte Kurama"
      - 御池: "O Lago (na propriedade)"
      - 雪解の御所: "O Palácio do Degelo (vila fora da capital)"
    locais_chineses:
      - 震旦: "A China (nome antigo)"
    locais_budistas_ou_infernais:
      - 奈落: "O Inferno, o Abismo"
      - 紅蓮大紅蓮: "Lótus Vermelho e Grande Lótus Vermelho (infernos frios)"
      - 剣山刀樹: "A Montanha de Espadas e as Árvores de Lâminas"

  obras_de_artes:
    - 地獄変の屏風: "O Painel do Inferno"
    - 五趣生死の絵: "A Pintura dos Cinco Reinos da Transmigração"
    - よぢり不動: "O Fudō Torcido (pintura)"

  eventos:
    - 梅花の宴: "O Banquete das Flores de Ameixeira"
    - 陸奥の戦ひ: "A Batalha de Mutsu"

  organizacoes_grupos_sociais_titulos:
    - 月卿雲客: "Os Nobres das Nuvens e da Lua (alta nobreza)"
    - 乞食非人: "Os Mendigos e Párias"
    - 青女房: "As Damas da Corte de Baixo Escalão"
    - 念仏僧: "O Monge do Nembutsu"
    - 侍学生: "O Samurai Erudito"
    - 陰陽師: "O Mestre do Yin-Yang (adivinho da corte)"
    - 生受領: "O Governador Provincial Ganancioso"

  conceitos_filosoficos_ou_religiosos:
    - 五常: "As Cinco Virtudes Constantes (confucionismo: benevolência, retidão, propriedade, sabedoria, confiabilidade)"
    - 五趣生死: "Os Cinco Reinos da Transmigração"

  itens_especificos:
    roupas_e_acessorios:
      - 丁字染の狩衣: "Manto de Caça Tingido com Cravo"
      - 揉烏帽子: "Chapéu Cerimonial Preto Amassado"
      - 紫匂の袿: "Túnica Perfumada de Púrpura"
      - 紅の袙: "Túnica Interior Carmesim"
      - 束帯: "Traje Formal da Corte"
      - 五つ衣: "Vestimenta de Cinco Camadas"
      - 高足駄: "Tamancos de Madeira Altos"
      - 細長: "Veste Longa e Estreita"
      - 浅黄の直衣: "Veste Informal da Corte Amarelo-Clara"
      - 濃い紫の浮紋の指貫: "Calças Púrpura Escura com Padrões em Relevo"
      - 桜の唐衣: "Casaco de Estilo Chinês com Padrão de Cerejeira"
      - 黄金の釵子: "Grampo de Cabelo Dourado"
    objetos:
      - 寒紅梅: "Ramo de Ameixeira Vermelha de Inverno"
      - 蒔絵の高坏: "Pedestal de Laca com Incrustações Douradas"
      - 檳榔毛の車: "Carruagem com Teto de Fibra de Palmeira"
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
    target_language_code = "es" # Placeholder: consider passing this from the client

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
                lines = f.readlines() # Read all existing lines
                f.seek(0)            # Move the file pointer to the beginning
                f.truncate()         # Clear the file content (we'll rewrite it)

                inserted = False
                for line in lines:
                    # Look for the </body> tag and insert the new entry just before it.
                    if '</body>' in line and not inserted:
                        f.write(tmx_entry + "\n") # Add the new TMX entry, followed by a newline
                        inserted = True
                    f.write(line) # Write the current line back to the file

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
                lang = tuv.get('{http://www.w3.org/XML/1998/namespace}lang') # Get xml:lang attribute
                seg = tuv.find('seg') # Find the segment tag

                if seg is not None:
                    if lang == 'en': # Assuming 'en' is always the source language
                        original_seg = seg.text
                        original_lang = lang
                    else: # Assuming any other language is the target language
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
