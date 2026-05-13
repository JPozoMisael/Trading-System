import yfinance as yf

from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange

from datetime import datetime


# =========================================
# MARKET DATA
# =========================================

def get_market_data():

    gold = yf.Ticker("GC=F")

    data = gold.history(
        period="1d",
        interval="15m"
    )

    return data


# =========================================
# MARKET CONTEXT
# =========================================

def build_market_context():

    data = get_market_data()

    # =====================================
    # EMA 20
    # =====================================

    ema20 = EMAIndicator(
        close=data["Close"],
        window=20
    ).ema_indicator()

    # =====================================
    # EMA 50
    # =====================================

    ema50 = EMAIndicator(
        close=data["Close"],
        window=50
    ).ema_indicator()

    # =====================================
    # ATR
    # =====================================

    atr = AverageTrueRange(
        high=data["High"],
        low=data["Low"],
        close=data["Close"],
        window=14
    ).average_true_range()

    # =====================================
    # ADD INDICATORS TO DATAFRAME
    # =====================================

    data["EMA20"] = ema20

    data["EMA50"] = ema50

    data["ATR"] = atr

    # =====================================
    # RETURN CONTEXT
    # =====================================

    return {

        "data": data,

        "current_price": round(
            data["Close"].iloc[-1],
            2
        ),

        "high": round(
            data["High"].max(),
            2
        ),

        "low": round(
            data["Low"].min(),
            2
        ),

        "ema20": round(
            data["EMA20"].iloc[-1],
            2
        ),

        "ema50": round(
            data["EMA50"].iloc[-1],
            2
        ),

        "atr": round(
            data["ATR"].iloc[-1],
            2
        )
    }


# =========================================
# SESSION DETECTION
# =========================================

def detect_session():

    current_hour = datetime.utcnow().hour

    # Asia
    if 0 <= current_hour < 7:
        return "ASIA"

    # London
    elif 7 <= current_hour < 13:
        return "LONDON"

    # New York
    elif 13 <= current_hour < 21:
        return "NEW_YORK"

    return "DEAD_ZONE"


# =========================================
# TREND DETECTION
# =========================================

def detect_trend(context):

    ema20 = context["ema20"]

    ema50 = context["ema50"]

    # Bullish
    if ema20 > ema50:
        return "BULLISH"

    # Bearish
    elif ema20 < ema50:
        return "BEARISH"

    return "RANGE"


# =========================================
# SWING DETECTION
# =========================================

def detect_swings(context):

    data = context["data"]

    swing_high = data["High"].max()

    swing_low = data["Low"].min()

    return {

        "swing_high": round(
            swing_high,
            2
        ),

        "swing_low": round(
            swing_low,
            2
        )
    }


# =========================================
# FIBONACCI LEVELS
# =========================================

def calculate_fibonacci(context):

    swings = detect_swings(context)

    high = swings["swing_high"]

    low = swings["swing_low"]

    difference = high - low

    fib_levels = {

        "0.236": round(
            high - (difference * 0.236),
            2
        ),

        "0.382": round(
            high - (difference * 0.382),
            2
        ),

        "0.5": round(
            high - (difference * 0.5),
            2
        ),

        "0.618": round(
            high - (difference * 0.618),
            2
        ),

        "0.786": round(
            high - (difference * 0.786),
            2
        )
    }

    return fib_levels


# =========================================
# BREAK OF STRUCTURE
# =========================================

def detect_bos(context):

    data = context["data"]

    highs = data["High"]

    lows = data["Low"]

    closes = data["Close"]

    previous_high = highs.iloc[-2]

    previous_low = lows.iloc[-2]

    current_close = closes.iloc[-1]

    # Bullish BOS
    if current_close > previous_high:
        return "BULLISH"

    # Bearish BOS
    elif current_close < previous_low:
        return "BEARISH"

    return "NONE"


# =========================================
# ENGULFING PATTERN
# =========================================

def detect_engulfing(context):

    data = context["data"]

    previous = data.iloc[-2]

    current = data.iloc[-1]

    prev_open = previous["Open"]

    prev_close = previous["Close"]

    curr_open = current["Open"]

    curr_close = current["Close"]

    # Bullish engulfing
    if (

        prev_close < prev_open

        and curr_close > curr_open

        and curr_open < prev_close

        and curr_close > prev_open
    ):

        return "BULLISH"

    # Bearish engulfing
    if (

        prev_close > prev_open

        and curr_close < curr_open

        and curr_open > prev_close

        and curr_close < prev_open
    ):

        return "BEARISH"

    return "NONE"


# =========================================
# LIQUIDITY SWEEP DETECTION
# =========================================

