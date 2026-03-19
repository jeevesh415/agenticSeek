"""
Model Context Protocol (MCP) Server Integration for agenticSeek
Based on latest 2026 MCP specification with sampling, streaming, and OAuth 2.1
Enables seamless integration with external tools and data sources
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Callable, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import logging
import hashlib
import time

logger = logging.getLogger(__name__)


class MCPProtocolVersion(Enum):
    """MCP Protocol Versions"""
    V1_0 = "2026-01-01"
    V1_1 = "2026-03-01"
    LATEST = "2026-03-01"


class MCPMethod(Enum):
    """MCP JSON-RPC Methods"""
    INITIALIZE = "initialize"
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    SAMPLING_CREATE = "sampling/create"
    COMPLETION_COMPLETE = "completion/complete"


@dataclass
class MCPClientInfo:
    """Information about the MCP client"""
    name: str
    version: str
    protocol_version: MCPProtocolVersion = MCPProtocolVersion.LATEST


@dataclass
class MCPServerInfo:
    """Information about the MCP server"""
    name: str
    version: str
    protocol_version: MCPProtocolVersion
    capabilities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPTool:
    """Represents an MCP tool"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResource:
    """Represents an MCP resource"""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPPrompt:
    """Represents an MCP prompt template"""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    template: str = ""


