"""
Deep Research Agent for agenticSeek
Autonomous investigation and synthesis of complex topics
Based on latest 2026 research agent capabilities
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class ResearchDepth(Enum):
    """Depth levels for research"""
    SURFACE = "surface"  # Quick overview
    STANDARD = "standard"  # Balanced depth
    DEEP = "deep"  # Comprehensive
    EXHAUSTIVE = "exhaustive"  # Maximum detail


class ResearchPhase(Enum):
    """Phases of the research process"""
    PLANNING = "planning"
    EXPLORATION = "exploration"
    SYNTHESIS = "synthesis"
    VERIFICATION = "verification"
    REPORTING = "reporting"


@dataclass
class ResearchQuery:
    """Represents a research query"""
    topic: str
    depth: ResearchDepth = ResearchDepth.STANDARD
    focus_areas: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)  # Preferred sources


@dataclass
class ResearchSource:
    """Represents a research source"""
    url: str
    title: str
    credibility: float = 0.5
    relevance: float = 0.5
    content: Optional[str] = None
    extracted_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchFinding:
    """Represents a finding from research"""
    claim: str
    source: Optional[ResearchSource] = None
    confidence: float = 0.5
    evidence: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchReport:
    """Complete research report"""
    query: ResearchQuery
    executive_summary: str
    findings: List[ResearchFinding]
    sources: List[ResearchSource]
    timeline: Dict[str, Any]
    gaps: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DeepResearchAgent:
    """
    Deep Research Agent for autonomous investigation
    Implements multi-phase research with verification and synthesis
    
    Key Capabilities (2026):
    - Multi-source investigation
    - Evidence verification and cross-referencing
    - Contradiction detection
    - Automatic gap identification
    - Structured report generation
    - Real-time source evaluation
    """
    
    def __init__(
        self,
        web_search_func: Callable,
        web_fetch_func: Callable,
        llm_client: Any,
        config: Optional[Dict[str, Any]] = None
    ):
        self.web_search = web_search_func
        self.web_fetch = web_fetch_func
        self.llm = llm_client
        self.config = config or {}
        
        # Research parameters
        self.max_sources = self.config.get("max_sources", 50)
        self.max_iterations = self.config.get("max_iterations", 10)
        self.verification_threshold = self.config.get("verification_threshold", 0.7)
        
        # State
        self.current_phase = ResearchPhase.PLANNING
        self.sources: List[ResearchSource] = []
        self.findings: List[ResearchFinding] = []
        self.search_queries: List[str] = []
        
    async def research(
        self,
        query: ResearchQuery,
        progress_callback: Optional[Callable] = None
    ) -> ResearchReport:
        """
        Conduct deep research on a topic
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting deep research on: {query.topic}")
        
        # Phase 1: Planning
        if progress_callback:
            await progress_callback("Planning research approach...")
        research_plan = await self._planning_phase(query)
        
        # Phase 2: Exploration
        if progress_callback:
            await progress_callback("Exploring sources...")
        await self._exploration_phase(query, research_plan)
        
        # Phase 3: Synthesis
        if progress_callback:
            await progress_callback("Synthesizing findings...")
        synthesis = await self._synthesis_phase(query)
        
        # Phase 4: Verification
        if progress_callback:
            await progress_callback("Verifying evidence...")
        verified_findings = await self._verification_phase(synthesis)
        
        # Phase 5: Reporting
        if progress_callback:
            await progress_callback("Generating report...")
        report = await self._reporting_phase(
            query, verified_findings, start_time
        )
        
        logger.info(f"Research completed: {len(self.sources)} sources, {len(self.findings)} findings")
        
        return report
    
    async def _planning_phase(self, query: ResearchQuery) -> Dict[str, Any]:
        """
        Phase 1: Create research plan
        """
        self.current_phase = ResearchPhase.PLANNING
        
        planning_prompt = f"""Create a comprehensive research plan for this topic:

Topic: {query.topic}
Depth: {query.depth.value}
Focus Areas: {', '.join(query.focus_areas) if query.focus_areas else 'General'}
Constraints: {json.dumps(query.constraints)}

Create a research plan that includes:
1. Key aspects to investigate
2. Different perspectives to explore
3. Search queries to use
4. Types of sources needed
5. Potential counter-arguments to consider

Format as JSON with keys: aspects, perspectives, search_queries, source_types, counter_arguments
"""
        
        response = await self._call_llm(planning_prompt)
        
        try:
            if isinstance(response, str):
                plan = json.loads(response)
            else:
                plan = response
        except:
            plan = {
                "aspects": ["General overview", "Key concepts", "Applications"],
                "perspectives": ["Technical", "Practical", "Critical"],
                "search_queries": [query.topic, f"{query.topic} research", f"{query.topic} latest"],
                "source_types": ["Academic", "Industry", "News"],
                "counter_arguments": []
            }
        
        return plan
    
    async def _exploration_phase(
        self,
        query: ResearchQuery,
        plan: Dict[str, Any]
    ):
        """
        Phase 2: Explore and gather sources
        """
        self.current_phase = ResearchPhase.EXPLORATION
        
        # Generate search queries
        search_queries = plan.get("search_queries", [query.topic])
        
        # Add depth-specific queries
        if query.depth in [ResearchDepth.DEEP, ResearchDepth.EXHAUSTIVE]:
            search_queries.extend([
                f"{query.topic} research 2025 2026",
                f"{query.topic} latest developments",
                f"{query.topic} academic papers"
            ])
        
        # Search and gather sources
        for query_str in search_queries[:self.max_iterations]:
            if len(self.sources) >= self.max_sources:
                break
            
            # Web search
            search_results = await self._web_search(query_str)
            
            for result in search_results:
                if len(self.sources) >= self.max_sources:
                    break
                
                source = await self._fetch_and_process_source(result)
                if source and self._is_relevant(source, query):
                    self.sources.append(source)
                    self.search_queries.append(query_str)
        
        logger.info(f"Exploration complete: {len(self.sources)} sources gathered")
    
    async def _synthesis_phase(self, query: ResearchQuery) -> Dict[str, Any]:
        """
        Phase 3: Synthesize information from sources
        """
        self.current_phase = ResearchPhase.SYNTHESIS
        
        # Prepare source summaries
        source_summaries = "\n\n".join([
            f"Source {i+1}: {s.title}\nURL: {s.url}\nContent: {s.content[:500] if s.content else 'N/A'}..."
            for i, s in enumerate(self.sources[:20])  # Limit for context
        ])
        
        synthesis_prompt = f"""Analyze and synthesize findings from these sources on: {query.topic}

Sources:
{source_summaries}

Extract and synthesize:
1. Key claims and findings
2. Supporting evidence
3. Contradicting viewpoints
4. Knowledge gaps
5. Emerging trends or developments

Format as JSON with keys:
- claims: [list of main claims]
- evidence: [corresponding evidence for each claim]
- contradictions: [list of contradictions found]
- gaps: [knowledge gaps identified]
- trends: [emerging trends]
"""
        
        response = await self._call_llm(synthesis_prompt)
        
        try:
            synthesis = json.loads(response) if isinstance(response, str) else response
        except:
            synthesis = {
                "claims": ["Unable to parse synthesis"],
                "evidence": [],
                "contradictions": [],
                "gaps": [],
                "trends": []
            }
        
        # Convert to ResearchFinding objects
        for i, claim in enumerate(synthesis.get("claims", [])):
            finding = ResearchFinding(
                claim=claim,
                evidence=synthesis.get("evidence", [])[i:i+1] if i < len(synthesis.get("evidence", [])) else [],
                contradictions=synthesis.get("contradictions", [])
            )
            self.findings.append(finding)
        
        return synthesis
    
    async def _verification_phase(self, synthesis: Dict[str, Any]) -> List[ResearchFinding]:
        """
        Phase 4: Verify findings and check for contradictions
        """
        self.current_phase = ResearchPhase.VERIFICATION
        
        verified_findings = []
        
        for finding in self.findings:
            # Check evidence strength
            evidence_count = len(finding.evidence)
            
            # Cross-reference with sources
            supporting_sources = []
            contradicting_sources = []
            
            for source in self.sources:
                if source.content:
                    # Simple keyword matching for demonstration
                    if any(keyword.lower() in source.content.lower() 
                           for keyword in finding.claim.split()[:5]):
                        supporting_sources.append(source)
                    elif any(contradiction.lower() in source.content.lower()
                             for contradiction in finding.contradictions):
                        contradicting_sources.append(source)
            
            # Update finding with verification info
            finding.confidence = self._calculate_confidence(
                evidence_count,
                len(supporting_sources),
                len(contradicting_sources)
            )
            
            if finding.source is None and supporting_sources:
                finding.source = supporting_sources[0]
            
            # Only include high-confidence findings in deep research
            if finding.confidence >= self.verification_threshold:
                verified_findings.append(finding)
        
        logger.info(f"Verification complete: {len(verified_findings)}/{len(self.findings)} findings verified")
        
        return verified_findings
    
    async def _reporting_phase(
        self,
        query: ResearchQuery,
        findings: List[ResearchFinding],
        start_time: datetime
    ) -> ResearchReport:
        """
        Phase 5: Generate final report
        """
        self.current_phase = ResearchPhase.REPORTING
        
        # Prepare findings summary
        findings_summary = "\n\n".join([
            f"{i+1}. {f.claim} (Confidence: {f.confidence:.2f})"
            f"\n   Evidence: {'; '.join(f.evidence[:2])}"
            for i, f in enumerate(findings)
        ])
        
        # Generate executive summary
        summary_prompt = f"""Create an executive summary for this research report:

Topic: {query.topic}
Depth: {query.depth.value}

Key Findings:
{findings_summary}

Create a concise 2-3 paragraph executive summary that:
1. Answers the main research question
2. Highlights the most important findings
3. Notes any critical gaps or limitations

Also provide:
- Top 5 recommendations
- Key gaps in current knowledge
"""
        
        summary_response = await self._call_llm(summary_prompt)
        
        try:
            if isinstance(summary_response, str):
                # Try to parse as JSON
                try:
                    summary_data = json.loads(summary_response)
                    executive_summary = summary_data.get("summary", summary_response)
                    recommendations = summary_data.get("recommendations", [])
                    gaps = summary_data.get("gaps", [])
                except:
                    executive_summary = summary_response
                    recommendations = []
                    gaps = []
            else:
                executive_summary = summary_response.get("summary", "")
                recommendations = summary_response.get("recommendations", [])
                gaps = summary_response.get("gaps", [])
        except:
            executive_summary = f"Research on {query.topic} completed with {len(findings)} verified findings."
            recommendations = []
            gaps = []
        
        # Calculate timeline
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return ResearchReport(
            query=query,
            executive_summary=executive_summary,
            findings=findings,
            sources=self.sources,
            timeline={
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "duration_seconds": duration,
                "phases": [p.value for p in ResearchPhase]
            },
            gaps=gaps,
            recommendations=recommendations,
            metadata={
                "total_sources": len(self.sources),
                "verified_findings": len(findings),
                "search_queries_used": len(set(self.search_queries))
            }
        )
    
    async def _web_search(self, query: str) -> List[Dict[str, Any]]:
        """Perform web search"""
        try:
            results = await self.web_search(query)
            return results if isinstance(results, list) else []
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []
    
    async def _fetch_and_process_source(
        self,
        search_result: Dict[str, Any]
    ) -> Optional[ResearchSource]:
        """Fetch and process a source"""
        url = search_result.get("url", "")
        title = search_result.get("title", "")
        
        if not url:
            return None
        
        try:
            content = await self.web_fetch(url)
            
            source = ResearchSource(
                url=url,
                title=title,
                credibility=self._evaluate_credibility(url, content),
                relevance=self._evaluate_relevance(content, self.search_queries[-1] if self.search_queries else ""),
                content=content,
                extracted_at=datetime.utcnow()
            )
            
            return source
        except Exception as e:
            logger.error(f"Failed to fetch source {url}: {e}")
            return None
    
    def _is_relevant(self, source: ResearchSource, query: ResearchQuery) -> bool:
        """Check if source is relevant to query"""
        if not source.content:
            return False
        
        # Check relevance score
        if source.relevance < 0.3:
            return False
        
        # Check focus areas
        if query.focus_areas:
            content_lower = source.content.lower()
            return any(
                area.lower() in content_lower
                for area in query.focus_areas
            )
        
        return True
    
    def _evaluate_credibility(self, url: str, content: Optional[str]) -> float:
        """Evaluate source credibility"""
        credibility = 0.5
        
        # URL-based scoring
        credible_domains = [
            "arxiv.org", "nature.com", "science.org",
            "IEEE.org", "scholar.google", "github.com",
            "wikipedia.org", "official.edu"
        ]
        
        for domain in credible_domains:
            if domain in url.lower():
                credibility += 0.2
                break
        
        # Content-based scoring
        if content:
            # Check for citations/references
            if "references" in content.lower() or "citations" in content.lower():
                credibility += 0.1
            
            # Check for academic structure
            if any(marker in content for marker in ["Abstract", "Introduction", "Conclusion"]):
                credibility += 0.1
        
        return min(credibility, 1.0)
    
    def _evaluate_relevance(self, content: Optional[str], query: str) -> float:
        """Evaluate content relevance to query"""
        if not content or not query:
            return 0.5
        
        query_terms = set(query.lower().split())
        content_lower = content.lower()
        
        matches = sum(1 for term in query_terms if term in content_lower)
        relevance = matches / len(query_terms) if query_terms else 0.5
        
        return min(relevance, 1.0)
    
    def _calculate_confidence(
        self,
        evidence_count: int,
        supporting_sources: int,
        contradicting_sources: int
    ) -> float:
        """Calculate confidence score for a finding"""
        base_confidence = 0.3
        
        # Evidence count
        base_confidence += min(evidence_count * 0.1, 0.3)
        
        # Supporting sources
        base_confidence += min(supporting_sources * 0.1, 0.2)
        
        # Contradictions reduce confidence
        if contradicting_sources > 0:
            base_confidence -= contradicting_sources * 0.15
        
        return max(0.0, min(1.0, base_confidence))
    
    async def _call_llm(self, prompt: str) -> Any:
        """Call LLM with prompt"""
        try:
            response = await self.llm.generate(prompt)
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ""


class ResearchAgent:
    """
    High-level research agent that uses DeepResearchAgent
    Provides simplified interface for autonomous research
    """
    
    def __init__(
        self,
        web_search_func: Callable,
        web_fetch_func: Callable,
        llm_client: Any,
        config: Optional[Dict[str, Any]] = None
    ):
        self.deep_researcher = DeepResearchAgent(
            web_search_func=web_search_func,
            web_fetch_func=web_fetch_func,
            llm_client=llm_client,
            config=config
        )
    
    async def investigate(
        self,
        topic: str,
        depth: str = "standard",
        focus_areas: Optional[List[str]] = None
    ) -> ResearchReport:
        """
        Conduct research on a topic
        """
        depth_enum = ResearchDepth(depth.lower())
        
        query = ResearchQuery(
            topic=topic,
            depth=depth_enum,
            focus_areas=focus_areas or []
        )
        
        return await self.deep_researcher.research(query)
    
    async def quick_research(self, topic: str) -> str:
        """
        Quick research for rapid information gathering
        """
        query = ResearchQuery(
            topic=topic,
            depth=ResearchDepth.SURFACE
        )
        
        report = await self.deep_researcher.research(query)
        return report.executive_summary
