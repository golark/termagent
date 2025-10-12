"""Rules management for user-defined instructions and guidelines."""

import json
import os
from typing import List, Dict, Optional


class RulesManager:
    """Manages user-defined rules and guidelines."""
    
    def __init__(self, rules_file: str = None):
        if rules_file is None:
            rules_file = os.path.expanduser("~/.termagent/rules.json")
        
        self.rules_file = rules_file
        self.rules: List[Dict[str, str]] = self._load_rules()
    
    def _load_rules(self) -> List[Dict[str, str]]:
        """Load rules from file."""
        if not os.path.exists(self.rules_file):
            return []
        
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('rules', [])
        except (json.JSONDecodeError, IOError):
            return []
    
    def _save_rules(self) -> None:
        """Save rules to file."""
        os.makedirs(os.path.dirname(self.rules_file), exist_ok=True)
        
        data = {'rules': self.rules}
        with open(self.rules_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def add_rule(self, rule: str, description: str = None) -> int:
        """Add a new rule. Returns the rule ID."""
        rule_id = len(self.rules) + 1
        rule_entry = {
            'id': rule_id,
            'rule': rule,
            'description': description or ''
        }
        self.rules.append(rule_entry)
        self._save_rules()
        return rule_id
    
    def remove_rule(self, rule_id: int) -> bool:
        """Remove a rule by ID. Returns True if successful."""
        for i, rule in enumerate(self.rules):
            if rule['id'] == rule_id:
                self.rules.pop(i)
                self._save_rules()
                return True
        return False
    
    def get_rule(self, rule_id: int) -> Optional[Dict[str, str]]:
        """Get a specific rule by ID."""
        for rule in self.rules:
            if rule['id'] == rule_id:
                return rule
        return None
    
    def list_rules(self) -> List[Dict[str, str]]:
        """List all rules."""
        return self.rules.copy()
    
    def clear_all(self) -> None:
        """Clear all rules."""
        self.rules.clear()
        self._save_rules()
    
    def get_rules_text(self) -> str:
        """Get all rules as formatted text for system prompt."""
        if not self.rules:
            return ""
        
        text = "# User-Defined Rules\n"
        for rule in self.rules:
            if rule.get('description'):
                text += f"- {rule['rule']} ({rule['description']})\n"
            else:
                text += f"- {rule['rule']}\n"
        
        return text
    
    def has_rules(self) -> bool:
        """Check if any rules exist."""
        return len(self.rules) > 0


# Global instance
_rules_manager = None


def get_rules_manager() -> RulesManager:
    """Get or create the global rules manager instance."""
    global _rules_manager
    if _rules_manager is None:
        _rules_manager = RulesManager()
    return _rules_manager


def add_rule(rule: str, description: str = None) -> int:
    """Add a new rule. Returns the rule ID."""
    return get_rules_manager().add_rule(rule, description)


def remove_rule(rule_id: int) -> bool:
    """Remove a rule by ID. Returns True if successful."""
    return get_rules_manager().remove_rule(rule_id)


def list_rules() -> List[Dict[str, str]]:
    """List all rules."""
    return get_rules_manager().list_rules()


def get_rules_text() -> str:
    """Get all rules as formatted text for system prompt."""
    return get_rules_manager().get_rules_text()


def has_rules() -> bool:
    """Check if any rules exist."""
    return get_rules_manager().has_rules()

