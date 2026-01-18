# ğŸš€ GreenTrades - Advanced Altcoin Arbitrage Bot

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/batuyesil/greentrades-bot)

Professional cryptocurrency arbitrage bot focused on mid-cap altcoins with high spread potential.

## âœ¨ Features

- ğŸ¯ **Multi-Exchange Arbitrage** - Supports 6+ exchanges (MEXC, Gate.io, KuCoin, Bybit, OKX, Binance)
- ğŸ’ **Altcoin Focused** - Targets mid-cap coins with 1-5% spreads
- ğŸ® **Dual Mode** - Fake money testing & Real money trading
- ğŸ“± **Telegram Integration** - Real-time notifications and control
- âš¡ **WebSocket Support** - Millisecond-level execution speed
- ğŸ›¡ï¸ **Risk Management** - Advanced stop-loss and position sizing
- ğŸ“Š **Performance Tracking** - Detailed analytics and reporting
- ğŸ”„ **Auto-Rebalancing** - Automated portfolio management

## ğŸš€ Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/batuyesil/greentrades-bot.git
cd greentrades-bot
```

### 2. Install Dependencies

#### Windows:
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### Linux/Mac:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run (Fake Money - No Risk!)

```bash
python main.py --balance 1000
```

**That's it!** The bot is now running with $1000 virtual money.

## ğŸ“– Documentation

- [ğŸ“˜ Full Documentation](README.md) - Complete guide
- [âš¡ Quick Start Guide](QUICKSTART.md) - Get started in 5 minutes
- [ğŸ’° Balance Configuration](BAKIYE_AYARLAMA.md) - Balance setup guide (Turkish)
- [ğŸ› ï¸ Setup Instructions](NASIL_KULLANILIR.md) - Installation guide (Turkish)

## ğŸ¯ Usage Examples

### Fake Money Testing
```bash
# Test with $500
python main.py --balance 500

# Test with $5000
python main.py --balance 5000

# Verbose logging
python main.py --balance 1000 --verbose
```

### Real Money Trading (CAREFUL!)
```bash
# Use 50% of API balance
python main.py --mode real_money --balance-percent 50

# Maximum $2000 limit
python main.py --mode real_money --balance 2000
```

### Telegram Bot
```bash
# Enable Telegram notifications
python main.py --telegram

# Commands in Telegram:
# /start - Bot status
# /balance - Check balance
# /stats - Statistics
# /profit - Daily profit
```

## âš™ï¸ Configuration

Edit `config/config.yaml`:

```yaml
# Mode selection
mode: "fake_money"  # or "real_money"

# Starting balance
balance:
  fake_money:
    total: 1000  # Test with $1000

# Target coins
coins:
  priority_list:
    - MATIC/USDT
    - ARB/USDT
    - OP/USDT
    # Add more...

# Minimum spread
strategy:
  spot_arbitrage:
    min_spread_percent: 0.8  # 0.8% minimum
```

## ğŸ“Š Expected Performance

### Conservative (Fake Money):
- Capital: $1,000
- Daily: 1-2% ($10-20)
- Monthly: 30-60% ($300-600)
- Risk: None

### Moderate (Real Money):
- Capital: $1,000
- Daily: 0.5-2% ($5-20)
- Monthly: 15-60% ($150-600)
- Risk: Low-Medium

## ğŸ›¡ï¸ Security

**CRITICAL:**
- âœ… API Keys: **ONLY** Spot Trading + Read permissions
- âŒ API Keys: **NEVER** enable Withdrawal permission
- âœ… Use IP Whitelist
- âœ… Enable 2FA on all exchanges
- âœ… Never commit API keys to Git

## ğŸ“± Telegram Setup

1. Create bot with [@BotFather](https://t.me/BotFather)
2. Get your Chat ID from [@userinfobot](https://t.me/userinfobot)
3. Edit `config/telegram.yaml`:
   ```yaml
   telegram:
     bot_token: "YOUR_BOT_TOKEN"
     chat_id: "YOUR_CHAT_ID"
   ```

## ğŸ› Troubleshooting

### Windows Encoding Error
```powershell
chcp 65001
$env:PYTHONIOENCODING="utf-8"
python main.py
```

### Module Not Found
```bash
pip install -r requirements.txt --force-reinstall
```

### No Opportunities Found
Lower the spread threshold in `config/config.yaml`:
```yaml
strategy:
  spot_arbitrage:
    min_spread_percent: 0.5  # Lower threshold
