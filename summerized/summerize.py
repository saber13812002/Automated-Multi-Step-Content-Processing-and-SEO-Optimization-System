import sys
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

def summarize(text: str, model_name: str) -> str:
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    
    summarizer = pipeline("summarization", model=model, tokenizer=tokenizer)
    summary = summarizer(text, max_length=200, min_length=30, do_sample=False)
    
    return summary[0]['summary_text']

def main():
    if len(sys.argv) < 3:
        print("Usage: python summarize.py <path_to_file> <language>")
        print("Language options: fa (Persian) | en (English)")
        sys.exit(1)

    path_to_file = sys.argv[1]
    lang = sys.argv[2].lower()

    try:
        with open(path_to_file, "r", encoding="utf-8") as file:
            text = file.read()
    except FileNotFoundError:
        print(f"Error: File not found at path '{path_to_file}'")
        sys.exit(1)

    if lang == "fa":
        model_name = "m3hrdadfi/bart-base-parsinlu-summary"
    elif lang == "en":
        model_name = "facebook/bart-large-cnn"
    else:
        print("Invalid language. Use 'fa' for Persian or 'en' for English.")
        sys.exit(1)

    try:
        print("🔹 Original Text:\n", text[:1000] + ('...' if len(text) > 1000 else ''))
        print("\n🔹 Summary:\n", summarize(text, model_name))
    except Exception as e:
        print(f"Error during summarization: {e}")

if __name__ == "__main__":
    main()
