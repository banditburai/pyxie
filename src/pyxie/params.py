# Copyright 2025 firefly
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License. 

"""Parameter parsing utilities for Pyxie."""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from .utilities import log

logger = logging.getLogger(__name__)

# Regex pattern for parameter parsing
PARAM_PATTERN = re.compile(r'(\w+(?:-\w+)*)=(?:"([^"]+)"|\'([^\']+)\'|(\S+))')

def normalize_class_attr(params: Dict[str, str]) -> Dict[str, str]:
    """Normalize class/cls attributes to use class consistently."""
    if 'cls' in params and 'class' not in params:
        params['class'] = params.pop('cls')
    return params

def parse_params(params_str: Optional[str]) -> Dict[str, str]:
    """Parse key=value parameters from a string.
    
    Example:
        >>> parse_params('class="hero" id=main data-type=\'custom\'')
        {'class': 'hero', 'id': 'main', 'data-type': 'custom'}
        >>> parse_params('cls="hero"')  # cls is converted to class
        {'class': 'hero'}
    """
    if not params_str:
        return {}
    
    params = {}
    matches = PARAM_PATTERN.finditer(params_str.strip())
    
    for match in matches:
        key = match.group(1)
        # Take first non-None value from capture groups 2-4
        value = next(v for v in match.groups()[1:] if v is not None)
        params[key] = value
        log(logger, "Params", "debug", "parse", f"Parsed parameter: {key}={value}")
    
    # Normalize class attributes
    params = normalize_class_attr(params)
    
    return params

def format_params(params: Dict[str, Any]) -> str:
    """Format parameters as a string.
    
    Example:
        >>> format_params({'class': 'hero', 'id': 'main'})
        'class="hero" id=main'
    """
    # Normalize class attributes
    params = normalize_class_attr(dict(params))
    
    parts = []
    for key, value in sorted(params.items()):
        if value is None:
            continue
        value_str = str(value)
        if " " in value_str:
            value_str = f'"{value_str}"'
        parts.append(f"{key}={value_str}")
    
    return " ".join(parts) 