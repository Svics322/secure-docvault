import bleach

def sanitize_user_input(text: str) -> str:
    if not text:
        return ""
    
    cleaned_text = bleach.clean(
        text,
        tags=[],
        strip=True
    )
    return cleaned_text.strip()