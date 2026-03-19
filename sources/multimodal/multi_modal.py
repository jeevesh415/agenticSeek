"""
Multi-Modal Processing Module for agenticSeek
Vision, audio, document, and video understanding
Based on latest 2026 multi-modal AI advancements
"""

import asyncio
import json
import logging
import base64
import io
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class ModalityType(Enum):
    """Types of modalities supported"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    CODE = "code"
    STRUCTURED = "structured"  # JSON, CSV, etc.


@dataclass
class MultiModalInput:
    """Represents a multi-modal input"""
    modality: ModalityType
    content: Any  # str for text, bytes for binary
    metadata: Dict[str, Any] = field(default_factory=dict)
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if isinstance(self.modality, str):
            self.modality = ModalityType(self.modality)


@dataclass
class ProcessingResult:
    """Result of multi-modal processing"""
    modality: ModalityType
    summary: str
    entities: List[Dict[str, Any]] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_output: Any = None


@dataclass
class MultiModalAnalysis:
    """Complete multi-modal analysis"""
    inputs: List[MultiModalInput]
    results: List[ProcessingResult]
    cross_modal_insights: List[str] = field(default_factory=list)
    unified_summary: str = ""
    recommendations: List[str] = field(default_factory=list)


class VisionProcessor:
    """
    Vision processing for images and screenshots
    Capabilities: OCR, object detection, scene understanding, chart analysis
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        self.llm = llm_client
        
    async def process_image(
        self,
        image_data: Union[bytes, str],  # bytes or base64
        task: str = "describe",
        include_ocr: bool = True,
        include_objects: bool = True
    ) -> ProcessingResult:
        """
        Process an image and extract information
        """
        # Convert to base64 if needed
        if isinstance(image_data, bytes):
            image_b64 = base64.b64encode(image_data).decode()
        else:
            image_b64 = image_data
        
        # Determine specific processing based on task
        prompts = {
            "describe": self._describe_prompt(),
            "analyze_chart": self._chart_analysis_prompt(),
            "read_text": self._ocr_prompt(),
            "detect_objects": self._object_detection_prompt(),
            "understand_ui": self._ui_analysis_prompt()
        }
        
        prompt = prompts.get(task, prompts["describe"])
        
        # Call vision-capable LLM
        if self.llm:
            response = await self._call_vision_llm(prompt, image_b64)
        else:
            response = {"summary": "No LLM configured for vision processing"}
        
        return ProcessingResult(
            modality=ModalityType.IMAGE,
            summary=response.get("summary", ""),
            entities=response.get("entities", []),
            key_points=response.get("key_points", []),
            confidence=response.get("confidence", 0.8),
            metadata=response.get("metadata", {}),
            raw_output=response
        )
    
    def _describe_prompt(self) -> str:
        """Prompt for general image description"""
        return """Analyze this image thoroughly. Provide:
1. A detailed description of what's in the image
2. Key objects and their positions
3. Any text visible (OCR)
4. The overall context or setting
5. Notable colors, emotions, or themes

Format as JSON with keys: summary, entities, key_points, confidence, metadata"""
    
    def _chart_analysis_prompt(self) -> str:
        """Prompt for chart/graph analysis"""
        return """Analyze this chart or graph in detail. Provide:
1. Type of chart (bar, line, pie, etc.)
2. Title and labels
3. Key data points and trends
4. Notable patterns or anomalies
5. Conclusions you can draw

Format as JSON with keys: summary, data_points, trends, conclusions, confidence"""
    
    def _ocr_prompt(self) -> str:
        """Prompt for OCR-focused analysis"""
        return """Perform OCR on this image and extract ALL text visible.
Return the exact text content, maintaining reading order.
Note any formatting, headers, or special text.

Format as JSON with keys: full_text, partial_text, format_notes, confidence"""
    
    def _object_detection_prompt(self) -> str:
        """Prompt for object detection"""
        return """Detect and list all objects in this image.
For each object provide:
- Object name
- Position (if discernible)
- Size relative to image
- Any notable characteristics

Format as JSON with keys: objects (list with name, position, size, characteristics), confidence"""
    
    def _ui_analysis_prompt(self) -> str:
        """Prompt for UI/screenshot analysis"""
        return """Analyze this UI screenshot or interface. Provide:
1. Type of interface (web, mobile, desktop)
2. Key UI elements identified
3. Layout structure
4. Any interactive elements
5. Overall usability observations

Format as JSON with keys: ui_type, elements, layout, interactions, observations"""
    
    async def _call_vision_llm(self, prompt: str, image_b64: str) -> Dict[str, Any]:
        """Call LLM with image"""
        try:
            response = await self.llm.generate(
                prompt=prompt,
                image=image_b64
            )
            if isinstance(response, str):
                return json.loads(response)
            return response
        except Exception as e:
            logger.error(f"Vision LLM call failed: {e}")
            return {"summary": str(e), "confidence": 0.0}


