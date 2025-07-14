
# 🎮 Telegram Tic Tac Toe Bot

Welcome to **Tic Tac Toe TGBot**, a powerful and engaging Telegram bot that brings the classic Tic Tac Toe game to life with multiplayer, AI, spectator mode, and a live leaderboard — all in your chat!

---

## ✨ Features

- 🤖 **Play vs AI** – Practice your skills against a built-in computer player.
- 👬 **Play with Friends** – Challenge other users in real-time matches.
- 👀 **Spectate Mode** – Watch ongoing games unfold.
- 🏆 **Leaderboard** – Track global scores and see who's on top.
- 💾 **Persistent Game Data** – All match data is saved using SQLite for history and rankings.

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Nepcoder-coder/tictactoe-tgbot.git
cd tictactoe-tgbot
```

### 2. Install Dependencies

Ensure Python 3.7+ is installed, then install the required package:

```bash
pip install -r requirements.txt
```

#### `requirements.txt` content:

```
pyTelegramBotAPI
```

### 3. Configure Your Bot

Open `main.py` and set your Telegram bot token:

```python
TOKEN = "YOUR_BOT_TOKEN_HERE"
```

Get your bot token from [@BotFather](https://t.me/BotFather) on Telegram.

### 4. Run the Bot

```bash
python main.py
```

Your bot will now be running and available for users to interact with.

---

## 📁 Project Structure

```
tictactoe-tgbot/
├── main.py              # Main bot logic
├── requirements.txt     # Python dependencies
├── leaderboard.db       # SQLite database (auto-generated)
└── README.md            # Project documentation
```

---

## 📊 How It Works

- Players interact via inline Telegram buttons.
- Each game is assigned a unique session ID.
- SQLite stores player data, scores, and match logs.
- The leaderboard updates automatically after each match.
- Spectators can join any game and view it in real-time.

---

## 📌 Future Plans

- [ ] Implement advanced AI using minimax
- [ ] Group chat and multiplayer tournaments
- [ ] Match replay history
- [ ] Skins or custom board themes

---

## 🤝 Join the Community

Stay updated, get help, or contribute ideas:

- 🌐 Join our Dev Channel: [t.me/nepdevsz](https://t.me/nepdevsz)
- 💬 Developer Contact: [t.me/nepcodernp](https://t.me/nepcodernp)

---

## 🤝 Contributing

We welcome contributions!

1. Fork the repository
2. Create a feature branch: `git checkout -b new-feature`
3. Commit changes: `git commit -m "Add new feature"`
4. Push your branch: `git push origin new-feature`
5. Open a Pull Request

---

## 📄 License

Licensed under the [MIT License](https://opensource.org/licenses/MIT).

---

## 🔗 Links

- 📂 GitHub Repository: [Nepcoder-coder/tictactoe-tgbot](https://github.com/Nepcoder-coder/tictactoe-tgbot)
- 🤖 Create your bot: [@BotFather](https://t.me/BotFather)
- 📦 Library used: [pyTelegramBotAPI on PyPI](https://pypi.org/project/pyTelegramBotAPI/)
- 💬 Developer: [t.me/nepcodernp](https://t.me/nepcodernp)
- 🌍 Community: [t.me/nepdevsz](https://t.me/nepdevsz)

---

## 🙌 Thanks for Checking Out the Project!

Made with ❤️ by [@nepcodernp](https://t.me/nepcodernp)
