# -*- coding: utf-8 -*-
"""KonfigÃ¼rasyon yÃ¼kleyici"""
import yaml
from pathlib import Path

class ConfigLoader:
    def __init__(self, config_path='config/config.yaml'):
        self.config_path = config_path
        self.config = {}
        self.load_all()

    def load_all(self):
        """TÃ¼m konfigÃ¼rasyonlarÄ± yÃ¼kle"""
        with open(self.config_path, encoding='utf-8') as f:
            self.config = yaml.safe_load(f) or {}

        # Exchanges
        try:
            with open('config/exchanges.yaml', encoding='utf-8') as f:
                exchanges = yaml.safe_load(f) or {}
                self.config.update(exchanges)
        except Exception:
            pass

        # Telegram
        try:
            with open('config/telegram.yaml', encoding='utf-8') as f:
                telegram = yaml.safe_load(f) or {}
                # telegram.yaml root'a telegram:, notifications:, message_templates: basÄ±yor
                self.config.update(telegram)
        except Exception:
            pass

    def get(self, key, default=None):
        """NoktalÄ± key ile deÄŸer al (Ã¶rn: 'strategy.spot_arbitrage.enabled')"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value if value is not None else default

    def set(self, key, value):
        """DeÄŸer ata"""
        keys = key.split('.')
        cfg = self.config
        for k in keys[:-1]:
            if k not in cfg or not isinstance(cfg[k], dict):
                cfg[k] = {}
            cfg = cfg[k]
        cfg[keys[-1]] = value

    def get_template(self, template_name, **kwargs):
        """
        Telegram template'i iki yerden de arar:
        1) message_templates.<name>              (senin telegram.yaml bu formatta)
        2) telegram.message_templates.<name>     (eski format)
        """
        template = self.get(f'message_templates.{template_name}', None)
        if template is None:
            template = self.get(f'telegram.message_templates.{template_name}', '')

        template = (template or "").strip()
        if not template:
            return ""

        try:
            return template.format(**kwargs)
        except Exception:
            return template



