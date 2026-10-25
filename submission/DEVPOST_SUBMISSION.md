# VeriBar (VeriShield) — NextSpark Hacks submission draft

NextSpark Hacks requires a public source repository, a 1–3 minute explanatory demo, at least one screenshot, and disclosure of technologies, resources, and AI assistance. Check your Devpost form for any additional fields. The published deadline is **October 26, 2026 at 10:00 pm CDT** (October 27 at 8:30 am IST). Confirm the current deadline on the hackathon page before submitting.

## Project name

VeriBar (VeriShield)

## Tagline

A Chrome extension that shows a local GPT-2 text-detector estimate beside web articles.

## Project story

### Inspiration

It is hard to tell what an AI-content score means when a tool shows only a number. We wanted to put the estimate next to the text being read and make the method and limitations visible.

### What it does

VeriBar scans article-like text on web pages and adds a small expandable bar. The bar shows a GPT-2-like score, the method, model confidence, and word count. A corner page index and extension popup summarize the scanned items. New content added to a page can be picked up as it appears. Images, audio, and video are marked **Not analyzed** rather than given an unsupported score.

### How we built it

The Chrome Manifest V3 extension finds readable text and sends it to a FastAPI service running on the user's own computer. The service extracts text from HTML and runs the `openai-community/roberta-base-openai-detector` model with PyTorch and Hugging Face Transformers. If the service cannot respond, the extension displays a separately labeled writing-pattern estimate. The demo includes a local sample page and a 95-second screen recording.

### Who it helps

Readers who want context about a text-detector estimate while reading an article, without sending the article to a hosted VeriBar service.

### Challenges

News sites use very different HTML structures, so the scanner needed to recognize both semantic articles and long text blocks on real pages. We also had to avoid leaving a bar stuck on “Analyzing…” when the local service stalls or a page changes while scanning.

### What we learned and what comes next

The model was trained to distinguish GPT-2 output from WebText, mainly in English. Its score is an estimate, not proof of authorship, a general detector for modern AI writing, or a fact check. Media manipulation and provenance are not analyzed in this version. Future work would require an appropriate, independently evaluated model for each media type and clearer accuracy testing across real sites.

## Built with

Chrome Extension, Manifest V3, JavaScript, Python, FastAPI, PyTorch, Hugging Face Transformers, Beautiful Soup

## Resources and AI assistance

- Pretrained model: `openai-community/roberta-base-openai-detector` from Hugging Face. The model is not our original training work.
- OpenAI Codex assisted with code generation, debugging, test and demo preparation, and documentation. The submitter directed the project concept and reviewed the working prototype.
- The demo page and SVG are sample content created for this project. The prototype does not implement image, audio, or video verification.

## Links to add before submission

- **Code / Try it out:** Public repository URL containing the project source and setup steps in `README.md`. The `veribar-source.zip` bundle is ready to upload if needed, but NextSpark specifically requires a public repository.
- **Demo video:** Upload `submission/veribar-devpost-demo.mp4` to YouTube or Vimeo, then paste its judge-accessible link into Devpost. It is 95 seconds long and has captions explaining the features.
- **Real-site walkthrough:** `submission/veribar-real-site-walkthrough.mp4` is a 102-second captioned video built from actual Chrome captures of VeriBar on Wikipedia's [Photosynthesis](https://en.wikipedia.org/wiki/Photosynthesis) article and an [AP News report on data centers](https://apnews.com/article/data-centers-artificial-intelligence-nimby-tech-b4b0544036989fc33820e8306593aff9). Wikipedia shows a 0% GPT-2-like estimate. AP News shows a 37% estimate on a 40-word text block associated with the lead photo; the article body scored 0%. These are model estimates, not proof of authorship. This is an edited walkthrough of captured screens, not a continuous live recording. Wikipedia page content is available under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); credit the article and its contributors if publishing the video. Credit AP News and link the report as well.
- **Gallery thumbnail:** Upload `submission/veribar-thumbnail.png`.

The local `127.0.0.1` URLs are only available on the computer running the project; they are not public demo links. Judges need to install the extension and run the backend as described in `README.md`.
