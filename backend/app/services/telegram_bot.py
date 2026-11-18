"""Telegram bot service for high-confidence signal alerts."""
from __future__ import annotations

import os
import logging
from typing import Optional
import requests
from app.core.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

class TelegramBot:
    """Send signal alerts via Telegram bot."""
    
    def __init__(self):
        self.bot_token = getattr(settings, 'telegram_bot_token', None)
        self.chat_id = getattr(settings, 'telegram_chat_id', None)
        self.enabled = bool(self.bot_token and self.chat_id)
        
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message via Telegram bot."""
        if not self.enabled:
            logger.debug("Telegram bot not configured, skipping message")
            return False
            
        try:
            url = TELEGRAM_API_URL.format(token=self.bot_token)
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Telegram alert sent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def send_signal_alert(self, signal: dict) -> bool:
        """Format and send a high-confidence signal alert."""
        if not self.enabled:
            return False
            
        symbol = signal.get('symbol', 'UNKNOWN').replace('.NS', '')
        action = signal.get('signal', 'UNKNOWN')
        confidence = signal.get('confidence', 0)
        entry = signal.get('entry', 0)
        target = signal.get('target', 0)
        stop_loss = signal.get('stop_loss', 0)
        rr_ratio = signal.get('rr_ratio', 0)
        reasoning = signal.get('reasoning', '')
        sector = signal.get('sector', '')
        
        emoji = "🟢" if action in ('BUY', 'WEAK BUY', 'LONG') else "🔴" if action in ('SELL', 'WEAK SELL', 'SHORT') else "⚪"
        
        text = (
            f"{emoji} <b>HIGH-CONFIDENCE SIGNAL ALERT</b> {emoji}\n\n"
            f"<b>Symbol:</b> {symbol}\n"
            f"<b>Action:</b> {action}\n"
            f"<b>Confidence:</b> {confidence}%\n"
            f"<b>Sector:</b> {sector}\n\n"
            f"💰 <b>Entry:</b> ₹{entry:,.2f}\n"
            f"🎯 <b>Target:</b> ₹{target:,.2f}\n"
            f"🛑 <b>Stop Loss:</b> ₹{stop_loss:,.2f}\n"
            f"⚖️ <b>R:R Ratio:</b> 1:{rr_ratio}\n\n"
        )
        
        if reasoning:
            text += f"📝 <b>Reasoning:</b> {reasoning}\n\n"
            
        text += f"<i>⚠️ Paper trading only. Not SEBI registered advice.</i>"
        
        return self.send_message(text)
    
    def send_morning_brief(self, signals: list) -> bool:
        """Send morning brief with top signals."""
        if not self.enabled or not signals:
            return False
            
        text = "🌅 <b>MORNING MARKET BRIEF</b>\n\n"
        text += f"Top {len(signals)} signals for today's open:\n\n"
        
        for i, sig in enumerate(signals, 1):
            symbol = sig.get('symbol', 'UNKNOWN').replace('.NS', '')
            action = sig.get('signal', 'UNKNOWN')
            confidence = sig.get('confidence', 0)
            entry = sig.get('entry', sig.get('current_price', 0))
            target = sig.get('target', 0)
            stop_loss = sig.get('stop_loss', 0)
            
            emoji = "🟢" if action in ('BUY', 'WEAK BUY', 'LONG') else "🔴"
            
            text += (
                f"\n{i}. {emoji} <b>{symbol}</b> — {action} ({confidence}%)\n"
                f"   Entry: ₹{entry:,.2f} | Target: ₹{target:,.2f} | SL: ₹{stop_loss:,.2f}\n"
            )
            
        text += "\n<i>⚠️ Paper trading only. Verify before allocating real funds.</i>"
        
        return self.send_message(text)


# Global instance
telegram_bot = TelegramBot()