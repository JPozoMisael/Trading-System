import yfinance as yf
import numpy as np
import pytz

from ta.trend     import EMAIndicator
from ta.momentum  import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime     import datetime


# =========================================
# CONSTANTES
# =========================================

SYMBOL    = "GC=F"
PERIOD    = "5d"
INTERVAL  = "15m"

ATR_MIN_THRESHOLD = 3.0


# =========================================
# MARKET DATA
# =========================================

def get_market_data():
    """
    Descarga velas M15 de los últimos 5 días.
    Retorna None si yfinance falla o el mercado está cerrado.
    """
    try:
        gold = yf.Ticker(SYMBOL)
        data = gold.history(period=PERIOD, interval=INTERVAL)

        if data is None or data.empty:
            return None

        # Eliminar filas con NaN en columnas críticas
        data = data.dropna(subset=["Open", "High", "Low", "Close"])

        # Necesitamos al menos 60 velas para calcular indicadores
        if len(data) < 60:
            return None

        return data

    except Exception as e:
        print(f"[market_service] Error descargando datos: {e}")
        return None


# =========================================
# MARKET CONTEXT
# =========================================

def build_market_context():
    """
    Construye el contexto completo del mercado con todos los indicadores.
    Retorna None si no hay datos disponibles.
    """
    data = get_market_data()

    if data is None:
        return None

    ema20 = EMAIndicator(close=data["Close"], window=20).ema_indicator()
    ema50 = EMAIndicator(close=data["Close"], window=50).ema_indicator()
    atr   = AverageTrueRange(
                high=data["High"],
                low=data["Low"],
                close=data["Close"],
                window=14
            ).average_true_range()
    rsi   = RSIIndicator(close=data["Close"], window=14).rsi()

    data = data.copy()
    data["EMA20"] = ema20
    data["EMA50"] = ema50
    data["ATR"]   = atr
    data["RSI"]   = rsi

    return {
        "data":          data,
        "current_price": round(float(data["Close"].iloc[-1]), 2),
        "ema20":         round(float(data["EMA20"].iloc[-1]), 2),
        "ema50":         round(float(data["EMA50"].iloc[-1]), 2),
        "atr":           round(float(data["ATR"].iloc[-1]),   2),
        "rsi":           round(float(data["RSI"].iloc[-1]),   2),
    }


# =========================================
# SESSION DETECTION (con DST real)
# =========================================

def detect_session():
    """
    Detecta la sesión activa usando zonas horarias reales con DST.
    Londres: 08:00–17:00 BST / 08:00–17:00 GMT
    Nueva York: 13:00–22:00 EDT / 14:00–23:00 EST
    """
    now_utc = datetime.now(pytz.utc)

    london_tz   = pytz.timezone("Europe/London")
    newyork_tz  = pytz.timezone("America/New_York")
    tokyo_tz    = pytz.timezone("Asia/Tokyo")

    now_london  = now_utc.astimezone(london_tz)
    now_newyork = now_utc.astimezone(newyork_tz)
    now_tokyo   = now_utc.astimezone(tokyo_tz)

    london_open  = 8   <= now_london.hour  < 17
    newyork_open = 8   <= now_newyork.hour < 17
    tokyo_open   = 9   <= now_tokyo.hour   < 18

    # Overlap Londres + NY es la ventana más poderosa para XAUUSD
    if london_open and newyork_open:
        return "LONDON_NY_OVERLAP"

    if london_open:
        return "LONDON"

    if newyork_open:
        return "NEW_YORK"

    if tokyo_open:
        return "ASIA"

    return "DEAD_ZONE"


# =========================================
# TREND DETECTION
# =========================================

def detect_trend(context):
    if context is None:
        return "UNKNOWN"

    ema20 = context["ema20"]
    ema50 = context["ema50"]
    price = context["current_price"]

    # Tendencia fuerte: precio y EMA20 ambos sobre EMA50
    if ema20 > ema50 and price > ema20:
        return "BULLISH"

    # Tendencia bajista fuerte
    if ema20 < ema50 and price < ema20:
        return "BEARISH"

    # Precio entre las EMAs → rango
    return "RANGE"


# =========================================
# SWING DETECTION (ventana adaptativa)
# =========================================

