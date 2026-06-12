# FlyTime Live Monitor — Start Here

No terminal commands needed. Just double-click files in this folder.

## The one thing to do

**Double-click `Start FlyTime.bat`**

That automatically:
1. Starts collecting live match data in the background
2. Starts the dashboard
3. Opens your web browser to the dashboard

You'll see two small windows minimize to your taskbar — leave them there. Don't close them.

---

## Other files (also just double-click)

| File | What it does |
|------|----------------|
| **Start FlyTime.bat** | Turn everything on |
| **Stop FlyTime.bat** | Turn everything off |
| **Check Status.bat** | See if it's working and how many matches/flies collected |

---

## Dashboard

After starting, your browser opens to:

**http://127.0.0.1:8787/**

This page auto-refreshes every 60 seconds. It shows:
- How many matches are being tracked
- Yellow / green / blue / red fly counts
- Per-league stats

---

## Important: laptop sleep

**The monitor stops when your laptop sleeps.** There is no way around this on a sleeping laptop.

For a game weekend:
1. Plug in your laptop
2. Go to **Settings → System → Power → Screen and sleep**
3. Set **When plugged in, put device to sleep** to **Never** (or 3 hours)
4. Double-click **Start FlyTime.bat**
5. When done, double-click **Stop FlyTime.bat**
6. Set sleep back to normal if you want

---

## How do I know it's working?

1. Double-click **Check Status.bat** during a live game
2. Look for **Last poll** showing a recent time
3. Look for **Live** matches > 0
4. After a close finish, **Blue** or **Green** counts should increase

---

## Troubleshooting

**Browser says "can't connect"**
- Wait 10 seconds and refresh — the dashboard takes a moment to start
- Make sure you didn't close the minimized taskbar windows

**Monitor: NOT RUNNING**
- Double-click **Start FlyTime.bat** again

**Nothing happening during games**
- Laptop may have slept — check power settings
- Wi-Fi may have dropped — check your connection

**Error about Python**
- Python must be installed. Open PowerShell and type `python --version` to check.

---

## Folder location

```
C:\Projects\ScoreFly\scorefly\flytime-engine\
```

You can right-click **Start FlyTime.bat** → **Send to** → **Desktop (create shortcut)** to put a shortcut on your desktop.
