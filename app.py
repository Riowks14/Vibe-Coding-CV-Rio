from base64 import b64encode
from io import BytesIO
import warnings
import webbrowser

from flask import Flask, jsonify, render_template_string, request
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge

MAX_PHOTO_BYTES = 2 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_PHOTO_BYTES + 64 * 1024
MAX_PHOTO_PIXELS = 25_000_000
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
HTML_PAGE = r"""<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f7f8fc">
  <title>BuildCV — CV builder</title>
  <style>
    :root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:#172033;background:#f6f7fb;font-synthesis:none;text-rendering:optimizeLegibility}
    *{box-sizing:border-box}body{margin:0}button,input,textarea,select{font:inherit}button{cursor:pointer}
    .topbar{height:70px;background:#fff;border-bottom:1px solid #e8eaf1;display:flex;align-items:center;justify-content:space-between;padding:0 max(24px,calc((100vw - 1280px)/2));position:sticky;top:0;z-index:5}
    .brand{font-weight:800;letter-spacing:-.6px;font-size:20px;color:#222b48}.brand b{color:#6658e8}.top-actions{display:flex;gap:10px;align-items:center}
    .page{max-width:1280px;margin:auto;padding:34px 24px 70px}.eyebrow{color:#6559d9;font-size:12px;font-weight:800;letter-spacing:1.3px;text-transform:uppercase}
    h1{font-size:clamp(28px,4vw,40px);letter-spacing:-1.3px;margin:8px 0}.lede{color:#6c7486;max-width:700px;line-height:1.65;margin:0}
    .steps{display:flex;gap:9px;flex-wrap:wrap;margin:27px 0}.step{border:1px solid #e2e5ee;background:white;border-radius:99px;padding:9px 15px;font-size:13px;color:#6c7486}.step.active{color:#4f45c7;border-color:#c9c4ff;background:#f0efff;font-weight:700}
    .toolbar{display:flex;justify-content:space-between;align-items:center;gap:14px;margin:28px 0 18px;flex-wrap:wrap}.tabs{display:flex;gap:8px}.tab,.button{border:1px solid #e1e4ed;background:#fff;color:#414a5d;border-radius:10px;padding:10px 15px;font-weight:650}.tab.selected{background:#252d49;color:#fff;border-color:#252d49}.button.primary{background:#6658e8;border-color:#6658e8;color:#fff}.button:hover,.tab:hover{transform:translateY(-1px);box-shadow:0 5px 16px #1b24400d}
    .purpose-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:14px 16px;background:#fff;border:1px solid #e8eaf1;border-radius:14px;margin:0 0 20px}.purpose-row label{font-size:13px;font-weight:750}.purpose-row select{border:1px solid #dfe2eb;background:white;border-radius:8px;padding:9px 32px 9px 11px;color:#273149}.purpose-note{font-size:12px;color:#7a8292}
    .template-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.template-card{background:#fff;border:1px solid #e5e7ef;border-radius:16px;overflow:hidden;transition:.18s;display:flex;flex-direction:column}.template-card.chosen{border:2px solid #6a5de8;box-shadow:0 8px 28px #6658e81c}.template-card:hover{transform:translateY(-2px)}
    .mini{height:190px;background:#f0f2f8;padding:17px 22px;display:flex;justify-content:center;overflow:hidden}.mini-paper{width:120px;height:160px;background:#fff;box-shadow:0 3px 12px #1d25441b;padding:13px 11px;display:flex;gap:7px;color:#172033}.mini-lines{display:flex;flex-direction:column;gap:5px;flex:1}.mini-line{height:3px;background:#d8dce7;border-radius:3px}.mini-line.short{width:55%}.mini-line.mid{width:76%}.mini-title{height:6px;width:54%;background:#313b59;border-radius:4px;margin-bottom:2px}.mini-head{height:16px;background:#edf0f7;margin:-2px -2px 3px}.mini-col{display:flex;flex-direction:column;gap:5px;flex:1}.mini-side{width:34px;background:#34415e;margin:-13px 0 -13px -11px;padding:11px 5px;display:flex;flex-direction:column;gap:5px}.mini-side .mini-line{background:#ffffff75;height:2px}.mini-accent{height:5px;width:60%;background:#7664e8;border-radius:4px;margin:2px 0}.mini-dot{width:13px;height:13px;border-radius:50%;background:#cdd3e0;margin:0 auto 2px}
    .layout-ats .mini-paper{display:block}.layout-classic .mini-paper{display:block}.layout-classic .mini-head{height:23px;background:#f0f2f8;border-bottom:3px solid #273655}.layout-editorial .mini-paper{display:flex}.layout-editorial .mini-side{background:#23334d;width:30px}.layout-profile .mini-side{background:#6558d9;width:40px}.layout-profile .mini-dot{background:#ffffff90}.layout-timeline .mini-paper{display:block}.layout-timeline .mini-head{height:9px;background:#6658e8}.layout-timeline .mini-line:nth-child(odd){margin-left:9px}.layout-portfolio .mini-paper{display:block}.layout-portfolio .mini-head{height:25px;background:#e8e3ff;border-radius:4px}.layout-portfolio .mini-col{display:grid;grid-template-columns:1fr 1fr}
    .card-body{padding:17px 18px 18px;display:flex;flex-direction:column;flex:1}.card-kicker{font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#7064d6;font-weight:800}.card-body h3{margin:6px 0;font-size:17px}.card-body p{font-size:13px;line-height:1.55;color:#70788a;margin:0 0 16px;flex:1}.card-foot{display:flex;align-items:center;justify-content:space-between;gap:8px}.badge{font-size:10px;padding:5px 8px;border-radius:99px;background:#f0efff;color:#584cca;font-weight:700}
    .builder{display:grid;grid-template-columns:minmax(280px,.8fr) minmax(440px,1.2fr);gap:20px;align-items:start}.panel{background:#fff;border:1px solid #e6e8f0;border-radius:16px;padding:20px}.panel h2{font-size:18px;margin:0 0 5px}.panel-sub{font-size:12px;color:#7a8291;margin:0 0 18px}.field-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.field{display:flex;flex-direction:column;gap:6px}.field.full{grid-column:1/-1}.field label{font-size:12px;font-weight:700;color:#454e62}.field input,.field textarea{border:1px solid #e0e3ec;border-radius:8px;padding:10px 11px;outline:none;width:100%;background:#fff}.field textarea{resize:vertical;min-height:84px}.field input:focus,.field textarea:focus{border-color:#8176e9;box-shadow:0 0 0 3px #7567e81c}
    .section-head{display:flex;align-items:center;justify-content:space-between;margin:22px 0 10px}.section-head h3{font-size:14px;margin:0}.entry{border:1px solid #edf0f5;border-radius:10px;padding:12px;margin:9px 0;position:relative}.entry .field-grid{gap:9px}.entry-remove{border:0;background:none;color:#9b5260;font-size:12px;padding:4px}.add-button{border:1px dashed #c9cde0;background:#fafaff;color:#554aca;border-radius:8px;padding:9px 12px;font-weight:650;font-size:12px;width:100%}
    .preview-panel{position:sticky;top:88px}.preview-tools{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}.paper-wrap{background:#eef0f5;padding:20px;border-radius:12px;max-height:calc(100vh - 200px);overflow:auto}.resume{width:100%;max-width:595px;min-height:842px;margin:0 auto;background:#fff;color:#1d2638;box-shadow:0 5px 24px #1b24401a;padding:42px 45px;font-family:Arial,sans-serif;font-size:11px;line-height:1.48;overflow-wrap:anywhere}    .resume h1{font-size:27px;letter-spacing:-.7px;margin:0 0 4px;color:#202a40}.resume .contact{font-size:9px;color:#637087;margin:0 0 18px}.resume .contact-list{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px;min-width:0}.resume .contact-item{display:inline-flex;align-items:center;white-space:nowrap;min-width:0;overflow-wrap:normal;word-break:normal}.resume .contact-item + .contact-item::before{content:"•";margin-right:8px;color:#8a93a7}.resume h2{font-size:11px;text-transform:uppercase;letter-spacing:1.1px;color:#394768;margin:17px 0 7px;border-bottom:1px solid #dce1eb;padding-bottom:4px}.resume p{margin:4px 0}.resume .resume-entry{margin:8px 0}.resume .resume-entry strong{font-size:11px}.resume .muted{color:#697487}.resume .resume-head{margin-bottom:12px}.resume .resume-body{min-width:0}.resume .resume-columns{display:grid;grid-template-columns:1fr 1fr;gap:21px}.resume .resume-side{background:#f1f3f8;padding:14px;margin:-42px 0 -42px -45px}.resume .resume-side h1{font-size:22px}.resume .resume-side h2{margin-top:17px}
    .resume.layout-classic{padding-top:49px}.resume.layout-classic .resume-head{text-align:center;border-bottom:3px solid #263858;padding-bottom:15px}.resume.layout-classic h2{border:0;border-left:3px solid #344a70;padding:2px 0 2px 8px}
    .resume.layout-editorial{display:grid;grid-template-columns:minmax(180px,.42fr) minmax(0,1fr);gap:18px;padding:0;align-items:stretch}.resume.layout-editorial .resume-side{background:#253751;color:white;padding:28px 16px;margin:0;display:flex;flex-direction:column;gap:12px}.resume.layout-editorial .resume-side h1,.resume.layout-editorial .resume-side h2{color:white}.resume.layout-editorial .resume-side h2{border-color:#8190aa}.resume.layout-editorial .resume-body{padding:32px 24px 32px 0;min-width:0}.resume.layout-editorial .resume-side-content{display:flex;flex-direction:column;gap:8px;min-width:0}.resume.layout-editorial .resume-side-content p,.resume.layout-profile .resume-side-content p{margin:0;line-height:1.35}
    .resume.layout-profile{display:grid;grid-template-columns:minmax(180px,.42fr) minmax(0,1fr);gap:18px;padding:0;align-items:stretch}.resume.layout-profile .resume-side{background:#6254d5;color:white;padding:28px 16px;margin:0;display:flex;flex-direction:column;gap:12px}.resume.layout-profile .resume-side h1,.resume.layout-profile .resume-side h2{color:white}.resume.layout-profile .resume-side h2{border-color:#ffffff66}.resume.layout-profile .resume-body{padding:32px 24px 32px 0;min-width:0}.resume.layout-profile .resume-side-content{display:flex;flex-direction:column;gap:8px;min-width:0}.resume.layout-profile .resume-side .initials{width:54px;height:54px;border-radius:50%;border:2px solid #ffffffa0;display:grid;place-items:center;font-size:19px;font-weight:bold;margin-bottom:18px}.resume.layout-profile .resume-side .resume-photo,.resume.layout-editorial .resume-side .resume-photo{margin:0 auto 6px}.resume.layout-editorial .resume-side .resume-photo.position-left,.resume.layout-editorial .resume-side .resume-photo.position-right,.resume.layout-profile .resume-side .resume-photo.position-left,.resume.layout-profile .resume-side .resume-photo.position-right{margin:0 auto}    .photo-panel{border:1px solid #e6e8f0;border-radius:12px;padding:14px;margin:18px 0;background:#fbfbfe}.photo-panel h3{font-size:14px;margin:0 0 4px}.photo-help{font-size:11px;color:#737c8d;line-height:1.5;margin:0 0 11px}.photo-row{display:flex;gap:12px;align-items:center}.photo-preview{display:none;width:68px;height:68px;object-fit:cover;border:1px solid #d9dce5;background:white}.photo-preview.visible{display:block}.photo-preview.shape-round{border-radius:50%}.photo-preview.shape-rounded{border-radius:12px}.photo-preview.shape-square{border-radius:0}.photo-buttons{display:flex;gap:8px;flex-wrap:wrap}.photo-settings{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin-top:13px}.photo-settings label{font-size:11px;font-weight:700;color:#454e62}.photo-settings select{display:block;width:100%;margin-top:5px;border:1px solid #e0e3ec;border-radius:7px;padding:8px 6px;background:#fff;color:#273149}.photo-settings select:disabled{opacity:.55}.photo-error{font-size:11px;color:#ad3547;min-height:16px;margin:8px 0 0}.photo-status{font-size:10px;color:#737c8d;margin-top:8px}
    .resume-photo{object-fit:contain;background:#f1f2f5;border:1px solid #e3e6ed;display:block;flex:none}.resume-photo.size-small{width:62px;height:62px}.resume-photo.size-medium{width:82px;height:82px}.resume-photo.size-large{width:102px;height:102px}.resume-photo.shape-round{border-radius:50%}.resume-photo.shape-rounded{border-radius:13px}.resume-photo.shape-square{border-radius:0}    .resume .resume-head.has-photo{display:flex;align-items:flex-start;gap:15px}.resume-head.has-photo.photo-center{display:flex;flex-direction:column;align-items:center;text-align:center}.resume-head-content{flex:1;min-width:0}.resume-photo.position-left{order:-1}.resume-photo.position-right{order:1}.resume-photo.position-center{order:0;align-self:center;margin:0 auto 8px}.resume.layout-classic .resume-head.has-photo{text-align:left}.resume.layout-classic .resume-head.has-photo .resume-photo.position-left{order:-1}.resume.layout-classic .resume-head.has-photo .resume-photo.position-right{order:1}.resume.layout-classic .resume-head.has-photo.photo-center{text-align:center}.resume.layout-editorial .resume-side .resume-photo,.resume.layout-profile .resume-side .resume-photo{margin:0 auto 15px}.resume.layout-editorial .resume-side .resume-photo{border-color:#ffffff80}.resume.layout-profile .resume-side .resume-photo{border-color:#ffffffa0}.resume.layout-editorial .resume-side .resume-photo.position-center,.resume.layout-profile .resume-side .resume-photo.position-center{margin:0 auto 12px}    .resume.layout-editorial .resume-side,.resume.layout-profile .resume-side{display:flex;align-items:flex-start;gap:9px;flex-wrap:wrap}.resume-side-content{flex:1;min-width:0}.resume.layout-profile .profile-photo-area{flex-basis:100%;display:flex;justify-content:center}.resume.layout-editorial .resume-side .resume-photo.position-left,.resume.layout-profile .resume-side .resume-photo.position-left,.resume.layout-editorial .resume-side .resume-photo.position-right,.resume.layout-profile .resume-side .resume-photo.position-right{margin:0}
    .resume.layout-editorial .resume-side>.resume-photo.position-left,.resume.layout-profile .resume-side>.resume-photo.position-left{order:0;align-self:flex-start}.resume.layout-editorial .resume-side>.resume-photo.position-right,.resume.layout-profile .resume-side>.resume-photo.position-right{order:0;align-self:flex-end}
    .photo-form-actions{display:flex;gap:8px;flex-wrap:wrap}.button.small{font-size:11px;padding:7px 10px}
    .resume.layout-timeline{border-top:8px solid #6759e0;padding-top:35px}.resume.layout-timeline .resume-head{padding-bottom:13px;border-bottom:1px solid #e2e5ee}.resume.layout-timeline .resume-entry{border-left:2px solid #b9b2f5;padding-left:10px}
    .resume.layout-portfolio{border-top:8px solid #6759e0;padding-top:32px}.resume.layout-portfolio .resume-head{background:#f1efff;padding:17px;border-radius:8px}.resume.layout-portfolio .resume-columns{grid-template-columns:1fr 1fr}.resume.layout-portfolio .resume-entry{background:#f7f7fb;padding:8px;border-radius:6px}
    .empty{font-size:11px;color:#9098a8;font-style:italic}.status{font-size:12px;color:#677087}.hidden{display:none!important}
    @media(max-width:900px){.template-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.builder{grid-template-columns:1fr}.preview-panel{position:static}.paper-wrap{max-height:none}}
    @media(max-width:560px){.page{padding:24px 14px 50px}.template-grid{grid-template-columns:1fr}.topbar{padding:0 15px}.field-grid{grid-template-columns:1fr}.field.full{grid-column:auto}.resume{padding:27px 24px;min-height:842px}.resume .resume-side{margin:-27px 0 -27px -24px}.resume.layout-editorial,.resume.layout-profile{grid-template-columns:minmax(0,1fr);gap:0}.resume.layout-editorial .resume-side,.resume.layout-profile .resume-side{padding:25px 20px}.resume.layout-editorial .resume-body,.resume.layout-profile .resume-body{padding:24px 20px}.resume.layout-editorial .resume-side-content,.resume.layout-profile .resume-side-content{width:100%}.paper-wrap{padding:10px}}
    @page{size:A4;margin:0}
    @media print{body{background:#fff}.topbar,.page>header,.steps,.toolbar,.purpose-row,.editor-panel,.preview-tools{display:none!important}.page{max-width:none;padding:0;margin:0}.builder{display:block}.preview-panel{position:static;border:0;padding:0}.paper-wrap{padding:0;background:#fff;max-height:none;overflow:visible}.resume{width:210mm;min-height:297mm;max-width:none;margin:0;padding:18mm;box-shadow:none;font-size:10pt;print-color-adjust:exact;-webkit-print-color-adjust:exact}.resume.layout-editorial,.resume.layout-profile{grid-template-columns:minmax(180px,.42fr) minmax(0,1fr);gap:18px;padding:0;min-height:297mm}.resume.layout-editorial .resume-side,.resume.layout-profile .resume-side{padding:18mm 10mm}.resume.layout-editorial .resume-body,.resume.layout-profile .resume-body{padding:18mm 12mm 18mm 0}.resume .resume-side{margin:-18mm 0 -18mm -18mm}.resume.layout-classic{padding-top:22mm}.resume.layout-portfolio{padding-top:17mm}.resume.layout-timeline{padding-top:18mm}.resume-photo{print-color-adjust:exact;-webkit-print-color-adjust:exact}.resume .resume-entry,.resume section{break-inside:avoid-page}.resume-photo{max-width:28mm;max-height:28mm}}
  </style>
</head>
<body>
  <nav class="topbar"><div class="brand">BuildCV</div><div class="top-actions"><span class="status" id="save-status">Tersimpan otomatis</span><button class="button primary" onclick="downloadPdf()">Unduh PDF</button></div></nav>
  <main class="page">
    <header><div class="eyebrow">CV builder</div><h1>Buat CV yang mencerminkan diri Anda.</h1><p class="lede">Pilih tujuan untuk menyesuaikan isi, lalu pilih desain yang Anda suka. Keduanya bisa diganti kapan saja tanpa menghapus data.</p></header>
    <div class="steps"><span class="step active">1. Tujuan CV</span><span class="step active">2. Desain</span><span class="step">3. Isi &amp; preview</span></div>
    <div class="purpose-row"><label for="purpose">Tujuan CV</label><select id="purpose"></select><span class="purpose-note" id="purpose-note"></span></div>
    <div class="toolbar"><div class="tabs"><button class="tab selected" data-category="formal">FORMAL</button><button class="tab" data-category="creative">CREATIVE</button></div><div class="status">Pilih desain; data Anda tetap aman saat berpindah.</div></div>
    <section id="template-grid" class="template-grid" aria-label="Pilihan template"></section>
    <section id="builder" class="builder hidden">
      <div class="panel editor-panel"><h2>Isi CV Anda</h2><p class="panel-sub">Tujuan: <strong id="builder-purpose"></strong>. Semua perubahan tersimpan otomatis di perangkat ini.</p><div id="form-fields"></div></div>
      <div class="panel preview-panel"><div class="preview-tools"><div><h2>Preview langsung</h2><p class="panel-sub" id="preview-name"></p><button id="change-design" class="button">Ganti desain</button></div><button class="button primary" onclick="downloadPdf()">Unduh PDF A4</button></div><div class="paper-wrap"><article id="resume" class="resume"></article></div></div>
    </section>
  </main>
  <script>
    const purposes = {
      pekerjaan:{label:"Pekerjaan",note:"Tonjolkan pengalaman dan keterampilan yang relevan.",sections:["experience","projects","achievements"]},
      magang:{label:"Magang",note:"Tampilkan pengalaman, proyek, dan kesiapan belajar.",sections:["experience","projects","achievements"]},
      beasiswa:{label:"Beasiswa",note:"Fokus pada pendidikan, prestasi, dan kegiatan.",sections:["education","activities","achievements"]},
      akademik:{label:"Akademik",note:"Utamakan pendidikan, riset, publikasi, dan penghargaan.",sections:["education","research","achievements"]},
      organisasi:{label:"Organisasi formal",note:"Sorot pengalaman organisasi dan kontribusi.",sections:["activities","experience","achievements"]},
      kreatif:{label:"Portofolio & bidang kreatif",note:"Tonjolkan proyek, portofolio, dan keterampilan.",sections:["projects","experience","achievements"]}
    };
    const templates = [
      {id:"ats",name:"ATS-Friendly",category:"formal",desc:"Satu kolom yang sederhana, mudah dipindai ATS, dan tanpa elemen dekoratif.",layout:"layout-ats",badge:"ATS • 1 kolom"},
      {id:"classic",name:"Klasik Elegan",category:"formal",desc:"Header terpusat, pembatas tegas, dan alur baca formal yang rapi.",layout:"layout-classic",badge:"Elegan"},
      {id:"editorial",name:"Editorial Navy",category:"formal",desc:"Kolom kontak di sisi kiri dan area isi luas dengan nuansa navy profesional.",layout:"layout-editorial",badge:"Dua kolom"},
      {id:"profile",name:"Creative Profile",category:"creative",desc:"Sidebar berwarna untuk identitas dan keahlian, dengan konten utama terpisah.",layout:"layout-profile",badge:"Sidebar"},
      {id:"timeline",name:"Modern Timeline",category:"creative",desc:"Penekanan visual pada perjalanan pengalaman dengan garis waktu yang ekspresif.",layout:"layout-timeline",badge:"Timeline"},
      {id:"portfolio",name:"Portfolio Grid",category:"creative",desc:"Panel proyek bergaya portofolio untuk menampilkan karya dan pencapaian.",layout:"layout-portfolio",badge:"Grid proyek"}
    ];
    const sectionInfo = {
      education:{title:"Pendidikan",fields:[["school","Institusi / sekolah"],["degree","Jurusan / gelar"],["period","Periode"],["detail","Keterangan","textarea"]]},
      experience:{title:"Pengalaman kerja",fields:[["role","Posisi"],["organization","Perusahaan / organisasi"],["period","Periode"],["detail","Kontribusi / pencapaian","textarea"]]},
      activities:{title:"Organisasi & kegiatan",fields:[["role","Posisi / peran"],["organization","Organisasi / kegiatan"],["period","Periode"],["detail","Kontribusi","textarea"]]},
      projects:{title:"Proyek & portofolio",fields:[["name","Nama proyek"],["role","Peran"],["link","Tautan (opsional)"],["detail","Deskripsi / hasil","textarea"]]},
      research:{title:"Riset & publikasi",fields:[["name","Judul riset / publikasi"],["organization","Institusi / media"],["period","Tahun"],["detail","Ringkasan / tautan","textarea"]]},
      achievements:{title:"Prestasi & penghargaan",fields:[["name","Nama prestasi"],["organization","Pemberi / penyelenggara"],["period","Tahun"],["detail","Keterangan","textarea"]]}
    };
    const emptyState = {purpose:"pekerjaan",template:"ats",name:"",email:"",phone:"",location:"",website:"",headline:"",summary:"",skills:"",photo:"",photoShape:"rounded",photoSize:"medium",photoPosition:"right",sections:{education:[],experience:[],activities:[],projects:[],research:[],achievements:[]}};
    let state;
    try { state = {...emptyState,...JSON.parse(localStorage.getItem("cvcraft-data")||"{}")}; }
    catch (error) { console.error("Data CV tersimpan tidak dapat dibaca.",error); state = {...emptyState}; }
    state.sections = {...emptyState.sections,...(state.sections||{})};
    if(typeof state.photo!=="string"||!/^data:image\/jpeg;base64,[A-Za-z0-9+/]+=*$/.test(state.photo))state.photo="";
    if(!["square","round","rounded"].includes(state.photoShape))state.photoShape="rounded";
    if(!["small","medium","large"].includes(state.photoSize))state.photoSize="medium";
    if(!["left","right","center","sidebar"].includes(state.photoPosition))state.photoPosition="right";
    let category = "formal";
    const $ = (selector) => document.querySelector(selector);
    const escapeHtml = (value) => String(value??"").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
    function save() {
      try { localStorage.setItem("cvcraft-data",JSON.stringify(state)); $("#save-status").textContent="Tersimpan otomatis"; }
      catch (error) { $("#save-status").textContent="Gagal menyimpan"; console.error("Tidak dapat menyimpan data CV.",error); }
    }
    function renderPurposes() {
      $("#purpose").innerHTML=Object.entries(purposes).map(([id,p])=>`<option value="${id}" ${state.purpose===id?"selected":""}>${escapeHtml(p.label)}</option>`).join("");
      $("#purpose-note").textContent=purposes[state.purpose].note;
      $("#builder-purpose").textContent=purposes[state.purpose].label;
    }
    function renderMini(layout) {
      let lines='<div class="mini-title"></div><div class="mini-line"></div><div class="mini-line mid"></div><div class="mini-line short"></div><div class="mini-accent"></div><div class="mini-line"></div><div class="mini-line mid"></div>';
      if(layout==="layout-editorial"||layout==="layout-profile") return `<div class="mini-side"><div class="mini-dot"></div><div class="mini-line"></div><div class="mini-line mid"></div><div class="mini-line"></div></div><div class="mini-col">${lines}<div class="mini-line"></div></div>`;
      if(layout==="layout-portfolio") return `<div class="mini-head"></div><div class="mini-col">${lines}${lines}</div>`;
      return `<div class="mini-head"></div><div class="mini-col">${lines}${layout==="layout-classic"?"":'<div class="mini-line"></div>'}</div>`;
    }
    function renderTemplates() {
      $("#template-grid").innerHTML=templates.filter(t=>t.category===category).map(t=>`<article class="template-card ${state.template===t.id?"chosen":""}"><div class="mini ${t.layout}"><div class="mini-paper">${renderMini(t.layout)}</div></div><div class="card-body"><span class="card-kicker">${t.category==="formal"?"FORMAL":"CREATIVE"}</span><h3>${t.name}</h3><p>${t.desc}</p><div class="card-foot"><span class="badge">${t.badge}</span><button class="button ${state.template===t.id?"primary":""}" data-template="${t.id}">${state.template===t.id?"Dipilih":"Pilih Template"}</button></div></div></article>`).join("");
    }
    function fieldMarkup(key,label,value,type="text",full=false) {
      const safe=escapeHtml(value);
      return `<div class="field ${full?"full":""}"><label for="${key}">${label}</label>${type==="textarea"?`<textarea id="${key}" data-field="${key}" rows="3">${safe}</textarea>`:`<input id="${key}" data-field="${key}" value="${safe}" type="${type}" ${type==="email"?'autocomplete="email"':""}>`}</div>`;
    }
    function renderPhotoMarkup(position) {
      if(!state.photo)return "";
      return `<img class="resume-photo size-${state.photoSize} shape-${state.photoShape} position-${position}" src="${state.photo}" alt="Foto profil">`;
    }
    function renderPhotoForm() {
      const chosen=templates.find(t=>t.id===state.template)||templates[0];
      const sidebarSupported=chosen.id==="profile";
      const validPosition=sidebarSupported?state.photoPosition:(state.photoPosition==="sidebar"||!['left','right','center'].includes(state.photoPosition)?"right":state.photoPosition);
      $("#photo-preview").src=state.photo||"";
      $("#photo-preview").className=`photo-preview shape-${state.photoShape}${state.photo?" visible":""}`;
      $("#photo-preview").alt=state.photo?"Preview foto profil":"";
      $("#photo-status").textContent=state.photo?"Foto disimpan di browser sampai dihapus atau data situs dibersihkan; salinan tidak disimpan di server.":"Foto opsional. Jika tidak diunggah, CV tidak menampilkan foto atau placeholder.";
      $("#photo-upload").textContent=state.photo?"Ganti Foto":"Upload Foto";
      $("#photo-remove").classList.toggle("hidden",!state.photo);
      $("#photo-size").value=state.photoSize;
      $("#photo-shape").value=state.photoShape;
      $("#photo-position").value=validPosition;
      $("#photo-position-sidebar").disabled=!sidebarSupported;
      $("#photo-position-help").textContent=sidebarSupported?"Template ini mendukung foto di sidebar.":"Template ini memakai posisi foto di kiri, tengah, atau kanan bagian atas.";
    }
    function renderForm() {
      const core=`<div class="field-grid">${fieldMarkup("name","Nama lengkap",state.name)}${fieldMarkup("headline","Headline / posisi yang dituju",state.headline)}${fieldMarkup("email","Email",state.email,"email")}${fieldMarkup("phone","Telepon",state.phone,"tel")}${fieldMarkup("location","Kota / domisili",state.location)}${fieldMarkup("website","LinkedIn / situs / portofolio",state.website)}${fieldMarkup("summary","Profil singkat",state.summary,"textarea",true)}${fieldMarkup("skills","Keahlian (pisahkan dengan koma)",state.skills,"text",true)}</div>`;
      const photo=`<section class="photo-panel" aria-labelledby="photo-title"><h3 id="photo-title">Foto Profil (Opsional)</h3><p class="photo-help">JPG, JPEG, atau PNG · Maksimal 2 MB. Foto diproses di aplikasi dan tidak dikirim ke layanan AI.</p><div class="photo-row"><img id="photo-preview" class="photo-preview shape-${state.photoShape}" alt=""><div class="photo-form-actions"><input id="photo-file" class="hidden" type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png"><button id="photo-upload" class="button small" type="button">Upload Foto</button><button id="photo-remove" class="button small hidden" type="button">Hapus Foto</button></div></div><div class="photo-settings"><label for="photo-shape">Bentuk<select id="photo-shape"><option value="square">Persegi</option><option value="round">Bulat</option><option value="rounded">Sudut membulat</option></select></label><label for="photo-size">Ukuran<select id="photo-size"><option value="small">Kecil</option><option value="medium">Sedang</option><option value="large">Besar</option></select></label><label for="photo-position">Posisi<select id="photo-position"><option value="left">Kiri atas</option><option value="center">Tengah</option><option value="right">Kanan atas</option><option id="photo-position-sidebar" value="sidebar" ${state.template==="profile"?"":"disabled"}>Sidebar</option></select></label></div><div id="photo-position-help" class="photo-status"></div><p id="photo-status" class="photo-status"></p><p id="photo-error" class="photo-error" role="alert"></p></section>`;
      const sections=purposes[state.purpose].sections.map(key=>{const info=sectionInfo[key],entries=state.sections[key]||[];return `<section><div class="section-head"><h3>${info.title}</h3><button class="add-button" data-add="${key}">+ Tambah</button></div><div>${entries.map((entry,index)=>`<div class="entry"><div class="field-grid">${info.fields.map(([field,label,type])=>fieldMarkup(`${key}-${index}-${field}`,label,entry[field]||"",type||"text",type==="textarea")).join("")}</div><div style="text-align:right"><button class="entry-remove" data-remove="${key}:${index}">Hapus bagian ini</button></div></div>`).join("")||'<p class="empty">Belum ada data. Bagian ini opsional.</p>'}</div></section>`}).join("");
      $("#form-fields").innerHTML=core+photo+sections;
      $("#form-fields").querySelectorAll("[data-field]").forEach(el=>el.addEventListener("input",()=>{const parts=el.dataset.field.split("-");if(parts.length===1)state[parts[0]]=el.value;else{const [section,index,...field]=parts;state.sections[section][Number(index)][field.join("-")]=el.value;}save();renderPreview();}));
      renderPhotoForm();
    }
    function escapeText(value){return escapeHtml(value).replace(/\n/g,"<br>");}
    function renderSection(key) {
      const entries=state.sections[key]||[];
      if(!entries.length)return "";
      const info=sectionInfo[key];
      return `<section><h2>${info.title}</h2>${entries.map(entry=>{const title=entry.role||entry.school||entry.name||entry.degree||"Detail";const org=entry.organization||entry.degree||"";return `<div class="resume-entry"><strong>${escapeText(title)}</strong>${org?`<span class="muted"> · ${escapeText(org)}</span>`:""}${entry.period?`<span class="muted"> · ${escapeText(entry.period)}</span>`:""}${entry.link?`<p>${escapeText(entry.link)}</p>`:""}${entry.detail?`<p>${escapeText(entry.detail)}</p>`:""}</div>`}).join("")}</section>`;
    }
    function renderPreview() {
      const chosen=templates.find(t=>t.id===state.template)||templates[0];
      const contacts=[state.email,state.phone,state.location,state.website].filter(Boolean);
      const contactMarkup=contacts.length?`<div class="contact-list">${contacts.map(item=>`<span class="contact-item">${escapeText(item)}</span>`).join("")}</div>`:'<span class="muted">Tambahkan kontak di formulir</span>';
      const name=escapeText(state.name||"Nama Anda");
      const headline=state.headline?`<p class="muted">${escapeText(state.headline)}</p>`:"";
      const profile=`${state.summary?`<section><h2>Profil</h2><p>${escapeText(state.summary)}</p></section>`:""}${state.skills?`<section><h2>Keahlian</h2><p>${escapeText(state.skills.split(",").map(v=>v.trim()).filter(Boolean).join(" · "))}</p></section>`:""}`;
      const selected=purposes[state.purpose].sections;
      const sections=selected.map(renderSection).join("");
      const photoPosition = state.photoPosition === "sidebar" && chosen.id === "profile" ? "sidebar" : (['left','right','center'].includes(state.photoPosition) ? state.photoPosition : "right");
      let markup;
      if(chosen.id==="editorial"||chosen.id==="profile"){
        const photo=chosen.id==="profile"&&photoPosition==="sidebar"?`<div class="profile-photo-area">${renderPhotoMarkup("sidebar")}</div>`:renderPhotoMarkup(photoPosition);
        const side=`<aside class="resume-side">${photo}<div class="resume-side-content"><h1>${name}</h1>${headline}${contactMarkup}${profile}</div></aside>`;
        markup=`${side}<div class="resume-body">${sections||'<p class="empty">Tambahkan detail CV melalui formulir.</p>'}</div>`;
      } else if(chosen.id==="portfolio"){
        markup=`<header class="resume-head ${state.photo?"has-photo":""} ${photoPosition === "center" ? "photo-center" : ""}">${renderPhotoMarkup(photoPosition)}<div class="resume-head-content"><h1>${name}</h1>${headline}<div class="contact">${contactMarkup}</div></div></header>${profile}<div class="resume-columns">${sections}</div>`;
      } else {
        markup=`<header class="resume-head ${state.photo?"has-photo":""} ${photoPosition === "center" ? "photo-center" : ""}">${renderPhotoMarkup(photoPosition)}<div class="resume-head-content"><h1>${name}</h1>${headline}<div class="contact">${contactMarkup}</div></div></header>${profile}${sections||'<p class="empty">Tambahkan detail CV melalui formulir.</p>'}`;
      }
      const resume=$("#resume");resume.className=`resume ${chosen.layout}`;resume.innerHTML=markup;
      $("#preview-name").textContent=`${chosen.name} · ${purposes[state.purpose].label}`;
      document.title=`${state.name||"CV"} — BuildCV`;
    }
    function showBuilder() {
      $("#builder").classList.remove("hidden");$("#template-grid").classList.add("hidden");$(".toolbar").classList.add("hidden");$(".steps").classList.add("hidden");
      renderPurposes();renderForm();renderPreview();window.scrollTo({top:0,behavior:"smooth"});
    }
    function showTemplates() {
      $("#builder").classList.add("hidden");$("#template-grid").classList.remove("hidden");$(".toolbar").classList.remove("hidden");$(".steps").classList.remove("hidden");
      renderPurposes();renderTemplates();window.scrollTo({top:0,behavior:"smooth"});
    }
    function downloadPdf(){window.print();}
    $("#purpose").addEventListener("change",event=>{state.purpose=event.target.value;save();renderPurposes();if(!$("#builder").classList.contains("hidden")){renderForm();renderPreview();}});
    document.querySelectorAll(".tab").forEach(button=>button.addEventListener("click",()=>{category=button.dataset.category;document.querySelectorAll(".tab").forEach(tab=>tab.classList.toggle("selected",tab===button));renderTemplates();}));
    $("#template-grid").addEventListener("click",event=>{const button=event.target.closest("[data-template]");if(!button)return;state.template=button.dataset.template;save();showBuilder();});
    $("#change-design").addEventListener("click",showTemplates);
    $("#form-fields").addEventListener("click",event=>{if(event.target.closest("#photo-upload")){$("#photo-file").click();return;}if(event.target.closest("#photo-remove")){state.photo="";$("#photo-file").value="";$("#photo-error").textContent="";save();renderPhotoForm();renderPreview();return;}const add=event.target.closest("[data-add]");if(add){state.sections[add.dataset.add].push({});save();renderForm();renderPreview();return;}const remove=event.target.closest("[data-remove]");if(remove){const [section,index]=remove.dataset.remove.split(":");state.sections[section].splice(Number(index),1);save();renderForm();renderPreview();}});
    $("#form-fields").addEventListener("change",async event=>{
      if(event.target.id==="photo-file"){
        const file=event.target.files[0];if(!file)return;
        const allowedExtensions=["jpg","jpeg","png"],extension=file.name.split(".").pop().toLowerCase();
        const allowedTypes=["image/jpeg","image/png"];
        if(!allowedExtensions.includes(extension)||!allowedTypes.includes(file.type)){ $("#photo-error").textContent="Format tidak didukung. Pilih file JPG, JPEG, atau PNG.";event.target.value="";return; }
        if(file.size>2*1024*1024){ $("#photo-error").textContent="Ukuran foto melebihi batas 2 MB. Pilih file yang lebih kecil.";event.target.value="";return; }
        $("#photo-error").textContent="";$("#photo-status").textContent="Memproses foto…";
        try{
          const formData=new FormData();formData.append("photo",file);
          const response=await fetch("/api/profile-photo",{method:"POST",body:formData});
          const result=await response.json();
          if(!response.ok)throw new Error(result.error||"Foto tidak dapat diproses.");
          state.photo=result.photo;save();renderPhotoForm();renderPreview();
        }catch(error){$("#photo-error").textContent=error.message||"Unggah gagal. Coba file lain.";renderPhotoForm();console.error("Unggah foto profil gagal.",error);}
        finally{event.target.value="";}
        return;
      }
      if(["photo-shape","photo-size","photo-position"].includes(event.target.id)){
        const settings={"photo-shape":"photoShape","photo-size":"photoSize","photo-position":"photoPosition"};
        state[settings[event.target.id]]=event.target.value;save();renderPhotoForm();renderPreview();
      }
    });
    renderPurposes();renderTemplates();
  </script>
</body>
</html>
"""

