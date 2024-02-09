import os
import re
from hashlib import md5
from ast import literal_eval
from typing import Any, Optional, List
from langchain.embeddings.bedrock import BedrockEmbeddings
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.bedrock import Bedrock
from utils.utils_os import write_text, read_text

# Color codes for terminal output
c_blue, c_green, c_norm = "\033[94m", "\033[92m", "\033[0m"


# A subclass of Bedrock class to incorporate caching
class BedrockCached(Bedrock):
    # A flag to control verbose logging
    verbose: bool = False

    # Overridden method to handle calls with caching
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        # Formatting the prompt for consistency
        if "Human" not in prompt:
            prompt = "\n\nHuman: " + prompt

        # Ensure the prompt ends with 'Assistant:'
        prompt = prompt.rstrip()
        prompt = re.sub(r"Answer:?$", "Assistant:", prompt)
        if "Assistant" not in prompt:
            prompt = prompt + "\n\nAssistant:"

        # Verbose logging
        if self.verbose:
            print("-" * 80)

            # Shorten the displayed prompt for readability
            short = re.sub(
                r"<document>.*</document>",
                "<document>...</document>",
                prompt,
                flags=re.DOTALL,
            )
            print(c_green, short, c_norm)

        # Generate a unique cache key based on the prompt, stop words, and model ID
        cache_key = "{},{},{}".format(prompt, stop, self.model_id)
        cache_hex = md5(cache_key.encode("utf-8"), usedforsecurity=False).hexdigest()
        cache_file = f"cache/bedrock/{self.model_id}/{cache_hex}.txt"

        # Check if response is already cached
        if os.path.exists(cache_file):
            if self.verbose:
                print(f"Using {self.model_id} cached", cache_file)
            response = read_text(cache_file)
        else:
            # Call the parent class's method if not cached
            if self.verbose:
                print(f"Bedrock {self.model_id} is called")

            response = super()._call(
                prompt=prompt, stop=stop, run_manager=run_manager, **kwargs
            )
            write_text(cache_file, response)

        # Display the response if verbose
        if self.verbose:
            print(c_blue, response, c_norm)
            print("-" * 80)

        return response


# A subclass of BedrockEmbeddings to incorporate caching for embeddings
class BedrockEmbeddingsCached(BedrockEmbeddings):
    verbose: bool = False

    # Overridden method to handle embeddings with caching
    def _embedding_func(self, text: str) -> List[float]:
        """Call out to Bedrock embedding endpoint."""

        # Generate a cache key and file path for the embedding
        cache_key = "{},{}".format(text, self.model_id)
        cache_hex = md5(cache_key.encode("utf-8"), usedforsecurity=False).hexdigest()
        cache_file = f"cache/bedrock/{self.model_id}/{cache_hex}.txt"

        # Check if embedding is already cached
        if os.path.exists(cache_file):
            if self.verbose:
                print(f"Using {self.model_id} cached", cache_file)
            vector = read_text(cache_file)
            return literal_eval(vector)

        # Generate embedding using the parent class's method if not cached
        vector = super()._embedding_func(text)
        write_text(cache_file, str(vector))

        return vector
