from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.market_service import (
    get_market_data,
    build_market_context,
    detect_trend,
    detect_swings,
    calculate_fibonacci,
    generate_signal,
    calculate_score,
    detect_bos,
    detect_engulfing,
    calculate_trade_levels
)

app = FastAPI()

templates = Jinja2Templates(directory="templates")


# =========================================
# ROOT
# =========================================

@app.get("/")
def root():

    return {
        "status": "ok",
        "service": "analysis-engine"
    }


# =========================================
# ANALYSIS ENGINE
# =========================================

@app.get("/analyze/xauusd")
def analyze_xauusd():

    # =====================================
    # BUILD CONTEXT
    # =====================================

    context = build_market_context()

    # =====================================
    # TREND
    # =====================================

    trend = detect_trend(context)

    # =====================================
    # MARKET STRUCTURE
    # =====================================

    swings = detect_swings(context)

    # =====================================
    # FIBONACCI
    # =====================================

    fib_levels = calculate_fibonacci(context)

    # =====================================
    # SIGNAL ENGINE
    # =====================================

    signal_data = generate_signal(context)

    # =====================================
    # CONFIDENCE ENGINE
    # =====================================

    score_data = calculate_score(context)

    # =====================================
    # BREAK OF STRUCTURE
    # =====================================

    bos = detect_bos(context)

    # =====================================
    # CANDLESTICK PATTERNS
    # =====================================

    engulfing = detect_engulfing(context)

    # =====================================
    # TRADE LEVELS
    # =====================================

    trade_levels = calculate_trade_levels(context)

    # =====================================
    # RESPONSE
    # =====================================

    return {

        "symbol": "XAUUSD",

        "timeframe": "M15",

        # =================================
        # MARKET CONTEXT
        # =================================

        "market_state": trend,

        # =================================
        # STRUCTURE
        # =================================

        "swing_high": swings["swing_high"],

        "swing_low": swings["swing_low"],

        # =================================
        # FIBONACCI
        # =================================

        "fibonacci": fib_levels,

        # =================================
        # SIGNAL
        # =================================

        "signal": signal_data["signal"],

        "current_price": signal_data["current_price"],

        # =================================
        # CONFIDENCE
        # =================================

        "score": score_data["score"],

        "confidence": score_data["confidence"],

        # =================================
        # CONFIRMATION
        # =================================

        "bos": bos,

        "engulfing": engulfing,

        # =================================
        # TRADE LEVELS
        # =================================

        "entry": trade_levels["entry"],

        "sl": trade_levels["sl"],

        "tp": trade_levels["tp"]
    }


# =========================================
# MARKET DATA
# =========================================

@app.get("/market-data/xauusd")
def market_data():

    data = get_market_data()

    candles = []

    for index, row in data.iterrows():

        candles.append({

            "time": index.strftime("%Y-%m-%d"),

            "open": float(round(row["Open"], 2)),

            "high": float(round(row["High"], 2)),

            "low": float(round(row["Low"], 2)),

            "close": float(round(row["Close"], 2))
        })

    return candles


# =========================================
# CHART VIEW
# =========================================

@app.get("/chart", response_class=HTMLResponse)
def chart(request: Request):

    return templates.TemplateResponse(
        "chart.html",
        {
            "request": request
        }
    )