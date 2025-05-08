from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

def summarize(text, model_name):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    summarizer = pipeline("summarization", model=model, tokenizer=tokenizer)
    summary = summarizer(text, max_length=200, min_length=30, do_sample=False)

    return summary[0]['summary_text']


# # مثال انگلیسی
# english_text = """
# Facebook is an American online social media and social networking service owned by Meta Platforms. 
# Founded in 2004 by Mark Zuckerberg with fellow Harvard College students, its name comes from the face book directories often given to American university students. 
# Membership was initially limited to Harvard students, gradually expanding to other North American universities and, since 2006, to anyone over 13 years old.
# """
# print("🔹 English Summary:\n", summarize(english_text, "facebook/bart-large-cnn"))

# # مثال فارسی
# persian_text = """
# قانون اساسی جمهوری اسلامی ایران در سال ۱۳۵۸ به تصویب رسید و در سال ۱۳۶۸ مورد بازنگری قرار گرفت. 
# این قانون اصول و مبانی حکومت را مشخص می‌کند و ساختار قوا، حقوق ملت و وظایف دولت را تعیین می‌کند. 
# با گذشت بیش از چهار دهه از تصویب آن، نیاز به تفسیر و بازنگری در برخی اصول آن احساس می‌شود.
# """
# print("\n🔹 خلاصه فارسی:\n", summarize(persian_text, "m3hrdadfi/bart-base-parsinlu-summary"))
