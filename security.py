import re
import time
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from collections import defaultdict
import html

class SecurityManager:
    def __init__(self):
        self.rate_limit_window = 3600  # 1 hour
        self.max_requests_per_hour = 100
        self.max_message_length = 5000
        self.suspicious_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe.*?>',
            r'<object.*?>',
            r'<embed.*?>',
            r'<form.*?>',
            r'<input.*?>',
            r'<textarea.*?>',
            r'<select.*?>',
            r'<button.*?>',
            r'<link.*?>',
            r'<meta.*?>',
            r'<style.*?>',
            r'<title.*?>',
            r'<base.*?>',
            r'<bgsound.*?>',
            r'<link.*?>',
            r'<meta.*?>',
            r'<style.*?>',
            r'<title.*?>',
            r'<base.*?>',
            r'<bgsound.*?>',
            r'<link.*?>',
            r'<meta.*?>',
            r'<style.*?>',
            r'<title.*?>',
            r'<base.*?>',
            r'<bgsound.*?>',
        ]
        
        # Rate limiting storage (in production, use Redis)
        self.request_counts = defaultdict(list)
        self.blocked_ips = set()
        self.suspicious_ips = defaultdict(int)
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize user input to prevent XSS and injection attacks"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Escape HTML entities
        text = html.escape(text)
        
        # Remove suspicious patterns
        for pattern in self.suspicious_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def validate_message(self, message: str) -> bool:
        """Validate message content and length"""
        if not message or not message.strip():
            return False
        
        if len(message) > self.max_message_length:
            return False
        
        # Check for suspicious content - compare sanitized with stripped original
        sanitized = self.sanitize_input(message)
        stripped_original = message.strip()
        if sanitized != stripped_original:
            return False
        
        return True
    
    def check_rate_limit(self, user_id: int, ip_address: str = None) -> bool:
        """Check if user has exceeded rate limit"""
        current_time = time.time()
        
        # Clean old requests
        cutoff_time = current_time - self.rate_limit_window
        
        # Check user-based rate limiting
        user_requests = self.request_counts[f"user_{user_id}"]
        user_requests = [req for req in user_requests if req > cutoff_time]
        self.request_counts[f"user_{user_id}"] = user_requests
        
        if len(user_requests) >= self.max_requests_per_hour:
            return False
        
        # Check IP-based rate limiting (if IP provided)
        if ip_address:
            ip_requests = self.request_counts[f"ip_{ip_address}"]
            ip_requests = [req for req in ip_requests if req > cutoff_time]
            self.request_counts[f"ip_{ip_address}"] = ip_requests
            
            if len(ip_requests) >= self.max_requests_per_hour * 2:  # Higher limit for IP
                return False
        
        return True
    
    def record_request(self, user_id: int, ip_address: str = None):
        """Record a request for rate limiting"""
        current_time = time.time()
        
        self.request_counts[f"user_{user_id}"].append(current_time)
        
        if ip_address:
            self.request_counts[f"ip_{ip_address}"].append(current_time)
    
    def detect_suspicious_activity(self, message: str, user_id: int, ip_address: str = None) -> bool:
        """Detect potentially suspicious activity"""
        suspicious_score = 0
        
        # Check for suspicious patterns in message
        for pattern in self.suspicious_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                suspicious_score += 10
        
        # Check for excessive repetition
        words = message.lower().split()
        if len(words) > 10:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            max_repetition = max(word_counts.values()) if word_counts else 0
            if max_repetition > len(words) * 0.3:  # More than 30% repetition
                suspicious_score += 5
        
        # Check for rapid requests
        current_time = time.time()
        user_requests = self.request_counts[f"user_{user_id}"]
        recent_requests = [req for req in user_requests if req > current_time - 60]  # Last minute
        
        if len(recent_requests) > 10:  # More than 10 requests per minute
            suspicious_score += 15
        
        # Record suspicious activity
        if suspicious_score > 5:
            if ip_address:
                self.suspicious_ips[ip_address] += 1
            
            # Block if too suspicious
            if suspicious_score > 20:
                if ip_address:
                    self.blocked_ips.add(ip_address)
                return True
        
        return False
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked"""
        return ip_address in self.blocked_ips
    
    def validate_session(self, session_id: str) -> bool:
        """Validate session ID format"""
        # UUID format validation
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, session_id))
    
    def sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize conversation context"""
        if not context:
            return {}
        
        sanitized_context = {}
        
        for key, value in context.items():
            if isinstance(value, str):
                sanitized_context[key] = self.sanitize_input(value)
            elif isinstance(value, dict):
                sanitized_context[key] = self.sanitize_context(value)
            elif isinstance(value, list):
                sanitized_context[key] = [
                    self.sanitize_input(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized_context[key] = value
        
        return sanitized_context
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        current_time = time.time()
        cutoff_time = current_time - self.rate_limit_window
        
        # Count active requests
        active_requests = 0
        for requests in self.request_counts.values():
            active_requests += len([req for req in requests if req > cutoff_time])
        
        return {
            "blocked_ips": len(self.blocked_ips),
            "suspicious_ips": len(self.suspicious_ips),
            "active_requests": active_requests,
            "rate_limit_window": self.rate_limit_window,
            "max_requests_per_hour": self.max_requests_per_hour
        }

# Initialize global security manager
security_manager = SecurityManager() 