class AudioProcessor:
    """
    Audio processing for speech and sound
    Capabilities: transcription, translation, sentiment analysis, speaker identification
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        self.llm = llm_client
        
    async def process_audio(
        self,
        audio_data: bytes,
        task: str = "transcribe",
        language: Optional[str] = None
    ) -> ProcessingResult:
        """
        Process audio data
        """
        # Convert to base64 for transport
        audio_b64 = base64.b64encode(audio_data).decode()
        
        prompts = {
            "transcribe": self._transcription_prompt(language),
            "translate": self._translation_prompt(language),
            "sentiment": self._sentiment_prompt(),
            "summarize": self._summary_prompt()
        }
        
        prompt = prompts.get(task, prompts["transcribe"])
        
        if self.llm:
            response = await self._call_audio_llm(prompt, audio_b64)
        else:
            response = {"summary": "No LLM configured for audio processing"}
        
        return ProcessingResult(
            modality=ModalityType.AUDIO,
            summary=response.get("summary", ""),
            entities=response.get("entities", []),
            key_points=response.get("key_points", []),
            confidence=response.get("confidence", 0.8),
            metadata=response.get("metadata", {}),
            raw_output=response
        )
    
    def _transcription_prompt(self, language: Optional[str]) -> str:
        lang_note = f" (Language: {language})" if language else ""
        return f"""Transcribe this audio{lang_note}. Provide:
1. Full transcript with timestamps
2. Speaker identification if multiple speakers
3. Any non-speech sounds noted
4. Audio quality observations

Format as JSON with keys: transcript, speakers, non_speech, quality, confidence"""
    
    def _translation_prompt(self, target_language: Optional[str]) -> str:
        target = target_language or "English"
        return f"""Transcribe and translate this audio to {target}. Provide:
1. Original transcript
2. Translated transcript
3. Any cultural context notes
4. Translation challenges noted

Format as JSON with keys: original, translation, context, challenges, confidence"""
    
    def _sentiment_prompt(self) -> str:
        return """Analyze the sentiment and emotion in this audio. Provide:
1. Overall sentiment (positive, negative, neutral)
2. Emotion categories detected
3. Speaker emotional states
4. Intensity of emotions

Format as JSON with keys: sentiment, emotions, speaker_states, intensity, confidence"""
    
    def _summary_prompt(self) -> str:
        return """Summarize this audio content. Provide:
1. Main topics discussed
2. Key points and arguments
3. Important details
4. Conclusions or outcomes