def detect_liquidity_sweep(context):

    data = context["data"]

    previous = data.iloc[-2]

    current = data.iloc[-1]

    prev_high = previous["High"]

    prev_low = previous["Low"]

    curr_high = current["High"]

    curr_low = current["Low"]

    curr_close = current["Close"]

    # =====================================
    # BEARISH SWEEP
    # =====================================

    if (

        curr_high > prev_high

        and curr_close < prev_high
    ):

        return "BEARISH"

    # =====================================
    # BULLISH SWEEP
    # =====================================

    elif (

        curr_low < prev_low

        and curr_close > prev_low
    ):

        return "BULLISH"

    return "NONE"


# =========================================
# SIGNAL ENGINE
# =========================================

def generate_signal(context):

    trend = detect_trend(context)

    fib = calculate_fibonacci(context)

    engulfing = detect_engulfing(context)

    bos = detect_bos(context)

    sweep = detect_liquidity_sweep(context)

    current_price = context["current_price"]

    atr = context["atr"]

    session = detect_session()

    fib_618 = fib["0.618"]

    fib_786 = fib["0.786"]

    signal = "WAIT"

    reasons = []

    # =====================================
    # DEAD SESSION FILTER
    # =====================================

    if session == "DEAD_ZONE":

        reasons.append("Dead market session")

    # =====================================
    # LOW VOLATILITY FILTER
    # =====================================

    if atr < 5:

        reasons.append("Low volatility ATR")

    # =====================================
    # TREND CHECK
    # =====================================

    if trend == "RANGE":

        reasons.append("Market in range")

    # =====================================
    # BOS CHECK
    # =====================================

    if bos == "NONE":

        reasons.append("No BOS detected")

    # =====================================
    # LIQUIDITY SWEEP CHECK
    # =====================================

    if sweep == "NONE":

        reasons.append(
            "No liquidity sweep detected"
        )

    # =====================================
    # ENGULFING CHECK
    # =====================================

    if engulfing == "NONE":

        reasons.append("No engulfing pattern")

    # =====================================
    # FIB CHECK
    # =====================================

    fib_zone_valid = (
        fib_786 <= current_price <= fib_618
        or
        fib_618 <= current_price <= fib_786
    )

    if not fib_zone_valid:

        reasons.append(
            "Price outside Fibonacci zone"
        )

    # =====================================
    # BUY SETUP
    # =====================================

    if (

        trend == "BULLISH"

        and fib_786 <= current_price <= fib_618

        and engulfing == "BULLISH"

        and (
            bos == "BULLISH"
            or
            sweep == "BULLISH"
        )

        and atr >= 5
    ):

        signal = "BUY"

        reasons = [
            "Bullish setup confirmed"
        ]

    # =====================================
    # SELL SETUP
    # =====================================

    elif (

        trend == "BEARISH"

        and fib_618 <= current_price <= fib_786

        and engulfing == "BEARISH"

        and (
            bos == "BEARISH"
            or
            sweep == "BEARISH"
        )

        and atr >= 5
    ):

        signal = "SELL"

        reasons = [
            "Bearish setup confirmed"
        ]

    return {

        "signal": signal,

        "current_price": current_price,

        "reasons": reasons
    }


# =========================================
# CONFIDENCE ENGINE
# =========================================

def calculate_score(context):

    trend = detect_trend(context)

    signal_data = generate_signal(context)

    atr = context["atr"]

    session = detect_session()

    score = 0

    # Trend score
    if trend == "BULLISH":
        score += 2

    elif trend == "BEARISH":
        score += 2

    # Signal score
    if signal_data["signal"] != "WAIT":
        score += 3

    # Volatility score
    if atr > 8:
        score += 2

    # Session score
    if session == "LONDON":
        score += 2

    elif session == "NEW_YORK":
        score += 3

    # Low volatility penalty
    if atr < 5:
        score -= 3

    confidence = min(
        max(score * 10, 0),
        100
    )

    return {

        "score": score,

        "confidence": confidence
    }


# =========================================
# TRADE LEVELS
# =========================================

def calculate_trade_levels(context):

    signal_data = generate_signal(context)

    signal = signal_data["signal"]

    current_price = signal_data["current_price"]

    atr = context["atr"]

    sl = None

    tp = None

    # Buy levels
    if signal == "BUY":

        sl = round(
            current_price - (atr * 1.5),
            2
        )

        tp = round(
            current_price + (atr * 3),
            2
        )

    # Sell levels
    elif signal == "SELL":

        sl = round(
            current_price + (atr * 1.5),
            2
        )

        tp = round(
            current_price - (atr * 3),
            2
        )

    return {

        "entry": current_price,

        "sl": sl,

        "tp": tp
    }