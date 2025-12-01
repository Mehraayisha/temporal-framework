"""
Logging configuration for the temporal framework
"""
import logging
import logging.config
import os
from datetime import datetime

def setup_logging():
    """Configure logging for the temporal framework"""
    
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Generate log filename with timestamp
    log_filename = f"temporal_framework_{datetime.now().strftime('%Y%m%d')}.log"
    log_path = os.path.join(logs_dir, log_filename)
    
    audit_filename = f"audit_{datetime.now().strftime('%Y%m%d')}.log"
    audit_path = os.path.join(logs_dir, audit_filename)
    
    security_filename = f"security_{datetime.now().strftime('%Y%m%d')}.log"
    security_path = os.path.join(logs_dir, security_filename)
    
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(asctime)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'audit': {
                'format': '%(asctime)s - AUDIT - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'security': {
                'format': '%(asctime)s - SECURITY - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'simple',
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.FileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': log_path,
                'mode': 'a',
                'encoding': 'utf-8'
            },
            'audit': {
                'class': 'logging.FileHandler',
                'level': 'INFO',
                'formatter': 'audit',
                'filename': audit_path,
                'mode': 'a',
                'encoding': 'utf-8'
            },
            'security': {
                'class': 'logging.FileHandler',
                'level': 'WARNING',
                'formatter': 'security',
                'filename': security_path,
                'mode': 'a',
                'encoding': 'utf-8'
            }
        },
        'loggers': {
            'temporal_framework': {
                'level': 'DEBUG',
                'handlers': ['console', 'file'],
                'propagate': False
            },
            'temporal_framework.audit': {
                'level': 'INFO',
                'handlers': ['audit'],
                'propagate': False
            },
            'temporal_framework.security': {
                'level': 'WARNING',
                'handlers': ['security', 'console'],
                'propagate': False
            },
            'temporal_framework.policy': {
                'level': 'DEBUG',
                'handlers': ['console', 'file'],
                'propagate': False
            },
            'temporal_framework.graphiti': {
                'level': 'INFO',
                'handlers': ['console', 'file'],
                'propagate': False
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console']
        }
    }
    
    logging.config.dictConfig(logging_config)
    
    # Return commonly used loggers
    return {
        'main': logging.getLogger('temporal_framework'),
        'audit': logging.getLogger('temporal_framework.audit'),
        'security': logging.getLogger('temporal_framework.security'),
        'policy': logging.getLogger('temporal_framework.policy'),
        'graphiti': logging.getLogger('temporal_framework.graphiti')
    }

# Initialize loggers
loggers = setup_logging()