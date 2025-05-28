

import google.generativeai as genai  # pip install google-generativeai
from google.api_core import exceptions as google_exceptions # Import for specific exception handling
import time
from dotenv import dotenv_values

class LLM:
    
    config = dotenv_values(".env")  # config = {"USER": "foo", "EMAIL": "foo@example.org"}
    api_key = config["GOOGLE_API_KEY"]
    MODEL_NAME = "gemini-2.5-flash-preview-05-20"
    MODEL_FALLBACK_NAME = "gemini-2.0-flash-001" # A model that might have different limits or capabilities
    HYPOTHETICAL_MODEL_LIMIT_PRIMARY = 245000  # Primary model's hypothetical token limit for the whole prompt
    HYPOTHETICAL_MODEL_LIMIT_FALLBACK = 1000000 # Fallback model's hypothetical token limit
    RETRY_DELAY_SECONDS = 3
    MAX_TEXT_FALLBACK_RETRIES = 1
    
    genai.configure(api_key=api_key)

    def list_models(self):
        from google import genai as genai_models
        
        models = list()

        client = genai_models.Client(api_key=self.api_key)

        for model in client.models.list():
            models.append(model)

        return models

    def print_models(self):
        models = self.list_models()
        for model in models:
            print(f"{model.input_token_limit} {model.display_name} {model.name}")

    
    def get_token_count(self, model_instance, content_parts):
        """Counts tokens for the given content parts using the specified model instance."""
        try:
            # Ensure content_parts is suitable for count_tokens
            # count_tokens expects `contents` which can be str | File | Iterable[str | File | Part]`
            # If content_parts is already a list like [question, file_or_text_content], it's fine.
            return model_instance.count_tokens(content_parts).total_tokens
        except Exception as e:
            print(f"  Warning: Could not count tokens for model {model_instance.model_name}. Error: {e}")
            return float('inf') # Assume worst case if count fails

    def select_model_based_on_tokens(self, primary_model, fallback_model, prompt_parts, primary_limit, fallback_limit):
        """Selects a model based on token count and defined limits."""
        token_count_primary = self.get_token_count(primary_model, prompt_parts)
        if token_count_primary <= primary_limit:
            print(f"  Prompt fits primary model {primary_model.model_name} ({token_count_primary} tokens, limit: {primary_limit}).")
            return primary_model, token_count_primary
        else:
            print(f"  Prompt ({token_count_primary} tokens) too large for primary model {primary_model.model_name} (limit: {primary_limit}). Checking fallback.")
            token_count_fallback = self.get_token_count(fallback_model, prompt_parts)
            if token_count_fallback <= fallback_limit:
                print(f"  Prompt fits fallback model {fallback_model.model_name} ({token_count_fallback} tokens, limit: {fallback_limit}).")
                return fallback_model, token_count_fallback
            else:
                print(f"  Prompt too large for both primary ({token_count_primary} tokens, limit: {primary_limit}) and fallback ({token_count_fallback} tokens, limit: {fallback_limit}) models.")
                return None, token_count_primary # Return None and primary's count for logging

    def ask_gemini_with_text_retry(self, chosen_model, question, text_content, pdf_name_for_logging):
        """Asks Gemini with extracted text, includes retry logic for 429 errors, using the chosen model."""
        for attempt in range(self.MAX_TEXT_FALLBACK_RETRIES + 1):
            try:
                prompt_parts_text = [question, text_content]
                print(f"  Asking Gemini with extracted text using model {chosen_model.model_name} (attempt {attempt + 1})...")
                response = chosen_model.generate_content(prompt_parts_text)
                return response.text
            except google_exceptions.ResourceExhausted as e_rate:
                print(f"  Rate limit hit (429) for {chosen_model.model_name}: {e_rate}.")
                if attempt < self.MAX_TEXT_FALLBACK_RETRIES:
                    print(f"  Waiting {self.RETRY_DELAY_SECONDS}s and retrying (attempt {attempt + 2}/{self.MAX_TEXT_FALLBACK_RETRIES + 1})...")
                    time.sleep(self.RETRY_DELAY_SECONDS)
                else:
                    print(f"  Max retries reached after rate limit with {chosen_model.model_name}.")
                    raise
            except Exception as e_text_processing:
                print(f"  Error asking Gemini using {chosen_model.model_name}: {e_text_processing}")
                raise
        return None # Should only be reached if MAX_TEXT_FALLBACK_RETRIES is < 0 (which it isn't)

    def completion(self, prompt):
        
        question = prompt

        primary_model_instance = genai.GenerativeModel(self.MODEL_NAME)
        fallback_model_instance = genai.GenerativeModel(self.MODEL_FALLBACK_NAME)

        # print(f"Using primary model: {self.MODEL_NAME}")
        # print(f"Using fallback model: {self.MODEL_FALLBACK_NAME}")
        # print(f"Primary model hypothetical token limit: {self.HYPOTHETICAL_MODEL_LIMIT_PRIMARY}")
        # print(f"Fallback model hypothetical token limit: {self.HYPOTHETICAL_MODEL_LIMIT_FALLBACK}")

        try:

                prompt_parts_file = [question]
                chosen_model_for_file_api, _ = self.select_model_based_on_tokens(
                    primary_model_instance, fallback_model_instance, prompt_parts_file,
                    self.HYPOTHETICAL_MODEL_LIMIT_PRIMARY, self.HYPOTHETICAL_MODEL_LIMIT_FALLBACK
                )

                if chosen_model_for_file_api:
                    print(f"  Asking Gemini using model: {chosen_model_for_file_api.model_name}...")
                    final_model_used_name = chosen_model_for_file_api.model_name
                    response = chosen_model_for_file_api.generate_content(prompt_parts_file)
                    answer_text = response.text

        except google_exceptions.ResourceExhausted as e_rate_limit:
            print(f"  Rate limit hit (429) during processing: {e_rate_limit}.")
            prompt_parts_text = [question]
            # Check if fallback model can handle the text content
            token_count_fallback_text = self.get_token_count(fallback_model_instance, prompt_parts_text)
            if token_count_fallback_text <= self.HYPOTHETICAL_MODEL_LIMIT_FALLBACK:
                try:
                    final_model_used_name = fallback_model_instance.model_name
                    answer_text = self.ask_gemini_with_text_retry(fallback_model_instance, question)
                except Exception as e_text_fallback_after_rate_limit:
                    answer_text = f"Error: Text fallback also failed after initial rate limit. Details: {e_text_fallback_after_rate_limit}"
            else:
                answer_text = f"Error: Text content ({token_count_fallback_text} tokens) too large for fallback model after rate limit."


        except google_exceptions.InvalidArgument as e_invalid_arg:
            print(f"  InvalidArgument error processing (possibly with File API): {e_invalid_arg}.")
            print(f"  Attempting text extraction fallback...")
            prompt_parts_text = [question]
            chosen_model, _ = self.select_model_based_on_tokens(
                primary_model_instance, fallback_model_instance, prompt_parts_text,
                self.HYPOTHETICAL_MODEL_LIMIT_PRIMARY, self.HYPOTHETICAL_MODEL_LIMIT_FALLBACK
            )
            if chosen_model:
                final_model_used_name = chosen_model.model_name
                try:
                    answer_text = self.ask_gemini_with_text_retry(chosen_model, question)
                except Exception as e_text_fallback_after_invalid_arg:
                    answer_text = f"Error: Text fallback failed after InvalidArgument. Details: {e_text_fallback_after_invalid_arg}"
            else:
                answer_text = f"Error: Text content (after InvalidArgument) too large."
           
        except Exception as e_general:
            print(f"  A general error occurred while processing prompt: {e_general}")
            answer_text = f"Error: A general error occurred. Details: {e_general}"

        finally:
            return answer_text