@app.errorhandler(RequestEntityTooLarge)
def handle_oversized_request(_error):
    return jsonify(error="Ukuran unggahan melebihi batas maksimum 2 MB."), _error.code or 413


@app.get("/")
@app.get("/index.html")
def index():
    return render_template_string(HTML_PAGE)


@app.post("/api/profile-photo")
def upload_profile_photo():
    uploaded = request.files.get("photo")
    if uploaded is None or not uploaded.filename:
        return jsonify(error="Pilih foto JPG, JPEG, atau PNG terlebih dahulu."), 400

    extension = uploaded.filename.rsplit(".", 1)[-1].lower() if "." in uploaded.filename else ""
    if extension not in {"jpg", "jpeg", "png"}:
        return jsonify(error="Format tidak didukung. Pilih file JPG, JPEG, atau PNG."), 415

    content = uploaded.stream.read(MAX_PHOTO_BYTES + 1)
    if len(content) > MAX_PHOTO_BYTES:
        return jsonify(error="Ukuran foto melebihi batas 2 MB. Pilih file yang lebih kecil."), 413
    if not content:
        return jsonify(error="File foto kosong. Pilih gambar lain."), 400

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                actual_format = image.format
                if actual_format not in {"JPEG", "PNG"}:
                    return jsonify(error="Isi file bukan gambar JPG, JPEG, atau PNG yang valid."), 415
                if (actual_format == "JPEG" and extension not in {"jpg", "jpeg"}) or (
                    actual_format == "PNG" and extension != "png"
                ):
                    return jsonify(error="Ekstensi file tidak sesuai dengan format gambar sebenarnya."), 415
                if image.width * image.height > MAX_PHOTO_PIXELS:
                    return jsonify(error="Resolusi foto terlalu besar. Gunakan gambar dengan ukuran piksel lebih kecil."), 413
                image.load()
                oriented = ImageOps.exif_transpose(image)
                if oriented.mode in {"RGBA", "LA"} or "transparency" in oriented.info:
                    rgba = oriented.convert("RGBA")
                    normalized = Image.new("RGB", rgba.size, "white")
                    normalized.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    normalized = oriented.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        return jsonify(error="Gambar tidak valid atau rusak. Pilih foto JPG atau PNG yang dapat dibuka."), 415

    normalized.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
    output = BytesIO()
    normalized.save(output, format="JPEG", quality=86, optimize=True)
    while output.tell() > 1024 * 1024 and max(normalized.size) > 320:
        normalized.thumbnail((int(normalized.width * 0.8), int(normalized.height * 0.8)), Image.Resampling.LANCZOS)
        output = BytesIO()
        normalized.save(output, format="JPEG", quality=78, optimize=True)
    photo_data = "data:image/jpeg;base64," + b64encode(output.getvalue()).decode("ascii")
    return jsonify(photo=photo_data, message="Foto berhasil diproses.")


def main():
    address = "127.0.0.1"
    port = 8000
    url = f"http://{address}:{port}"
    print(f"BuildCV berjalan di {url} (tekan Ctrl+C untuk berhenti)")
    webbrowser.open(url)
    app.run(host=address, port=port, debug=False)


if __name__ == "__main__":
    main()