```

## ğŸ¤ Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## âš ï¸ Disclaimer

This bot is for educational purposes only. Cryptocurrency trading carries risk. Never invest more than you can afford to lose. The developers are not responsible for any financial losses.

## ğŸ“œ License

MIT License - see [LICENSE](LICENSE) file for details.

## ğŸ™ Acknowledgments

- [CCXT](https://github.com/ccxt/ccxt) - Cryptocurrency trading library
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram integration

## ğŸ“ Support

- ğŸ“– [Documentation](README.md)
- ğŸ› [Issues](https://github.com/batuyesil/greentrades-bot/issues)
- ğŸ’¬ [Discussions](https://github.com/batuyesil/greentrades-bot/discussions)

---

**â­ Star this repo if you find it useful!**

**Made with â¤ï¸ for the crypto arbitrage community**

## ğŸªŸ Windows KullanÄ±cÄ±larÄ± Ä°Ã§in Ã–zel

### Kolay BaÅŸlatma (Ã‡ift TÄ±kla!)

`start.bat` dosyasÄ±na Ã§ift tÄ±kla - HER ÅEY OTOMATÄ°K!

VEYA PowerShell'de:

```powershell
# Tek seferlik ayar
chcp 65001
$env:PYTHONIOENCODING="utf-8"

# Her zaman bunu ekle
python main.py --balance 1000
```

### PowerShell Profile'a Ekle (KalÄ±cÄ± Ã‡Ã¶zÃ¼m)

```powershell
# Profile dosyasÄ±nÄ± aÃ§
notepad $PROFILE

# Åunu ekle ve kaydet:
$env:PYTHONIOENCODING="utf-8"
chcp 65001 > $null

# Åimdi her PowerShell aÃ§Ä±lÄ±ÅŸÄ±nda hazÄ±r!
```

---

## ğŸ“ Proje YapÄ±sÄ±

```
greentrades-bot/
â”œâ”€â”€ start.bat              # Windows kolay baÅŸlatma
â”œâ”€â”€ main.py                # Ana program
â”œâ”€â”€ requirements.txt       # Python baÄŸÄ±mlÄ±lÄ±klarÄ±
â”œâ”€â”€ LICENSE               # MIT License
â”œâ”€â”€ README.md             # Bu dosya
â”œâ”€â”€ QUICKSTART.md         # HÄ±zlÄ± baÅŸlangÄ±Ã§
â”œâ”€â”€ config/               # KonfigÃ¼rasyon
â”‚   â”œâ”€â”€ config.yaml       # Ana ayarlar
â”‚   â”œâ”€â”€ exchanges.yaml    # API anahtarlarÄ±
â”‚   â””â”€â”€ telegram.yaml     # Telegram bot
â”œâ”€â”€ src/                  # Kaynak kodlar
â”‚   â”œâ”€â”€ core/            # Ana sistem
â”‚   â”œâ”€â”€ strategies/      # Arbitraj stratejileri
â”‚   â”œâ”€â”€ utils/           # YardÄ±mcÄ± araÃ§lar
â”‚   â””â”€â”€ data/            # Veri yÃ¶netimi
â””â”€â”€ logs/                # Log dosyalarÄ±
```

---

## ğŸ”¥ HÄ±zlÄ± Komutlar

```bash
# Fake money test
python main.py --balance 500

# Belirli coinlerle
python main.py --coins MATIC,ARB,OP

# Minimum spread ayarla
python main.py --min-spread 1.5

# DetaylÄ± log
python main.py --verbose

# Telegram ile
python main.py --telegram

# Real money (DÄ°KKATLÄ°!)
python main.py --mode real_money --balance-percent 50
```

---

## ğŸ“ˆ Roadmap

- [x] Spot Arbitrage
- [x] Fake Money Mode
- [x] Real Money Mode  
- [x] Telegram Integration
- [x] Risk Management
- [ ] Triangular Arbitrage (Coming Soon)
- [ ] Statistical Arbitrage (Coming Soon)
- [ ] Web Dashboard (Planned)
- [ ] Mobile App (Planned)

---

## ğŸ’° BaÄŸÄ±ÅŸ

Projeyi beÄŸendiysen:
- â­ Star at
- ğŸ´ Fork yap
- ğŸ› Issue aÃ§
- ğŸ’¬ KatkÄ±da bulun

**Crypto Donations:**
- BTC: `bc1q...` (yakÄ±nda)
- ETH: `0x...` (yakÄ±nda)
- USDT (TRC20): `T...` (yakÄ±nda)

---

## ğŸ“Š Ä°statistikler

![GitHub stars](https://img.shields.io/github/stars/batuyesil/greentrades-bot?style=social)
![GitHub forks](https://img.shields.io/github/forks/batuyesil/greentrades-bot?style=social)
![GitHub issues](https://img.shields.io/github/issues/batuyesil/greentrades-bot)
![GitHub last commit](https://img.shields.io/github/last-commit/batuyesil/greentrades-bot)

---

## ğŸŒŸ YÄ±ldÄ±zla Bizi!

Proje iÅŸine yaradÄ±ysa GitHub'da â­ vermeyi unutma!

---

**Happy Trading! ğŸ’°ğŸš€**

**Made with â¤ï¸ by the crypto arbitrage community**