def detect_swings(context):
    """
    Detecta swings reales usando una ventana adaptativa.
    Usa ventana de 10 velas (vs 5 anterior) para reducir ruido en M15.
    """
    if context is None:
        return {"swing_high": None, "swing_low": None}

    data   = context["data"]
    highs  = data["High"].values
    lows   = data["Low"].values
    window = 10  # más robusto que 5 para M15

    swing_high = None
    swing_low  = None

    for i in range(len(data) - window - 1, window, -1):
        left_right_highs = np.concatenate([highs[i - window:i], highs[i + 1:i + window + 1]])
        left_right_lows  = np.concatenate([lows[i  - window:i], lows[i  + 1:i + window + 1]])

        if swing_high is None and highs[i] > np.max(left_right_highs):
            swing_high = highs[i]

        if swing_low is None and lows[i] < np.min(left_right_lows):
            swing_low = lows[i]

        if swing_high is not None and swing_low is not None:
            break

    # Fallback al histórico si no encuentra swings claros
    if swing_high is None:
        swing_high = float(data["High"].max())
    if swing_low is None:
        swing_low  = float(data["Low"].min())

    return {
        "swing_high": round(float(swing_high), 2),
        "swing_low":  round(float(swing_low),  2),
    }


# =========================================
# FIBONACCI LEVELS
# =========================================

def calculate_fibonacci(context):
    if context is None:
        return {}

    swings = detect_swings(context)
    high   = swings["swing_high"]
    low    = swings["swing_low"]

    if high is None or low is None:
        return {}

    diff = high - low

    return {
        "0.0":   round(high, 2),
        "0.236": round(high - diff * 0.236, 2),
        "0.382": round(high - diff * 0.382, 2),
        "0.5":   round(high - diff * 0.5,   2),
        "0.618": round(high - diff * 0.618, 2),
        "0.786": round(high - diff * 0.786, 2),
        "1.0":   round(low,  2),
    }


# =========================================
# BREAK OF STRUCTURE
# =========================================

def detect_bos(context):
    if context is None:
        return "NONE"

    swings        = detect_swings(context)
    current_close = context["current_price"]

    if swings["swing_high"] and current_close > swings["swing_high"]:
        return "BULLISH"
    if swings["swing_low"] and current_close < swings["swing_low"]:
        return "BEARISH"

    return "NONE"


# =========================================
# ENGULFING PATTERN
# =========================================

def detect_engulfing(context):
    if context is None:
        return "NONE"

    data     = context["data"]
    prev     = data.iloc[-2]
    curr     = data.iloc[-1]

    p_open, p_close = float(prev["Open"]), float(prev["Close"])
    c_open, c_close = float(curr["Open"]), float(curr["Close"])

    # Bullish engulfing
    if p_close < p_open and c_close > c_open:
        if c_open <= p_close and c_close >= p_open:
            return "BULLISH"

    # Bearish engulfing
    if p_close > p_open and c_close < c_open:
        if c_open >= p_close and c_close <= p_open:
            return "BEARISH"

    return "NONE"


# =========================================
# LIQUIDITY SWEEP
# =========================================

def detect_liquidity_sweep(context):
    if context is None:
        return "NONE"

    data = context["data"]
    prev = data.iloc[-2]
    curr = data.iloc[-1]

    p_high, p_low   = float(prev["High"]),  float(prev["Low"])
    c_high, c_low   = float(curr["High"]),  float(curr["Low"])
    c_close         = float(curr["Close"])

    # Barrió stops alcistas (above high) y cerró adentro → señal bajista
    if c_high > p_high and c_close < p_high:
        return "BEARISH"

    # Barrió stops bajistas (below low) y cerró adentro → señal alcista
    if c_low < p_low and c_close > p_low:
        return "BULLISH"

    return "NONE"


# =========================================
# SIGNAL ENGINE
# =========================================

