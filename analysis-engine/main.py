from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

import time

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
    detect_liquidity_sweep,
    calculate_trade_levels,
    detect_session,
)

app = FastAPI(title="XAUUSD Analysis Engine", version="2.0.0")

templates = Jinja2Templates(directory="templates")

# =========================================
# CORS — necesario para el chart en browser
# =========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================
# CACHÉ EN MEMORIA (TTL = 60 segundos)
# =========================================

_cache: dict = {}
CACHE_TTL = 60  # segundos


def get_cached(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL:
        return entry["data"]
    return None


def set_cached(key: str, data):
    _cache[key] = {"data": data, "ts": time.time()}


# =========================================
# ERROR HANDLER GLOBAL
# =========================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# =========================================
# ROOT
# =========================================

@app.get("/")
def root():
    return {
        "status":  "ok",
        "service": "XAUUSD Analysis Engine",
        "version": "2.0.0",
        "endpoints": [
            "/analyze/xauusd",
            "/market-data/xauusd",
            "/chart",
        ]
    }


# =========================================
# ANALYSIS ENGINE
# =========================================

@app.get("/analyze/xauusd")
def analyze_xauusd():

    # Intentar desde caché primero
    cached = get_cached("analysis")
    if cached:
        return {**cached, "cached": True}

    context = build_market_context()

    if context is None:
        raise HTTPException(
            status_code=503,
            detail="Market data unavailable. Market may be closed or API is down."
        )

    trend        = detect_trend(context)
    swings       = detect_swings(context)
    fib_levels   = calculate_fibonacci(context)
    signal_data  = generate_signal(context)
    score_data   = calculate_score(context)
    bos          = detect_bos(context)
    engulfing    = detect_engulfing(context)
    sweep        = detect_liquidity_sweep(context)
    trade_levels = calculate_trade_levels(context)
    session      = detect_session()

    response = {
        "symbol":        "XAUUSD",
        "timeframe":     "M15",
        "session":       session,

        # Market context
        "market_state":  trend,
        "ema20":         context["ema20"],
        "ema50":         context["ema50"],
        "atr":           context["atr"],
        "rsi":           context["rsi"],

        # Structure
        "swing_high":    swings["swing_high"],
        "swing_low":     swings["swing_low"],

        # Fibonacci
        "fibonacci":     fib_levels,

        # Signal
        "signal":        signal_data["signal"],
        "reasons":       signal_data["reasons"],
        "current_price": signal_data["current_price"],

        # Confidence
        "score":         score_data["score"],
        "confidence":    score_data["confidence"],

        # Confirmations
        "bos":           bos,
        "engulfing":     engulfing,
        "sweep":         sweep,

        # Trade levels
        "entry":         trade_levels["entry"],
        "sl":            trade_levels["sl"],
        "tp":            trade_levels["tp"],

        "cached":        False,
    }

    set_cached("analysis", response)
    return response


# =========================================
# MARKET DATA (para gráfico de velas)
# =========================================

@app.get("/market-data/xauusd")
def market_data():

    cached = get_cached("candles")
    if cached:
        return cached

    data = get_market_data()

    if data is None:
        raise HTTPException(
            status_code=503,
            detail="Market data unavailable."
        )

    candles = []
    for index, row in data.iterrows():
        # timestamp Unix en segundos — requerido por lightweight-charts
        ts = int(index.timestamp())
        candles.append({
            "time":  ts,
            "open":  float(round(row["Open"],  2)),
            "high":  float(round(row["High"],  2)),
            "low":   float(round(row["Low"],   2)),
            "close": float(round(row["Close"], 2)),
        })

    set_cached("candles", candles)
    return candles


# =========================================
# CHART VIEW
# =========================================

@app.get("/chart", response_class=HTMLResponse)
def chart(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="chart.html",
    )