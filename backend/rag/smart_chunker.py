"""
Smart Chunking Module - Script-type aware chunking for runbooks

Different script types have different logical structures:
- Ansible: Tasks, Plays, Handlers
- Terraform: Resources, Modules, Providers
- Shell: Functions, Sections
- Kubernetes: Resources (Deployment, Service, ConfigMap)

This module chunks scripts based on their type for better retrieval.
"""

import os
import re
import yaml
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import structlog

logger = structlog.get_logger()


@dataclass
class Chunk:
    """A chunk of a script with metadata"""
    chunk_id: str
    content: str
    chunk_type: str
    script_id: str
    script_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding_text: str = ""  # Text optimized for embedding

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.chunk_id,
            "content": self.content,
            "chunk_type": self.chunk_type,
            "script_id": self.script_id,
            "script_type": self.script_type,
            "metadata": self.metadata,
            "embedding_text": self.embedding_text
        }


@dataclass
class ChunkingConfig:
    """Configuration for chunking behavior"""
    max_chunk_size: int = 1000
    min_chunk_size: int = 100
    overlap_size: int = 50
    include_context: bool = True


class SmartChunker:
    """
    Smart Chunker that processes scripts based on their type.

    Strategies:
    - Ansible: Chunk by tasks/plays
    - Terraform: Chunk by resources/modules
    - Shell: Chunk by functions/sections
    - Kubernetes: Chunk by resource definitions
    - General: Chunk by semantic sections
    """

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()
        self._type_handlers = {
            "ansible": self._chunk_ansible,
            "terraform": self._chunk_terraform,
            "shell": self._chunk_shell,
            "kubernetes": self._chunk_kubernetes,
            "python": self._chunk_python,
            "yaml": self._chunk_yaml,
            "json": self._chunk_json,
        }

        logger.info(
            "smart_chunker_initialized",
            max_chunk_size=self.config.max_chunk_size,
            supported_types=list(self._type_handlers.keys())
        )

    def chunk_script(self, script: Dict[str, Any]) -> List[Chunk]:
        """
        Chunk a script based on its type.

        Args:
            script: Script with 'id', 'content', 'type', and optional 'metadata'

        Returns:
            List of Chunk objects
        """
        script_type = self._detect_script_type(script)
        handler = self._type_handlers.get(script_type, self._chunk_general)

        try:
            chunks = handler(script)
            logger.info(
                "script_chunked",
                script_id=script.get("id"),
                script_type=script_type,
                chunks=len(chunks)
            )
            return chunks
        except Exception as e:
            logger.error(
                "chunking_failed",
                script_id=script.get("id"),
                error=str(e)
            )
            return self._chunk_general(script)

    def chunk_directory(self, directory: str) -> List[Chunk]:
        """
        Chunk all scripts in a directory.

        Args:
            directory: Path to directory containing scripts

        Returns:
            List of all chunks from all scripts
        """
        all_chunks = []
        script_extensions = {
            ".yml": "ansible",
            ".yaml": "ansible",
            ".tf": "terraform",
            ".sh": "shell",
            ".py": "python",
            ".json": "json"
        }

        path = Path(directory)
        if not path.exists():
            logger.warning("directory_not_found", directory=directory)
            return []

        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix in script_extensions:
                try:
                    content = file_path.read_text()
                    script = {
                        "id": str(file_path.relative_to(path)),
                        "content": content,
                        "type": script_extensions.get(file_path.suffix, "general"),
                        "path": str(file_path),
                        "metadata": {
                            "filename": file_path.name,
                            "directory": str(file_path.parent.relative_to(path))
                        }
                    }
                    chunks = self.chunk_script(script)
                    all_chunks.extend(chunks)
                except Exception as e:
                    logger.error("file_chunking_failed", path=str(file_path), error=str(e))

        logger.info(
            "directory_chunked",
            directory=directory,
            files_processed=len(list(path.rglob("*"))),
            total_chunks=len(all_chunks)
        )

        return all_chunks

    def _detect_script_type(self, script: Dict[str, Any]) -> str:
        """Detect script type from content or metadata"""
        # Check explicit type
        if "type" in script:
            return script["type"].lower()

        # Check file extension in path
        path = script.get("path", "")
        if path:
            ext = Path(path).suffix.lower()
            type_map = {
                ".yml": "ansible",
                ".yaml": "ansible",
                ".tf": "terraform",
                ".sh": "shell",
                ".bash": "shell",
                ".py": "python",
                ".json": "json"
            }
            if ext in type_map:
                return type_map[ext]

        # Detect from content
        content = script.get("content", "")
        if "tasks:" in content or "hosts:" in content or "playbook" in content.lower():
            return "ansible"
        if "resource " in content or "provider " in content or "terraform {" in content:
            return "terraform"
        if content.startswith("#!/bin/bash") or content.startswith("#!/bin/sh"):
            return "shell"
        if "apiVersion:" in content and "kind:" in content:
            return "kubernetes"

        return "general"

    def _chunk_ansible(self, script: Dict[str, Any]) -> List[Chunk]:
        """Chunk Ansible playbooks by plays and tasks"""
        content = script.get("content", "")
        script_id = script.get("id", "unknown")
        chunks = []

        # Split by YAML document separator
        documents = re.split(r'\n---\n', content)

        for doc_idx, doc in enumerate(documents):
            if not doc.strip():
                continue

            # Try to parse as YAML
            try:
                parsed = yaml.safe_load(doc)
                if isinstance(parsed, list):
                    # It's a playbook with plays
                    for play_idx, play in enumerate(parsed):
                        if isinstance(play, dict):
                            # Chunk individual tasks if present
                            tasks = play.get("tasks", [])
                            if tasks and len(tasks) > 3:
                                # Chunk by task groups
                                for task_idx, task in enumerate(tasks):
                                    task_content = yaml.dump(task, default_flow_style=False)
                                    chunk = Chunk(
                                        chunk_id=f"{script_id}_play{play_idx}_task{task_idx}",
                                        content=task_content,
                                        chunk_type="ansible_task",
                                        script_id=script_id,
                                        script_type="ansible",
                                        metadata={
                                            **script.get("metadata", {}),
                                            "play_index": play_idx,
                                            "task_index": task_idx,
                                            "task_name": task.get("name", "unnamed")
                                        },
                                        embedding_text=self._create_ansible_embedding_text(task)
                                    )
                                    chunks.append(chunk)
                            else:
                                # Keep play as single chunk
                                play_content = yaml.dump(play, default_flow_style=False)
                                chunk = Chunk(
                                    chunk_id=f"{script_id}_play{play_idx}",
                                    content=play_content,
                                    chunk_type="ansible_play",
                                    script_id=script_id,
                                    script_type="ansible",
                                    metadata={
                                        **script.get("metadata", {}),
                                        "play_index": play_idx,
                                        "play_name": play.get("name", "unnamed")
                                    },
                                    embedding_text=self._create_ansible_embedding_text(play)
                                )
                                chunks.append(chunk)
            except yaml.YAMLError:
                # Can't parse, chunk as text
                chunk = Chunk(
                    chunk_id=f"{script_id}_doc{doc_idx}",
                    content=doc,
                    chunk_type="ansible_document",
                    script_id=script_id,
                    script_type="ansible",
                    metadata=script.get("metadata", {}),
                    embedding_text=doc[:500]
                )
                chunks.append(chunk)

        return chunks if chunks else self._chunk_general(script)

    def _chunk_terraform(self, script: Dict[str, Any]) -> List[Chunk]:
        """Chunk Terraform files by resources and modules"""
        content = script.get("content", "")
        script_id = script.get("id", "unknown")
        chunks = []

        # Patterns for Terraform blocks
        block_pattern = r'(resource|module|data|provider|variable|output|locals)\s+"([^"]+)"(?:\s+"([^"]+)")?\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'

        matches = list(re.finditer(block_pattern, content, re.MULTILINE | re.DOTALL))

        if matches:
            for idx, match in enumerate(matches):
                block_type = match.group(1)
                block_name = match.group(2)
                block_resource = match.group(3) or ""
                block_content = match.group(0)

                chunk = Chunk(
                    chunk_id=f"{script_id}_{block_type}_{idx}",
                    content=block_content,
                    chunk_type=f"terraform_{block_type}",
                    script_id=script_id,
                    script_type="terraform",
                    metadata={
                        **script.get("metadata", {}),
                        "block_type": block_type,
                        "block_name": block_name,
                        "resource_type": block_resource
                    },
                    embedding_text=f"Terraform {block_type} {block_name} {block_resource} {block_content[:300]}"
                )
                chunks.append(chunk)

        return chunks if chunks else self._chunk_general(script)

    def _chunk_shell(self, script: Dict[str, Any]) -> List[Chunk]:
        """Chunk shell scripts by functions and sections"""
        content = script.get("content", "")
        script_id = script.get("id", "unknown")
        chunks = []

        # Split by function definitions
        function_pattern = r'(?:function\s+(\w+)|(\w+)\s*\(\s*\))\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = list(re.finditer(function_pattern, content, re.MULTILINE | re.DOTALL))

        if matches:
            for idx, match in enumerate(matches):
                func_name = match.group(1) or match.group(2)
                func_content = match.group(0)

                chunk = Chunk(
                    chunk_id=f"{script_id}_func_{func_name}",
                    content=func_content,
                    chunk_type="shell_function",
                    script_id=script_id,
                    script_type="shell",
                    metadata={
                        **script.get("metadata", {}),
                        "function_name": func_name
                    },
                    embedding_text=f"Shell function {func_name}: {func_content[:300]}"
                )
                chunks.append(chunk)

        # Also look for section comments
        section_pattern = r'(?:^|\n)(#{3,}\s*[^\n]+\s*#{3,}\n(?:[^\n]*\n)*?)(?=\n#{3,}|\Z)'
        section_matches = list(re.finditer(section_pattern, content))

        for idx, match in enumerate(section_matches):
            section_content = match.group(1)
            # Extract section title
            title_match = re.search(r'#{3,}\s*([^\n#]+)', section_content)
            section_title = title_match.group(1).strip() if title_match else f"section_{idx}"

            chunk = Chunk(
                chunk_id=f"{script_id}_section_{idx}",
                content=section_content,
                chunk_type="shell_section",
                script_id=script_id,
                script_type="shell",
                metadata={
                    **script.get("metadata", {}),
                    "section_title": section_title
                },
                embedding_text=f"Shell section {section_title}: {section_content[:300]}"
            )
            chunks.append(chunk)

        return chunks if chunks else self._chunk_general(script)

    def _chunk_kubernetes(self, script: Dict[str, Any]) -> List[Chunk]:
        """Chunk Kubernetes manifests by resource definitions"""
        content = script.get("content", "")
        script_id = script.get("id", "unknown")
        chunks = []

        # Split by YAML document separator
        documents = re.split(r'\n---\n', content)

        for doc_idx, doc in enumerate(documents):
            if not doc.strip():
                continue

            try:
                parsed = yaml.safe_load(doc)
                if isinstance(parsed, dict) and "kind" in parsed:
                    kind = parsed.get("kind", "unknown")
                    name = parsed.get("metadata", {}).get("name", "unnamed")

                    chunk = Chunk(
                        chunk_id=f"{script_id}_{kind}_{name}",
                        content=doc,
                        chunk_type=f"k8s_{kind.lower()}",
                        script_id=script_id,
                        script_type="kubernetes",
                        metadata={
                            **script.get("metadata", {}),
                            "kind": kind,
                            "resource_name": name,
                            "namespace": parsed.get("metadata", {}).get("namespace", "default")
                        },
                        embedding_text=f"Kubernetes {kind} {name}: {doc[:300]}"
                    )
                    chunks.append(chunk)
            except yaml.YAMLError:
                # Can't parse, add as raw chunk
                chunk = Chunk(
                    chunk_id=f"{script_id}_doc{doc_idx}",
                    content=doc,
                    chunk_type="k8s_document",
                    script_id=script_id,
                    script_type="kubernetes",
                    metadata=script.get("metadata", {}),
                    embedding_text=doc[:500]
                )
                chunks.append(chunk)

        return chunks if chunks else self._chunk_general(script)

    def _chunk_python(self, script: Dict[str, Any]) -> List[Chunk]:
        """Chunk Python scripts by functions and classes"""
        content = script.get("content", "")
        script_id = script.get("id", "unknown")
        chunks = []

        # Pattern for function definitions
        func_pattern = r'((?:async\s+)?def\s+(\w+)\s*\([^)]*\)(?:\s*->\s*[^:]+)?:\s*(?:"""[^"]*"""|\'\'\'[^\']*\'\'\')?\s*(?:[^\n]*\n)*?(?=\n(?:async\s+)?def\s|\nclass\s|\Z))'

        matches = list(re.finditer(func_pattern, content, re.MULTILINE))

        for match in matches:
            func_content = match.group(1)
            func_name = match.group(2)

            # Extract docstring if present
            docstring_match = re.search(r'(?:"""([^"]*)"""|\'\'\'([^\']*)\'\'\')', func_content)
            docstring = (docstring_match.group(1) or docstring_match.group(2) or "").strip() if docstring_match else ""

            chunk = Chunk(
                chunk_id=f"{script_id}_func_{func_name}",
                content=func_content,
                chunk_type="python_function",
                script_id=script_id,
                script_type="python",
                metadata={
                    **script.get("metadata", {}),
                    "function_name": func_name,
                    "has_docstring": bool(docstring)
                },
                embedding_text=f"Python function {func_name}: {docstring} {func_content[:200]}"
            )
            chunks.append(chunk)

        return chunks if chunks else self._chunk_general(script)

    def _chunk_yaml(self, script: Dict[str, Any]) -> List[Chunk]:
        """Chunk generic YAML files"""
        return self._chunk_ansible(script)  # Reuse ansible chunking for YAML

    def _chunk_json(self, script: Dict[str, Any]) -> List[Chunk]:
        """Chunk JSON files by top-level keys"""
        content = script.get("content", "")
        script_id = script.get("id", "unknown")
        chunks = []

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    chunk_content = json.dumps({key: value}, indent=2)
                    chunk = Chunk(
                        chunk_id=f"{script_id}_key_{key}",
                        content=chunk_content,
                        chunk_type="json_section",
                        script_id=script_id,
                        script_type="json",
                        metadata={
                            **script.get("metadata", {}),
                            "json_key": key
                        },
                        embedding_text=f"JSON {key}: {chunk_content[:300]}"
                    )
                    chunks.append(chunk)
        except json.JSONDecodeError:
            pass

        return chunks if chunks else self._chunk_general(script)

    def _chunk_general(self, script: Dict[str, Any]) -> List[Chunk]:
        """General chunking by size with overlap"""
        content = script.get("content", "")
        script_id = script.get("id", "unknown")
        script_type = script.get("type", "general")
        chunks = []

        # Split by paragraphs first
        paragraphs = re.split(r'\n\n+', content)

        current_chunk = ""
        chunk_idx = 0

        for para in paragraphs:
            if len(current_chunk) + len(para) <= self.config.max_chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk.strip():
                    chunk = Chunk(
                        chunk_id=f"{script_id}_chunk{chunk_idx}",
                        content=current_chunk.strip(),
                        chunk_type="general_chunk",
                        script_id=script_id,
                        script_type=script_type,
                        metadata=script.get("metadata", {}),
                        embedding_text=current_chunk[:500]
                    )
                    chunks.append(chunk)
                    chunk_idx += 1

                current_chunk = para + "\n\n"

        # Don't forget the last chunk
        if current_chunk.strip():
            chunk = Chunk(
                chunk_id=f"{script_id}_chunk{chunk_idx}",
                content=current_chunk.strip(),
                chunk_type="general_chunk",
                script_id=script_id,
                script_type=script_type,
                metadata=script.get("metadata", {}),
                embedding_text=current_chunk[:500]
            )
            chunks.append(chunk)

        return chunks

    def _create_ansible_embedding_text(self, obj: Any) -> str:
        """Create embedding-friendly text from Ansible object"""
        parts = []

        if isinstance(obj, dict):
            if "name" in obj:
                parts.append(f"Task: {obj['name']}")
            for module in ["shell", "command", "copy", "template", "service", "package", "file", "user", "group"]:
                if module in obj:
                    parts.append(f"Module: {module}")
                    if isinstance(obj[module], dict):
                        parts.append(str(obj[module]))
                    else:
                        parts.append(str(obj[module])[:200])
            if "when" in obj:
                parts.append(f"Condition: {obj['when']}")

        return " ".join(parts) if parts else yaml.dump(obj, default_flow_style=False)[:500]


# Global instance
smart_chunker = SmartChunker()