Format as JSON with keys: topics, key_points, details, conclusions, confidence"""
    
    async def _call_audio_llm(self, prompt: str, audio_b64: str) -> Dict[str, Any]:
        """Call LLM with audio"""
        try:
            response = await self.llm.generate(
                prompt=prompt,
                audio=audio_b64
            )
            if isinstance(response, str):
                return json.loads(response)
            return response
        except Exception as e:
            logger.error(f"Audio LLM call failed: {e}")
            return {"summary": str(e), "confidence": 0.0}


class DocumentProcessor:
    """
    Document processing for PDFs, DOCs, and structured documents
    Capabilities: extraction, summarization, structure analysis, table extraction
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        self.llm = llm_client
        
    async def process_document(
        self,
        document_data: bytes,
        document_type: str = "auto",
        task: str = "full_analysis"
    ) -> ProcessingResult:
        """
        Process a document
        """
        # Determine document type if auto
        if document_type == "auto":
            document_type = self._detect_document_type(document_data)
        
        # Extract text based on type
        text = await self._extract_text(document_data, document_type)
        
        prompts = {
            "full_analysis": self._full_analysis_prompt(),
            "summarize": self._summarization_prompt(),
            "extract_tables": self._table_extraction_prompt(),
            "extract_key_info": self._key_info_prompt()
        }
        
        prompt = prompts.get(task, prompts["full_analysis"])
        full_prompt = f"{prompt}\n\nDocument:\n{text[:10000]}"  # Limit context
        
        if self.llm:
            response = await self._call_llm(full_prompt)
        else:
            response = {"summary": text[:500], "confidence": 0.5}
        
        return ProcessingResult(
            modality=ModalityType.DOCUMENT,
            summary=response.get("summary", ""),
            entities=response.get("entities", []),
            key_points=response.get("key_points", []),
            confidence=response.get("confidence", 0.8),
            metadata={
                "document_type": document_type,
                "length": len(text),
                **response.get("metadata", {})
            },
            raw_output=response
        )
    
    def _detect_document_type(self, data: bytes) -> str:
        """Detect document type from magic bytes"""
        # PDF
        if data[:5] == b'%PDF-':
            return "pdf"
        # DOCX
        elif data[:4] == b'PK\x03\x04':
            return "docx"
        # Plain text
        else:
            try:
                data.decode('utf-8')
                return "txt"
            except:
                return "unknown"
    
    async def _extract_text(self, data: bytes, doc_type: str) -> str:
        """Extract text from document"""
        if doc_type == "txt":
            return data.decode('utf-8', errors='ignore')
        elif doc_type == "pdf":
            # In production, use PyPDF2 or pdfplumber
            return "[PDF text extraction not implemented]"
        elif doc_type == "docx":
            # In production, use python-docx
            return "[DOCX text extraction not implemented]"
        else:
            return "[Unsupported document type]"
    
    def _full_analysis_prompt(self) -> str:
        return """Perform a comprehensive analysis of this document. Provide:
1. Document type and structure
2. Main topics and themes
3. Key arguments or points
4. Important data or facts
5. Conclusions

Format as JSON with keys: summary, topics, arguments, data, conclusions, confidence"""
    
    def _summarization_prompt(self) -> str:
        return """Create a detailed summary of this document. Provide:
1. Executive summary (2-3 paragraphs)
2. Main points (bullet list)
3. Key takeaways

Format as JSON with keys: executive_summary, main_points, takeaways, confidence"""
    
    def _table_extraction_prompt(self) -> str:
        return """Extract all tables from this document. For each table provide:
- Table number
- Headers
- Rows (as lists)
- Summary of what the table shows

Format as JSON with keys: tables (list with number, headers, rows, summary), confidence"""
    
    def _key_info_prompt(self) -> str:
        return """Extract key information from this document:
1. Names of people mentioned
2. Dates and times
3. Numbers and statistics
4. Locations mentioned
5. Key terms and definitions

Format as JSON with keys: people, dates, numbers, locations, terms, confidence"""
    
    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """Call LLM with prompt"""
        try:
            response = await self.llm.generate(prompt)
            if isinstance(response, str):
                return json.loads(response)
            return response
        except Exception as e:
            logger.error(f"Document LLM call failed: {e}")
            return {"summary": str(e), "confidence": 0.0}


