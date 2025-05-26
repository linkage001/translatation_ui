import requests
import json


class LLM:

    presets = {
        'kindacognizant': {
            'temperature': 1.0,
            'top_k': 0.0,
            'top_p': 1.0,
            'typical_p': 1.0,
            'min_p': 0.1,
            'top_a': 0.0,
            'tfs_z': 1.0,
            'repeat_penalty': 1.0,
        },
        'Divine Intellect': {
            'temperature': 1.31,
            'top_p': 0.14,
            'repetition_penalty': 1.17,
            'top_k': 49,
        }
    }

    def __init__(self,
                 url="http://localhost:8080",  # default: http://127.0.0.1:8080/completion
                 temperature=0.7,  # Adjust the randomness of the generated text (default: 0.8).
                 top_k=40,  # Limit the next token selection to the K most probable tokens (default: 40).
                 top_p=0.95,
                 # Limit the next token selection to a subset of tokens with a cumulative probability above a threshold P (default: 0.95).
                 n_predict=-1,
                 # Set the number of tokens to predict when generating text. **Note:** May exceed the set limit slightly if the last token is a partial multibyte character. When 0, no tokens will be generated but the prompt is evaluated into the cache. (default: -1, -1 = infinity).
                 n_keep=-1,
                 # Specify the number of tokens from the initial prompt to retain when the model resets its internal context. By default, this value is set to 0 (meaning no tokens are kept). Use `-1` to retain all tokens from the initial prompt.
                 stream=False,
                 # It allows receiving each predicted token in real-time instead of waiting for the completion to finish. To enable this, set to `true`.
                 stop=[],
                 # Specify a JSON array of stopping strings. These words will not be included in the completion, so make sure to add them to the prompt for the next iteration (default: []).
                 tfs_z=1.0,  # Enable tail free sampling with parameter z (default: 1.0, 1.0 = disabled).
                 typical_p=1.0,  # Enable locally typical sampling with parameter p (default: 1.0, 1.0 = disabled).
                 repeat_penalty=1.1,  # Control the repetition of token sequences in the generated text (default: 1.1).
                 repeat_last_n=64,
                 # Last n tokens to consider for penalizing repetition (default: 64, 0 = disabled, -1 = ctx-size).
                 penalize_nl=True,  # Penalize newline tokens when applying the repeat penalty (default: true).
                 presence_penalty=0.0,  # Repeat alpha presence penalty (default: 0.0, 0.0 = disabled).
                 frequency_penalty=0.0,  # Repeat alpha frequency penalty (default: 0.0, 0.0 = disabled);
                 mirostat=0,
                 # Enable Mirostat sampling, controlling perplexity during text generation (default: 0, 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0).
                 mirostat_tau=5.0,  # Set the Mirostat target entropy, parameter tau (default: 5.0).
                 mirostat_eta=0.1,  # Set the Mirostat learning rate, parameter eta (default: 0.1).
                 grammar="",  # Set grammar for grammar-based sampling (default: no grammar)
                 seed=-1,  # Set the random number generator (RNG) seed (default: -1, -1 = random seed).
                 ignore_eos=False,  # Ignore end of stream token and continue generating (default: false).
                 logit_bias=[],
                 # Modify the likelihood of a token appearing in the generated text completion. For example, use `"logit_bias": [[15043,1.0]]` to increase the likelihood of the token 'Hello', or `"logit_bias": [[15043,-1.0]]` to decrease its likelihood. Setting the value to false, `"logit_bias": [[15043,false]]` ensures that the token `Hello` is never produced (default: []).
                 n_probs=0,
                 # If greater than 0, the response also contains the probabilities of top N tokens for each generated token (default: 0)
                 ):

        self.url = url
        self.temperature = temperature
        self.top_k = top_k
        self.top_p = top_p
        self.n_predict = n_predict
        self.n_keep = n_keep
        self.stream = stream
        self.stop = stop
        self.tfs_z = tfs_z
        self.typical_p = typical_p
        self.repeat_penalty = repeat_penalty
        self.repeat_last_n = repeat_last_n
        self.penalize_nl = penalize_nl
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.mirostat = mirostat
        self.mirostat_tau = mirostat_tau
        self.mirostat_eta = mirostat_eta
        self.grammar = grammar
        self.seed = seed
        self.ignore_eos = ignore_eos
        self.logit_bias = logit_bias
        self.n_probs = n_probs

    def completion(self, prompt, preset='', callback='', is_question=True):
        if is_question:
            prompt = f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant"
        """Continue the text in `prompt`. Add user/assistant tags by default. If you want to use simple completion, 
        set is_question to False.
        `callback` is called by callback(b'data: {"content":"token","stop":false}').
        Return is like the following:
            {
                "content": " I have used the following command, but it doesn't",
                "generation_settings": {
                    "frequency_penalty": 0.0,
                    "grammar": "",
                    "ignore_eos": false,
                    "logit_bias": [],
                    "mirostat": 0,
                    "mirostat_eta": 0.10000000149011612,
                    "mirostat_tau": 5.0,
                    "model": "./models/synthia-7b-v1.3.Q6_K.gguf",
                    "n_ctx": 2048,
                    "n_keep": 0,
                    "n_predict": 10,
                    "n_probs": 0,
                    "penalize_nl": true,
                    "presence_penalty": 0.0,
                    "repeat_last_n": 64,
                    "repeat_penalty": 1.100000023841858,
                    "seed": 4294967295,
                    "stop": [],
                    "stream": false,
                    "temp": 0.800000011920929,
                    "tfs_z": 1.0,
                    "top_k": 40,
                    "top_p": 0.949999988079071,
                    "typical_p": 1.0
                },
                "model": "./models/synthia-7b-v1.3.Q6_K.gguf",
                "prompt": "What is the command on ubuntu to show the desktop?",
                "stop": true,
                "stopped_eos": false,
                "stopped_limit": true,
                "stopped_word": false,
                "stopping_word": "",
                "timings": {
                    "predicted_ms": 1602.354,
                    "predicted_n": 10,
                    "predicted_per_second": 6.240818196228798,
                    "predicted_per_token_ms": 160.2354,
                    "prompt_ms": 0.0,
                    "prompt_n": 1,
                    "prompt_per_second": null,
                    "prompt_per_token_ms": 0.0
                },
                "tokens_cached": 23,
                "tokens_evaluated": 14,
                "tokens_predicted": 10,
                "truncated": false
            } """
        if callback == '':
            callback = None

        data = {
            "prompt": prompt,
            "temperature": self.temperature,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "n_predict": self.n_predict,
            "n_keep": self.n_keep,
            "stream": self.stream,
            "stop": self.stop,
            "tfs_z": self.tfs_z,
            "typical_p": self.typical_p,
            "repeat_penalty": self.repeat_penalty,
            "repeat_last_n": self.repeat_last_n,
            "penalize_nl": self.penalize_nl,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty,
            "mirostat": self.mirostat,
            "mirostat_tau": self.mirostat_tau,
            "mirostat_eta": self.mirostat_eta,
            "grammar": self.grammar,
            "seed": self.seed,
            "ignore_eos": self.ignore_eos,
            "logit_bias": self.logit_bias,
            "cache_prompt": True,
            "n_probs": self.n_probs
        }

        if preset != '':
            data.update(self.presets[preset])

        response = requests.post(self.url + '/completion', headers={"Content-Type": "application/json"}, data=json.dumps(data))

        if response.status_code == 200:
            if callback is not None and callable(callback):
                for line in response.iter_lines():
                    if line:
                        callback(line)
                return None

            else:
                return response.json()["content"].split("</think>")[1].strip() if "</think>" in response.json()["content"] else response.json()["content"]

        else:
            return None