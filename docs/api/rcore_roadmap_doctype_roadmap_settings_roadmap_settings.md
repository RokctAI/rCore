# API Reference: roadmap_settings

Source file: `rcore/roadmap/doctype/roadmap_settings/roadmap_settings.py`

## Classes

### class `RoadmapSettings`

#### Documented Internal Methods
##### `before_save(self)`
On saving the Roadmap Settings, automatically generate a GitHub Action Secret
if one does not already exist, and populate default security prompts.
