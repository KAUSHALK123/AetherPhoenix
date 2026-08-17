# PPT Generator Module Documentation

The `ppt_tool` module allows the Worker Agent to generate structured PowerPoint presentations (.pptx) from validated content schemas. It integrates safety mechanisms, output file validation, and consistent design layouts.

---

## 1. Architectural Overview

```
              +-------------------------+
              |      Worker Agent       |
              +------------+------------+
                           |
                           v
              +------------+------------+
              |     PPTGenerator        |
              +------+-----------+------+
                     |           |
                     | 1. Request Permission
                     |           v
                     |     +-----+-------------------+
                     |     |    PermissionManager    |
                     |     |  (FILE_SYSTEM permission)|
                     |     +-----+-------------------+
                     |           |
                     |           | 2. Approved (GRANTED)
                     |           v
                     |     +-----+-------------------+
                     +---->|      python-pptx        |
                           +-----------+-------------+
                                       |
                                       | 3. Save & Validate
                                       v
                           +-----------+-------------+
                           |       Output PPTX       |
                           +-------------------------+
```

1. **Permission Check**: Before writing files, the generator requests `FILE_SYSTEM` permission from the `PermissionManager`.
2. **Layout Generation**: Converts a Pydantic `PresentationSchema` into slides using the `python-pptx` library.
3. **Basic Typography**: Applies standard formatting (Arial font, size adjustments, colors) to titles and bullets.
4. **Validation**: Re-loads the generated file to ensure it is not corrupt and has the expected slide counts.

---

## 2. Schemas

The following models are defined in [ppt.py](file:///c:/Users/kruthin/AetherPhoenix/backend/app/schemas/ppt.py):

*   **`SlideType` (Enum)**:
    *   `title`: Used for title pages (uses slide layout `0`).
    *   `content`: Used for standard content and bullet points (uses slide layout `1`).
*   **`SlideContent` (BaseModel)**:
    *   `slide_type`: The layout style.
    *   `title`: The slide header text.
    *   `subtitle`: Optional subtitle (title slides).
    *   `bullets`: List of string bullet points (content slides).
    *   `speaker_notes`: Optional speaker notes text.
*   **`PresentationSchema` (BaseModel)**:
    *   `title`: Presentation document title.
    *   `subtitle`: Optional document subtitle.
    *   `slides`: List of `SlideContent` items.
*   **`PPTGenerationResult` (BaseModel)**:
    *   `file_path`: Absolute path to the generated PPTX file.
    *   `file_size`: File size in bytes.
    *   `slide_count`: Number of compiled slides.
    *   `generated_at`: UTC timestamp of generation.

---

## 3. Registration in Tool Registry

The `ppt_tool` is registered with the following metadata:

*   **Name**: `ppt_tool`
*   **Adapter**: `app.tools.ppt.generator.PPTGenerator`
*   **Dependencies**: `["python-pptx"]`
*   **Required Permissions**: `["FILE_SYSTEM"]`

---

## 4. Usage Example

```python
from uuid import uuid4
from app.tools.ppt import PPTGenerator
from app.schemas.ppt import PresentationSchema, SlideContent, SlideType

generator = PPTGenerator()

# 1. Prepare structured data
presentation_data = PresentationSchema(
    title="Quarterly Review",
    subtitle="Q3 Performance Metrics",
    slides=[
        SlideContent(
            slide_type=SlideType.TITLE,
            title="Q3 Review",
            subtitle="Confidential Presentation"
        ),
        SlideContent(
            slide_type=SlideType.CONTENT,
            title="Key Takeaways",
            bullets=[
                "Increased active users by 15%",
                "Reduced runtime latency by 200ms",
                "Successfully introduced self-healing architecture"
            ],
            speaker_notes="Focus on the self-healing stats."
        )
    ]
)

# 2. Compile to PPTX
result = generator.generate(
    presentation=presentation_data,
    output_path="outputs/q3_review.pptx",
    workflow_id=uuid4()
)

print(f"Presentation generated at {result.file_path} (size: {result.file_size} bytes)")
```

---

## 5. Security & Verification

*   **Permission Enforcement**: Attempts to generate files without a `GRANTED` permission status will throw `PermissionDeniedException`.
*   **Automated Validation**: Re-reading output files detects corrupted or incomplete writes early.
