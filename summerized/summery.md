# Text Summarizer (Persian & English)

A simple Python script to summarize Persian and English text files using Hugging Face transformer models.

## ✨ Features

- Summarizes long texts into concise summaries
- Supports **Persian** (`fa`) and **English** (`en`)
- Automatically loads models:
  - `facebook/bart-large-cnn` for English
  - `m3hrdadfi/bart-base-parsinlu-summary` for Persian

## 🛠 Installation

```bash
pip install transformers torch sentencepiece
```

## 📦 Usage

```bash
python summarize.py <path_to_file> <language>


Language codes:
fa – Persian

en – English

Example:
bash
Copy
Edit
python summarize.py input_fa.txt fa
python summarize.py input_en.txt en
📁 Example input (input_fa.txt):
Copy
Edit
قانون اساسی جمهوری اسلامی ایران در سال ۱۳۵۸ به تصویب رسید و در سال ۱۳۶۸ مورد بازنگری قرار گرفت...
📦 Requirements
Python 3.7+

transformers

torch

sentencepiece


MIT License
