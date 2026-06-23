# Deploy Live on Streamlit Cloud

Host the web dashboard for free at a public URL.

---

## Prerequisites

- Repo on GitHub: [Gesture-based-Presentation-System](https://github.com/iSarthakKaushal/Gesture-based-Presentation-System)
- Free [Streamlit Cloud](https://share.streamlit.io) account (GitHub sign-in)

---

## One-Click Deploy

**[Deploy on Streamlit Cloud](https://share.streamlit.io/deploy?repository=https://github.com/iSarthakKaushal/Gesture-based-Presentation-System&branch=main&mainModule=dashboard.py)**

---

## Manual Deploy

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **Create app**
3. Repository: `iSarthakKaushal/Gesture-based-Presentation-System`
4. Main file: `dashboard.py`
5. Branch: `main`
6. Click **Deploy**

Your URL: `https://<app-name>.streamlit.app`

---

## What Works on Cloud

| Feature | Works? |
|---------|--------|
| PNG/JPG slide upload | Yes |
| Webcam gestures | Yes |
| Drawing + navigation | Yes |
| `.pptx` conversion | No (needs Windows + PowerPoint) |

**Tip:** Export PowerPoint as PNG and upload images.

---

## Auto-Redeploy

Every push to `main` redeploys automatically:

```bash
git push
```

---

## After Deploy

Update the live URL in `README.md` with your actual Streamlit app name.