def generate_signal(context):
    if context is None:
        return {
            "signal":        "WAIT",
            "current_price": None,
            "reasons":       ["No market data available"],
        }

    trend     = detect_trend(context)
    fib       = calculate_fibonacci(context)
    engulfing = detect_engulfing(context)
    bos       = detect_bos(context)
    sweep     = detect_liquidity_sweep(context)
    price     = context["current_price"]
    atr       = context["atr"]
    rsi       = context["rsi"]
    session   = detect_session()

    signal  = "WAIT"
    reasons = []

    # ---- Filtros de mercado ----
    if session == "DEAD_ZONE":
        reasons.append("Dead market session")

    if atr < ATR_MIN_THRESHOLD:
        reasons.append(f"Low volatility (ATR {atr} < {ATR_MIN_THRESHOLD})")

    if trend == "RANGE":
        reasons.append("Market in range")

    # Si algún filtro bloqueante se activa, no operar
    if reasons:
        return {"signal": "WAIT", "current_price": price, "reasons": reasons}

    # ---- Zonas OTE Fibonacci ----
    fib_618 = fib.get("0.618")
    fib_786 = fib.get("0.786")

    if fib_618 is None or fib_786 is None:
        return {"signal": "WAIT", "current_price": price, "reasons": ["Fibonacci no calculado"]}

    fib_low  = min(fib_618, fib_786)
    fib_high = max(fib_618, fib_786)

    in_bullish_ote = fib_low  <= price <= fib_high
    in_bearish_ote = fib_low  <= price <= fib_high

    confirmation_bullish = engulfing == "BULLISH" or sweep == "BULLISH" or bos == "BULLISH"
    confirmation_bearish = engulfing == "BEARISH" or sweep == "BEARISH" or bos == "BEARISH"

    # ---- BUY ----
    if trend == "BULLISH" and in_bullish_ote and confirmation_bullish:
        # RSI como filtro extra: no comprar en sobrecompra
        if rsi < 70:
            signal  = "BUY"
            reasons = ["Bullish OTE confirmado", f"RSI {rsi}", f"Sesión {session}"]

    # ---- SELL ----
    elif trend == "BEARISH" and in_bearish_ote and confirmation_bearish:
        # RSI como filtro extra: no vender en sobreventa
        if rsi > 30:
            signal  = "SELL"
            reasons = ["Bearish OTE confirmado", f"RSI {rsi}", f"Sesión {session}"]

    if signal == "WAIT" and not reasons:
        reasons.append("Waiting for structural alignment")

    return {"signal": signal, "current_price": price, "reasons": reasons}


# =========================================
# CONFIDENCE SCORE
# =========================================

def calculate_score(context):
    if context is None:
        return {"score": 0, "confidence": 0}

    trend       = detect_trend(context)
    signal_data = generate_signal(context)
    atr         = context["atr"]
    rsi         = context["rsi"]
    session     = detect_session()

    score = 0

    # Tendencia definida
    if trend in ("BULLISH", "BEARISH"):
        score += 2

    # Señal activa (no WAIT)
    if signal_data["signal"] != "WAIT":
        score += 3

    # Volatilidad
    if atr > 8:   score += 3
    elif atr > 5: score += 2
    elif atr > 3: score += 1
    else:         score -= 3  # baja volatilidad penaliza

    # Sesión
    session_scores = {
        "LONDON_NY_OVERLAP": 4,
        "NEW_YORK":          3,
        "LONDON":            2,
        "ASIA":              1,
        "DEAD_ZONE":        -3,
    }
    score += session_scores.get(session, 0)

    # RSI — penalizar extremos si van contra la señal
    signal = signal_data["signal"]
    if signal == "BUY"  and rsi > 65: score -= 1
    if signal == "SELL" and rsi < 35: score -= 1
    if signal == "BUY"  and rsi < 40: score += 1  # sobreventa favorece compra
    if signal == "SELL" and rsi > 60: score += 1  # sobrecompra favorece venta

    # Si hay señal WAIT el confidence no puede ser alto
    if signal_data["signal"] == "WAIT":
        score = min(score, 3)

    confidence = min(max(score * 8, 0), 100)

    return {"score": score, "confidence": confidence}


# =========================================
# TRADE LEVELS (ATR dinámico)
# =========================================

def calculate_trade_levels(context):
    if context is None:
        return {"entry": None, "sl": None, "tp": None}

    signal_data = generate_signal(context)
    signal      = signal_data["signal"]
    price       = signal_data["current_price"]
    atr         = context["atr"]

    if signal == "BUY":
        return {
            "entry": price,
            "sl":    round(price - atr * 2.0, 2),
            "tp":    round(price + atr * 4.0, 2),
        }

    if signal == "SELL":
        return {
            "entry": price,
            "sl":    round(price + atr * 2.0, 2),
            "tp":    round(price - atr * 4.0, 2),
        }

    return {"entry": price, "sl": None, "tp": None}