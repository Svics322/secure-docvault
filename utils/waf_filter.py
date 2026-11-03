import re
import logging

logger = logging.getLogger("waf_filter")

ATTACK_SIGNATURES = [
    (r"\.\.[\\/]", "Path Traversal Attack"),
    (r"(?i)(union\s+select|insert\s+into|drop\s+table|' OR '1'='1|--|/\*|exec\s+xp_)", "SQL Injection Signature"),
    (r"(?i)(<script|javascript:|onerror=|onload=)", "XSS Attack Signature"),
    (r"(?i)(\|\s*sh|\|\s*bash|cmd\.exe|system\(|exec\()", "Command Injection Signature")
]

def inspect_payload(content: str) -> tuple[bool, str]:
    if not content:
        return False, ""
    for pattern, desc in ATTACK_SIGNATURES:
        if re.search(pattern, content):
            return True, desc
    return False, ""

def inspect_request_data(url_path: str, query_params: str, body_text: str, client_ip: str) -> tuple[bool, str]:
    full_inspectable_data = f"{url_path}?{query_params}\n{body_text}"
    is_attack, attack_desc = inspect_payload(full_inspectable_data)
    
    if is_attack:
        logger.error(f"[WAF BLOCK] IP: {client_ip} | Attack: '{attack_desc}' | Path: {url_path}")
    
    return is_attack, attack_desc