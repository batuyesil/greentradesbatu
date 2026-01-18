# ğŸš€ GreenTrades - HÄ±zlÄ± BaÅŸlangÄ±Ã§ KÄ±lavuzu

## âš¡ 5 Dakikada BaÅŸla!

### 1ï¸âƒ£ Kurulum (2 dakika)

```bash
# Repoyu indir veya zip'i aÃ§
cd greentrades

# Otomatik kurulum
bash install.sh

# VEYA Manuel kurulum
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2ï¸âƒ£ Ä°lk Ã‡alÄ±ÅŸtÄ±rma - Fake Money (1 dakika)

```bash
# HiÃ§bir ayar yapmadan direkt Ã§alÄ±ÅŸtÄ±r!
python main.py
```

âœ… **Ä°ÅŸte bu kadar!** Bot ÅŸimdi:
- GerÃ§ek piyasa verilerini okuyacak
- FÄ±rsatlarÄ± tarayacak
- Sanal para ile iÅŸlem simÃ¼le edecek
- Her ÅŸeyi log'layacak

âŒ **Risk YOK** - Sadece test!

### 3ï¸âƒ£ Telegram BaÄŸla (Opsiyonel - 2 dakika)

```bash
# 1. @BotFather'a git
#    /newbot -> "GreenTrades Bot" -> KullanÄ±cÄ± adÄ± belirle
#    Token'Ä± kopyala

# 2. @userinfobot'a git
#    Chat ID'ni kopyala

# 3. config/telegram.yaml dÃ¼zenle
nano config/telegram.yaml

# bot_token ve chat_id kÄ±sÄ±mlarÄ±nÄ± doldur
# Kaydet ve Ã§Ä±k (Ctrl+X, Y, Enter)

# 4. Tekrar Ã§alÄ±ÅŸtÄ±r
python main.py --telegram
```

ğŸ“± ArtÄ±k Telegram'dan bildirim alacaksÄ±n!

---

## ğŸ“Š Ä°lk 24 Saat - Ne Beklemeli?

### Fake Money Modunda:

```
â° Ä°lk 1 saat:
- 10-20 fÄ±rsat bulacak
- 2-5 iÅŸlem simÃ¼le edecek
- $5-15 sanal kar (veya zarar)

â° Ä°lk 24 saat:
- 50-200 fÄ±rsat
- 20-80 iÅŸlem
- $50-200 sanal kar beklentisi
```

### GerÃ§ek Performans Ã–rneÄŸi:

```
ğŸ’° BaÅŸlangÄ±Ã§: $1,000
ğŸ“ˆ 24 Saat Sonra: $1,045 (+4.5%)
ğŸ“Š Ä°ÅŸlemler: 32 (29 baÅŸarÄ±lÄ±, 3 baÅŸarÄ±sÄ±z)
ğŸ¯ En KarlÄ±: MATIC/USDT (+$8.50)
```

---

## ğŸ¯ Ã–nemli Komutlar

### BaÅŸlatma:

```bash
# Basit baÅŸlatma
python main.py

# Ã–zel ayarlarla
python main.py --balance 2000 --coins MATIC,ARB,OP

# Verbose (detaylÄ± loglar)
python main.py --verbose

# Durdurmak iÃ§in
Ctrl+C
```

### Telegram KomutlarÄ±:

```
/start      - Bot durumu
/balance    - Bakiye
/stats      - Ä°statistikler
/profit     - GÃ¼nlÃ¼k kar
/help       - YardÄ±m
```

---

## âš™ï¸ AyarlarÄ± Ã–zelleÅŸtir

### Temel Ayarlar (config/config.yaml):

```yaml
# BaÅŸlangÄ±Ã§ parasÄ±
balance:
  fake_money: 2000  # $2000 ile baÅŸla

# Hangi coinler
coins:
  priority_list:
    - MATIC/USDT
    - ARB/USDT
    - OP/USDT
    # Ä°stediÄŸin coinleri ekle

# Minimum spread
strategy:
  spot_arbitrage:
    min_spread_percent: 1.0  # %1'den dÃ¼ÅŸÃ¼ÄŸÃ¼nÃ¼ alma
```

---

## ğŸ”„ Real Money'e GeÃ§iÅŸ

### âš ï¸ DÄ°KKAT! Ã–nce ÅunlarÄ± Yap:

âœ… **Checklist:**
- [ ] En az 1 ay fake money test yaptÄ±m
- [ ] SonuÃ§lardan memnunum
- [ ] API key oluÅŸturmayÄ± biliyorum
- [ ] Risk yÃ¶netimini anlÄ±yorum
- [ ] KÃ¼Ã§Ã¼k parayla ($100-500) baÅŸlayacaÄŸÄ±m

### AdÄ±mlar:

```bash
# 1. API Keys oluÅŸtur (her borsa iÃ§in)
#    - mexc.com > API Management
#    - gateio.com > API Keys
#    - vb.

