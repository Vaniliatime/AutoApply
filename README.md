# AutoApply

AutoApply is your all-in-one, privacy-friendly platform to supercharge the job search process.  
Generate tailored AI cover letters, keep your applications organized, and never lose track of where you applied — all in your browser, with no data sent to any third-party except OpenAI (for generation).


![screenshot](/screenshots/1.png)
![screenshot](/screenshots/2.png)
![screenshot](/screenshots/3.png)

---

> **Stop losing track of your job applications and let AI help you write better cover letters, faster!**


## Features

- ✍️ **AI Cover Letter Generator:** Enter a job description, get a tailored letter (using OpenAI GPT-3.5/4).
- 📋 **Application Tracker:** Add jobs manually or automatically from the generator.
- 🗂 **History & Edit:** Search, filter, and edit all applications in a powerful dashboard.
- ⏰ **Smart Status:** After 30 days, applications with no feedback are marked "no response" automatically.
- 💾 **Export:** Download your full application history to Excel.
- 🔒 **No secrets in code:** Uses `.env` for API keys (OpenAI).

---

## Why AutoApply?

Tired of copying, pasting, and losing track of your job hunt? AutoApply makes applying and tracking effortless:
- Generate high-quality cover letters with one click.
- Track every application, status, and deadline.
- Keep all your data private and secure.

---

## Quickstart

1. **Clone this repo using git.**

   Use `git clone` to copy this repository to your local machine.

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your `.env` file**

   Create a file called `.env` in the project directory:
   ```
   OPENAI_API_KEY=sk-...your-key...
   ```

4. **Run the app**

   ```bash
   streamlit run app.py
   ```

## File Guide

### `template.pdf` (Cover Letter PDF Template)

`template.pdf` is the visual template used for generating cover letters in PDF format.
It contains your preferred layout, fonts, header, footer, and contact information, but **does not include the cover letter text itself** (which is inserted automatically).

**To create your own template:**
1. Design an A4 PDF in any editor (Word, Google Docs, Canva, Photoshop, etc.), including your contact details, header/footer, logo, or any custom branding.
2. Leave a large empty space for the cover letter body (usually centered on the page).
3. Export as PDF and save as `template.pdf` in your project directory.
4. The app will overlay generated cover letter content into this template when producing final PDFs.

---

### `profile.txt` (Candidate Profile)

`profile.txt` stores your personal profile and skills.  
The content of this file is used to tailor cover letters to your experience.

**How to edit:**
- Open `profile.txt` in any text editor.
- Add a summary of your background, experience, key skills, certifications, and any information that should be reflected in your cover letters.

**Example:**
```
IT Support Specialist with over 5 years of experience (2019–present) in IT Support and Application Support roles, including working with 50,000+ users in international, remote-first environments. Skilled in incident resolution, system troubleshooting (Jira, ServiceNow, Oracle SQL), and Windows Server. Confident with WordPress, Bootstrap, and Tailwind in web-related tasks.

Skills:
- Ticketing (Jira, ServiceNow), Incident Analysis
- Remote Support (AnyDesk), Office 365
- Oracle SQL, C# (Unity), Git
- HTML5 / CSS3 / JS, Bootstrap, Tailwind
- WordPress, Digital Publishing
```
Update this file whenever you want to improve or update your profile for future cover letters.

## Privacy

Your application data is never sent outside your own computer. All files (`applications_history.csv`, `cover-letters/`, `profile.txt`) are local. Only cover letter generation uses OpenAI's API; your key is kept secure via `.env`.


## Contributing

Pull requests and suggestions are welcome!  
If you find a bug or want to request a feature, please open an issue.

## License

MIT

---
## Contact

For feedback, questions, or collaboration, visit my portfolio:  
[kkaszuba.eu](https://kkaszuba.eu)

---


Created by [Krzysztof Kaszuba]  
Inspired by job-seeking frustration 😄
