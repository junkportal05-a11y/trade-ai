"""Repository layer — all database CRUD using SQLAlchemy ORM."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.db.models import (
    SignalHistory,
    TradeJournal,
    PredictionsHistory,
    MetricsCache,
    PortfolioState,
    RiskSettings,
    RejectedSignal,
    DataQuality,
)

logger = logging.getLogger(__name__)


def _now_ist() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)


class SignalRepository:
    @staticmethod
    def add(db: Session, sig: dict[str, Any]) -> int | None:
        existing = (
            db.query(SignalHistory)
            .filter(SignalHistory.symbol == sig["symbol"], SignalHistory.status == "PENDING")
            .first()
        )
        if existing:
            same_dir = ("BUY" in existing.signal_type) == ("BUY" in sig.get("direction", ""))
            if same_dir:
                return None
            # Close opposite direction
            existing.status = "CLOSED"
            existing.exit_price = sig.get("entry_price", 0.0)
            existing.exit_at = _now_ist()
            existing.pnl_pct = 0.0
            db.commit()

        new_sig = SignalHistory(
            symbol=sig["symbol"],
            name=sig.get("name", sig["symbol"]),
            sector=sig.get("sector", "NSE"),
            signal_type=sig.get("direction", "HOLD"),
            confidence=sig.get("confidence", 0),
            score=sig.get("bull_score", 0) if "BUY" in sig.get("direction", "") else sig.get("bear_score", 0),
            entry_price=sig.get("entry", 0.0),
            target=sig.get("target", 0.0),
            stop_loss=sig.get("stop_loss", 0.0),
            rr_ratio=sig.get("rr_ratio", 0.0),
            atr=sig.get("atr", 0.0),
            scanned_at=_now_ist(),
            scan_type=sig.get("scan_type", "INTRADAY"),
            status="PENDING",
        )
        db.add(new_sig)
        db.commit()
        db.refresh(new_sig)
        return new_sig.id

    @staticmethod
    def get_pending(db: Session) -> list[dict]:
        rows = (
            db.query(SignalHistory)
            .filter(SignalHistory.status == "PENDING")
            .order_by(desc(SignalHistory.scanned_at))
            .all()
        )
        return [r.to_dict() for r in rows]

    @staticmethod
    def update_batch(db: Session, updates: list[tuple]) -> None:
        """updates: list of (status, exit_price, exit_at, pnl_pct, id)"""
        if not updates:
            return
        for status, exit_price, exit_at, pnl_pct, sig_id in updates:
            row = db.query(SignalHistory).filter(SignalHistory.id == sig_id).first()
            if row:
                row.status = status
                row.exit_price = exit_price
                row.exit_at = exit_at
                row.pnl_pct = pnl_pct
        db.commit()

    @staticmethod
    def get_stats(db: Session) -> dict[str, Any]:
        total = db.query(SignalHistory).count()
        pending = db.query(SignalHistory).filter(SignalHistory.status == "PENDING").count()
        won = db.query(SignalHistory).filter(SignalHistory.status == "HIT_TARGET").count()
        lost = db.query(SignalHistory).filter(SignalHistory.status == "HIT_STOP").count()
        expired = db.query(SignalHistory).filter(SignalHistory.status == "EXPIRED").count()
        closed = db.query(SignalHistory).filter(SignalHistory.status == "CLOSED").count()
        resolved = won + lost + closed + expired
        win_rate = round((won / resolved) * 100, 1) if resolved > 0 else 0.0

        avg_pnl_row = db.query(func.avg(SignalHistory.pnl_pct)).filter(
            SignalHistory.pnl_pct.isnot(None)
        ).scalar()
        avg_pnl = round(avg_pnl_row, 2) if avg_pnl_row else 0.0

        return {
            "total": total,
            "pending": pending,
            "won": won,
            "lost": lost,
            "expired": expired,
            "closed": closed,
            "resolved": resolved,
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
        }

    @staticmethod
    def get_by_sector(db: Session) -> list[dict]:
        rows = (
            db.query(
                SignalHistory.sector,
                func.count(SignalHistory.id).label("total"),
                func.sum(func.case((SignalHistory.status == "HIT_TARGET", 1), else_=0)).label("wins"),
            )
            .filter(SignalHistory.status.in_(["HIT_TARGET", "HIT_STOP", "CLOSED", "EXPIRED"]))
            .group_by(SignalHistory.sector)
            .all()
        )
        return [
            {
                "sector": r.sector,
                "total": r.total,
                "wins": r.wins or 0,
                "win_rate": round((r.wins or 0) / r.total * 100, 1) if r.total > 0 else 0.0,
            }
            for r in rows
        ]

    @staticmethod
    def get_by_direction(db: Session) -> list[dict]:
        rows = (
            db.query(
                func.case(
                    (SignalHistory.signal_type.like("%BUY%"), "BUY"), else_="SELL"
                ).label("direction"),
                func.count(SignalHistory.id).label("total"),
                func.sum(func.case((SignalHistory.status == "HIT_TARGET", 1), else_=0)).label("wins"),
                func.avg(SignalHistory.pnl_pct).label("avg_pnl"),
            )
            .filter(SignalHistory.status.in_(["HIT_TARGET", "HIT_STOP", "CLOSED", "EXPIRED"]))
            .group_by("direction")
            .all()
        )
        return [
            {
                "direction": r.direction,
                "total": r.total,
                "wins": r.wins or 0,
                "win_rate": round((r.wins or 0) / r.total * 100, 1) if r.total > 0 else 0.0,
                "avg_pnl": round(r.avg_pnl, 2) if r.avg_pnl else 0.0,
            }
            for r in rows
        ]

    @staticmethod
    def get_history(db: Session, limit: int = 100, symbol: str | None = None, status: str | None = None) -> list[dict]:
        q = db.query(SignalHistory)
        if symbol:
            q = q.filter(SignalHistory.symbol == symbol)
        if status:
            q = q.filter(SignalHistory.status == status)
        rows = q.order_by(desc(SignalHistory.scanned_at)).limit(limit).all()
        return [r.to_dict() for r in rows]

    @staticmethod
    def clear_all(db: Session) -> None:
        db.query(SignalHistory).delete()
        db.commit()

    @staticmethod
    def expire_old_intraday(db: Session) -> None:
        today = _now_ist().strftime("%Y-%m-%d")
        db.query(SignalHistory).filter(
            SignalHistory.status == "PENDING",
            SignalHistory.scan_type == "INTRADAY",
            SignalHistory.scanned_at < today,
        ).update(
            {"status": "EXPIRED", "exit_at": _now_ist()},
            synchronize_session=False,
        )
        db.commit()


class JournalRepository:
    @staticmethod
    def add(db: Session, entry: dict[str, Any], user_id: str | None = None) -> int:
        if not user_id:
            raise ValueError("user_id is required for Journal operations")
        new_entry = TradeJournal(
            symbol=entry["symbol"].upper(),
            direction=entry["direction"].upper(),
            entry_price=float(entry["entry_price"]),
            exit_price=float(entry["exit_price"]) if entry.get("exit_price") else None,
            qty=int(entry["qty"]),
            entry_date=entry.get("entry_date", _now_ist().isoformat()),
            reason=entry.get("reason", ""),
            emotion=entry.get("emotion", "Calm"),
            status=entry.get("status", "OPEN"),
            pnl=float(entry["pnl"]) if entry.get("pnl") is not None else None,
            user_id=user_id,
        )
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        return new_entry.id

    @staticmethod
    def get_all(db: Session, user_id: str | None = None) -> list[dict]:
        if not user_id:
            raise ValueError("user_id is required for Journal operations")
        query = db.query(TradeJournal).filter(TradeJournal.user_id == user_id)
        rows = query.order_by(desc(TradeJournal.entry_date)).all()
        return [r.to_dict() for r in rows]

    @staticmethod
    def delete(db: Session, entry_id: int, user_id: str | None = None) -> bool:
        if not user_id:
            raise ValueError("user_id is required for Journal operations")
        query = db.query(TradeJournal).filter(TradeJournal.id == entry_id, TradeJournal.user_id == user_id)
        row = query.first()
        if row:
            db.delete(row)
            db.commit()
            return True
        return False



def _sf(v: Any, default: float | None = None) -> float | None:
    if v is None:
        return default
    try:
        return float(v)
    except Exception:
        return default

def _parse_datetime(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


class PredictionRepository:
    @staticmethod
    def add(db: Session, pred: dict[str, Any]) -> int:
        new_pred = PredictionsHistory(
            symbol=pred["symbol"].upper(),
            prediction_date=_parse_datetime(pred.get("prediction_date")) or _now_ist(),
            prediction_type=pred["prediction_type"].upper(),
            entry_price=_sf(pred.get("entry_price"), 0.0),
            target_price=_sf(pred.get("target_price"), 0.0),
            stop_loss=_sf(pred.get("stop_loss"), 0.0),
            confidence_score=int(pred.get("confidence_score", 50)),
            rsi=_sf(pred.get("rsi")),
            macd=_sf(pred.get("macd")),
            adx=_sf(pred.get("adx")),
            sector=pred.get("sector"),
            market_cap=_sf(pred.get("market_cap")),
            volume_ratio=_sf(pred.get("volume_ratio")),
            vwap_distance=_sf(pred.get("vwap_distance")),
            atr=_sf(pred.get("atr"), 0.0),
            news_score=_sf(pred.get("news_score"), 0.0),
            market_breadth=_sf(pred.get("market_breadth"), 0.0),
            sector_strength=_sf(pred.get("sector_strength"), 0.0),
            nifty_trend=pred.get("nifty_trend", "FLAT"),
            status=pred.get("status", "PENDING"),
            reason=pred.get("reason", ""),
            setup_type=pred.get("setup_type", "UNKNOWN"),
            market_regime_snapshot=pred.get("market_regime_snapshot", "UNKNOWN"),
            risk_amount=_sf(pred.get("risk_amount"), 0.0),
            confidence_probability=_sf(pred.get("confidence_probability"), 0.5),
            regime_score=_sf(pred.get("regime_score"), 0.0),
            sector_score=_sf(pred.get("sector_score"), 0.0),
            volume_score=_sf(pred.get("volume_score"), 0.0),
            rs_score=_sf(pred.get("rs_score"), 0.0),
            trade_quality_score=_sf(pred.get("trade_quality_score"), 0.0),
            correlation_score=_sf(pred.get("correlation_score"), 0.0),
            signal_time=_parse_datetime(pred.get("signal_time")),
            order_time=_parse_datetime(pred.get("order_time")),
        )
        db.add(new_pred)
        db.commit()
        db.refresh(new_pred)
        return new_pred.id

    @staticmethod
    def get_all(db: Session) -> list[dict]:
        rows = db.query(PredictionsHistory).order_by(desc(PredictionsHistory.prediction_date)).all()
        return [r.to_dict() for r in rows]

    @staticmethod
    def get_pending(db: Session) -> list[dict]:
        rows = (
            db.query(PredictionsHistory)
            .filter(PredictionsHistory.status == "PENDING")
            .order_by(desc(PredictionsHistory.prediction_date))
            .all()
        )
        return [r.to_dict() for r in rows]


class MetricsRepository:
    @staticmethod
    def set(db: Session, key: str, value_json: str) -> None:
        from app.db.models import MetricsCache
        row = db.query(MetricsCache).filter(MetricsCache.key == key).first()
        if row:
            row.value_json = value_json
            row.updated_at = _now_ist()
        else:
            db.add(MetricsCache(key=key, value_json=value_json, updated_at=_now_ist()))
        db.commit()

    @staticmethod
    def get(db: Session, key: str) -> dict | None:
        from app.db.models import MetricsCache
        row = db.query(MetricsCache).filter(MetricsCache.key == key).first()
        if not row:
            return None
        try:
            return json.loads(row.value_json)
        except json.JSONDecodeError:
            return None


class RiskRepository:
    @staticmethod
    def get_settings(db: Session) -> dict:
        row = db.query(RiskSettings).first()
        if row:
            return {
                "daily_loss_limit": row.daily_loss_limit,
                "daily_drawdown_limit": row.daily_drawdown_limit,
                "max_consecutive_losses": row.max_consecutive_losses,
            }
        return {"daily_loss_limit": -3.0, "daily_drawdown_limit": -4.0, "max_consecutive_losses": 5}


class PortfolioRepository:
    @staticmethod
    def get_state(db: Session) -> dict:
        row = db.query(PortfolioState).first()
        if row:
            return {
                "current_equity": row.current_equity,
                "peak_equity": row.peak_equity,
                "daily_equity": row.daily_equity,
                "sector_exposure": json.loads(row.sector_exposure) if row.sector_exposure else {},
                "active_positions": json.loads(row.active_positions) if row.active_positions else [],
                "last_updated": row.last_updated.isoformat() if row.last_updated else None,
            }
        return {
            "current_equity": 100_000.0,
            "peak_equity": 100_000.0,
            "daily_equity": 100_000.0,
            "sector_exposure": {},
            "active_positions": [],
        }


class RejectedSignalRepository:
    @staticmethod
    def add(db: Session, sig: dict[str, Any]) -> int:
        new_rej = RejectedSignal(
            symbol=sig["symbol"].upper(),
            rejection_category=sig.get("rejection_category", "UNKNOWN"),
            rejection_reason=sig.get("rejection_reason", ""),
            signal_price=float(sig.get("signal_price", 0.0)),
            target_price=float(sig.get("target_price", 0.0)),
            stop_loss=float(sig.get("stop_loss", 0.0)),
            status="PENDING",
            scanned_at=_now_ist(),
        )
        db.add(new_rej)
        db.commit()
        db.refresh(new_rej)
        return new_rej.id


class DataQualityRepository:
    @staticmethod
    def add(db: Session, result: dict[str, Any]) -> int:
        new_dq = DataQuality(
            checked_at=_now_ist(),
            total_trades=result.get("total_trades"),
            valid_trades=result.get("valid_trades"),
            confidence_score=result.get("confidence_score"),
            failures=json.dumps(result.get("failures", [])),
            locked=result.get("locked", True),
        )
        db.add(new_dq)
        db.commit()
        db.refresh(new_dq)
        return new_dq.id

    @staticmethod
    def get_latest(db: Session) -> dict | None:
        row = db.query(DataQuality).order_by(desc(DataQuality.checked_at)).first()
        if not row:
            return None
        return {
            "id": row.id,
            "checked_at": row.checked_at.isoformat() if row.checked_at else None,
            "total_trades": row.total_trades,
            "valid_trades": row.valid_trades,
            "confidence_score": row.confidence_score,
            "failures": json.loads(row.failures) if row.failures else [],
            "locked": row.locked,
        }


# ── Convenience aliases for compatibility ───────────────────────────────────
class Repository:
    signals = SignalRepository()
    journal = JournalRepository()
    predictions = PredictionRepository()
    metrics = MetricsRepository()
    risk = RiskRepository()
    portfolio = PortfolioRepository()
    rejected = RejectedSignalRepository()
    data_quality = DataQualityRepository()


repo = Repository()
