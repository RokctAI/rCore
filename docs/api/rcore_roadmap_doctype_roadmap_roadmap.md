# API Reference: roadmap

Source file: `rcore/roadmap/doctype/roadmap/roadmap.py`

## Classes

### class `Roadmap`

#### Documented Internal Methods
##### `before_save(self)`
On saving the Roadmap document, automatically update the AI and GitHub statuses
based on the current configuration.
