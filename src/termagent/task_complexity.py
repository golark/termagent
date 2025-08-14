#!/usr/bin/env python3
"""
Task complexity analyzer for determining when to use GPT-4o vs GPT-3.5-turbo.
"""

import re
from typing import Dict, List, Tuple


class TaskComplexityAnalyzer:
    """Analyzes task complexity to determine the appropriate LLM model."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        
        # Keywords that indicate complex reasoning tasks
        self.complex_keywords = {
            'analyze', 'analyze', 'debug', 'troubleshoot', 'investigate', 'diagnose',
            'optimize', 'refactor', 'design', 'architect', 'plan', 'strategy',
            'algorithm', 'logic', 'reasoning', 'problem-solving', 'complex',
            'multi-step', 'multi step', 'complicated', 'sophisticated',
            'performance', 'efficiency', 'scalability', 'maintainability',
            'security', 'vulnerability', 'testing', 'validation', 'verification',
            'integration', 'deployment', 'configuration', 'setup', 'environment',
            'dependency', 'compatibility', 'migration', 'upgrade', 'downgrade',
            'backup', 'restore', 'recovery', 'monitoring', 'logging',
            'error handling', 'exception', 'edge case', 'corner case',
            'data analysis', 'statistics', 'metrics', 'reporting',
            'automation', 'scripting', 'workflow', 'pipeline',
            # Query-specific complex keywords
            'how to', 'what is the best way', 'why does', 'when should',
            'which approach', 'compare', 'difference between', 'similarities',
            'pros and cons', 'advantages', 'disadvantages', 'trade-offs',
            'best practices', 'recommendations', 'suggestions', 'alternatives',
            'considerations', 'implications', 'consequences', 'impact',
            'evaluation', 'assessment', 'review', 'analysis of'
        }
        
        # Keywords that indicate simple tasks
        self.simple_keywords = {
            'list', 'show', 'display', 'print', 'echo', 'cat', 'ls', 'dir',
            'count', 'find', 'search', 'grep', 'copy', 'cp', 'move', 'mv',
            'delete', 'rm', 'remove', 'create', 'mkdir', 'touch', 'new',
            'start', 'stop', 'restart', 'status', 'info', 'help',
            'install', 'uninstall', 'update', 'upgrade', 'downgrade',
            'check', 'verify', 'test', 'run', 'execute', 'launch'
        }
        
        # Patterns that indicate complex reasoning
        self.complex_patterns = [
            r'\b(why|how|what if|suppose|imagine|consider)\b',
            r'\b(if|when|unless|while|for|foreach)\b',
            r'\b(and|or|but|however|nevertheless|therefore)\b',
            r'\b(problem|issue|bug|error|failure|crash)\b',
            r'\b(improve|enhance|better|faster|more efficient)\b',
            r'\b(compare|contrast|difference|similarity)\b',
            r'\b(before|after|during|while|until)\b',
            r'\b(unless|otherwise|alternatively|instead)\b',
            r'\b(complex|complicated|sophisticated|advanced)\b',
            r'\b(multi.?step|multi.?stage|multi.?phase)\b',
            r'\b(conditional|dependent|interdependent)\b',
            r'\b(sequence|order|priority|dependency)\b',
            r'\b(analysis|investigation|research|study)\b',
            r'\b(design|architecture|structure|framework)\b',
            r'\b(optimization|performance|efficiency|scalability)\b',
            r'\b(security|vulnerability|threat|risk)\b',
            r'\b(testing|validation|verification|quality)\b',
            r'\b(integration|deployment|configuration|setup)\b',
            r'\b(automation|scripting|workflow|pipeline)\b',
            r'\b(monitoring|logging|alerting|tracking)\b',
            # Query-specific complex patterns
            r'\b(how to|what is the best way|why does|when should)\b',
            r'\b(which approach|compare|difference between|similarities)\b',
            r'\b(pros and cons|advantages|disadvantages|trade.?offs)\b',
            r'\b(best practices|recommendations|suggestions|alternatives)\b',
            r'\b(considerations|implications|consequences|impact)\b',
            r'\b(evaluation|assessment|review|analysis of)\b',
            r'\b(what would happen if|suppose that|imagine if)\b',
            r'\b(under what circumstances|in what situations)\b',
            r'\b(how would you|what would you recommend)\b',
            r'\b(explain why|describe how|analyze the)\b'
        ]
        
        # Patterns that indicate simple tasks
        self.simple_patterns = [
            r'\b(list|show|display|print|echo)\b',
            r'\b(count|find|search|grep)\b',
            r'\b(copy|move|delete|remove|create)\b',
            r'\b(start|stop|restart|status|info)\b',
            r'\b(install|uninstall|update|upgrade)\b',
            r'\b(check|verify|test|run|execute)\b',
            r'^\s*[a-z]+\s+[a-z0-9_.-]+\s*$',  # Simple command pattern
            r'^\s*[a-z]+\s+[a-z0-9_.-]+\s+[a-z0-9_.-]+\s*$',  # Command with 2 args
        ]
    
    def _debug_print(self, message: str):
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(f"complexity_analyzer | {message}")
    
    def analyze_complexity(self, task: str) -> Dict[str, any]:
        """Analyze the complexity of a task.
        
        Args:
            task: The task string to analyze
            
        Returns:
            Dictionary with complexity analysis results
        """
        task_lower = task.lower().strip()
        
        # Initialize scores
        complexity_score = 0
        reasoning_score = 0
        step_count_estimate = 1
        
        # Check for complex keywords
        complex_keyword_count = sum(1 for keyword in self.complex_keywords if keyword in task_lower)
        complexity_score += complex_keyword_count * 2
        
        # Check for simple keywords
        simple_keyword_count = sum(1 for keyword in self.simple_keywords if keyword in task_lower)
        complexity_score -= simple_keyword_count * 1
        
        # Check for complex patterns
        complex_pattern_count = sum(1 for pattern in self.complex_patterns if re.search(pattern, task_lower))
        complexity_score += complex_pattern_count * 3
        
        # Check for simple patterns
        simple_pattern_count = sum(1 for pattern in self.simple_patterns if re.search(pattern, task_lower))
        complexity_score -= simple_pattern_count * 2
        
        # Analyze reasoning requirements
        reasoning_indicators = [
            'why', 'how', 'what if', 'suppose', 'imagine', 'consider',
            'problem', 'issue', 'bug', 'error', 'failure', 'crash',
            'improve', 'enhance', 'better', 'faster', 'more efficient',
            'compare', 'contrast', 'difference', 'similarity',
            'unless', 'otherwise', 'alternatively', 'instead'
        ]
        
        reasoning_score = sum(1 for indicator in reasoning_indicators if indicator in task_lower)
        
        # Estimate step count based on complexity
        if complexity_score > 10:
            step_count_estimate = 3
        elif complexity_score > 5:
            step_count_estimate = 2
        else:
            step_count_estimate = 1
        
        # Determine if task requires complex reasoning
        requires_complex_reasoning = (
            complexity_score > 8 or 
            reasoning_score > 3 or 
            step_count_estimate > 2 or
            len(task.split()) > 15 or
            any(word in task_lower for word in ['debug', 'troubleshoot', 'investigate', 'analyze'])
        )
        
        # Determine recommended model
        recommended_model = "gpt-4o" if requires_complex_reasoning else "gpt-3.5-turbo"
        
        analysis = {
            'complexity_score': complexity_score,
            'reasoning_score': reasoning_score,
            'step_count_estimate': step_count_estimate,
            'requires_complex_reasoning': requires_complex_reasoning,
            'recommended_model': recommended_model,
            'complex_keywords_found': [k for k in self.complex_keywords if k in task_lower],
            'simple_keywords_found': [k for k in self.simple_keywords if k in task_lower],
            'word_count': len(task.split()),
            'reasoning_indicators': [i for i in reasoning_indicators if i in task_lower]
        }
        
        if self.debug:
            self._debug_print(f"Task: '{task}'")
            self._debug_print(f"Complexity score: {complexity_score}")
            self._debug_print(f"Reasoning score: {reasoning_score}")
            self._debug_print(f"Step count estimate: {step_count_estimate}")
            self._debug_print(f"Requires complex reasoning: {requires_complex_reasoning}")
            self._debug_print(f"Recommended model: {recommended_model}")
            self._debug_print(f"Complex keywords: {analysis['complex_keywords_found']}")
            self._debug_print(f"Simple keywords: {analysis['simple_keywords_found']}")
            self._debug_print(f"Reasoning indicators: {analysis['reasoning_indicators']}")
        
        return analysis
    
    def should_use_gpt4o(self, task: str) -> bool:
        """Determine if GPT-4o should be used for a task.
        
        Args:
            task: The task string to analyze
            
        Returns:
            True if GPT-4o should be used, False otherwise
        """
        analysis = self.analyze_complexity(task)
        return analysis['requires_complex_reasoning']
    
    def get_recommended_model(self, task: str) -> str:
        """Get the recommended LLM model for a task.
        
        Args:
            task: The task string to analyze
            
        Returns:
            Recommended model name
        """
        analysis = self.analyze_complexity(task)
        return analysis['recommended_model']
