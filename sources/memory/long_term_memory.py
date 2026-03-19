"""
Long-Horizon Memory System for agenticSeek
Enhanced persistence and context management across sessions
Based on latest 2026 research in agent memory architectures
"""

import asyncio
import json
import logging
import hashlib
import time
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import sqlite3
import numpy as np

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memory"""
    EPISODIC = "episodic"  # Specific experiences/events
    SEMANTIC = "semantic"  # General knowledge/facts
    WORKING = "working"    # Current context/active information
    PROCEDURAL = "procedural"  # Skills and procedures
    METACOGNITIVE = "metacognitive"  # Learning about learning


class MemoryPriority(Enum):
    """Priority levels for memories"""
    CRITICAL = 3  # Must remember
    HIGH = 2      # Important
    MEDIUM = 1    # Normal priority
    LOW = 0       # Can be forgotten


@dataclass
class MemoryItem:
    """Represents a single memory item"""
    id: str
    content: str
    memory_type: MemoryType
    priority: MemoryPriority = MemoryPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    importance_score: float = 0.5
    decay_factor: float = 1.0
    embeddings: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    linked_memories: List[str] = field(default_factory=list)  # IDs of related memories
    
    def access(self):
        """Record memory access"""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1
        # Increase importance with repeated access
        self.importance_score = min(1.0, self.importance_score + 0.05)


@dataclass
class MemoryQuery:
    """Query for retrieving memories"""
    content: Optional[str] = None
    memory_type: Optional[MemoryType] = None
    tags: Optional[List[str]] = None
    time_range: Optional[tuple] = None  # (start, end)
    min_importance: float = 0.0
    limit: int = 10
    include_embeddings: bool = False


class LongTermMemoryStore:
    """
    Long-term memory storage with importance-based retention
    Implements memory consolidation, retrieval, and forgetting
    """
    
    def __init__(
        self,
        db_path: str = ":memory:",
        max_memories: int = 10000,
        retention_days: int = 90
    ):
        self.db_path = db_path
        self.max_memories = max_memories
        self.retention_days = retention_days
        
        self._conn: Optional[sqlite3.Connection] = None
        self._initialize_db()
        
    def _initialize_db(self):
        """Initialize SQLite database"""
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        
        # Create tables
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                importance_score REAL DEFAULT 0.5,
                decay_factor REAL DEFAULT 1.0,
                embeddings BLOB,
                metadata TEXT,
                tags TEXT,
                linked_memories TEXT
            )
        """)
        
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)
        """)
        
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance_score)
        """)
        
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at)
        """)
        
        self._conn.commit()
        
    def store(self, memory: MemoryItem) -> str:
        """Store a memory"""
        memory.id = memory.id or self._generate_id(memory.content)
        
        self._conn.execute("""
            INSERT OR REPLACE INTO memories
            (id, content, memory_type, priority, created_at, last_accessed,
             access_count, importance_score, decay_factor, embeddings, metadata, tags, linked_memories)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.id,
            memory.content,
            memory.memory_type.value,
            memory.priority.value,
            memory.created_at.isoformat(),
            memory.last_accessed.isoformat(),
            memory.access_count,
            memory.importance_score,
            memory.decay_factor,
            json.dumps(memory.embeddings) if memory.embeddings else None,
            json.dumps(memory.metadata),
            json.dumps(memory.tags),
            json.dumps(memory.linked_memories)
        ))
        
        self._conn.commit()
        
        # Check memory limit and consolidate if needed
        self._consolidate_if_needed()
        
        logger.debug(f"Stored memory: {memory.id}")
        return memory.id
    
    def retrieve(self, query: MemoryQuery) -> List[MemoryItem]:
        """Retrieve memories based on query"""
        sql = "SELECT * FROM memories WHERE 1=1"
        params = []
        
        if query.content:
            sql += " AND content LIKE ?"
            params.append(f"%{query.content}%")
        
        if query.memory_type:
            sql += " AND memory_type = ?"
            params.append(query.memory_type.value)
        
        if query.tags:
            for tag in query.tags:
                sql += " AND tags LIKE ?"
                params.append(f"%{tag}%")
        
        if query.time_range:
            sql += " AND created_at BETWEEN ? AND ?"
            params.append(query.time_range[0].isoformat())
            params.append(query.time_range[1].isoformat())
        
        if query.min_importance > 0:
            sql += " AND importance_score >= ?"
            params.append(query.min_importance)
        
        sql += " ORDER BY importance_score DESC, access_count DESC"
        sql += f" LIMIT {query.limit}"
        
        cursor = self._conn.execute(sql, params)
        rows = cursor.fetchall()
        
        memories = []
        for row in rows:
            memory = self._row_to_memory(row)
            memory.access()  # Update access stats
            memories.append(memory)
        
        return memories
    
    def retrieve_by_id(self, memory_id: str) -> Optional[MemoryItem]:
        """Retrieve a specific memory by ID"""
        cursor = self._conn.execute(
            "SELECT * FROM memories WHERE id = ?",
            (memory_id,)
        )
        row = cursor.fetchone()
        
        if row:
            memory = self._row_to_memory(row)
            memory.access()
            return memory
        
        return None
    
    def retrieve_related(self, memory_id: str, limit: int = 5) -> List[MemoryItem]:
        """Retrieve memories related to a given memory"""
        memory = self.retrieve_by_id(memory_id)
        if not memory:
            return []
        
        # Get linked memories
        related_ids = memory.linked_memories[:limit]
        related = [self.retrieve_by_id(mid) for mid in related_ids if mid != memory_id]
        
        # Also find by similar tags
        if len(related) < limit:
            query = MemoryQuery(
                tags=memory.tags,
                limit=limit - len(related),
                min_importance=0.3
            )
            by_tags = [m for m in self.retrieve(query) if m.id != memory_id]
            related.extend(by_tags)
        
        return [m for m in related if m][:limit]
    
    def update(self, memory: MemoryItem):
        """Update an existing memory"""
        self._conn.execute("""
            UPDATE memories SET
                content = ?,
                memory_type = ?,
                priority = ?,
                last_accessed = ?,
                access_count = ?,
                importance_score = ?,
                decay_factor = ?,
                embeddings = ?,
                metadata = ?,
                tags = ?,
                linked_memories = ?
            WHERE id = ?
        """, (
            memory.content,
            memory.memory_type.value,
            memory.priority.value,
            memory.last_accessed.isoformat(),
            memory.access_count,
            memory.importance_score,
            memory.decay_factor,
            json.dumps(memory.embeddings) if memory.embeddings else None,
            json.dumps(memory.metadata),
            json.dumps(memory.tags),
            json.dumps(memory.linked_memories),
            memory.id
        ))
        
        self._conn.commit()
    
    def delete(self, memory_id: str):
        """Delete a memory"""
        self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self._conn.commit()
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID for memory"""
        return hashlib.sha256(
            f"{content}{time.time()}".encode()
        ).hexdigest()[:16]
    
    def _row_to_memory(self, row: sqlite3.Row) -> MemoryItem:
        """Convert database row to MemoryItem"""
        return MemoryItem(
            id=row["id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            priority=MemoryPriority(row["priority"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            last_accessed=datetime.fromisoformat(row["last_accessed"]),
            access_count=row["access_count"],
            importance_score=row["importance_score"],
            decay_factor=row["decay_factor"],
            embeddings=json.loads(row["embeddings"]) if row["embeddings"] else None,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            tags=json.loads(row["tags"]) if row["tags"] else [],
            linked_memories=json.loads(row["linked_memories"]) if row["linked_memories"] else []
        )
    
    def _consolidate_if_needed(self):
        """Consolidate memories when limit is reached"""
        cursor = self._conn.execute("SELECT COUNT(*) FROM memories")
        count = cursor.fetchone()[0]
        
        if count > self.max_memories:
            # Delete lowest importance memories
            to_delete = count - self.max_memories
            self._conn.execute("""
                DELETE FROM memories
                WHERE id IN (
                    SELECT id FROM memories
                    ORDER BY importance_score ASC, last_accessed ASC
                    LIMIT ?
                )
            """, (to_delete,))
            self._conn.commit()
            logger.info(f"Memory consolidation: removed {to_delete} low-importance memories")


class MemoryConsolidator:
    """
    Consolidates working memories into long-term storage
    Implements forgetting curve and importance decay
    """
    
    def __init__(
        self,
        memory_store: LongTermMemoryStore,
        decay_rate: float = 0.01
    ):
        self.store = memory_store
        self.decay_rate = decay_rate
    
    async def consolidate(
        self,
        working_memory: List[MemoryItem],
        threshold: float = 0.3
    ) -> List[str]:
        """
        Consolidate working memories into long-term storage
        Returns IDs of consolidated memories
        """
        consolidated = []
        
        for memory in working_memory:
            # Calculate decay
            age_days = (datetime.utcnow() - memory.created_at).days
            decay = self.decay_rate * age_days
            
            effective_importance = memory.importance_score * (1 - decay)
            
            if effective_importance >= threshold:
                # Update memory with new importance
                memory.decay_factor = 1 - decay
                memory.memory_type = MemoryType.SEMANTIC
                
                self.store.store(memory)
                consolidated.append(memory.id)
            else:
                # Memory too faded, don't consolidate
                pass
        
        logger.info(f"Consolidated {len(consolidated)} memories")
        return consolidated
    
    def calculate_importance(
        self,
        content: str,
        context_importance: float,
        repetition: int,
        recency: float
    ) -> float:
        """
        Calculate importance score for a memory
        Based on multiple factors
        """
        # Base importance from context
        importance = context_importance * 0.4
        
        # Repetition bonus
        importance += min(repetition * 0.1, 0.3)
        
        # Recency bonus
        importance += recency * 0.3
        
        return min(1.0, max(0.0, importance))


class MemoryManager:
    """
    Central memory management system
    Coordinates episodic, semantic, working, and procedural memory
    """
    
    def __init__(
        self,
        llm_client: Any,
        config: Optional[Dict[str, Any]] = None
    ):
        self.config = config or {}
        
        # Initialize memory stores
        self.episodic = LongTermMemoryStore(
            db_path=self.config.get("db_path", "episodic.db"),
            max_memories=self.config.get("max_episodic", 5000)
        )
        
        self.semantic = LongTermMemoryStore(
            db_path=self.config.get("db_path", "semantic.db"),
            max_memories=self.config.get("max_semantic", 5000)
        )
        
        self.procedural = LongTermMemoryStore(
            db_path=self.config.get("db_path", "procedural.db"),
            max_memories=self.config.get("max_procedural", 1000)
        )
        
        # Working memory (in-memory, not persisted)
        self.working: List[MemoryItem] = []
        self.max_working = self.config.get("max_working", 50)
        
        # Consolidator
        self.consolidator = MemoryConsolidator(self.episodic)
        
        # LLM for memory operations
        self.llm = llm_client
        
        # Recent context
        self.current_session_id: Optional[str] = None
        self.session_start: Optional[datetime] = None
        
    async def remember(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.EPISODIC,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a new memory
        """
        # Generate embeddings if LLM available
        embeddings = None
        if self.llm and hasattr(self.llm, 'get_embeddings'):
            try:
                embeddings = await self.llm.get_embeddings(content)
            except:
                pass
        
        memory = MemoryItem(
            id="",  # Will be generated
            content=content,
            memory_type=memory_type,
            priority=priority,
            tags=tags or [],
            metadata=metadata or {},
            embeddings=embeddings
        )
        
        # Store in appropriate memory store
        if memory_type == MemoryType.EPISODIC:
            return self.episodic.store(memory)
        elif memory_type == MemoryType.SEMANTIC:
            return self.semantic.store(memory)
        elif memory_type == MemoryType.PROCEDURAL:
            return self.procedural.store(memory)
        elif memory_type == MemoryType.WORKING:
            self.working.append(memory)
            # Maintain working memory limit
            if len(self.working) > self.max_working:
                self.working.pop(0)
            return memory.id
        
        return ""
    
    async def recall(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10
    ) -> List[MemoryItem]:
        """
        Recall memories matching query
        """
        memories = []
        
        if memory_types is None:
            memory_types = [MemoryType.EPISODIC, MemoryType.SEMANTIC, MemoryType.WORKING]
        
        query_obj = MemoryQuery(
            content=query,
            limit=limit,
            min_importance=0.2
        )
        
        for mem_type in memory_types:
            query_obj.memory_type = mem_type
            
            if mem_type == MemoryType.EPISODIC:
                memories.extend(self.episodic.retrieve(query_obj))
            elif mem_type == MemoryType.SEMANTIC:
                memories.extend(self.semantic.retrieve(query_obj))
            elif mem_type == MemoryType.WORKING:
                # Filter working memory by content
                working_results = [
                    m for m in self.working
                    if query.lower() in m.content.lower()
                ]
                memories.extend(working_results[:limit])
        
        # Sort by importance and recency
        memories.sort(
            key=lambda m: (m.importance_score, m.last_accessed),
            reverse=True
        )
        
        return memories[:limit]
    
    async def get_context(self, max_memories: int = 20) -> str:
        """
        Get current context for LLM prompts
        Combines recent and important memories
        """
        # Get recent episodic memories
        query = MemoryQuery(limit=max_memories, min_importance=0.3)
        recent = self.episodic.retrieve(query)
        
        # Get semantic memories
        semantic = self.semantic.retrieve(query)
        
        # Combine with working memory
        all_memories = recent + semantic + self.working
        
        # Sort by importance
        all_memories.sort(key=lambda m: m.importance_score, reverse=True)
        
        # Format as context string
        context_parts = []
        for memory in all_memories[:max_memories]:
            type_indicator = {
                MemoryType.EPISODIC: "[Episode]",
                MemoryType.SEMANTIC: "[Knowledge]",
                MemoryType.WORKING: "[Current]",
                MemoryType.PROCEDURAL: "[Skill]",
                MemoryType.METACOGNITIVE: "[Meta]"
            }.get(memory.memory_type, "[Memory]")
            
            context_parts.append(
                f"{type_indicator} {memory.content}"
            )
        
        return "\n\n".join(context_parts)
    
    async def learn_skill(
        self,
        skill_name: str,
        procedure: str,
        description: str = ""
    ):
        """
        Learn a new skill/procedure
        """
        memory = MemoryItem(
            id=skill_name.lower().replace(" ", "_"),
            content=f"Skill: {skill_name}\nProcedure: {procedure}\nDescription: {description}",
            memory_type=MemoryType.PROCEDURAL,
            priority=MemoryPriority.HIGH,
            tags=["skill", skill_name.lower()]
        )
        
        return self.procedural.store(memory)
    
    async def get_skill(self, skill_name: str) -> Optional[MemoryItem]:
        """
        Retrieve a learned skill
        """
        query = MemoryQuery(
            content=skill_name,
            memory_type=MemoryType.PROCEDURAL
        )
        
        skills = self.procedural.retrieve(query)
        
        # Find exact match
        for skill in skills:
            if skill_name.lower() in skill.content.lower():
                return skill
        
        return skills[0] if skills else None
    
    async def start_session(self) -> str:
        """
        Start a new memory session
        """
        self.session_start = datetime.utcnow()
        self.current_session_id = hashlib.sha256(
            f"{self.session_start.isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Remember session start
        await self.remember(
            content=f"Session started: {self.session_start.isoformat()}",
            memory_type=MemoryType.EPISODIC,
            tags=["session_start"]
        )
        
        return self.current_session_id
    
    async def end_session(self):
        """
        End current session and consolidate memories
        """
        if not self.current_session_id:
            return
        
        # Consolidate working memory
        await self.consolidator.consolidate(self.working)
        
        # Remember session end
        await self.remember(
            content=f"Session ended: {datetime.utcnow().isoformat()}",
            memory_type=MemoryType.EPISODIC,
            tags=["session_end"]
        )
        
        self.current_session_id = None
        self.session_start = None
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory system statistics
        """
        return {
            "episodic_count": self._count_memories(self.episodic),
            "semantic_count": self._count_memories(self.semantic),
            "procedural_count": self._count_memories(self.procedural),
            "working_count": len(self.working),
            "session_active": self.current_session_id is not None,
            "session_duration": (
                datetime.utcnow() - self.session_start
            ).total_seconds() if self.session_start else 0
        }
    
    def _count_memories(self, store: LongTermMemoryStore) -> int:
        """Count memories in a store"""
        cursor = store._conn.execute("SELECT COUNT(*) FROM memories")
        return cursor.fetchone()[0]
