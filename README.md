## AI Mentor - Installation Guide
LLM Wrapper Mentor is an AI-powered teaching assistant that helps mentors generate comprehensive learning materials for technical interview preparation. The tool creates three types of documents for any given topic:

1. **Pre-Class Materials** - Preparation documents for students
2. **In-Class Lesson Plans** - Detailed teaching guides
3. **Post-Class Materials** - Quizzes and practice problems

## Features
- 🚀 AI-powered content generation using GPT-4
- 📚 Three difficulty levels (Beginner, Intermediate, Advanced)
- 📁 Save and load previous generations
- 📥 Export materials as PDF or Markdown
- 🔐 Secure user authentication system
- 💾 Local SQLite database storage

## Prerequisites
- Python 3.8+
- pip package manager
- OpenAI API key (from https://platform.openai.com)

## Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/ayushshankaram/LLM-wrapper-Mentor.git
cd <"to the directory">
```
2. Create and activate virtual environment (not compulsory) :
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Install dependencies:
```bash
streamlit run app.py
```
