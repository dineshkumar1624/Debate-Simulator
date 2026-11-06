import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class OCRLineSchema(BaseModel):
    text: str = Field(..., description="Verbatim optical character recognition line text")
    confidence: float = Field(default=90.0, description="OCR recognition confidence (0-100 or 0-1)")
    box: Optional[List[List[int]]] = Field(
        default=None,
        description="4 corner bounding box coordinates [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]"
    )

class VisualEvidenceItemSchema(BaseModel):
    id: str = Field(default_factory=lambda: f"img-ev-{uuid.uuid4().hex[:6]}", description="Unique visual evidence identifier (e.g. img-ev-1)")
    label: str = Field(..., description="Short descriptive title of the visual evidence")
    type: str = Field(
        default="visible_data",
        description="Type of evidence: visible_data, ocr_label, chart_trend, diagram_element, uncertainty"
    )
    location: str = Field(
        default="center",
        description="Spatial coordinates or descriptive position (e.g. top-left, center blue box, legend)"
    )
    content: str = Field(..., description="Factual description grounded directly in the visual evidence")
    confidence: float = Field(default=90.0, description="Confidence score (0-100)")

class ImageDimensionsSchema(BaseModel):
    width: int
    height: int
    format: str
    mode: str
    megapixels: float
    aspect_ratio: str

class ImageUnderstandingRepresentation(BaseModel):
    image_id: str
    filename: str
    dimensions: ImageDimensionsSchema
    summary: str
    ocr_text: str
    ocr_lines: List[OCRLineSchema] = Field(default_factory=list)
    visual_observations: List[str] = Field(default_factory=list)
    key_entities: List[str] = Field(default_factory=list)
    numerical_values: List[str] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list)
    evidence_items: List[VisualEvidenceItemSchema] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    file_path: Optional[str] = None