# 2. config/exchanges.yaml dÃ¼zenle
nano config/exchanges.yaml

# 3. API keys'leri gir
# Ã–NEMLÄ°: Sadece Spot Trading + Read yetkisi!
# Withdrawal yetkisi ASLA!

# 4. config.yaml dÃ¼zenle
nano config/config.yaml

# mode: "real_money" yap

# 5. Son kontrol
python main.py --mode real_money --balance 500

# Onay isteyecek, "evet" yaz
```

---

## ğŸ“ˆ Ä°lk HaftanÄ± Optimize Et

### GÃ¼n 1-2: GÃ¶zlemle
```bash
# Sadece izle, ayar yapma
python main.py --verbose
```

### GÃ¼n 3-4: Ä°nce Ayar
```yaml
# En Ã§ok kar eden coinleri tespit et
# config.yaml'da sadece onlarÄ± bÄ±rak

coins:
  priority_list:
    - MATIC/USDT  # %2.5 ortalama spread
    - GALA/USDT   # %1.8 ortalama spread
    # DÃ¼ÅŸÃ¼k performanslÄ±larÄ± Ã§Ä±kar
```

### GÃ¼n 5-7: Optimize
```yaml
# Risk yÃ¶netimini sÄ±kÄ±laÅŸtÄ±r
risk_management:
  max_position_per_coin: 200  # Daha kÃ¼Ã§Ã¼k pozisyonlar
  
# Spread eÅŸiÄŸini artÄ±r
strategy:
  spot_arbitrage:
    min_spread_percent: 1.2  # Sadece %1.2+ al
```

---

## ğŸ› Sorun mu YaÅŸÄ±yorsun?

### Bot baÅŸlamÄ±yor:
```bash
# Python versiyonu kontrol
python3 --version  # 3.8-3.11 olmalÄ±

# BaÄŸÄ±mlÄ±lÄ±klarÄ± tekrar yÃ¼kle
pip install -r requirements.txt --force-reinstall
```

### Telegram Ã§alÄ±ÅŸmÄ±yor:
```bash
# Token ve Chat ID doÄŸru mu?
cat config/telegram.yaml

# Test et
python -c "from src.utils.telegram_bot import TelegramNotifier; print('OK')"
```

### FÄ±rsat bulamÄ±yor:
```yaml
# Spread eÅŸiÄŸini dÃ¼ÅŸÃ¼r
strategy:
  spot_arbitrage:
    min_spread_percent: 0.5  # Daha toleranslÄ±
```

### Log'larÄ± kontrol et:
```bash
# Hata loglarÄ±
tail -f logs/errors/error.log

# Genel loglar
tail -f logs/main.log
```

---

## ğŸ’¡ Pro Ä°puÃ§larÄ±

### 1. En KarlÄ± Saatler:
```
ğŸŒ… 06:00-09:00 UTC: Asya piyasalarÄ± aÃ§Ä±lÄ±ÅŸ
ğŸŒ† 13:00-16:00 UTC: Avrupa aktif
ğŸŒƒ 21:00-00:00 UTC: US piyasalarÄ±
```

### 2. En Ä°yi Coinler (Mid-cap):
```
Gaming: GALA, SAND, MANA
Layer2: MATIC, ARB, OP
DeFi: LDO, UNI, AAVE
```

### 3. Borsa KombinasyonlarÄ±:
```
En Ä°yi Spreadler:
- MEXC + Gate.io
- MEXC + KuCoin
- KuCoin + Bybit
```

---

## ğŸ“š Daha Fazla Bilgi

- **DetaylÄ± DÃ¶kÃ¼man**: README.md
- **KonfigÃ¼rasyon**: config/config.yaml iÃ§indeki notlar
- **Stratejiler**: src/strategies/ klasÃ¶rÃ¼
- **Log Analizi**: logs/ klasÃ¶rÃ¼

---

## ğŸ¯ Hedefler

### Ä°lk Hafta:
```
ğŸ¯ Bot'u tanÄ±
ğŸ¯ AyarlarÄ± optimize et
ğŸ¯ Fake money'de karlÄ±lÄ±k saÄŸla
```

### Ä°lk Ay:
```
ğŸ¯ TutarlÄ± kar (fake money)
ğŸ¯ Real money'e geÃ§iÅŸ hazÄ±rlÄ±ÄŸÄ±
ğŸ¯ Risk yÃ¶netimi pratiÄŸi
```

### Ä°lk 3 Ay:
```
ğŸ¯ Real money'de kar
ğŸ¯ Stratejileri geliÅŸtir
ğŸ¯ Sermayeyi artÄ±r
```

---

## ğŸš€ BaÅŸla!

```bash
python main.py
```

**BaÅŸarÄ±lar! ğŸ’°**



