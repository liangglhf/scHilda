""" This file contains the code for calling all LLM APIs. """
import tiktoken
import anthropic
from openai import OpenAI
import yaml

enc = tiktoken.get_encoding("cl100k_base")
anthropic_client = None
openai_client = None
deepseek_client = None

class TooLongPromptError(Exception):
    """Exception raised for errors in the prompt length."""
    def __init__(self, message="The prompt is too long."):
        self.message = message
        super().__init__(self.message)

class LLMError(Exception):
    """Exception raised for errors related to the LLM."""
    def __init__(self, message="An error occurred with the LLM."):
        self.message = message
        super().__init__(self.message)

def log_to_file(log_file, prompt, completion, model):
    """ Log the prompt and completion to a file."""
    with open(log_file, "a", encoding="utf-8") as f:
        f.write("\n===================prompt=====================\n")
        f.write(f"Human: {prompt}\n\nAssistant:")
        num_prompt_tokens = len(enc.encode(prompt))
        f.write(f"\n==================={model} response =====================\n")
        f.write(completion)
        num_sample_tokens = len(enc.encode(completion))
        f.write("\n===================tokens=====================\n")
        f.write(f"Number of prompt tokens: {num_prompt_tokens}\n")
        f.write(f"Number of sampled tokens: {num_sample_tokens}\n")
        f.write("\n\n")

def get_anthropic_client():
    """ Lazily initialize and return the Anthropic client."""
    global anthropic_client
    if anthropic_client is None:
        try:
            anthropic_client = anthropic.Client(api_key=open("APIs/claude_api_key.txt").read().strip())
        except Exception as e:
            print(f"Error initializing Anthropic client: {e}")
            anthropic_client = None
    return anthropic_client

def get_openai_client():
    """ Lazily initialize and return the OpenAI client."""
    global openai_client
    if openai_client is None:
        try:
            openai_client = OpenAI(
                api_key=open("APIs/openai_api_key (myself).txt").read().strip(),
                timeout=60*10,
            )
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")
            openai_client = None
    return openai_client

def get_deepseek_client():
    """ Lazily initialize and return the DeepSeek client."""
    global deepseek_client
    if deepseek_client is None:
        try:
            key = yaml.safe_load(open("APIs/deepseek_api_key.yaml").read())
            deepseek_client = OpenAI(
                base_url=key["base_url"],
                api_key=key["api_key"]
            )
        except Exception as e:
            print(f"Error initializing DeepSeek client: {e}")
            deepseek_client = None
    return deepseek_client

def complete_text_claude(prompt, stop_sequences=[anthropic.HUMAN_PROMPT], model="claude-3.5-sonnet", max_tokens_to_sample = 2000, temperature=0.5, log_file=None, **kwargs):
    """ Call the Claude API to complete a prompt."""
    client = get_anthropic_client()
    if not client:
        raise LLMError("Anthropic client is not available.")
    try:
        message = client.messages.create(
            model=model, max_tokens=max_tokens_to_sample, temperature=temperature,
            messages=[{"role": "user", "content": prompt}], stop_sequences=stop_sequences, **kwargs
        )
        completion = message.content[0].text
        if log_file is not None:
            log_to_file(log_file, prompt, completion, model)
        return completion
    except anthropic.APIStatusError as e:
        print(e); raise TooLongPromptError()
    except Exception as e:
        raise LLMError(str(e))

def complete_text_openai(prompt, model="o3-mini", temperature=0.5, log_file=None, **kwargs):
    """ Call the OpenAI API to complete a prompt."""
    client = get_openai_client()
    if not client:
        raise LLMError("OpenAI client is not available.")
    
    if model == "gpt5-nano":
        temperature = 1
        
    raw_request = {"model": model, "temperature": temperature, **kwargs}
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(**{"messages": messages, **raw_request})
    completion = response.choices[0].message.content
        
    if log_file is not None:
        log_to_file(log_file, prompt, completion, model)
    return completion

def complete_text_deepseek(prompt, model="deepseek-chat", temperature=0.5, log_file=None, stream=False, **kwargs):
    """ Call the DeepSeek API to complete a prompt."""
    client = get_deepseek_client()
    if not client:
        raise LLMError("DeepSeek client is not available.")
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": prompt}],
                temperature=temperature, stream=stream, **kwargs
            )
            completion = response.choices[0].message.content
            if log_file is not None:
                log_to_file(log_file, prompt, completion, model)
            return completion
        except Exception as e:
            print(f"Attempt {attempt+1} failed with error: {e}. Retrying...")
    raise LLMError("Failed to complete the prompt after multiple attempts.")

def complete_text(prompt, model, log_file=None, **kwargs):
    """ Complete text using the specified model with appropriate API. """
    completion = ""
    if model.startswith("claude"):
        completion = complete_text_claude(prompt, log_file=log_file, model=model, **kwargs)
    elif model.startswith("o1") or model.startswith("o3") or model == "gpt5-nano":
        completion = complete_text_openai(prompt, log_file=log_file, model=model, **kwargs)
    elif model.startswith("deepseek-chat"):
        completion = complete_text_deepseek(prompt, log_file=log_file, model=model, **kwargs)
    else:
        print(f"Warning: Model '{model}' not found in LLM.py. Returning empty string.")

    return completion