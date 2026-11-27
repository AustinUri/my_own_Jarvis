"""Lexical matching shared by the cloud and desktop memory stores."""
import re


_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "my", "your", "our", "i", "me", "you", "we", "it", "this", "that",
    "what", "which", "who", "how", "do", "does", "did", "to", "of", "in",
    "on", "for", "and", "or", "with", "about", "from", "called", "name",
    "please", "can", "could", "would", "should",
    "של", "שלי", "שלך", "מה", "מי", "איך", "את", "אתה", "אני", "הוא",
    "היא", "זה", "זאת", "עם", "על", "אל", "לי", "לך", "לנו", "קוראים",
}


def memory_tokens(text: str) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[\w\u0590-\u05FF]+", text or "", flags=re.UNICODE)
        if len(token) >= 2 and token.casefold() not in _STOP_WORDS
    }