class VideoProcessor:
    """
    Video processing combining vision and audio
    Capabilities: scene detection, key frame extraction, video summarization
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        self.llm = llm_client
        self.vision = VisionProcessor(llm_client)
        self.audio = AudioProcessor(llm_client)
        
    async def process_video(
        self,
        video_data: bytes,
        task: str = "summarize",
        extract_frames: int = 5
    ) -> ProcessingResult:
        """
        Process a video file
        """
        # Extract key frames
        frames = await self._extract_frames(video_data, extract_frames)
        
        # Extract audio
        audio = await self._extract_audio(video_data)
        
        # Process audio
        audio_result = None
        if audio:
            audio_result = await self.audio.process_audio(audio, task="transcribe")
        
        # Process frames
        frame_results = []
        for frame in frames:
            frame_result = await self.vision.process_image(frame, task="describe")
            frame_results.append(frame_result)
        
        # Combine results
        combined_summary = self._combine_results(frame_results, audio_result)
        
        return ProcessingResult(
            modality=ModalityType.VIDEO,
            summary=combined_summary["summary"],
            entities=combined_summary.get("entities", []),
            key_points=combined_summary.get("key_points", []),
            confidence=sum(r.confidence for r in frame_results) / len(frame_results) if frame_results else 0.5,
            metadata={
                "frames_extracted": len(frames),
                "has_audio": audio is not None,
                **combined_summary.get("metadata", {})
            }
        )
    
    async def _extract_frames(self, video_data: bytes, count: int) -> List[bytes]:
        """Extract key frames from video"""
        # In production, use OpenCV or ffmpeg
        # For now, return placeholder
        return [video_data[:1000] for _ in range(count)]
    
    async def _extract_audio(self, video_data: bytes) -> Optional[bytes]:
        """Extract audio track from video"""
        # In production, use ffmpeg
        return None
    
    def _combine_results(
        self,
        frame_results: List[ProcessingResult],
        audio_result: Optional[ProcessingResult]
    ) -> Dict[str, Any]:
        """Combine frame and audio analysis results"""
        summaries = [r.summary for r in frame_results]
        if audio_result:
            summaries.append(audio_result.summary)
        
        combined = f"Video analysis: {' '.join(summaries[:3])}"
        
        all_entities = []
        all_key_points = []
        
        for r in frame_results:
            all_entities.extend(r.entities)
            all_key_points.extend(r.key_points)
        
        if audio_result:
            all_entities.extend(audio_result.entities)
            all_key_points.extend(audio_result.key_points)
        
        return {
            "summary": combined,
            "entities": all_entities[:20],
            "key_points": list(set(all_key_points))[:10],
            "metadata": {}
        }


class MultiModalManager:
    """
    Central manager for multi-modal processing
    Coordinates different modality processors
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        self.llm = llm_client
        
        # Initialize processors
        self.vision = VisionProcessor(llm_client)
        self.audio = AudioProcessor(llm_client)
        self.document = DocumentProcessor(llm_client)
        self.video = VideoProcessor(llm_client)
        
    async def process(
        self,
        inputs: List[MultiModalInput]
    ) -> MultiModalAnalysis:
        """
        Process multiple multi-modal inputs
        """
        results = []
        
        for input_data in inputs:
            result = await self._process_single(input_data)
            results.append(result)
        
        # Generate cross-modal insights
        cross_modal = await self._generate_cross_modal_insights(results)
        
        # Generate unified summary
        unified = await self._generate_unified_summary(results)
        
        return MultiModalAnalysis(
            inputs=inputs,
            results=results,
            cross_modal_insights=cross_modal,
            unified_summary=unified,
            recommendations=[]  # Could add recommendation generation
        )
    
    async def _process_single(self, input_data: MultiModalInput) -> ProcessingResult:
        """Process a single multi-modal input"""
        if input_data.modality == ModalityType.IMAGE:
            return await self.vision.process_image(input_data.content)
        elif input_data.modality == ModalityType.AUDIO:
            return await self.audio.process_audio(input_data.content)
        elif input_data.modality == ModalityType.DOCUMENT:
            return await self.document.process_document(input_data.content)
        elif input_data.modality == ModalityType.VIDEO:
            return await self.video.process_video(input_data.content)
        else:
            return ProcessingResult(
                modality=input_data.modality,
                summary=str(input_data.content)[:500],
                confidence=1.0
            )
    
    async def _generate_cross_modal_insights(
        self,
        results: List[ProcessingResult]
    ) -> List[str]:
        """Generate insights from multiple modalities"""
        if len(results) < 2:
            return []
        
        # Collect all summaries
        summaries = "\n\n".join([r.summary for r in results])
        
        prompt = f"""Analyze these results from multiple modalities and identify:
1. Connections between different modalities
2. Consistency or contradictions
3. Additional insights from combining modalities

Results:
{summaries}

Format as JSON with keys: connections, contradictions, insights (list of strings)"""
        
        if self.llm:
            response = await self.llm.generate(prompt)
            if isinstance(response, dict):
                return response.get("insights", [])
        
        return []
    
    async def _generate_unified_summary(
        self,
        results: List[ProcessingResult]
    ) -> str:
        """Generate unified summary from all modalities"""
        summaries = [r.summary for r in results]
        
        if len(summaries) == 1:
            return summaries[0]
        
        combined = "\n\n".join(summaries)
        
        prompt = f"""Create a unified summary that combines all these modality analyses:
{combined}

Provide a coherent summary that integrates all the information."""

        if self.llm:
            return await self.llm.generate(prompt)
        
        return combined[:1000]
    
    async def process_url(
        self,
        url: str,
        modalities: Optional[List[ModalityType]] = None
    ) -> MultiModalAnalysis:
        """
        Process content from a URL (auto-detect modalities)
        """
        # In production, fetch URL and detect content type
        # For now, return placeholder
        return MultiModalAnalysis(
            inputs=[],
            results=[],
            unified_summary="URL processing not fully implemented"
        )
