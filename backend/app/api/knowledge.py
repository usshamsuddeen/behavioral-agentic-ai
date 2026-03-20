"""
Knowledge Base API for Behavioral Agentic AI
FRD v3.0 — Tenant-scoped Knowledge Management

All endpoints require JWT authentication.
Tenant isolation is enforced via tenant_id as the ChromaDB collection key (FR-7.3).

Endpoints:
- POST /knowledge/upload: Upload and index document
- POST /knowledge/faqs: Upload and index FAQs
- POST /knowledge/text: Upload raw text
- GET /knowledge/search: Search knowledge base
- GET /knowledge/documents: List all documents
- DELETE /knowledge/document/{document_id}: Delete a document
- DELETE /knowledge: Delete entire knowledge base
- GET /knowledge/stats: Get statistics
"""

import os
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.knowledge.manager import get_knowledge_manager
from app.database import get_db
from app.models.user import User
from app.models.knowledge_document import KnowledgeDocument
from app.middleware.jwt import get_current_user, get_tenant_for_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base"])


# ═══════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════

class FAQItem(BaseModel):
    """Single FAQ item."""
    question: str = Field(..., description="FAQ question")
    answer: str = Field(..., description="FAQ answer")


class FAQUploadRequest(BaseModel):
    """Request to upload FAQs."""
    faqs: List[FAQItem] = Field(..., description="List of FAQs")
    category: str = Field("general", description="FAQ category")


class TextUploadRequest(BaseModel):
    """Request to upload raw text."""
    text: str = Field(..., description="Text content to index")
    source: str = Field("manual_entry", description="Source identifier")
    doc_type: str = Field("general", description="Document type")
    category: str = Field("general", description="Category")


class SearchRequest(BaseModel):
    """Request for knowledge search."""
    query: str = Field(..., description="Search query")
    top_k: int = Field(5, ge=1, le=20, description="Number of results")
    doc_type: Optional[str] = Field(None, description="Filter by document type")


class UploadResponse(BaseModel):
    """Response for upload operations."""
    success: bool
    document_id: Optional[str] = None
    filename: Optional[str] = None
    chunks_created: int = 0
    error: Optional[str] = None


class SearchResponse(BaseModel):
    """Response for search operations."""
    query: str
    results_count: int
    results: List[dict]


class StatsResponse(BaseModel):
    """Response for statistics."""
    client_id: str
    total_documents: int
    total_chunks: int
    total_size_bytes: int
    documents_by_type: dict


# ═══════════════════════════════════════════════════════════════════
# HELPER: Resolve tenant_id as knowledge client_id
# ═══════════════════════════════════════════════════════════════════

def resolve_client_id(current_user: User, db: Session) -> str:
    """
    Get the ChromaDB collection key for this user's tenant.
    Uses str(tenant.id) for tenant-isolated collections — FR-7.3.
    
    Admin/super_admin users who also own a tenant get their tenant's ID.
    Pure super admins (no tenant) get 'system'.
    """
    # First check if user has a direct tenant_id (covers admin users who own tenants)
    if current_user.tenant_id:
        return str(current_user.tenant_id)
    
    # Fallback: try to resolve via get_tenant_for_user
    tenant = get_tenant_for_user(current_user, db)
    if tenant is not None:
        return str(tenant.id)
    
    return "system"


