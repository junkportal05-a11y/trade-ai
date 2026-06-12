import timeit
import re

articles = [
    {"title": "Company reports record profit and massive gain", "description": "The success and rise of the company is a great milestone. Very positive dividend."},
    {"title": "Huge loss and warning", "description": "The penalty and drop in revenue caused a massive slump and decline in debt."},
] * 100

bullish_keywords = [
    "profit", "gain", "rise", "grow", "deal", "win", "high", "success",
    "contract", "bullish", "jump", "surge", "expand", "order", "beat",
    "positive", "milestone", "acquire", "revenue", "up", "dividend"
]
bearish_keywords = [
    "loss", "fall", "drop", "fell", "concern", "cut", "decline", "warn",
    "bearish", "slump", "plunge", "fine", "penalty", "miss", "negative",
    "debt", "shrink", "investigation", "down", "slashed"
]

def original():
    score = 0.0
    for art in articles:
        text = (art.get("title", "") + " " + art.get("description", "")).lower()
        for k in bullish_keywords:
            if k in text:
                score += 0.25
        for k in bearish_keywords:
            if k in text:
                score -= 0.25
    return max(-1.0, min(1.0, score))

bullish_pattern = re.compile(r'\b(' + '|'.join(re.escape(k) for k in bullish_keywords) + r')\b')
bearish_pattern = re.compile(r'\b(' + '|'.join(re.escape(k) for k in bearish_keywords) + r')\b')

def optimized():
    score = 0.0
    for art in articles:
        text = (art.get("title", "") + " " + art.get("description", "")).lower()

        # count unique keywords found?
        # original code: adds 0.25 for each keyword that is present
        # so unique keywords present in the text

        bullish_matches = bullish_pattern.findall(text)
        score += len(set(bullish_matches)) * 0.25

        bearish_matches = bearish_pattern.findall(text)
        score -= len(set(bearish_matches)) * 0.25

    return max(-1.0, min(1.0, score))

def optimized_no_word_boundaries():
    # If we want to strictly match the original code's behavior (substring matching)
    score = 0.0
    bullish_pattern = re.compile('(' + '|'.join(re.escape(k) for k in bullish_keywords) + ')')
    bearish_pattern = re.compile('(' + '|'.join(re.escape(k) for k in bearish_keywords) + ')')

    for art in articles:
        text = (art.get("title", "") + " " + art.get("description", "")).lower()

        bullish_matches = bullish_pattern.findall(text)
        score += len(set(bullish_matches)) * 0.25

        bearish_matches = bearish_pattern.findall(text)
        score -= len(set(bearish_matches)) * 0.25

    return max(-1.0, min(1.0, score))

if __name__ == "__main__":
    orig_res = original()
    opt_res = optimized()
    opt_nw_res = optimized_no_word_boundaries()
    print(f"Results: Original={orig_res}, Opt={opt_res}, Opt no boundaries={opt_nw_res}")

    t1 = timeit.timeit(original, number=1000)
    t2 = timeit.timeit(optimized, number=1000)
    t3 = timeit.timeit(optimized_no_word_boundaries, number=1000)

    print(f"Original: {t1:.4f} seconds")
    print(f"Optimized (with word boundaries): {t2:.4f} seconds")
    print(f"Optimized (without word boundaries): {t3:.4f} seconds")