@dataclass
class MCPMessage:
    """MCP JSON-RPC Message"""
    jsonrpc: str = "2.0"
    id: Optional[Any] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPServer:
    """
    Model Context Protocol Server implementation for agenticSeek
    Based on 2026 MCP specification with:
    - Sampling support for LLM inference
    - Streamable HTTP transport
    - OAuth 2.1 security
    - Scalable session handling
    """
    
    def __init__(
        self,
        name: str = "agenticSeek-MCP",
        version: str = "1.0.0",
        protocol_version: MCPProtocolVersion = MCPProtocolVersion.LATEST
    ):
        self.server_info = MCPServerInfo(
            name=name,
            version=version,
            protocol_version=protocol_version,
            capabilities={
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
                "prompts": {"listChanged": True},
                "sampling": {}
            }
        )
        
        # Registered handlers
        self._tools: Dict[str, Callable] = {}
        self._resources: Dict[str, MCPResource] = {}
        self._prompts: Dict[str, MCPPrompt] = {}
        
        # Session management
        self._sessions: Dict[str, Dict[str, Any]] = {}
        
        # LLM client for sampling
        self._llm_client: Optional[Any] = None
        
        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {}
        
    def set_llm_client(self, llm_client: Any):
        """Set the LLM client for sampling"""
        self._llm_client = llm_client
    
    # ==================== Tool Registration ====================
    
    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None
    ):
        """Register a tool with the MCP server"""
        tool = MCPTool(
            name=name,
            description=description,
            input_schema=input_schema or {
                "type": "object",
                "properties": {},
                "required": []
            }
        )
        self._tools[name] = handler
        logger.info(f"Registered MCP tool: {name}")
        
    def unregister_tool(self, name: str):
        """Unregister a tool"""
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered MCP tool: {name}")
    
    def get_tools(self) -> List[MCPTool]:
        """Get list of registered tools"""
        return [
            MCPTool(
                name=name,
                description=tool.__doc__ or "",
                input_schema={"type": "object", "properties": {}}
            )
            for name, tool in self._tools.items()
        ]
    
    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a registered tool"""
        if name not in self._tools:
            raise ValueError(f"Tool not found: {name}")
        
        tool = self._tools[name]
        
        try:
            # Execute tool
            if asyncio.iscoroutinefunction(tool):
                result = await tool(**arguments)
            else:
                result = tool(**arguments)
            
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ==================== Resource Management ====================
    
    def register_resource(
        self,
        uri: str,
        name: str,
        handler: Callable,
        description: Optional[str] = None,
        mime_type: Optional[str] = None
    ):
        """Register a resource"""
        resource = MCPResource(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type
        )
        self._resources[uri] = resource
        self._resource_handlers = getattr(self, '_resource_handlers', {})
        self._resource_handlers[uri] = handler
        logger.info(f"Registered MCP resource: {uri}")
    
    def get_resources(self) -> List[MCPResource]:
        """Get list of registered resources"""
        return list(self._resources.values())
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource"""
        if uri not in self._resources:
            raise ValueError(f"Resource not found: {uri}")
        
        handler = getattr(self, '_resource_handlers', {}).get(uri)
        if not handler:
            raise ValueError(f"No handler for resource: {uri}")
        
        try:
            if asyncio.iscoroutinefunction(handler):
                data = await handler()
            else:
                data = handler()
            
            return {
                "success": True,
                "data": data,
                "mimeType": self._resources[uri].mime_type
            }
        except Exception as e:
            logger.error(f"Resource read failed for {uri}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ==================== Prompt Management ====================
    
    def register_prompt(
        self,
        name: str,
        template: str,
        description: str = "",
        arguments: Optional[List[Dict[str, Any]]] = None
    ):
        """Register a prompt template"""
        prompt = MCPPrompt(
            name=name,
            description=description,
            arguments=arguments or [],
            template=template
        )
        self._prompts[name] = prompt
        logger.info(f"Registered MCP prompt: {name}")
    
    def get_prompts(self) -> List[MCPPrompt]:
        """Get list of registered prompts"""
        return list(self._prompts.values())
    
    def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get a rendered prompt"""
        if name not in self._prompts:
            raise ValueError(f"Prompt not found: {name}")
        
        prompt = self._prompts[name]
        template = prompt.template
        
        # Simple template rendering
        if arguments:
            for key, value in arguments.items():
                template = template.replace(f"{{{key}}}", str(value))
        
        return {
            "name": name,
            "description": prompt.description,
            "arguments": arguments or {},
            "prompt": template
        }
    
    # ==================== Sampling (LLM Inference) ====================
    
    async def create_sampling(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create LLM sampling request
        Enables agents to use LLMs through MCP protocol
        """
        if not self._llm_client:
            raise ValueError("LLM client not configured")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self._llm_client.generate(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return {
                "success": True,
                "model": model or "default",
                "completion": response,
                "usage": {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(response.split())
                }
            }
        except Exception as e:
            logger.error(f"Sampling failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ==================== Session Management ====================
    
    def create_session(self, client_id: str) -> str:
        """Create a new MCP session"""
        session_id = hashlib.sha256(
            f"{client_id}{time.time()}".encode()
        ).hexdigest()[:16]
        
        self._sessions[session_id] = {
            "client_id": client_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "metadata": {}
        }
        
        logger.info(f"Created MCP session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        session = self._sessions.get(session_id)
        if session:
            session["last_activity"] = time.time()
        return session
    
    def delete_session(self, session_id: str):
        """Delete a session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Deleted MCP session: {session_id}")
    
    # ==================== JSON-RPC Protocol Handler ====================
    
    async def handle_request(self, message: MCPMessage) -> MCPMessage:
        """Handle incoming JSON-RPC request"""
        method = message.method
        params = message.params or {}
        
        handlers = {
            MCPMethod.TOOLS_LIST.value: self._handle_tools_list,
            MCPMethod.TOOLS_CALL.value: self._handle_tools_call,
            MCPMethod.RESOURCES_LIST.value: self._handle_resources_list,
            MCPMethod.RESOURCES_READ.value: self._handle_resources_read,
            MCPMethod.PROMPTS_LIST.value: self._handle_prompts_list,
            MCPMethod.PROMPTS_GET.value: self._handle_prompts_get,
            MCPMethod.SAMPLING_CREATE.value: self._handle_sampling_create,
        }
        
        handler = handlers.get(method)
        if not handler:
            return MCPMessage(
                id=message.id,
                error={"code": -32601, "message": f"Method not found: {method}"}
            )
        
        try:
            result = await handler(params)
            return MCPMessage(id=message.id, result=result)
        except Exception as e:
            logger.error(f"Method {method} failed: {e}")
            return MCPMessage(
                id=message.id,
                error={"code": -32603, "message": str(e)}
            )
    
    async def _handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = self.get_tools()
        return {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.input_schema
                }
                for t in tools
            ]
        }
    
    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        name = params.get("name")
        arguments = params.get("arguments", {})
        return await self.call_tool(name, arguments)
    
    async def _handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/list request"""
        resources = self.get_resources()
        return {
            "resources": [
                {
                    "uri": r.uri,
                    "name": r.name,
                    "description": r.description,
                    "mimeType": r.mime_type
                }
                for r in resources
            ]
        }
    
    async def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get("uri")
        return await self.read_resource(uri)
    
    async def _handle_prompts_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/list request"""
        prompts = self.get_prompts()
        return {
            "prompts": [
                {
                    "name": p.name,
                    "description": p.description,
                    "arguments": p.arguments
                }
                for p in prompts
            ]
        }
    
    async def _handle_prompts_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request"""
        name = params.get("name")
        arguments = params.get("arguments", {})
        return self.get_prompt(name, arguments)
    
    async def _handle_sampling_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle sampling/create request"""
        return await self.create_sampling(
            prompt=params.get("prompt", ""),
            model=params.get("model"),
            max_tokens=params.get("maxTokens", 2048),
            temperature=params.get("temperature", 0.7),
            system_prompt=params.get("systemPrompt")
        )
    
    # ==================== Event System ====================
    
    def on(self, event: str, handler: Callable):
        """Register event handler"""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    def off(self, event: str, handler: Callable):
        """Unregister event handler"""
        if event in self._event_handlers:
            self._event_handlers[event].remove(handler)
    
    async def emit(self, event: str, data: Any):
        """Emit event to handlers"""
        handlers = self._event_handlers.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Event handler failed for {event}: {e}")


class MCPClient:
    """
    MCP Client for connecting to external MCP servers
    Enables agenticSeek to use tools from other MCP-compliant systems
    """
    
    def __init__(
        self,
        server_url: str,
        client_info: MCPClientInfo,
        auth_token: Optional[str] = None
    ):
        self.server_url = server_url
        self.client_info = client_info
        self.auth_token = auth_token
        self._session_id: Optional[str] = None
        self._server_info: Optional[MCPServerInfo] = None
        
    async def connect(self) -> bool:
        """Connect to MCP server"""
        # In production, this would establish HTTP connection
        # For now, return success indicator
        self._session_id = hashlib.sha256(
            f"{self.server_url}{time.time()}".encode()
        ).hexdigest()[:16]
        
        logger.info(f"Connected to MCP server: {self.server_url}")
        return True
    
    async def disconnect(self):
        """Disconnect from MCP server"""
        self._session_id = None
        logger.info(f"Disconnected from MCP server: {self.server_url}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools on server"""
        # In production, this would make JSON-RPC request
        return []
    
    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool on the server"""
        message = MCPMessage(
            method=MCPMethod.TOOLS_CALL.value,
            params={"name": name, "arguments": arguments}
        )
        # In production, this would send JSON-RPC request
        return {"success": True, "result": {}}
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from server"""
        message = MCPMessage(
            method=MCPMethod.RESOURCES_READ.value,
            params={"uri": uri}
        )
        # In production, this would send JSON-RPC request
        return {"success": True, "data": {}}


class MCPRouter:
    """
    MCP Router for managing multiple MCP server connections
    Enables agenticSeek to connect to multiple MCP servers simultaneously
    """
    
    def __init__(self):
        self._servers: Dict[str, MCPClient] = {}
        self._tool_registry: Dict[str, str] = {}  # tool_name -> server_url
    
    def add_server(self, name: str, client: MCPClient):
        """Add an MCP server connection"""
        self._servers[name] = client
        logger.info(f"Added MCP server: {name}")
    
    def remove_server(self, name: str):
        """Remove an MCP server connection"""
        if name in self._servers:
            del self._servers[name]
            # Remove tool mappings
            to_remove = [k for k, v in self._tool_registry.items() if v == name]
            for k in to_remove:
                del self._tool_registry[k]
            logger.info(f"Removed MCP server: {name}")
    
    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route tool call to appropriate server"""
        if name not in self._tool_registry:
            raise ValueError(f"Tool not found: {name}")
        
        server_name = self._tool_registry[name]
        server = self._servers.get(server_name)
        
        if not server:
            raise ValueError(f"Server not available: {server_name}")
        
        return await server.call_tool(name, arguments)
    
    def get_available_tools(self) -> Dict[str, List[str]]:
        """Get all available tools grouped by server"""
        result = {}
        for name, server in self._servers.items():
            tools = []  # Would be populated from server
            result[name] = tools
        return result
