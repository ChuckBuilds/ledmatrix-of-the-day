#!/usr/bin/env python3
"""
Helper functions to update plugin configuration.
Adds or removes categories from the plugin config.
"""

import os
import json
from pathlib import Path

LEDMATRIX_ROOT = os.environ.get('LEDMATRIX_ROOT', os.getcwd())
config_file = Path(LEDMATRIX_ROOT) / 'config' / 'config.json'

def load_config():
    """Load the main configuration file."""
    if not config_file.exists():
        return {}
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    """Save the configuration file."""
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def add_category_to_config(category_name, data_file, display_name):
    """Add a category to the plugin configuration."""
    config = load_config()
    
    # Get plugin config or create it
    plugin_config = config.get('of-the-day', {})
    
    # Get categories or create it
    categories = plugin_config.get('categories', {})
    
    # Add category
    categories[category_name] = {
        'enabled': True,
        'data_file': data_file,
        'display_name': display_name
    }
    
    plugin_config['categories'] = categories
    
    # Add to category_order if not present
    category_order = plugin_config.get('category_order', [])
    if category_name not in category_order:
        category_order.append(category_name)
    plugin_config['category_order'] = category_order
    
    # Save back to config
    config['of-the-day'] = plugin_config
    save_config(config)

def remove_category_from_config(category_name):
    """Remove a category from the plugin configuration."""
    config = load_config()
    
    plugin_config = config.get('of-the-day', {})
    if not plugin_config:
        return
    
    # Remove from categories
    categories = plugin_config.get('categories', {})
    if category_name in categories:
        del categories[category_name]
    plugin_config['categories'] = categories
    
    # Remove from category_order
    category_order = plugin_config.get('category_order', [])
    if category_name in category_order:
        category_order.remove(category_name)
    plugin_config['category_order'] = category_order
    
    # Save back to config
    config['of-the-day'] = plugin_config
    save_config(config)

