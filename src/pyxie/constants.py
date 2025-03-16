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

"""Constants used throughout the Pyxie package."""

from datetime import datetime
from enum import Enum, auto
from typing import Literal

# Date formats
COMMON_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y",
    "%B %d, %Y"
]

# Default metadata
DEFAULT_METADATA = {
    "layout": "default",
    "author": "Anonymous",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "image_template": "https://picsum.photos/seed/{seed}/{width}/{height}",
    "image_width": 800,
    "image_height": 600
}

# Content types
ContentType = Literal["markdown", "ft", "raw", "latex"]
VALID_CONTENT_TYPES = {"markdown", "ft", "raw", "latex"}

class RequiredMetadata(Enum):
    """Required metadata fields."""
    TITLE = auto()
    LAYOUT = auto()
    DATE = auto()
    AUTHOR = auto() 