# ═══════════════════════════════════════════════════════════════════
# API Endpoints (Tenant-Scoped)
# ═══════════════════════════════════════════════════════════════════

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("general"),
    category: str = Form("general"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and index a document (tenant-scoped).
    
    Supports: PDF, DOCX, TXT, JSON, CSV, MD, PNG, JPG, JPEG, WEBP
    
    - **file**: Document file to upload
    - **doc_type**: Document type (product, policy, faq, general)
    - **category**: Document category
    """
    client_id = resolve_client_id(current_user, db)
    
    try:
        content = await file.read()
        
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # ★ V4.1: Save image files to disk so they can be served in chat
        file_url = None
        filename = file.filename or "unnamed_document"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
        
        if ext in IMAGE_EXTENSIONS:
            import uuid
            uploads_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "data", "kb_uploads"
            )
            os.makedirs(uploads_dir, exist_ok=True)
            
            # Unique filename: tenant_id + uuid + original ext
            safe_name = f"{client_id}_{uuid.uuid4().hex[:8]}_{filename}"
            save_path = os.path.join(uploads_dir, safe_name)
            with open(save_path, "wb") as f:
                f.write(content)
            
            file_url = f"/uploads/{safe_name}"
            logger.info(f"📸 Image saved: {file_url}")
        
        manager = get_knowledge_manager()
        
        # Pass file_url as additional metadata so chunks carry the image reference
        additional_meta = {"file_url": file_url} if file_url else None
        
        # ★ V4.2: For standalone image uploads, prepend [IMAGE:url] tag to indexed text
        # so RAG can include the image reference in AI responses
        index_content = content
        if file_url and ext in IMAGE_EXTENSIONS:
            image_tag = f"[IMAGE:{file_url}]\n".encode("utf-8")
            index_content = image_tag + content

        result = manager.upload_document(
            client_id=client_id,
            content=index_content,
            filename=filename,
            doc_type=doc_type,
            category=category,
            metadata=additional_meta
        )

        # ── Track in SQL (FRD §12: knowledge_documents table) ──
        if result["success"]:
            try:
                resolved_tid = current_user.tenant_id or (tenant.id if (tenant := get_tenant_for_user(current_user, db)) else None)
                doc_record = KnowledgeDocument(
                    tenant_id=resolved_tid,
                    filename=filename,
                    doc_type=doc_type,
                    category=category,
                    file_size=len(content),
                    chunk_count=result.get("chunks_created", 0),
                    chromadb_doc_id=result.get("document_id"),
                    status="indexed",
                    uploaded_by=current_user.id,
                    file_url=file_url,  # ★ V4.1: Store image URL
                )
                db.add(doc_record)
                db.commit()
            except Exception as track_err:
                logger.warning(f"KB tracking failed (non-blocking): {track_err}")

        return UploadResponse(
            success=result["success"],
            document_id=result.get("document_id"),
            filename=result.get("filename"),
            chunks_created=result.get("chunks_created", 0),
            error=result.get("error")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/faqs", response_model=UploadResponse)
async def upload_faqs(
    request: FAQUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and index FAQ data (tenant-scoped).
    
    - **faqs**: List of FAQ items with question and answer
    - **category**: FAQ category
    """
    client_id = resolve_client_id(current_user, db)
    
    try:
        manager = get_knowledge_manager()
        
        faqs = [{"question": f.question, "answer": f.answer} for f in request.faqs]
        
        result = manager.upload_faqs(
            client_id=client_id,
            faqs=faqs,
            category=request.category
        )
        
        return UploadResponse(
            success=result["success"],
            document_id=result.get("document_id"),
            chunks_created=result.get("faqs_indexed", 0),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"❌ FAQ upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text", response_model=UploadResponse)
async def upload_text(
    request: TextUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and index raw text content (tenant-scoped).
    
    - **text**: Text content to index
    - **source**: Source identifier
    - **doc_type**: Document type
    - **category**: Category
    """
    client_id = resolve_client_id(current_user, db)
    
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text content is required")
    
    try:
        manager = get_knowledge_manager()
        
        # Convert text to bytes (manager.upload_document expects bytes)
        content = request.text.encode("utf-8")
        filename = f"{request.source}.txt" if request.source else "manual_entry.txt"
        
        result = manager.upload_document(
            client_id=client_id,
            content=content,
            filename=filename,
            doc_type=request.doc_type,
            category=request.category
        )

        # ── Track in SQL (FRD §12: knowledge_documents table) ──
        if result["success"]:
            try:
                resolved_tid = current_user.tenant_id or (tenant.id if (tenant := get_tenant_for_user(current_user, db)) else None)
                doc_record = KnowledgeDocument(
                    tenant_id=resolved_tid,
                    filename=filename,
                    doc_type=request.doc_type,
                    category=request.category,
                    file_size=len(content),
                    chunk_count=result.get("chunks_created", 0),
                    chromadb_doc_id=result.get("document_id"),
                    status="indexed",
                    uploaded_by=current_user.id,
                )
                db.add(doc_record)
                db.commit()
            except Exception as track_err:
                logger.warning(f"KB text tracking failed (non-blocking): {track_err}")

        return UploadResponse(
            success=result["success"],
            document_id=result.get("document_id"),
            filename=filename,
            chunks_created=result.get("chunks_created", 0),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"❌ Text upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search the knowledge base (tenant-scoped).
    
    - **query**: Search query
    - **top_k**: Number of results (1-20)
    - **doc_type**: Filter by document type (optional)
    """
    client_id = resolve_client_id(current_user, db)
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query is required")
    
    try:
        manager = get_knowledge_manager()
        result = manager.search_knowledge(
            client_id=client_id,
            query=request.query,
            top_k=request.top_k,
            doc_type=request.doc_type
        )
        
        return SearchResponse(
            query=result["query"],
            results_count=result["results_count"],
            results=result["results"]
        )
        
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=SearchResponse)
async def search_knowledge_get(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results"),
    doc_type: Optional[str] = Query(None, description="Filter by document type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search the knowledge base (GET version, tenant-scoped)."""
    return await search_knowledge(
        SearchRequest(query=query, top_k=top_k, doc_type=doc_type),
        current_user=current_user,
        db=db
    )


@router.get("/documents")
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all indexed documents (tenant-scoped).
    """
    client_id = resolve_client_id(current_user, db)
    
    try:
        manager = get_knowledge_manager()
        documents = manager.list_documents(client_id)
        
        return {
            "client_id": client_id,
            "total_documents": len(documents),
            "documents": documents
        }
        
    except Exception as e:
        logger.error(f"❌ List documents failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/document/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a specific document (tenant-scoped).
    
    - **document_id**: Document ID to delete
    """
    client_id = resolve_client_id(current_user, db)
    
    try:
        manager = get_knowledge_manager()
        result = manager.delete_document(client_id, document_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "Not found"))

        # ── Mark SQL record as deleted ──
        try:
            tenant = get_tenant_for_user(current_user, db)
            if tenant:
                doc_row = db.query(KnowledgeDocument).filter(
                    KnowledgeDocument.tenant_id == tenant.id,
                    KnowledgeDocument.chromadb_doc_id == document_id,
                    KnowledgeDocument.status != "deleted",
                ).first()
                if doc_row:
                    doc_row.status = "deleted"
                    db.commit()
        except Exception as del_err:
            logger.warning(f"KB delete tracking failed: {del_err}")

        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Delete document failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/{document_id}/content")
async def get_document_content(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get full text content for a specific document (tenant-scoped).
    
    - **document_id**: Document ID to retrieve
    """
    client_id = resolve_client_id(current_user, db)
    
    try:
        manager = get_knowledge_manager()
        result = manager.get_document_content(client_id, document_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Not found"))

        return {
            "document_id": result["document_id"],
            "filename": result["filename"],
            "content": result["content"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get document content failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.delete("")
async def delete_all_documents(
    confirm: bool = Query(False, description="Confirm deletion"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete entire knowledge base for this tenant.
    
    - **confirm**: Must be True to confirm deletion
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Please set confirm=true to delete all documents"
        )
    
    client_id = resolve_client_id(current_user, db)
    
    try:
        manager = get_knowledge_manager()
        result = manager.delete_all_documents(client_id)

        # ── Mark all SQL records as deleted ──
        try:
            tenant = get_tenant_for_user(current_user, db)
            if tenant:
                db.query(KnowledgeDocument).filter(
                    KnowledgeDocument.tenant_id == tenant.id,
                    KnowledgeDocument.status != "deleted",
                ).update({"status": "deleted"})
                db.commit()
        except Exception as del_err:
            logger.warning(f"KB bulk delete tracking failed: {del_err}")

        return result
        
    except Exception as e:
        logger.error(f"❌ Delete all documents failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get knowledge base statistics (tenant-scoped).
    """
    client_id = resolve_client_id(current_user, db)
    
    try:
        manager = get_knowledge_manager()
        stats = manager.get_knowledge_stats(client_id)
        
        return StatsResponse(
            client_id=stats["client_id"],
            total_documents=stats["total_documents"],
            total_chunks=stats["total_chunks"],
            total_size_bytes=stats["total_size_bytes"],
            documents_by_type=stats["documents_by_type"]
        )
        
    except Exception as e:
        logger.error(f"❌ Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
