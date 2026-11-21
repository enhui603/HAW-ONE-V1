# HAW-ONE

## Folder
app.py, store.py, ui.py, i18n.py, hawkers.py, pages_*.py, requirements.txt, invite_codes.json,
hawker_centres_final.csv, assets/ (icons, mascots, background), .streamlit/config.toml

## Run on your laptop
    pip install -r requirements.txt
    streamlit run app.py

## Put it online (Streamlit Community Cloud)
1. Upload everything in this folder to a GitHub repo (keep the .streamlit folder).
2. share.streamlit.io > New app > pick the repo > main file `app.py`.
3. App > Settings > Secrets: paste the contents of `.streamlit/secrets.toml.example` and fill it in.

## Trial codes
The 30 codes for sellers are in TRIAL_CODES_PRIVATE.csv (NOT in this folder, do not upload it).
The repo only holds their hashes (invite_codes.json). Each code works once.

## Team page
Open your app link with `?team=1` on the end, e.g. https://your-app.streamlit.app/?team=1
Reports, pausing stalls, promo posts for hawker centres, trial code usage.

## Important
Accounts, posts and photos are saved in a `data/` folder. On Streamlit Cloud that folder is wiped when the
app restarts or is redeployed. Fine for a demo; for real users move storage to a database.
