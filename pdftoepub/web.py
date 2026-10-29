"""
Web Application Backend for PDF to EPUB & AZW3 Converter.
Built with FastAPI. Supports drag-and-drop file upload, workspace PDF selection,
real-time progress tracking, and direct downloads.
"""

import os
import uuid
import glob
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .pipeline import ConversionPipeline


app = FastAPI(title="PDF to EPUB & AZW3 Studio", version="1.0.0")

# Serve static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# In-memory job state store
jobs: Dict[str, Dict[str, Any]] = {}

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "converted_ebooks")
os.makedirs(OUTPUT_DIR, exist_ok=True)


class ConvertExistingRequest(BaseModel):
    filename: str
    ocr_mode: str = "auto"
    title: Optional[str] = None
    author: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Web UI oluşturuluyor...</h1>"


_SYSTEM_STATUS: Optional[Dict[str, Any]] = None


def get_cached_system_status() -> Dict[str, Any]:
    global _SYSTEM_STATUS
    if _SYSTEM_STATUS is None:
        try:
            import torch
            from .converter_azw import AZW3Converter

            cuda_avail = torch.cuda.is_available()
            device_name = torch.cuda.get_device_name(0) if cuda_avail else "CPU"
            azw_conv = AZW3Converter()
            _SYSTEM_STATUS = {
                "cuda_available": cuda_avail,
                "device_name": device_name,
                "calibre_available": azw_conv.is_available,
                "calibre_path": azw_conv.calibre_exe
            }
        except Exception:
            _SYSTEM_STATUS = {
                "cuda_available": False,
                "device_name": "CPU",
                "calibre_available": False,
                "calibre_path": None
            }
    return _SYSTEM_STATUS


@app.get("/api/system-status")
async def get_system_status():
    """Returns GPU and Calibre availability status from safe cache."""
    return get_cached_system_status()


@app.get("/api/workspace-pdfs")
async def list_workspace_pdfs():
    """Lists PDF files already present in the workspace directory."""
    pdf_files = []
    for f in os.listdir(WORKSPACE_DIR):
        if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(WORKSPACE_DIR, f)):
            full_p = os.path.join(WORKSPACE_DIR, f)
            size_mb = round(os.path.getsize(full_p) / (1024 * 1024), 2)
            pdf_files.append({
                "name": f,
                "size_mb": size_mb,
                "path": full_p
            })
    return {"pdfs": pdf_files}


def run_conversion_job(job_id: str, pdf_path: str, ocr_mode: str, title: Optional[str], author: Optional[str]):
    filename = jobs.get(job_id, {}).get("filename", os.path.basename(pdf_path))
    print(f"\n[+] Dönüştürme Başlatıldı: '{filename}' (OCR Modu: {ocr_mode})")

    jobs[job_id]["status"] = "processing"
    jobs[job_id]["progress"] = 0.05
    jobs[job_id]["message"] = "Başlatılıyor..."

    pipeline = ConversionPipeline(ocr_mode=ocr_mode)

    last_milestone = [-1]

    def on_progress(percent: float, msg: str):
        jobs[job_id]["progress"] = percent
        jobs[job_id]["message"] = msg

        # Log essential milestone updates only (every 20% or key stages)
        milestone = int(percent * 100)
        is_key_stage = (
            milestone >= 70
            or milestone >= last_milestone[0] + 20
        )
        if is_key_stage and milestone != last_milestone[0]:
            last_milestone[0] = milestone
            print(f"    --> [%{milestone:02d}] {msg}")

    try:
        res = pipeline.convert(
            pdf_path=pdf_path,
            output_dir=OUTPUT_DIR,
            title=title,
            author=author,
            progress_callback=on_progress
        )
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["message"] = "Tamamlandı!"
        jobs[job_id]["result"] = res
        print(f"[✓] Dönüştürme Tamamlandı: '{filename}' (Toplam {res.get('total_chapters', '-')} bölüm)\n")
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Hata: {str(e)}"
        print(f"[!] Dönüştürme Hatası: '{filename}' -> {str(e)}\n")


@app.post("/api/convert-upload")
async def convert_uploaded_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    ocr_mode: str = Form("auto"),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Lütfen geçerli bir PDF dosyası yükleyin.")

    job_id = str(uuid.uuid4())
    upload_dir = os.path.join(OUTPUT_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    temp_pdf_path = os.path.join(upload_dir, f"{job_id}_{file.filename}")

    with open(temp_pdf_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    jobs[job_id] = {
        "job_id": job_id,
        "filename": file.filename,
        "status": "queued",
        "progress": 0.0,
        "message": "Sıraya alındı...",
        "result": None
    }

    background_tasks.add_task(
        run_conversion_job,
        job_id,
        temp_pdf_path,
        ocr_mode,
        title,
        author
    )

    return {"job_id": job_id}


@app.post("/api/convert-existing")
async def convert_existing_file(
    req: ConvertExistingRequest,
    background_tasks: BackgroundTasks
):
    pdf_path = os.path.join(WORKSPACE_DIR, req.filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Seçilen PDF dosyası bulunamadı.")

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "filename": req.filename,
        "status": "queued",
        "progress": 0.0,
        "message": "Sıraya alındı...",
        "result": None
    }

    background_tasks.add_task(
        run_conversion_job,
        job_id,
        pdf_path,
        req.ocr_mode,
        req.title,
        req.author
    )

    return {"job_id": job_id}


@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="İşlem kimliği bulunamadı.")
    return jobs[job_id]


@app.get("/api/download/{fmt}/{job_id}")
async def download_converted_file(fmt: str, job_id: str):
    if job_id not in jobs or jobs[job_id].get("status") != "completed":
        raise HTTPException(status_code=404, detail="Dosya hazır değil veya bulunamadı.")

    res = jobs[job_id]["result"]
    if fmt == "epub":
        target = res.get("epub_path")
        media_type = "application/epub+zip"
    elif fmt == "azw3":
        target = res.get("azw3_path")
        media_type = "application/vnd.amazon.ebook"
    else:
        raise HTTPException(status_code=400, detail="Geçersiz format.")

    if not target or not os.path.exists(target):
        raise HTTPException(status_code=404, detail=f"{fmt.upper()} dosyası mevcut değil.")

    return FileResponse(
        target,
        media_type=media_type,
        filename=os.path.basename(target)
    )
