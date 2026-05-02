# SpaceWith (Mistral Screen Assistant) ✦

A completely invisible, always-on-top desktop assistant built entirely in Python. It runs locally, uses lightning-fast OCR to extract text from a targeted region of your screen, and uses Mistral AI to give you the direct answer.

## ✨ Features
*   **Targeted Snipping Tool**: Instead of sending entire screenshots to an expensive vision API, you drag a tiny box over your text. 
*   **Locally Run OCR**: The app uses `EasyOCR` to read the text inside your snipped box locally in ~0.1 seconds.
*   **Zero-Vision Guarantee**: By using the `mistral-small-latest` text model instead of vision models, you completely avoid API rate limits and get lightning-fast answers.
*   **Ghost Mode**: The app runs silently in your system tray and is highly transparent when visible.
*   **Single-Instance Lock**: You never see duplicate windows.

---

## ⌨️ Global Shortcuts

These shortcuts work from **anywhere** on your computer, even if the app UI is hidden or you are typing in another app!

*   **`Ctrl + Shift + Z`** : **Trigger the Snipper Tool.** The screen will dim, cursor turns to a crosshair. Drag a box over your question and the answer will instantly generate.
*   **`Ctrl + Shift + Space`** : **Toggle Visibility.** If the app is hidden in the background, this brings it to the front. If it's visible, this hides it cleanly out of sight.

---

## 🚀 How to Launch

1. Go to your Desktop.
2. Double-click the **`run.bat`** script or run `python main.py`.
3. The app will open seamlessly!

---

## 🔑 Configuration

The app uses a hardcoded Mistral API key configured within the application for seamless access without requiring manual entry upon every launch. To change the API key, update it directly in the `OverlayApp` initialization inside `app/overlay.py`.
